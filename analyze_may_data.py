import csv
import re
import os

# Define file paths
FILE_WEB = r"d:\Trikarta Analis\Marketing\parse_whatsapp\Web Ngagel - Vegy.csv"
FILE_FOLLOWUP = r"d:\Trikarta Analis\Marketing\parse_whatsapp\Data Follow Up Trikarta NGAGEL Surabaya - April 2026.csv"
OUTPUT_FILE = r"d:\Trikarta Analis\Marketing\parse_whatsapp\May_Unique_Contacts_Analysis.txt"

def normalize_phone(phone_str):
    if not phone_str:
        return ""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', str(phone_str))
    if not digits:
        return ""
    
    # Normalization logic:
    # 1. If starts with 0 (e.g. 0812...), replace 0 with 62 -> 62812...
    # 2. If starts with 8 (e.g. 812... due to Excel stripping leading zero), prepends 62 -> 62812...
    # 3. If starts with 62, keep it.
    # 4. If other country codes, keep as is.
    if digits.startswith('0'):
        return '62' + digits[1:]
    elif digits.startswith('8'):
        if len(digits) >= 9 and len(digits) <= 13:
            return '62' + digits
    
    return digits

def get_month(date_str):
    if not date_str:
        return None
    # Strip spaces and split by '/' or '-'
    parts = [p.strip() for p in re.split(r'[/\-]', date_str)]
    if len(parts) >= 2:
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None

