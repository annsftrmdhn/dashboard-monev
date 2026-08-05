import pandas as pd
import numpy as np
from collections import Counter

from config.settings import (
    DEFAULT_SLA_THRESHOLD,
    TARGET_OCCUPANCY,
    EXPLANATION_KEYWORDS,
    STAFFING_FALLBACK_AHT_SECONDS,
)


def _mean_frt_minutes(df):
    """Rata-rata FRT/ASA (menit) dari kolom frt_seconds."""
    if 'frt_seconds' not in df.columns:
        return 0.0
    valid = df['frt_seconds'].dropna()
    return (valid.mean() / 60) if len(valid) > 0 else 0.0


def _mean_aht_minutes(df):
    """
    Rata-rata AHT (menit): durasi penanganan tiket.
    Menggunakan handle_seconds dari cleaner (Closed-Created atau Closed-Date Distribute).
    """
    if 'handle_seconds' in df.columns:
        valid = df['handle_seconds'].dropna()
        if len(valid) > 0:
            return valid.mean() / 60

    if 'Created Date' in df.columns and 'Closed Date' in df.columns:
        handle = (df['Closed Date'] - df['Created Date']).dt.total_seconds()
        valid = handle[(handle > 0) & (handle <= 24 * 3600)]
        if len(valid) > 0:
            return valid.mean() / 60
    return 0.0


def _staffing_aht_seconds(df):
    """
    AHT operasional (detik) untuk model staffing — terpisah dari KPI AHT.
    Menggunakan staffing_handle_seconds dari cleaner.
    """
    if 'staffing_handle_seconds' in df.columns:
        valid = df['staffing_handle_seconds'].dropna()
        if len(valid) > 0:
            return float(valid.median()), 'staffing_handle'

    if 'frt_seconds' in df.columns:
        valid = df['frt_seconds'].dropna()
        if len(valid) > 0:
            from config.settings import STAFFING_WRAP_SECONDS
            return float(valid.median()) + STAFFING_WRAP_SECONDS, 'frt_wrap_fallback'

    return float(STAFFING_FALLBACK_AHT_SECONDS), 'constant_fallback'


def calculate_kpi_metrics(df, sla_threshold=DEFAULT_SLA_THRESHOLD):
    """Metrik KPI utama — sumber tunggal untuk seluruh dashboard & export."""
    total_tickets = len(df)
    if total_tickets == 0:
        return {
            'total_tickets': 0,
            'asa_minutes': 0.0,
            'frt_minutes': 0.0,
            'service_level': 0.0,
            'resolution_rate': 0.0,
            'resolution_rate_pct': 0.0,
            'aht_minutes': 0.0,
            'avg_contacts_per_agent': 0.0,
        }

    valid_frt = df['frt_seconds'].dropna() if 'frt_seconds' in df.columns else pd.Series(dtype=float)
    frt_minutes = _mean_frt_minutes(df)
    asa_minutes = frt_minutes  # ASA = rata-rata waktu hingga respons pertama (FRT)

    if len(valid_frt) > 0:
        service_level = (valid_frt <= sla_threshold).sum() / len(valid_frt) * 100
    else:
        service_level = 0.0

    closed_statuses = ['closed', 'resolved', 'selesai']
    status_series = df['Ticket Status'].astype(str).str.lower()
    closed_count = status_series.isin(closed_statuses).sum()
    resolution_rate = closed_count / total_tickets
    resolution_rate_pct = resolution_rate * 100

    aht_minutes = _mean_aht_minutes(df)

    if 'First Response Agent' in df.columns:
        agent_counts = df['First Response Agent'].dropna().value_counts()
        avg_contacts = agent_counts.mean() if len(agent_counts) > 0 else 0.0
    else:
        avg_contacts = 0.0

    return {
        'total_tickets': total_tickets,
        'asa_minutes': asa_minutes,
        'frt_minutes': frt_minutes,
        'service_level': service_level,
        'resolution_rate': resolution_rate,
        'resolution_rate_pct': resolution_rate_pct,
        'aht_minutes': aht_minutes,
        'avg_contacts_per_agent': avg_contacts,
    }


