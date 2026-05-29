import argparse
import pandas as pd
import re
import warnings
from pathlib import Path

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

def common_prefix_len(left, right):
    total = 0
    for left_digit, right_digit in zip(left, right):
        if left_digit != right_digit:
            break
        total += 1
    return total

def levenshtein_distance(left, right):
    if left == right:
        return 0

    previous = list(range(len(right) + 1))
    for i, left_digit in enumerate(left, start=1):
        current = [i]
        for j, right_digit in enumerate(right, start=1):
            cost = 0 if left_digit == right_digit else 1
            current.append(min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + cost,
            ))
        previous = current

    return previous[-1]

def first_difference_position(left, right):
    for index, (left_digit, right_digit) in enumerate(zip(left, right), start=1):
        if left_digit != right_digit:
            return index

    if len(left) != len(right):
        return min(len(left), len(right)) + 1

    return None

def find_typo_candidates(web_numbers, followup_numbers, min_prefix, max_distance):
    candidates = []

    for followup_phone in sorted(followup_numbers):
        best_matches = []
        for web_phone in sorted(web_numbers):
            prefix_len = common_prefix_len(web_phone, followup_phone)
            if prefix_len < min_prefix:
                continue

            distance = levenshtein_distance(web_phone, followup_phone)
            if distance == 0 or distance > max_distance:
                continue

            best_matches.append({
                "web_phone": web_phone,
                "followup_phone": followup_phone,
                "prefix_len": prefix_len,
                "distance": distance,
                "diff_position": first_difference_position(web_phone, followup_phone),
            })

        if best_matches:
            best_matches.sort(key=lambda item: (item["distance"], -item["prefix_len"], item["web_phone"]))
            candidates.append(best_matches[0])

    candidates.sort(key=lambda item: (item["followup_phone"], item["distance"], -item["prefix_len"]))
    return candidates

def parse_args():
    parser = argparse.ArgumentParser(
        description="Bandingkan lead Web New Mei 2026 dengan data follow up."
    )
    parser.add_argument(
        "master_file",
        help="Path file CSV master web, contoh: \"Web Ngagel - Vegy.csv\"",
    )
    parser.add_argument(
        "followup_files",
        nargs="+",
        help="Satu atau lebih path file CSV data follow up",
    )
    parser.add_argument(
        "--output",
        help="Path file output .txt (opsional), contoh: \"hasil_web.txt\"",
    )
    parser.add_argument(
        "--typo-min-prefix",
        type=int,
        default=3,
        help="Minimal jumlah digit awal yang harus sama untuk kandidat typo. Default: 3",
    )
    parser.add_argument(
        "--typo-max-distance",
        type=int,
        default=2,
        help="Maksimal beda digit/edit untuk kandidat typo. Default: 2",
    )
    return parser.parse_args()

def read_csv_or_raise(file_path):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {path}")
    # Coba beberapa encoding umum
    for enc in ['utf-8', 'latin1', 'cp1252']:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)

def find_column(df, possible_names, label):
    # Bersihkan nama kolom dari df dulu
    clean_cols = [str(c).strip() for c in df.columns]
    for name in possible_names:
        if name in clean_cols:
            # Kembalikan nama kolom asli yang cocok
            idx = clean_cols.index(name)
            return df.columns[idx]
            
    available_columns = ", ".join(df.columns)
    raise KeyError(f"Kolom {label} tidak ditemukan. Kolom tersedia: {available_columns}")

def parse_date_flexible(val):
    if pd.isna(val):
        return pd.NaT
    
    s = str(val).strip().lower()
    if not s:
        return pd.NaT
        
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
            
    # Jika tidak ada tahun (seperti 5/5), tambahkan 2026
    if not re.search(r'\d{4}', s):
        if '/' in s:
            s = s + '/2026'
        else:
            s = s + '-2026'
            
    return pd.to_datetime(s, dayfirst=True, errors='coerce')

