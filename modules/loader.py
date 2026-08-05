import pandas as pd
import io

def detect_delimiter_and_encoding(file_source):
    """
    Detects the encoding and separator of a CSV file by reading a small chunk.
    Works for both file paths and file-like objects (e.g. Streamlit UploadedFile).
    """
    encodings = ['utf-8', 'latin1', 'cp1252']
    separators = [';', ',']
    
    # Read bytes first
    if hasattr(file_source, 'read'):
        # For BytesIO / UploadedFile
        content_bytes = file_source.read(10000)
        file_source.seek(0)  # Reset pointer
    else:
        # For file path string
        with open(file_source, 'rb') as f:
            content_bytes = f.read(10000)
            
    # Try decoding
    detected_encoding = 'utf-8'
    decoded_str = ""
    for enc in encodings:
        try:
            decoded_str = content_bytes.decode(enc)
            detected_encoding = enc
            break
        except Exception:
            continue
            
    # If decoding failed completely, fall back to latin1
    if not decoded_str:
        decoded_str = content_bytes.decode('latin1', errors='ignore')
        detected_encoding = 'latin1'
        
    # Detect separator
    detected_sep = ';'
    first_line = decoded_str.split('\n')[0]
    if first_line.count(',') > first_line.count(';'):
        detected_sep = ','
        
    return detected_sep, detected_encoding

def load_and_validate_csv(file_source):
    """
    Loads a CSV file into a Pandas DataFrame and normalizes column headers.
    Returns (df, error_msg). If valid, error_msg is None.
    """
    try:
        # Support Excel files (UploadedFile or file path)
        filename = None
        if hasattr(file_source, 'name'):
            filename = str(file_source.name).lower()
        elif isinstance(file_source, str):
            filename = file_source.lower()

        if filename and (filename.endswith('.xlsx') or filename.endswith('.xls')):
            # pandas can read file-like objects and paths for Excel
            if hasattr(file_source, 'seek'):
                file_source.seek(0)
            df = pd.read_excel(file_source)
        else:
            sep, encoding = detect_delimiter_and_encoding(file_source)
            
            if hasattr(file_source, 'seek'):
                file_source.seek(0)
                
            try:
                df = pd.read_csv(file_source, sep=sep, encoding=encoding)
            except (UnicodeDecodeError, Exception):
                if hasattr(file_source, 'seek'):
                    file_source.seek(0)
                try:
                    df = pd.read_csv(file_source, sep=sep, encoding='latin1')
                except Exception:
                    if hasattr(file_source, 'seek'):
                        file_source.seek(0)
                    df = pd.read_csv(file_source, sep=sep, encoding='cp1252', errors='replace')
        
        # Clean column names (strip spaces, normalize case)
        original_cols = df.columns.tolist()
        df.columns = [str(col).strip() for col in df.columns]
        
        # Required columns mapping (flexible match)
        required_mappings = {
            'Ticket Number': ['ticket number', 'ticket_number', 'no tiket', 'no_tiket'],
            'Category': ['category', 'kategori'],
            'Sub Category': ['sub category', 'sub_category', 'subkategori', 'sub kategori'],
            'Pertanyaan': ['pertanyaan', 'text', 'question', 'text_clean'],
            'Ticket Status': ['ticket status', 'status', 'ticket_status'],
            'Site Name': ['site name', 'site', 'site_name', 'kantor'],
            'Created Date': ['created date', 'created_date', 'tanggal dibuat', 'ticket created', 'ticket_open_date', 'open date'],
            'Closed Date': ['closed date', 'closed_date', 'tanggal selesai', 'ticket closed', 'ticket_close_date', 'close date'],
            'Date Distribute': ['date distribute', 'date_distribute', 'tanggal distribute', 'tanggal distribusi'],
            'First Response Agent': ['first response agent', 'agent', 'petugas'],
            'FRT': ['frt', 'first response time', 'response time', 'respon time']
        }
        
        found_cols = {}
        used_cols = set()
        missing_cols = []
        
        for standard_name, synonyms in required_mappings.items():
            match = None
            # Check for synonyms in order of preference
            for syn in synonyms:
                for col in df.columns:
                    if col.lower() == syn and col not in used_cols:
                        match = col
                        break
                if match:
                    break
            
            if match:
                found_cols[standard_name] = match
                used_cols.add(match)
            else:
                missing_cols.append(standard_name)
                
        # If crucial columns are missing, return error
        critical_missing = [col for col in ['Ticket Number', 'Created Date', 'FRT', 'Ticket Status'] if col in missing_cols]
        if critical_missing:
            return None, f"Kolom wajib berikut tidak ditemukan: {', '.join(critical_missing)}. Kolom terdeteksi: {original_cols}"
            
        # Rename columns to standard names
        rename_dict = {v: k for k, v in found_cols.items()}
        df = df.rename(columns=rename_dict)
        
        return df, None
        
    except Exception as e:
        return None, f"Gagal membaca file: {str(e)}"
