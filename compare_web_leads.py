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
        "followup_file",
        help="Path file CSV data follow up, contoh: \"Data Follow Up Trikarta NGAGEL Surabaya - April 2026.csv\"",
    )
    parser.add_argument(
        "--typo-min-prefix",
        type=int,
        default=3,
        help="Minimal jumlah digit awal yang harus sama untuk kandidat typo. Default: 5",
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
    return pd.read_csv(path)

def find_column(df, possible_names, label):
    for name in possible_names:
        if name in df.columns:
            return name
    available_columns = ", ".join(df.columns)
    raise KeyError(f"Kolom {label} tidak ditemukan. Kolom tersedia: {available_columns}")

def main():
    args = parse_args()

    print("="*65)
    print("   KHUSUS MEI 2026: WEB (NEW) VS DATA FOLLOW UP")
    print("="*65)
    
    # 1. Load CSV master web dari argumen terminal
    try:
        master_df = read_csv_or_raise(args.master_file)
        status_customer_col = find_column(
            master_df,
            ["Status Customer", "Status Custoimer"],
            "Status Customer",
        )
        # Paksa parsing tanggal
        master_df['Tanggal Chat'] = pd.to_datetime(master_df['Tanggal Chat'], dayfirst=True, errors='coerce')
        
        # FILTER KETAT MEI 2026
        # Catatan: Channel bisa 'Web' atau 'Tidak Diketahui'
        mask_master = (
            (master_df['Tanggal Chat'].dt.month == 5) & 
            (master_df['Tanggal Chat'].dt.year == 2026) &
            (master_df['Channel'].isin(['Web', 'Tidak Diketahui'])) &
            (master_df['Status'] == 'Lead') &
            (master_df[status_customer_col] == 'New')
        )
        qualified_leads = master_df[mask_master].copy()
        qualified_leads['norm_phone'] = qualified_leads['Nomor Klien'].apply(normalize_phone)
        master_set = set(qualified_leads['norm_phone'].dropna())
    except Exception as e:
        print(f"Error master: {e}")
        return

    # 2. Load CSV data follow up dari argumen terminal
    try:
        fu_df = read_csv_or_raise(args.followup_file)
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
    typo_candidates = find_typo_candidates(
        only_web,
        only_fu,
        args.typo_min_prefix,
        args.typo_max_distance,
    )
    
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

    if typo_candidates:
        print(f"\n[~] KANDIDAT NOMOR TYPO (FOLLOW UP VS WEB): {len(typo_candidates)}")
        print(f"    Aturan: awalan sama minimal {args.typo_min_prefix} digit, beda maksimal {args.typo_max_distance} edit.")
        for item in typo_candidates:
            print(
                f"- Follow Up: {item['followup_phone']}  |  Web: {item['web_phone']}  "
                f"| beda edit: {item['distance']}  | prefix sama: {item['prefix_len']} digit  "
                f"| beda mulai digit ke-{item['diff_position']}"
            )

if __name__ == "__main__":
    main()
