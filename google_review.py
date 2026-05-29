import pandas as pd
import argparse
import glob
import os
import sys
import re
from difflib import SequenceMatcher

def clean_name(name):
    if not name or str(name).lower() == 'nan':
        return ""
    # Hapus kata-kata umum yang sering mengganggu pencocokan
    noise_words = ['WEB', 'TAMBAHAN', 'REPEAT', 'EO', 'WO', 'KAK', 'MB_']
    cleaned = str(name).upper()
    for word in noise_words:
        cleaned = cleaned.replace(f" {word}", "").replace(f"{word} ", "")
    
    # Hapus karakter non-alfabet (kecuali spasi)
    cleaned = re.sub(r'[^A-Z\s]', '', cleaned)
    return cleaned.strip()

def fuzzy_match(s1, s2):
    return SequenceMatcher(None, clean_name(s1), clean_name(s2)).ratio()

def process_nota_csv(file_path):
    encodings = ["utf-8-sig", "utf-8", "latin1"]
    
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                lines = f.readlines()
            
            header_idx = -1
            for i, line in enumerate(lines):
                if 'TGL PSN' in line.upper():
                    header_idx = i
                    break
            
            if header_idx == -1:
                continue
                
            df = pd.read_csv(file_path, encoding=enc, skiprows=header_idx, sep=",", engine="python")
            df.columns = [str(c).strip() for c in df.columns]
            
            mapping = {
                'TGL PSN': 'tanggal_pesan',
                'NAMA PEMESAN': 'nama_pemesan',
                'VIA': 'via',
                'M': 'marketing',
                'JP': 'kategori',
                'PRODUCT': 'nama_product'
            }
            
            final_mapping = {}
            for orig, target in mapping.items():
                for col in df.columns:
                    if col.upper() == orig:
                        final_mapping[col] = target
                        break
            
            df = df[list(final_mapping.keys())].rename(columns=final_mapping)
            if 'via' not in df.columns:
                df['via'] = 'OFFLINE'
            
            df = df.dropna(subset=['nama_pemesan'])
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            
            df = df[df['nama_pemesan'].str.lower() != 'nan']
            df = df[df['nama_pemesan'] != '']
            
            def format_date(val):
                if not val or val.lower() == 'nan':
                    return val
                try:
                    dt = pd.to_datetime(val, format='%d/%m/%y', errors='coerce')
                    if pd.isna(dt):
                        dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
                    if not pd.isna(dt):
                        return f"{dt.day}/{dt.month}/{dt.year}"
                except:
                    pass
                return val

            if 'tanggal_pesan' in df.columns:
                df['tanggal_pesan'] = df['tanggal_pesan'].apply(format_date)
            
            target_order = ['tanggal_pesan', 'nama_pemesan', 'via', 'marketing', 'kategori', 'nama_product']
            df = df[[c for c in target_order if c in df.columns]]
            return df
        except Exception as e:
            print(f"Warning: Gagal memproses {file_path} ({enc}): {e}")
            continue
    return None

def compare_leads(nota_df, master_path, threshold=0.8):
    print(f"\nMemulai perbandingan dengan Master: {master_path}...")
    try:
        master_df = pd.read_csv(master_path, encoding='utf-8-sig', sep=",", engine="python")
    except Exception as e:
        # Coba encoding lain jika gagal
        master_df = pd.read_csv(master_path, encoding='latin1', sep=",", engine="python")
    
    # Bersihkan header master
    master_df.columns = [str(c).strip() for c in master_df.columns]
    
    results = []
    # Ambil list nama dari master untuk efisiensi
    master_names = master_df['Nama Klien'].tolist()
    
    for _, row in nota_df.iterrows():
        nama_nota = row['nama_pemesan']
        best_match = None
        best_ratio = 0
        match_idx = -1
        
        for idx, nama_master in enumerate(master_names):
            ratio = fuzzy_match(nama_nota, nama_master)
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = nama_master
                match_idx = idx
        
        if best_ratio >= threshold:
            master_row = master_df.iloc[match_idx]
            results.append({
                'nama_marketing': master_row.get('Marketing', '-'),
                'nama_klien': master_row.get('Nama Klien', nama_nota),
                'nomor_klien': str(master_row.get('Nomor Klien', '-')).strip(),
                'source_nota': nama_nota,
                'score': round(best_ratio, 2)
            })
            
    return pd.DataFrame(results)

def main():
    parser = argparse.ArgumentParser(
        description="Gabungkan file NOTA dan bandingkan dengan Master Data."
    )

    parser.add_argument("-i", "--input", nargs="+", help="Daftar file CSV yang ingin digabung")
    parser.add_argument("-p", "--pattern", help='Pattern file, contoh: "NOTA*.csv"')
    parser.add_argument("-o", "--output", default="hasil_gabungan.csv", help="Nama file output gabungan")
    parser.add_argument("--master", help="Path ke file Dashboard KPI Whatsapp - MASTER_DATA.csv untuk perbandingan")
    parser.add_argument("--compare-output", default="hasil_compare_dealing.csv", help="Nama file output perbandingan")

    args = parser.parse_args()

    files = []
    if args.input:
        files.extend(args.input)
    if args.pattern:
        files.extend(glob.glob(args.pattern))

    files = sorted(list(dict.fromkeys(files)))

    if not files and not args.master:
        print("Error: tidak ada file input atau perintah compare.")
        sys.exit(1)

    combined_df = None
    
    # Jika ada file input/pattern, proses penggabungan dulu
    if files:
        dataframes = []
        for file in files:
            if not os.path.exists(file):
                continue
            print(f"Memproses: {file}...")
            df = process_nota_csv(file)
            if df is not None and not df.empty:
                dataframes.append(df)
        
        if dataframes:
            combined_df = pd.concat(dataframes, ignore_index=True)
            
            # Memastikan hasil gabungan unik berdasarkan nama_pemesan
            combined_df = combined_df.drop_duplicates(subset=['nama_pemesan'])
            
            combined_df.to_csv(args.output, index=False, encoding="utf-8-sig")
            print(f"Gabungan disimpan di: {args.output} ({len(combined_df)} baris unik)")
    
    # Jika combined_df belum ada tapi file output gabungan sudah ada, load saja
    if combined_df is None and os.path.exists(args.output):
        combined_df = pd.read_csv(args.output, encoding="utf-8-sig")

    # Jalankan perbandingan jika master disediakan
    if args.master and combined_df is not None:
        comparison_result = compare_leads(combined_df, args.master)
        if not comparison_result.empty:
            # Hanya ambil kolom yang diminta: nama_marketing, nama_klien, nomor_klien
            final_output = comparison_result[['nama_marketing', 'nama_klien', 'nomor_klien']]
            
            # Memastikan hasil unik (1 nama dan 1 nomor)
            final_output = final_output.drop_duplicates(subset=['nama_klien', 'nomor_klien'])
            
            final_output.to_csv(args.compare_output, index=False, encoding="utf-8-sig")
            print(f"\nHasil perbandingan (Dealing) disimpan di: {args.compare_output}")
            print(f"Ditemukan {len(final_output)} data unik yang cocok (>= 80%).")
        else:
            print("\nTidak ditemukan data yang cocok antara Nota dan Master.")

if __name__ == "__main__":
    main()
