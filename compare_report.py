import pandas as pd
import re
import sys

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

csv_path = r'D:\Trikarta Analis\Marketing\parse_whatsapp\Dashboard KPI Whatsapp - MASTER_DATA.csv'
excel_path = r'D:\Trikarta Analis\Marketing\parse_whatsapp\data wa marketing (4).xlsx'
output_excel = r'D:\Trikarta Analis\Marketing\parse_whatsapp\hasil_perbandingan_mei2026.xlsx'
output_txt   = r'D:\Trikarta Analis\Marketing\parse_whatsapp\hasil_perbandingan_mei2026.txt'

# Filter bulan & tahun
FILTER_MONTH = 5
FILTER_YEAR  = 2026

# ─────────────────────────────────────────
def clean_phone(phone):
    if pd.isna(phone):
        return None
    if isinstance(phone, float):
        try:
            phone = int(phone)
        except Exception:
            pass
    cleaned = re.sub(r'\D', '', str(phone))
    if not cleaned:
        return None
    if cleaned.startswith('08'):
        cleaned = '628' + cleaned[2:]
    elif cleaned.startswith('8'):
        cleaned = '62' + cleaned
    return cleaned

# ─────────────────────────────────────────
# 1. Build mapping: nomor klien  ─> nama klien dari CSV (filter Mei 2026)
print(f"Membaca data CSV ... (filter: {FILTER_MONTH:02d}/{FILTER_YEAR})")
df_csv = pd.read_csv(csv_path)

# Parse kolom tanggal (format dd/mm/yyyy)
df_csv['_tgl'] = pd.to_datetime(df_csv['Tanggal Chat'], dayfirst=True, errors='coerce')
df_csv_filtered = df_csv[
    (df_csv['_tgl'].dt.month == FILTER_MONTH) &
    (df_csv['_tgl'].dt.year  == FILTER_YEAR)
].copy()
print(f"  Baris sebelum filter : {len(df_csv)}")
print(f"  Baris setelah filter : {len(df_csv_filtered)} (bulan {FILTER_MONTH}/{FILTER_YEAR})")

csv_data   = {}   # marketing -> set(nomor)
csv_detail = {}   # marketing -> {nomor: nama_klien}

for _, row in df_csv_filtered.iterrows():
    mkt = str(row['Marketing']).upper().strip()
    if mkt == 'NAN':
        continue
    phone = clean_phone(row['Nomor Klien'])
    if not phone:
        continue
    nama = str(row.get('Nama Klien', '-')).strip() if 'Nama Klien' in row.index else '-'
    csv_data.setdefault(mkt, set()).add(phone)
    csv_detail.setdefault(mkt, {})[phone] = nama

# ─────────────────────────────────────────
# 2. Build mapping dari Excel
print("Membaca data Excel …")
xl = pd.ExcelFile(excel_path)

excel_data   = {}  # marketing (cleaned) -> set(nomor)
excel_detail = {}  # marketing (cleaned) -> {nomor: nama}
sheet_map    = {}  # cleaned_name -> original sheet name

for sheet_name in xl.sheet_names:
    cleaned = re.sub(r'\b(BARAT|ROYAL|MLG)\b', '', sheet_name.upper()).strip()
    sheet_map[cleaned] = sheet_name
    df_xl = pd.read_excel(xl, sheet_name=sheet_name)
    excel_data.setdefault(cleaned, set())
    excel_detail.setdefault(cleaned, {})
    if 'NO. HP' in df_xl.columns:
        for i, hp in enumerate(df_xl['NO. HP']):
            phone = clean_phone(hp)
            if phone:
                excel_data[cleaned].add(phone)
                nama_col = 'NAMA' if 'NAMA' in df_xl.columns else None
                nama = str(df_xl[nama_col].iloc[i]).strip() if nama_col else '-'
                excel_detail[cleaned][phone] = nama

# ─────────────────────────────────────────
# 3. Compare dan cetak
all_marketing = sorted(set(csv_data.keys()) | set(excel_data.keys()))
rows_excel = []  # untuk export Excel

SEP = "=" * 70
sep = "-" * 70
lines = [SEP,
         f" HASIL PERBANDINGAN DATA NOMOR WA PER MARKETING",
         f" FILTER: BULAN MEI {FILTER_YEAR}",
         SEP]

