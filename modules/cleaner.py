import pandas as pd
import numpy as np
import re
from config.settings import (
    TECHNICAL_STATUS_PATTERNS,
    POSITIVE_CONTEXT_PATTERNS,
    EMOTIONAL_NEGATIVE_PATTERNS,
    EXPLANATION_KEYWORDS,
    AHT_MIN_SECONDS,
    AHT_MAX_SECONDS,
    STAFFING_WRAP_SECONDS,
    STAFFING_AHT_MAX_SECONDS,
    STAFFING_FALLBACK_AHT_SECONDS,
)

def parse_frt_to_seconds(val):
    """
    Parses FRT from format HH:MM:SS, string minutes, or numeric values into seconds.
    """
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    try:
        parts = val_str.split(':')
        if len(parts) == 3:
            h, m, s = int(float(parts[0])), int(float(parts[1])), int(float(parts[2]))
            return h * 3600 + m * 60 + s
        if len(parts) == 2:
            # Assume MM:SS format when only two parts are present
            m, s = int(float(parts[0])), int(float(parts[1]))
            return m * 60 + s
        # If it's a numeric value, assume it's in minutes (convert to seconds)
        return float(val_str) * 60
    except Exception:
        pass
    return None

def clean_and_validate_question(text):
    """
    Removes HTML markup, System auto-replies, and noise.
    Returns None if text is empty, too short, or noise.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    
    # Remove HTML tags & comments
    clean = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = re.sub(r'\|\|\d+', '', clean)
    clean = re.sub(r'\|\|', ' ', clean)
    
    # Remove system messages
    clean = re.sub(r'System:\s*Customer telah mengakhiri percakapan.*', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'Silakan tinggalkan pertanyaan Anda.*', '', clean, flags=re.IGNORECASE)
    clean = clean.strip()
    
    # Verify word count and length
    words = [w for w in re.findall(r'\b[a-zA-Z]{2,}\b', clean) if not w.isdigit()]
    if len(words) < 3 or len(clean) < 10:
        return None
        
    return clean

def reclassify_sentiment(text, original_label, original_score=0):
    """
    Reclassifies sentiment based on text context (heuristics).
    """
    if not isinstance(text, str) or not text.strip():
        return original_label
    
    text_lower = text.lower()
    has_emotional_neg = any(pattern in text_lower for pattern in EMOTIONAL_NEGATIVE_PATTERNS)
    has_positive_ctx = any(pattern in text_lower for pattern in POSITIVE_CONTEXT_PATTERNS)
    
    if has_positive_ctx and not has_emotional_neg:
        return 'positive'
    if has_emotional_neg:
        return 'negative'
    return original_label


def _parse_report_datetime(series):
    """Parse Monev datetime strings (UTC) and convert to WIB."""
    raw_values = series.astype(str).str.strip()
    parsed = pd.to_datetime(raw_values, format='%Y-%m-%d %H.%M.%S', errors='coerce', utc=True)
    nan_mask = parsed.isna() & series.notna()
    if nan_mask.any():
        fallback = raw_values.loc[nan_mask].str.replace(r'\.', ':', regex=True)
        parsed.loc[nan_mask] = pd.to_datetime(fallback, errors='coerce', utc=True)
    nan_mask = parsed.isna() & series.notna()
    if nan_mask.any():
        parsed.loc[nan_mask] = pd.to_datetime(raw_values.loc[nan_mask], errors='coerce', utc=True)
    return parsed.dt.tz_convert('Asia/Jakarta')


def compute_handle_seconds(df):
    """
    Average Handle Time (detik): durasi penanganan tiket.
    Prioritas: Closed - Created; jika 0 (live chat), gunakan Closed - Date Distribute.
    """
    if 'Closed Date' not in df.columns:
        return pd.Series(np.nan, index=df.index)

    closed_created = (df['Closed Date'] - df['Created Date']).dt.total_seconds() if 'Created Date' in df.columns else pd.Series(np.nan, index=df.index)
    handle = closed_created.copy()

    if 'Date Distribute' in df.columns:
        closed_distribute = (df['Closed Date'] - df['Date Distribute']).dt.total_seconds()
        use_fallback = handle.isna() | (handle <= 0)
        handle = handle.where(~use_fallback, closed_distribute)

    handle = handle.where((handle >= AHT_MIN_SECONDS) & (handle <= AHT_MAX_SECONDS))
    return handle


def compute_staffing_handle_seconds(df):
    """
    Durasi handle operasional per tiket untuk model staffing.
    Live chat (Created=Closed): FRT + wrap-up agen.
    Email/ticket lain: min(Closed−Created atau Closed−Distribute, cap 20 menit).
    """
    frt = df['frt_seconds'] if 'frt_seconds' in df.columns else pd.Series(np.nan, index=df.index)
    handle = compute_handle_seconds(df)

    if 'Created Date' in df.columns and 'Closed Date' in df.columns:
        closed_created = (df['Closed Date'] - df['Created Date']).dt.total_seconds()
        if (closed_created.fillna(-1) <= 0).mean() > 0.5:
            staffing = frt.fillna(0) + STAFFING_WRAP_SECONDS
            return staffing.clip(lower=AHT_MIN_SECONDS)

    staffing = handle.clip(upper=STAFFING_AHT_MAX_SECONDS)
    fallback = frt.fillna(0) + STAFFING_WRAP_SECONDS
    staffing = staffing.fillna(fallback)
    staffing = staffing.where(staffing > 0, fallback)
    return staffing.clip(lower=AHT_MIN_SECONDS)


def clean_dataframe(df):
    """
    Applies parsing, filtering, cleaning, and sentiment setup.
    """
    df = df.copy()
    
    # 1. Date parsing (UTC report timestamps -> WIB)
    date_cols = ['Created Date', 'Closed Date', 'Date Distribute']
    for col in date_cols:
        if col in df.columns:
            df[col] = _parse_report_datetime(df[col])

    if 'Created Date' in df.columns:
        df['created_dt_wib'] = df['Created Date']
        df['created_date_only'] = df['Created Date'].dt.date
        df['hour'] = df['Created Date'].dt.hour
        df['day_name'] = df['Created Date'].dt.day_name()
        df['day_of_week'] = df['Created Date'].dt.dayofweek  # 0=Monday, 6=Sunday
    else:
        df['created_dt_wib'] = pd.NaT
        df['created_date_only'] = None
        df['hour'] = None
        df['day_name'] = None
        df['day_of_week'] = None
        
    # 2. FRT parsing to seconds
    if 'FRT' in df.columns:
        df['frt_seconds'] = df['FRT'].apply(parse_frt_to_seconds)
    else:
        df['frt_seconds'] = np.nan

    df['handle_seconds'] = compute_handle_seconds(df)
    df['staffing_handle_seconds'] = compute_staffing_handle_seconds(df)
        
    # 3. Clean 'Pertanyaan' & filter out noise records
    if 'Pertanyaan' in df.columns:
        # Keep clean version
        df['pertanyaan_clean'] = df['Pertanyaan'].apply(clean_and_validate_question)
        # Filter out records where clean text is None
        df = df[df['pertanyaan_clean'].notna()].copy()
    else:
        df['pertanyaan_clean'] = ""
        
    # 4. Sentiment processing
    # If the file lacks sentiment column, we assign a rule-based sentiment
    if 'sentiment' not in df.columns:
        # Let's perform keyword-based heuristic classification
        def heuristic_sentiment(text):
            if not isinstance(text, str):
                return 'neutral'
            t_low = text.lower()
            if any(w in t_low for w in EMOTIONAL_NEGATIVE_PATTERNS):
                return 'negative'
            if any(w in t_low for w in POSITIVE_CONTEXT_PATTERNS):
                return 'positive'
            return 'neutral'
            
        df['sentiment'] = df['pertanyaan_clean'].apply(heuristic_sentiment)
        df['sentiment_original'] = df['sentiment']
    else:
        # Normalization and reclassification
        df['sentiment'] = df['sentiment'].str.lower()
        df['sentiment_original'] = df['sentiment']
        df['sentiment'] = df.apply(
            lambda r: reclassify_sentiment(r['pertanyaan_clean'], r['sentiment']),
            axis=1
        )
        
    return df