def get_metrics_formula_table(
    kpis,
    sla_threshold=DEFAULT_SLA_THRESHOLD,
    target_occupancy=TARGET_OCCUPANCY,
    staffing=None,
):
    """Tabel referensi rumus metrik call center (sinkron dengan perhitungan dashboard)."""
    sla_min = sla_threshold / 60

    staffing_value = '(lihat tab Volume & Staffing)'
    staffing_aht_value = '(lihat tab Volume & Staffing)'
    if staffing:
        staffing_value = (
            f"{staffing['agents_needed']} agen @ jam {staffing['peak_hour']:02d}:00 "
            f"({staffing['peak_volume']} tiket/jam, occupancy {staffing['target_occupancy']:.0%})"
        )
        staffing_aht_value = f"{staffing['aht_minutes']:.2f} menit ({staffing['aht_method_label']})"

    return pd.DataFrame([
        {
            'Metrik': 'Volume Tiket',
            'Rumus / Definisi': 'COUNT(tiket valid setelah cleaning)',
            'Nilai Dashboard': f"{kpis['total_tickets']:,}",
        },
        {
            'Metrik': 'ASA (Average Speed of Answer)',
            'Rumus / Definisi': 'AVG(FRT) — rata-rata waktu tunggu hingga respons pertama agen',
            'Nilai Dashboard': f"{kpis['asa_minutes']:.2f} menit",
        },
        {
            'Metrik': 'FRT (First Response Time)',
            'Rumus / Definisi': 'AVG(FRT) — sama dengan ASA; diambil dari kolom FRT report Monev',
            'Nilai Dashboard': f"{kpis['frt_minutes']:.2f} menit",
        },
        {
            'Metrik': 'Service Level (SL)',
            'Rumus / Definisi': f'% tiket dengan FRT ≤ {sla_threshold} detik ({sla_min:.0f} menit)',
            'Nilai Dashboard': f"{kpis['service_level']:.1f}%",
        },
        {
            'Metrik': 'Resolution Rate',
            'Rumus / Definisi': '% tiket berstatus Closed / Resolved / Selesai',
            'Nilai Dashboard': f"{kpis['resolution_rate_pct']:.1f}%",
        },
        {
            'Metrik': 'AHT (Average Handle Time)',
            'Rumus / Definisi': 'AVG(Closed − Created); jika 0 → AVG(Closed − Date Distribute) — metrik KPI resolusi',
            'Nilai Dashboard': f"{kpis['aht_minutes']:.2f} menit",
        },
        {
            'Metrik': 'Staffing AHT (operasional)',
            'Rumus / Definisi': 'Live chat: MEDIAN(FRT + wrap-up); Email: MEDIAN(min(handle, 20 menit))',
            'Nilai Dashboard': staffing_aht_value,
        },
        {
            'Metrik': 'Kontak per Agen',
            'Rumus / Definisi': 'AVG(jumlah tiket per First Response Agent)',
            'Nilai Dashboard': f"{kpis['avg_contacts_per_agent']:.1f}",
        },
        {
            'Metrik': 'Kebutuhan Agen (Staffing)',
            'Rumus / Definisi': f'CEIL(Vol_jam_sibuk × Staffing_AHT / (3600 × Occupancy)); Occupancy={target_occupancy:.0%}',
            'Nilai Dashboard': staffing_value,
        },
    ])


_STAFFING_METHOD_LABELS = {
    'staffing_handle': 'FRT + wrap-up atau handle terbatas',
    'frt_wrap_fallback': 'FRT + wrap-up (fallback)',
    'constant_fallback': 'nilai default 10 menit',
}


def get_peak_hour_staffing(df, kpis, target_occupancy=TARGET_OCCUPANCY):
    """
    Estimasi agen pada jam sibuk berdasarkan volume masuk per jam dan AHT.
    Returns dict dengan detail perhitungan atau None jika data jam tidak ada.
    """
    if 'hour' not in df.columns or df['hour'].isna().all():
        return None

    hourly = df.groupby('hour').size().reset_index(name='volume')
    if hourly.empty:
        return None

    peak = hourly.loc[hourly['volume'].idxmax()]
    peak_hour = int(peak['hour'])
    peak_volume = int(peak['volume'])

    aht_seconds, aht_method = _staffing_aht_seconds(df)
    agents = estimate_agents_needed(peak_volume, aht_seconds, target_occupancy)

    return {
        'peak_hour': peak_hour,
        'peak_volume': peak_volume,
        'aht_seconds': aht_seconds,
        'aht_minutes': aht_seconds / 60,
        'aht_method': aht_method,
        'aht_method_label': _STAFFING_METHOD_LABELS.get(aht_method, aht_method),
        'kpi_aht_minutes': kpis['aht_minutes'],
        'used_fallback_aht': aht_method == 'constant_fallback',
        'target_occupancy': target_occupancy,
        'agents_needed': agents,
    }