def main():
    args = parse_args()
    output_lines = []

    def log(msg=""):
        print(msg)
        output_lines.append(msg)

    log("="*65)
    log("   KHUSUS MEI 2026: WEB (NEW) VS DATA FOLLOW UP")
    log("="*65)
    
    # 1. Load CSV master web
    try:
        master_df = read_csv_or_raise(args.master_file)
        # Bersihkan spasi di nama kolom master
        master_df.columns = [str(c).strip() for c in master_df.columns]
        
        status_customer_col = find_column(
            master_df,
            ["Status Customer", "Status Custoimer"],
            "Status Customer",
        )
        marketing_col_master = find_column(master_df, ["Marketing"], "Marketing")
        
        master_df['Tanggal Chat'] = master_df['Tanggal Chat'].apply(parse_date_flexible)
        
        mask_master = (
            (master_df['Tanggal Chat'].dt.month == 5) & 
            (master_df['Tanggal Chat'].dt.year == 2026) &
            (master_df['Channel'] == 'Web') &
            (master_df['Status'] == 'Lead') &
            (master_df[status_customer_col] == 'New')
        )
        qualified_leads = master_df[mask_master].copy()
        qualified_leads['norm_phone'] = qualified_leads['Nomor Klien'].apply(normalize_phone)
        qualified_leads['norm_mkt'] = qualified_leads[marketing_col_master].astype(str).str.strip().str.lower()
    except Exception as e:
        log(f"Error master: {e}")
        return

    # 2. Load & Consolidate CSV data follow up
    try:
        # Mapping hardcoded berdasarkan nama file
        file_to_mkt = {
            "ngagel": "vegy",
            "royal": "lia",
            "malang": "adinda",
            "pakuwon": "nadine"
        }

        all_fu_may_list = []
        for fu_path in args.followup_files:
            fname = Path(fu_path).name.lower()
            
            # Tentukan PIC berdasarkan nama file
            assigned_mkt = None
            for key, val in file_to_mkt.items():
                if key in fname:
                    assigned_mkt = val
                    break
            
            if not assigned_mkt:
                log(f"[!] Lewati {fu_path}: Tidak dikenali sebagai Malang/Ngagel/Pakuwon/Royal")
                continue

            log(f"Membaca file follow-up: {fu_path} -> PIC: {assigned_mkt.upper()}")
            df_fu_raw = read_csv_or_raise(fu_path)
            df_fu_raw.columns = [str(c).strip() for c in df_fu_raw.columns]
            
            date_col = df_fu_raw.columns[0]
            phone_col_fu = find_column(df_fu_raw, ["NO HP"], "NO HP")
            
            df_fu_raw['parsed_date'] = df_fu_raw[date_col].apply(parse_date_flexible)
            
            mask_fu = (
                (df_fu_raw['parsed_date'].dt.month == 5) & 
                (df_fu_raw['parsed_date'].dt.year == 2026)
            )
            fu_may_part = df_fu_raw[mask_fu].copy()
            fu_may_part['norm_phone'] = fu_may_part[phone_col_fu].apply(normalize_phone)
            # HARDCODED: Semua baris di file ini dianggap milik PIC yang ditentukan
            fu_may_part['norm_mkt'] = assigned_mkt
            
            all_fu_may_list.append(fu_may_part)
            
        if not all_fu_may_list:
            log("Tidak ada data follow-up yang dimuat.")
            return
            
        fu_may = pd.concat(all_fu_may_list, ignore_index=True)
    except Exception as e:
        log(f"Error follow-up: {e}")
        return


    # 3. List Marketing (GABUNGAN)
    all_marketing = sorted(list(set(qualified_leads['norm_mkt'].unique()) | set(fu_may['norm_mkt'].unique())))
    
    log(f"\nTotal Lead Web (New) Mei 2026  : {len(qualified_leads['norm_phone'].dropna().unique())}")
    log(f"Total Follow Up Mei 2026       : {len(fu_may['norm_phone'].dropna().unique())}")
    log("-" * 65)

    for mkt in all_marketing:
        if mkt == 'nan' or not mkt or mkt == 'none':
            continue
            
        log("\n" + "#"*65)
        log(f" MARKETING: {mkt.upper()}")
        log("#"*65)
        
        mkt_leads = qualified_leads[qualified_leads['norm_mkt'] == mkt]
        mkt_fu = fu_may[fu_may['norm_mkt'] == mkt]
        
        master_set = set(mkt_leads['norm_phone'].dropna().unique())
        fu_set = set(mkt_fu['norm_phone'].dropna().unique())

        matching = master_set.intersection(fu_set)
        only_web = master_set - fu_set
        only_fu = fu_set - master_set
        typo_candidates = find_typo_candidates(
            only_web,
            only_fu,
            args.typo_min_prefix,
            args.typo_max_distance,
        )
        
        log(f"Lead Web (New) ditugaskan : {len(master_set)}")
        log(f"Berhasil di-Follow Up    : {len(fu_set)}")
        log("-" * 30)
        
        if matching:
            log(f"[v] NOMOR YANG SUDAH MATCH: {len(matching)}")

        if only_web:
            log(f"[!] HANYA DI WEB (BELUM FOLLOW UP): {len(only_web)}")
            for phone in sorted(list(only_web)):
                log(f"    - {phone}")

        if only_fu:
            log(f"[?] HANYA DI FOLLOW UP (TIDAK ADA DI MASTER MEI): {len(only_fu)}")
            for phone in sorted(list(only_fu)):
                log(f"    - {phone}")

        if typo_candidates:
            log(f"[~] KANDIDAT NOMOR TYPO:")
            for item in typo_candidates:
                log(
                    f"    - FU: {item['followup_phone']} | Web: {item['web_phone']} "
                    f"(beda: {item['distance']}, prefix: {item['prefix_len']})"
                )

    # 5. Save to file
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write("\n".join(output_lines))
            print(f"\n[OK] Hasil perbandingan telah disimpan ke: {args.output}")
        except Exception as e:
            print(f"Error menyimpan file: {e}")

if __name__ == "__main__":
    main()
