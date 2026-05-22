import pandas as pd
import re

csv_path = r'D:\Trikarta Analis\Marketing\parse_whatsapp\Dashboard KPI Whatsapp - MASTER_DATA.csv'
excel_path = r'D:\Trikarta Analis\Marketing\parse_whatsapp\data wa marketing (4).xlsx'

def clean_phone(phone):
    if pd.isna(phone):
        return None
    # Convert to string and remove all non-numeric characters
    # If Excel parsed it as float, e.g. 8113059770.0, it will become 81130597700 which is wrong.
    # So first convert to int if it's a float
    if isinstance(phone, float):
        try:
            phone = int(phone)
        except:
            pass
    
    cleaned = re.sub(r'\D', '', str(phone))
    
    # Standardize format to start with 628
    if cleaned.startswith('08'):
        cleaned = '628' + cleaned[2:]
    elif cleaned.startswith('8'):
        cleaned = '62' + cleaned
    
    return cleaned if cleaned else None

# 1. Process CSV
print("Membaca data CSV...")
df_csv = pd.read_csv(csv_path)

# Dictionary to store unique numbers per marketing from CSV
csv_data = {}
for index, row in df_csv.iterrows():
    marketing = str(row['Marketing']).upper().strip()
    if marketing == 'NAN':
        continue
    
    phone = clean_phone(row['Nomor Klien'])
    if phone:
        if marketing not in csv_data:
            csv_data[marketing] = set()
        csv_data[marketing].add(phone)

# 2. Process Excel
print("Membaca data Excel...")
excel_data = {}
xl = pd.ExcelFile(excel_path)
for sheet_name in xl.sheet_names:
    # Clean sheet name to match marketing name
    cleaned_name = sheet_name.upper()
    cleaned_name = re.sub(r'\b(BARAT|ROYAL|MLG)\b', '', cleaned_name).strip()
    
    df_excel = pd.read_excel(xl, sheet_name=sheet_name)
    
    excel_data[cleaned_name] = set()
    
    if 'NO. HP' in df_excel.columns:
        for phone_raw in df_excel['NO. HP']:
            phone = clean_phone(phone_raw)
            if phone:
                excel_data[cleaned_name].add(phone)

# 3. Compare and output
output_lines = ["=== HASIL PERBANDINGAN ==="]
all_marketing = set(csv_data.keys()).union(set(excel_data.keys()))

for marketing in sorted(all_marketing):
    output_lines.append(f"\n--- Marketing: {marketing} ---")
    csv_numbers = csv_data.get(marketing, set())
    excel_numbers = excel_data.get(marketing, set())
    
    if not csv_numbers and not excel_numbers:
        output_lines.append("Tidak ada data nomor HP.")
        continue
        
    intersect = csv_numbers.intersection(excel_numbers)
    only_in_csv = csv_numbers - excel_numbers
    only_in_excel = excel_numbers - csv_numbers
    
    output_lines.append(f"Total di CSV: {len(csv_numbers)}")
    output_lines.append(f"Total di Excel: {len(excel_numbers)}")
    
    output_lines.append(f"SAMA DI KEDUANYA (Total: {len(intersect)}):")
    if intersect:
        output_lines.append(", ".join(sorted(list(intersect))))
    else:
        output_lines.append("-")
        
    output_lines.append(f"\nHANYA ADA DI CSV (Total: {len(only_in_csv)}):")
    if only_in_csv:
        output_lines.append(", ".join(sorted(list(only_in_csv))))
    else:
        output_lines.append("-")
        
    output_lines.append(f"\nHANYA ADA DI EXCEL (Total: {len(only_in_excel)}):")
    if only_in_excel:
        output_lines.append(", ".join(sorted(list(only_in_excel))))
    else:
        output_lines.append("-")

full_output = "\n".join(output_lines)

# Print to terminal
print(full_output)

# Write to file
output_path = r'D:\Trikarta Analis\Marketing\parse_whatsapp\hasil_perbandingan.txt'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(full_output)
print(f"\n[INFO] Hasil lengkap juga telah disimpan ke: {output_path}")
