import pandas as pd
import re
import warnings
import datetime

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

def normalize_phone(phone):
    if pd.isna(phone):
        return None
    
    # If it's a float (common in Excel), convert to int first to avoid .0
    if isinstance(phone, float):
        s = str(int(phone))
    else:
        s = str(phone)
        
    # Remove any non-digit characters
    s = re.sub(r'\D', '', s)
    
    if not s:
        return None

    # Normalize to 62 format
    if s.startswith('0'):
        s = '62' + s[1:]
    elif s.startswith('62'):
        pass # Already in 62 format
    elif s.startswith('8'):
        # If it starts with 8 (typical for Indonesian mobile numbers without 0/62), prepend 62
        s = '62' + s
        
    return s

def clean_marketing_name(name):
    if pd.isna(name):
        return "Unknown"
    name = str(name).upper()
    # Remove specific keywords as requested
    for word in ['BARAT', 'MLG', 'ROYAL']:
        name = name.replace(word, '')
    return name.strip().capitalize()

def parse_date(val):
    if pd.isna(val):
        return pd.NaT
    if isinstance(val, (pd.Timestamp, datetime.datetime)):
        return val
    
    s = str(val).lower()
    # Mapping bulan Indonesia ke Inggris
    months = {
        'januari': 'January', 'februari': 'February', 'maret': 'March',
        'april': 'April', 'mei': 'May', 'juni': 'June',
        'juli': 'July', 'agustus': 'August', 'september': 'September',
        'oktober': 'October', 'november': 'November', 'desember': 'December',
        'jan': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'apr': 'Apr', 'mei': 'May',
        'jun': 'Jun', 'jul': 'Jul', 'ags': 'Aug', 'sep': 'Sep', 'okt': 'Oct',
        'nov': 'Nov', 'des': 'Dec'
    }
    for indo, eng in months.items():
        if indo in s:
            s = s.replace(indo, eng)
            break
            
    # Jika tidak ada tahun, tambahkan 2026
    if not re.search(r'\d{4}', s):
        # Coba deteksi format d-m atau d m
        s = s + '-2026'
        
    return pd.to_datetime(s, errors='coerce')

# Kolom yang digunakan:
# CSV (MASTER): Marketing, Nomor Klien, Tanggal Chat, Status Custoimer, Status, Channel
# EXCEL (DATA WA): Nama Sheet (sebagai Marketing), NO. HP, TGL

def main():
    print("Membaca data...")
    
    # 1. Load CSV
    try:
        csv_df = pd.read_csv('Dashboard KPI Whatsapp - MASTER_DATA.csv')
    except Exception as e:
        print(f"Error membaca CSV: {e}")
        return

    csv_df['Tanggal Chat'] = pd.to_datetime(csv_df['Tanggal Chat'], dayfirst=True, errors='coerce')
    csv_df['normalized_phone'] = csv_df['Nomor Klien'].apply(normalize_phone)
    csv_df['clean_marketing'] = csv_df['Marketing'].apply(clean_marketing_name)

    # Filter May 2026 + Status Customer == New + Status == Lead + Channel in [Instagram, Tiktok]
    csv_may = csv_df[
        (csv_df['Tanggal Chat'].dt.month == 5) & 
        (csv_df['Tanggal Chat'].dt.year == 2026) &
        (csv_df['Status Custoimer'] == 'New') &
        (csv_df['Status'] == 'Lead') &
        (csv_df['Channel'].isin(['Instagram', 'Tiktok']))
    ]
    
    # 2. Load Excel
    # Coba kedua kemungkinan nama file
    excel_file = 'data wa marketing.xlsx'
    import os
    if not os.path.exists(excel_file):
        excel_file = 'data wa marketing (4).xlsx'
        
    try:
        xl = pd.ExcelFile(excel_file)
    except Exception as e:
        print(f"Error membaca Excel ({excel_file}): {e}")
        return

    excel_data = []
    for sheet in xl.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet)
        if 'TGL' not in df.columns or 'NO. HP' not in df.columns:
            continue
            
        # Perbaikan: Lakukan forward-fill pada kolom TGL untuk menangani data yang kosong 
        # (biasanya tanggal hanya ditulis sekali untuk beberapa baris di bawahnya)
        df['TGL'] = df['TGL'].ffill()
            
        # Gunakan parser baru yang menangani bahasa Indonesia
        df['TGL_parsed'] = df['TGL'].apply(parse_date)
        df['normalized_phone'] = df['NO. HP'].apply(normalize_phone)
        
        # Filter May 2026
        df_may = df[(df['TGL_parsed'].dt.month == 5) & (df['TGL_parsed'].dt.year == 2026)].copy()
        
        marketing = clean_marketing_name(sheet)
        df_may['clean_marketing'] = marketing
        excel_data.append(df_may[['clean_marketing', 'normalized_phone']])

    if not excel_data:
        print("Tidak ada data valid di Excel untuk Mei 2026.")
        excel_may = pd.DataFrame(columns=['clean_marketing', 'normalized_phone'])
    else:
        excel_may = pd.concat(excel_data)

    # 3. Compare sets of (Marketing, Phone)
    csv_set = set(zip(csv_may['clean_marketing'], csv_may['normalized_phone']))
    excel_set = set(zip(excel_may['clean_marketing'], excel_may['normalized_phone']))

    # Remove entries where phone is None or empty
    csv_set = {x for x in csv_set if x[1]}
    excel_set = {x for x in excel_set if x[1]}

    # Results sets
    both = csv_set.intersection(excel_set)
    only_csv = csv_set - excel_set
    only_excel = excel_set - csv_set

    # 4. Output
    all_marketings = sorted(list(set([x[0] for x in csv_set.union(excel_set)])))
    
    print("\n" + "="*50)
    print(f"HASIL PERBANDINGAN DATA MARKETING - MEI 2026 (Filtrasi: New, Lead, IG/Tiktok)")
    print("="*50)

    for m in all_marketings:
        m_both = sorted([x[1] for x in both if x[0] == m])
        m_only_csv = sorted([x[1] for x in only_csv if x[0] == m])
        m_only_excel = sorted([x[1] for x in only_excel if x[0] == m])
        
        if not (m_both or m_only_csv or m_only_excel):
            continue

        print(f"\n> MARKETING: {m}")
        print(f"  [SAMA DI KEDUANYA] - {len(m_both)} nomor:")
        if m_both:
            for p in m_both: print(f"    - {p}")
        else:
            print("    (kosong)")

        print(f"  [HANYA DI CSV (MASTER)] - {len(m_only_csv)} nomor:")
        if m_only_csv:
            for p in m_only_csv: print(f"    - {p}")
        else:
            print("    (kosong)")

        print(f"  [HANYA DI EXCEL (DATA WA)] - {len(m_only_excel)} nomor:")
        if m_only_excel:
            for p in m_only_excel: print(f"    - {p}")
        else:
            print("    (kosong)")
    
    print("\n" + "="*50)
    print(f"TOTAL UNIK CSV (IG/Tiktok, New, Lead): {len(csv_set)}")
    print(f"TOTAL UNIK EXCEL: {len(excel_set)}")
    print(f"TOTAL SAMA: {len(both)}")
    print("="*50)

if __name__ == "__main__":
    main()