def get_site_scorecard(df, sla_threshold=DEFAULT_SLA_THRESHOLD):
    """Scorecard per site — memakai calculate_kpi_metrics yang sama."""
    if 'Site Name' not in df.columns:
        return pd.DataFrame()

    scorecard_data = []
    for site in df['Site Name'].dropna().unique():
        site_df = df[df['Site Name'] == site]
        kpis = calculate_kpi_metrics(site_df, sla_threshold)

        s_counts = site_df['sentiment'].astype(str).str.lower().value_counts()
        total = len(site_df)
        neg_pct = (s_counts.get('negative', 0) / total * 100) if total > 0 else 0.0
        pos_pct = (s_counts.get('positive', 0) / total * 100) if total > 0 else 0.0

        scorecard_data.append({
            'Site': site,
            'Total Tickets': kpis['total_tickets'],
            'ASA (min)': round(kpis['asa_minutes'], 2),
            'FRT (min)': round(kpis['frt_minutes'], 2),
            'Service Level (%)': round(kpis['service_level'], 1),
            'Resolution Rate (%)': round(kpis['resolution_rate_pct'], 1),
            'AHT (min)': round(kpis['aht_minutes'], 2),
            'Neg Sentimen (%)': round(neg_pct, 1),
            'Pos Sentimen (%)': round(pos_pct, 1),
        })

    return pd.DataFrame(scorecard_data)


def get_top_negative_category_insights(df, top_n=4):
    """Returns insight data for the top N categories with the most negative sentiment tickets."""
    if 'Category' not in df.columns or 'sentiment' not in df.columns:
        return []

    neg_df = df[df['sentiment'].astype(str).str.lower() == 'negative'].copy()
    if neg_df.empty:
        return []

    neg_df['Category'] = neg_df['Category'].fillna('Unknown')
    counts = neg_df.groupby('Category').size().reset_index(name='Negative Count')
    top_categories = counts.sort_values('Negative Count', ascending=False).head(top_n)

    negative_keywords = [kw.lower() for kw in EXPLANATION_KEYWORDS.get('negatif', [])]
    insights = []

    for _, row in top_categories.iterrows():
        category = row['Category']
        category_rows = neg_df[neg_df['Category'] == category]
        texts = category_rows['pertanyaan_clean'].dropna().astype(str).tolist()
        if not texts and 'Pertanyaan' in category_rows.columns:
            texts = category_rows['Pertanyaan'].dropna().astype(str).tolist()

        keyword_counts = Counter()
        for text in texts:
            lower_text = text.lower()
            for kw in negative_keywords:
                if kw in lower_text:
                    keyword_counts[kw] += 1

        top_keywords = [kw for kw, _ in keyword_counts.most_common(4)]
        keywords = ', '.join(top_keywords) if top_keywords else 'tidak tersedia'

        sample_question = ''
        if texts:
            sample_question = next((q for q in texts if q.strip()), texts[0])
        if not sample_question and 'Pertanyaan' in category_rows.columns:
            sample_question = category_rows['Pertanyaan'].dropna().astype(str).head(1).squeeze()

        sample_question = str(sample_question).replace('\n', ' ').strip()
        if len(sample_question) > 120:
            sample_question = sample_question[:117].rstrip() + '...'

        ticket_number = ''
        if 'Ticket Number' in category_rows.columns:
            ticket_number = category_rows['Ticket Number'].dropna().astype(str).tolist()
            ticket_number = next((t for t in ticket_number if t.strip()), '')

        insights.append({
            'Category': category,
            'Negative Count': int(row['Negative Count']),
            'Keywords': keywords,
            'Sample Question': sample_question or 'tidak tersedia',
            'Sample Ticket': ticket_number or 'tidak tersedia',
        })

    return insights


def estimate_agents_needed(volume_per_hour, aht_seconds, target_occupancy=TARGET_OCCUPANCY):
    """
    Staffing model (Erlang simplified):
    agents = (volume_per_hour × aht_seconds) / (3600 × target_occupancy)
    """
    if volume_per_hour <= 0 or aht_seconds <= 0 or target_occupancy <= 0:
        return 1
    workload_seconds = volume_per_hour * aht_seconds
    agents_needed = workload_seconds / (3600.0 * target_occupancy)
    return max(1, int(np.ceil(agents_needed)))
