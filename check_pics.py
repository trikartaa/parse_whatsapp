import pandas as pd
import os

files = [
    "web/Data Follow Up Trikarta Malang - April 2026.csv",
    "web/Data Follow Up Trikarta NGAGEL Surabaya - April 2026.csv",
    "web/Data Follow Up Trikarta PAKUWON Surabaya - April 2026.csv",
    "web/Data Follow Up Trikarta ROYAL Surabaya - April 2026.csv"
]

for f in files:
    if os.path.exists(f):
        try:
            df = pd.read_csv(f, encoding='latin1')
            # Kolom admin biasanya ada di indeks ke-10 (kolom ke-11)
            # Tapi kita bersihkan dulu nama kolomnya agar lebih pasti
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            admin_col = None
            for col in df.columns:
                if 'admin' in col:
                    admin_col = col
                    break
            
            if admin_col:
                pics = df[admin_col].dropna().unique()
                print(f"{os.path.basename(f)}:")
                for p in pics:
                    if str(p).strip():
                        print(f"  - {p}")
            else:
                print(f"{os.path.basename(f)}: Kolom admin tidak ditemukan")
        except Exception as e:
            print(f"{os.path.basename(f)}: Error membaca file - {e}")
    else:
        print(f"{os.path.basename(f)}: File tidak ditemukan")