for mkt in all_marketing:
    csv_nums   = csv_data.get(mkt, set())
    excel_nums = excel_data.get(mkt, set())

    intersect      = sorted(csv_nums & excel_nums)
    only_csv       = sorted(csv_nums - excel_nums)
    only_excel     = sorted(excel_nums - csv_nums)

    lines.append(f"\n{sep}")
    lines.append(f"  MARKETING : {mkt}")
    lines.append(f"  Sheet Excel: {sheet_map.get(mkt, '-')}")
    lines.append(f"  Total nomor di CSV   : {len(csv_nums)}")
    lines.append(f"  Total nomor di Excel : {len(excel_nums)}")
    lines.append(sep)

    lines.append(f"\n  [SAMA] SAMA DI KEDUANYA ({len(intersect)} nomor):")
    if intersect:
        for n in intersect:
            nama_csv   = csv_detail.get(mkt, {}).get(n, '-')
            nama_excel = excel_detail.get(mkt, {}).get(n, '-')
            lines.append(f"     {n}  | CSV: {nama_csv}  | Excel: {nama_excel}")
            rows_excel.append({'Marketing': mkt, 'Status': 'SAMA', 'Nomor': n,
                               'Nama CSV': nama_csv, 'Nama Excel': nama_excel})
    else:
        lines.append("     (tidak ada)")

    lines.append(f"\n  [HANYA CSV] HANYA ADA DI CSV ({len(only_csv)} nomor):")
    if only_csv:
        for n in only_csv:
            nama = csv_detail.get(mkt, {}).get(n, '-')
            lines.append(f"     {n}  | Nama: {nama}")
            rows_excel.append({'Marketing': mkt, 'Status': 'HANYA DI CSV', 'Nomor': n,
                               'Nama CSV': nama, 'Nama Excel': ''})
    else:
        lines.append("     (tidak ada)")

    lines.append(f"\n  [HANYA EXCEL] HANYA ADA DI EXCEL ({len(only_excel)} nomor):")
    if only_excel:
        for n in only_excel:
            nama = excel_detail.get(mkt, {}).get(n, '-')
            lines.append(f"     {n}  | Nama: {nama}")
            rows_excel.append({'Marketing': mkt, 'Status': 'HANYA DI EXCEL', 'Nomor': n,
                               'Nama CSV': '', 'Nama Excel': nama})
    else:
        lines.append("     (tidak ada)")

lines.append(f"\n{SEP}")
lines.append(" RINGKASAN")
lines.append(SEP)
for mkt in all_marketing:
    csv_nums   = csv_data.get(mkt, set())
    excel_nums = excel_data.get(mkt, set())
    intersect  = csv_nums & excel_nums
    only_csv   = csv_nums - excel_nums
    only_excel = excel_nums - csv_nums
    lines.append(f"  {mkt:<12} | CSV:{len(csv_nums):>4} | Excel:{len(excel_nums):>4} "
                 f"| Sama:{len(intersect):>4} | Hanya CSV:{len(only_csv):>4} | Hanya Excel:{len(only_excel):>4}")

full_output = "\n".join(lines)

# ─────────────────────────────────────────
# 4. Simpan ke .txt
with open(output_txt, 'w', encoding='utf-8') as f:
    f.write(full_output)
print(full_output)

# ─────────────────────────────────────────
# 5. Simpan ke Excel dengan warna
df_out = pd.DataFrame(rows_excel, columns=['Marketing', 'Status', 'Nomor', 'Nama CSV', 'Nama Excel'])

with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
    # Sheet ringkasan per marketing
    summary_rows = []
    for mkt in all_marketing:
        csv_nums   = csv_data.get(mkt, set())
        excel_nums = excel_data.get(mkt, set())
        intersect  = csv_nums & excel_nums
        summary_rows.append({
            'Marketing': mkt,
            'Sheet Excel': sheet_map.get(mkt, '-'),
            'Total CSV': len(csv_nums),
            'Total Excel': len(excel_nums),
            'Sama di Keduanya': len(intersect),
            'Hanya di CSV': len(csv_nums - excel_nums),
            'Hanya di Excel': len(excel_nums - csv_nums),
        })
    pd.DataFrame(summary_rows).to_excel(writer, sheet_name='Ringkasan', index=False)

    # Sheet detail per marketing
    for mkt in all_marketing:
        df_mkt = df_out[df_out['Marketing'] == mkt].drop(columns='Marketing')
        sheet_nm = mkt[:31]  # Excel sheet name max 31 chars
        df_mkt.to_excel(writer, sheet_name=sheet_nm, index=False)

    # Sheet semua detail
    df_out.to_excel(writer, sheet_name='SEMUA DETAIL', index=False)

print(f"\n[OK] File TXT  : {output_txt}")
print(f"[OK] File Excel: {output_excel}")
