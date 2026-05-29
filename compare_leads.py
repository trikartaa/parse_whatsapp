import argparse
import pandas as pd
import re
import warnings
import datetime
import sys
from pathlib import Path

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

def normalize_phone(phone):
    if pd.isna(phone):
        return None
    
    # If it's a float (common in Excel), convert to int first to avoid .0
    if isinstance(phone, float):
        s = "{:.0f}".format(phone)
    else:
        s = str(phone).strip()
        if s.endswith('.0'):
            s = s[:-2]
        
    # Remove any non-digit characters
    s = re.sub(r'\D', '', s)
    
    if not s:
        return None

    # Normalize to 62 format
    if s.startswith('0'):
        s = '62' + s[1:]
    elif s.startswith('8'):
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
        s = s + '-2026'
        
    return pd.to_datetime(s, errors='coerce')

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

def find_typo_candidates(csv_numbers, excel_numbers, min_prefix, max_distance):
    candidates = []
    for excel_phone in sorted(excel_numbers):
        best_matches = []
        for csv_phone in sorted(csv_numbers):
            prefix_len = common_prefix_len(csv_phone, excel_phone)
            if prefix_len < min_prefix:
                continue
            distance = levenshtein_distance(csv_phone, excel_phone)
            if distance == 0 or distance > max_distance:
                continue
            best_matches.append({
                "csv_phone": csv_phone,
                "excel_phone": excel_phone,
                "prefix_len": prefix_len,
                "distance": distance,
                "diff_position": first_difference_position(csv_phone, excel_phone),
            })
        if best_matches:
            best_matches.sort(key=lambda item: (item["distance"], -item["prefix_len"], item["csv_phone"]))
            candidates.append(best_matches[0])
    return candidates

def parse_args():
    parser = argparse.ArgumentParser(
        description="Bandingkan data Master CSV dengan Data WA Marketing (Excel)."
    )
    parser.add_argument(
        "csv_file",
        help="Path file CSV Master, contoh: \"Dashboard KPI Whatsapp - MASTER_DATA.csv\"",
    )
    parser.add_argument(
        "excel_file",
        help="Path file Excel Data WA, contoh: \"data wa marketing.xlsx\"",
    )
    parser.add_argument(
        "--typo-min-prefix",
        type=int,
        default=2,
        help="Minimal jumlah digit awal yang harus sama untuk kandidat typo. Default: 3",
    )
    parser.add_argument(
        "--typo-max-distance",
        type=int,
        default=2,
        help="Maksimal beda digit/edit untuk kandidat typo. Default: 2",
    )
    parser.add_argument(
        "-o", "--output",
        help="Path file output .txt untuk menyimpan hasil.",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Redirect output to file if requested
    if args.output:
        sys.stdout = Logger(args.output)
        
    print("="*65)
    print("   PERBANDINGAN DATA MARKETING - MEI 2026")
    print("="*65)
    
    # 1. Load CSV
    try:
        csv_df = pd.read_csv(args.csv_file)
        csv_df['Tanggal Chat'] = pd.to_datetime(csv_df['Tanggal Chat'], dayfirst=True, errors='coerce')
        csv_df['normalized_phone'] = csv_df['Nomor Klien'].apply(normalize_phone)
        csv_df['clean_marketing'] = csv_df['Marketing'].apply(clean_marketing_name)

        # Filter May 2026 + Status Customer == New + Status == Lead + Channel in [Instagram, Tiktok]
        csv_may = csv_df[
            (csv_df['Tanggal Chat'].dt.month == 5) & 
            (csv_df['Tanggal Chat'].dt.year == 2026) &
            (csv_df['Status Custoimer'] == 'New') &
            (csv_df['Status'] == 'Lead') &
            (csv_df['Channel'].isin(['Instagram']))
        ].copy()
    except Exception as e:
        print(f"Error membaca CSV: {e}")
        return

    # 2. Load Excel
    try:
        xl = pd.ExcelFile(args.excel_file)
        excel_data = []
        for sheet in xl.sheet_names:
            df = pd.read_excel(args.excel_file, sheet_name=sheet)
            if 'TGL' not in df.columns or 'NO. HP' not in df.columns:
                continue
                
            df['TGL'] = df['TGL'].ffill()
            df['TGL_parsed'] = df['TGL'].apply(parse_date)
            df['normalized_phone'] = df['NO. HP'].apply(normalize_phone)
            
            df_may = df[(df['TGL_parsed'].dt.month == 5) & (df['TGL_parsed'].dt.year == 2026)].copy()
            marketing = clean_marketing_name(sheet)
            df_may['clean_marketing'] = marketing
            excel_data.append(df_may[['clean_marketing', 'normalized_phone']])

        if not excel_data:
            excel_may = pd.DataFrame(columns=['clean_marketing', 'normalized_phone'])
        else:
            excel_may = pd.concat(excel_data)
    except Exception as e:
        print(f"Error membaca Excel: {e}")
        return

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

    # 4. Output per Marketing
    all_marketings = sorted(list(set([x[0] for x in csv_set.union(excel_set)])))
    
    for m in all_marketings:
        m_both = sorted([x[1] for x in both if x[0] == m])
        m_only_csv = sorted([x[1] for x in only_csv if x[0] == m])
        m_only_excel = sorted([x[1] for x in only_excel if x[0] == m])
        
        if not (m_both or m_only_csv or m_only_excel):
            continue

        print(f"\n> MARKETING: {m}")
        print(f"  [SAMA DI KEDUANYA] - {len(m_both)}")
        print(f"  [HANYA DI CSV (MASTER)] - {len(m_only_csv)}")
        if m_only_csv:
            for p in m_only_csv: print(f"    - {p}")

        print(f"  [HANYA DI EXCEL (DATA WA)] - {len(m_only_excel)}")
        if m_only_excel:
            for p in m_only_excel: print(f"    - {p}")

        # Typo detection per marketing
        if m_only_csv and m_only_excel:
            typos = find_typo_candidates(
                m_only_csv, 
                m_only_excel, 
                args.typo_min_prefix, 
                args.typo_max_distance
            )
            if typos:
                print(f"  [~] KANDIDAT TYPO ({m}):")
                for item in typos:
                    print(
                        f"    ? Excel: {item['excel_phone']} -> Master: {item['csv_phone']} "
                        f"(beda {item['distance']} digit, mulai digit ke-{item['diff_position']})"
                    )
    
    print("\n" + "="*65)
    print(f"TOTAL UNIK CSV (IG/Tiktok, New, Lead): {len(csv_set)}")
    print(f"TOTAL UNIK EXCEL: {len(excel_set)}")
    print(f"TOTAL SAMA: {len(both)}")
    print("="*65)

if __name__ == "__main__":
    main()
