import pandas as pd
import os

# Daftar file yang akan digabungkan
files = [
    r"web/Data Follow Up Trikarta Malang - April 2026.csv",
    r"web/Data Follow Up Trikarta NGAGEL Surabaya - April 2026.csv",
    r"web/Data Follow Up Trikarta PAKUWON Surabaya - April 2026.csv",
    r"web/Data Follow Up Trikarta ROYAL Surabaya - April 2026.csv"
]

all_df = []
for f in files:
    if os.path.exists(f):
        # Menggunakan encoding utf-8 atau latin1 jika ada error
        try:
            df = pd.read_csv(f, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(f, encoding='latin1')
            
        # Standarisasi nama kolom (menghapus spasi di awal/akhir dan kapitalisasi)
        df.columns = [c.strip() for c in df.columns]
        all_df.append(df)
        print(f"Berhasil membaca: {f}")
    else:
        print(f"File tidak ditemukan: {f}")

if all_df:
    combined_df = pd.concat(all_df, ignore_index=True)
    output_name = "web/Combined_FollowUp_Mei_2026.csv"
    combined_df.to_csv(output_name, index=False)
    print(f"\n[OK] Berhasil menggabungkan {len(all_df)} file menjadi: {output_name}")
else:
    print("\n[!] Tidak ada data yang digabungkan.")
