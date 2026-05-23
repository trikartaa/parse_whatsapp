import pandas as pd
import re
import warnings
from datetime import datetime

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

def normalize_phone(phone):
    if pd.isna(phone):
        return None
    
    # Konversi ke string tanpa notasi ilmiah (e+12)
    if isinstance(phone, (float, int)):
        s = "{:.0f}".format(phone)
    else:
        s = str(phone).strip()
        if s.endswith('.0'):
            s = s[:-2]
            
    # Ambil hanya angka
    s = re.sub(r'\D', '', s)
    
    if not s:
        return None

    # Normalisasi ke format 62
    if s.startswith('0'):
        s = '62' + s[1:]
    elif s.startswith('8'):
        s = '62' + s
    # Jika sudah 62, biarkan
    
    return s

def main():
    print("="*65)
    print("   KHUSUS MEI 2026: WEB (NEW) VS DATA FOLLOW UP")
    print("="*65)
    
    # 1. Load Web Ngagel - Vegy.csv
    master_file = 'Web Ngagel - Vegy.csv'
    try:
        master_df = pd.read_csv(master_file)
        # Paksa parsing tanggal
        master_df['Tanggal Chat'] = pd.to_datetime(master_df['Tanggal Chat'], dayfirst=True, errors='coerce')
        
        # FILTER KETAT MEI 2026
        # Catatan: Channel bisa 'Web' atau 'Tidak Diketahui'
        mask_master = (
            (master_df['Tanggal Chat'].dt.month == 5) & 
            (master_df['Tanggal Chat'].dt.year == 2026) &
            (master_df['Channel'].isin(['Web', 'Tidak Diketahui'])) &
            (master_df['Status'] == 'Lead') &
            (master_df['Status Custoimer'] == 'New')
        )
        qualified_leads = master_df[mask_master].copy()
        qualified_leads['norm_phone'] = qualified_leads['Nomor Klien'].apply(normalize_phone)
        master_set = set(qualified_leads['norm_phone'].dropna())
    except Exception as e:
        print(f"Error master: {e}")
        return

    # 2. Load Data Follow Up
    followup_file = 'Data Follow Up Trikarta NGAGEL Surabaya - April 2026.csv'
    try:
        fu_df = pd.read_csv(followup_file)
        date_col = fu_df.columns[0]
        fu_df[date_col] = pd.to_datetime(fu_df[date_col], dayfirst=True, errors='coerce')
        
        # FILTER KETAT MEI 2026
        mask_fu = (
            (fu_df[date_col].dt.month == 5) & 
            (fu_df[date_col].dt.year == 2026)
        )
        fu_may = fu_df[mask_fu].copy()
        fu_may['norm_phone'] = fu_may['NO HP'].apply(normalize_phone)
        fu_set = set(fu_may['norm_phone'].dropna())
    except Exception as e:
        print(f"Error follow-up: {e}")
        return

    # 3. Analisis
    matching = master_set.intersection(fu_set)
    only_web = master_set - fu_set
    only_fu = fu_set - master_set
    
    # 4. Tampilan
    print(f"Total Lead Web (New) Mei 2026  : {len(master_set)}")
    print(f"Total Follow Up Mei 2026       : {len(fu_set)}")
    print("-" * 65)
    
    if matching:
        print(f"\n[v] NOMOR YANG SAMA (MEI 2026): {len(matching)}")
        for phone in sorted(list(matching)):
            print(f"- {phone}")

    if only_web:
        print(f"\n[!] HANYA DI WEB (BELUM FOLLOW UP - MEI 2026): {len(only_web)}")
        for phone in sorted(list(only_web)):
            print(f"- {phone}")

    if only_fu:
        print(f"\n[?] HANYA DI FOLLOW UP (MEI 2026): {len(only_fu)}")
        for phone in sorted(list(only_fu)):
            print(f"- {phone}")

if __name__ == "__main__":
    main()
