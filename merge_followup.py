import pandas as pd
import os
import glob
from datetime import datetime

# 1. Cari semua file CSV di folder web
file_list = glob.glob("web/Data Follow Up Trikarta *.csv")

# Filter agar tidak memproses file "Combined" itu sendiri jika ada di folder yang sama
files = [f for f in file_list if "Combined" not in f]

all_df = []

print(f"Ditemukan {len(files)} file untuk diproses.")

for f in files:
    if os.path.exists(f):
        # Menggunakan encoding latin1 untuk menangani karakter spesial
        try:
            df = pd.read_csv(f, encoding='latin1')
        except Exception as e:
            print(f"Error membaca {f}: {e}")
            continue
            
        # Standarisasi nama kolom: hilangkan spasi di ujung dan buat jadi UPPERCASE
        # Contoh: 'Tanggal ' -> 'TANGGAL', 'admin ' -> 'ADMIN'
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # Identifikasi lokasi dari nama file
        filename = os.path.basename(f).upper()
        if "NGAGEL" in filename:
            location = "NGAGEL"
        elif "ROYAL" in filename:
            location = "ROYAL"
        elif "PAKUWON" in filename:
            location = "PAKUWON"
        elif "MALANG" in filename:
            location = "MALANG"
        else:
            location = "UNKNOWN"
            
        print(f"Memproses {os.path.basename(f)} -> Lokasi: {location}")
        
        # Konversi kolom TANGGAL untuk logika filter dan admin
        # Kolom asli biasanya 'Tanggal ' (dengan spasi)
        if 'TANGGAL' in df.columns:
            df['DT_TANGGAL'] = pd.to_datetime(df['TANGGAL'].astype(str).str.strip(), dayfirst=True, errors='coerce')
        else:
            print(f"[!] Kolom TANGGAL tidak ditemukan di {f}")
            df['DT_TANGGAL'] = pd.NaT

        # Logika penetapan Admin sesuai permintaan:
        # - Ngagel: Vegy
        # - Royal: Lia
        # - Pakuwon (Nadine): Nadine
        # - Malang: Adinda (< 15 Mei), Helga (>= 15 Mei)
        def assign_admin(row):
            if location == "NGAGEL":
                return "Vegy"
            elif location == "ROYAL":
                return "Lia"
            elif location == "PAKUWON":
                return "Nadine"
            elif location == "MALANG":
                if pd.isna(row['DT_TANGGAL']):
                    return "Adinda" # Default jika tanggal error
                if row['DT_TANGGAL'] >= datetime(2026, 5, 15):
                    return "Helga"
                else:
                    return "Adinda"
            return row.get('ADMIN', 'UNKNOWN')

        # Isi/Ganti kolom ADMIN dengan logika di atas
        df['ADMIN'] = df.apply(assign_admin, axis=1)
        
        # Tambahkan kolom LOKASI untuk mempermudah pengecekan
        df['LOKASI'] = location
            
        all_df.append(df)

if all_df:
    # Gabungkan semua data
    combined_df = pd.concat(all_df, ignore_index=True)
    
    # Hapus kolom pembantu datetime sebelum simpan
    if 'DT_TANGGAL' in combined_df.columns:
        combined_df = combined_df.drop(columns=['DT_TANGGAL'])
        
    output_name = "web/Combined_FollowUp_All.csv"
    combined_df.to_csv(output_name, index=False)
    
    print(f"\n[OK] Berhasil menggabungkan {len(all_df)} file.")
    print(f"Output: {output_name}")
    print(f"Total baris: {len(combined_df)}")
    
    # Tampilkan ringkasan admin per lokasi untuk verifikasi
    print("\nRingkasan Admin per Lokasi:")
    summary = combined_df.groupby(['LOKASI', 'ADMIN']).size().reset_index(name='Jumlah Baris')
    print(summary)
else:
    print("\n[!] Tidak ada file yang ditemukan atau diproses.")