def read_web_csv():
    records = []
    if not os.path.exists(FILE_WEB):
        print(f"Error: {FILE_WEB} not found.")
        return records
        
    with open(FILE_WEB, mode='r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row_idx, row in enumerate(reader, start=2):
            date_chat = row.get('Tanggal Chat', '')
            month = get_month(date_chat)
            
            # Filter for May (Month 5)
            if month == 5:
                phone_raw = row.get('Nomor Klien', '')
                phone_norm = normalize_phone(phone_raw)
                records.append({
                    'source': 'Web Ngagel - Vegy.csv',
                    'row_num': row_idx,
                    'date': date_chat,
                    'name': row.get('Nama Klien', '').strip(),
                    'phone_raw': phone_raw,
                    'phone_norm': phone_norm,
                    'status': row.get('Status', '').strip() or row.get('Status Custoimer', '').strip(),
                    'product': row.get('Produk', '').strip(),
                    'notes': row.get('Keterangan', '').strip()
                })
    return records

def read_followup_csv():
    records = []
    if not os.path.exists(FILE_FOLLOWUP):
        print(f"Error: {FILE_FOLLOWUP} not found.")
        return records
        
    with open(FILE_FOLLOWUP, mode='r', encoding='utf-8-sig', errors='ignore') as f:
        # First row is header. Let's read with general reader because first col might be blank
        reader = csv.reader(f)
        header = next(reader)
        
        # Let's map headers to indices
        # Jam kontak, NAMA, NO HP, KOTA, ACARA, TGL ACARA, RESPON, F1/ F2, KETERANGAN, admin, DEAL/TIDAK DEAL, REFRENSI
        # Date is in first column (index 0)
        for row_idx, row in enumerate(reader, start=2):
            if not row or len(row) < 4:
                continue
                
            date_str = row[0].strip()
            month = get_month(date_str)
            
            # Filter for May (Month 5)
            if month == 5:
                name = row[2].strip() if len(row) > 2 else ""
                phone_raw = row[3].strip() if len(row) > 3 else ""
                phone_norm = normalize_phone(phone_raw)
                keterangan = row[9].strip() if len(row) > 9 else ""
                deal_status = row[11].strip() if len(row) > 11 else ""
                
                records.append({
                    'source': 'Data Follow Up Trikarta NGAGEL.csv',
                    'row_num': row_idx,
                    'date': date_str,
                    'name': name,
                    'phone_raw': phone_raw,
                    'phone_norm': phone_norm,
                    'status': deal_status,
                    'product': '',
                    'notes': keterangan
                })
    return records

def main():
    print("Reading and parsing files...")
    web_records = read_web_csv()
    followup_records = read_followup_csv()
    
    print(f"Found {len(web_records)} records in May from Web Ngagel")
    print(f"Found {len(followup_records)} records in May from Follow Up Ngagel")
    
    # Combine records
    all_records = web_records + followup_records
    
    # Group by normalized phone number
    phone_groups = {}
    for r in all_records:
        phone = r['phone_norm']
        if not phone:
            continue
        if phone not in phone_groups:
            phone_groups[phone] = []
        phone_groups[phone].append(r)
        
    # Analyze duplicates based on cross-file existence
    unique_contacts = []       # Phone numbers that appear in ONLY ONE of the files
    duplicated_contacts = []    # Phone numbers that appear in BOTH files
    
    for phone, group in phone_groups.items():
        sources = set(r['source'] for r in group)
        if len(sources) > 1:
            duplicated_contacts.append((phone, group))
        else:
            unique_contacts.append((phone, group))
            
    # Write detailed report
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
        out.write("=========================================================================\n")
        out.write(" ANALISIS DATA TIDAK TERDUPLIKASI (KONTAK UNIK) - BULAN MEI 2026\n")
        out.write("=========================================================================\n\n")
        
        out.write(f"Total Kontak di Bulan Mei (Gabungan): {len(phone_groups)}\n")
        out.write(f"Total Kontak TIDAK TERDUPLIKASI (Hanya Muncul di Salah Satu File): {len(unique_contacts)}\n")
        out.write(f"Total Kontak TERDUPLIKASI (Muncul di Kedua File): {len(duplicated_contacts)}\n\n")
        
        out.write("-------------------------------------------------------------------------\n")
        out.write("1. DAFTAR KONTAK YANG TIDAK TERDUPLIKASI (HANYA ADA DI SALAH SATU FILE)\n")
        out.write("-------------------------------------------------------------------------\n")
        
        if not unique_contacts:
            out.write("Tidak ada kontak unik (semua terduplikasi di kedua file).\n")
        else:
            for idx, (phone, group) in enumerate(sorted(unique_contacts, key=lambda x: x[1][0]['date']), start=1):
                out.write(f"{idx}. Nomor HP: {phone} (Muncul {len(group)} kali di {group[0]['source']})\n")
                for sub_idx, rec in enumerate(group, start=1):
                    out.write(f"   [{sub_idx}] Nama Klien: {rec['name']} | Tanggal: {rec['date']}\n")
                    out.write(f"       Baris ke-{rec['row_num']}\n")
                    if rec['status']:
                        out.write(f"       Status     : {rec['status']}\n")
                    if rec['product']:
                        out.write(f"       Produk     : {rec['product']}\n")
                    if rec['notes']:
                        out.write(f"       Keterangan : {rec['notes']}\n")
                out.write("\n")
                
        out.write("-------------------------------------------------------------------------\n")
        out.write("2. DAFTAR KONTAK YANG TERDUPLIKASI (MUNCUL DI KEDUA FILE A DAN B)\n")
        out.write("-------------------------------------------------------------------------\n")
        
        if not duplicated_contacts:
            out.write("Tidak ada kontak yang muncul di kedua file sekaligus.\n")
        else:
            for idx, (phone, group) in enumerate(sorted(duplicated_contacts, key=lambda x: len(x[1]), reverse=True), start=1):
                out.write(f"{idx}. Nomor HP: {phone} (Muncul {len(group)} kali lintas file)\n")
                for sub_idx, rec in enumerate(group, start=1):
                    out.write(f"   [{sub_idx}] Nama Klien: {rec['name']} | Tanggal: {rec['date']}\n")
                    out.write(f"       Sumber File: {rec['source']} (Baris ke-{rec['row_num']})\n")
                    if rec['status']:
                        out.write(f"       Status     : {rec['status']}\n")
                    if rec['product']:
                        out.write(f"       Produk     : {rec['product']}\n")
                    if rec['notes']:
                        out.write(f"       Keterangan : {rec['notes']}\n")
                out.write("\n")
                
        # Let's also output a deduplicated list of all May contacts (combined unique list)
        out.write("-------------------------------------------------------------------------\n")
        out.write("3. REKAPITULASI DEDUPLIKASI (SATU BARIS PER NOMOR HP UNIK)\n")
        out.write("-------------------------------------------------------------------------\n")
        out.write("No,Nomor HP,Nama Klien,Tanggal Pertama,Jumlah Muncul,Sumber File\n")
        
        for idx, (phone, group) in enumerate(sorted(phone_groups.items(), key=lambda x: x[1][0]['date']), start=1):
            names = list(set([r['name'] for r in group if r['name']]))
            name_str = names[0] if names else "-"
            dates = [r['date'] for r in group]
            sources = list(set([r['source'].split('.')[0] for r in group]))
            out.write(f"{idx},{phone},{name_str},{dates[0]},{len(group)},{' & '.join(sources)}\n")
            
    print(f"Analysis completed successfully. Output saved to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
