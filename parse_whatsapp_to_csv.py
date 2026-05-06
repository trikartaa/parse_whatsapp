import re
import csv
from pathlib import Path
from typing import List, Tuple, Dict
from datetime import datetime


def extract_datetime_from_log(log_line: str) -> Tuple[str, str]:
    """
    Extract tanggal and jam from chat log line.
    Format: [HH.MM, D/M/YYYY] +62xxx: message
    Returns: (tanggal in D/M/YYYY, jam in HH:MM)
    """
    match = re.search(r'\[(\d{1,2})\.(\d{2}),\s+(\d{1,2})/(\d{1,2})/(\d{4})\]', log_line)
    if match:
        hour, minute, day, month, year = match.groups()
        tanggal = f"{day}/{month}/{year}"
        jam = f"{hour}:{minute}"
        return tanggal, jam
    return None, None


def extract_phone_number(text: str) -> str:
    """
    Extract phone number in format 62 xxx-xxxx-xxxx
    Returns the phone number or empty string if not found
    """
    match = re.search(r'62\s+[\d\-]+', text.strip())
    if match:
        return match.group(0)
    return ""


def is_client_chat_line(line: str, client_name: str, client_phone: str) -> bool:
    """
    Determine if a chat line is from the client.
    Tries multiple patterns:
    1. Phone number with exact spaces: +62 xxx-xxxx-xxxx
    2. Phone number without spaces: +62xxxxxxxxx
    3. Client name (partial match)
    """
    # Normalize phone for comparison
    phone_normalized = client_phone.replace(" ", "").replace("-", "")
    line_lower = line.lower()
    
    # Try phone number match (both with and without formatting)
    if f"+{phone_normalized}" in line.replace(" ", "").replace("-", ""):
        return True
    
    # Try name match (case-insensitive, partial match)
    if client_name != "-":
        # Split by spaces to handle multi-word names
        name_parts = client_name.split()
        # Check if all name parts appear in the line
        if all(part.lower() in line_lower for part in name_parts):
            return True
    
    return False


def extract_client_name(text: str) -> str:
    """
    Extract client name from first line of each block.
    If it's a phone number or empty, return "-"
    """
    text = text.strip()
    # Remove BOM character if present
    text = text.lstrip('\ufeff')
    
    # If empty, return "-"
    if not text:
        return "-"
    
    # If it's a phone number, return "-"
    if re.match(r'^62\s+[\d\-]+', text):
        return "-"
    
    # Otherwise it's a name
    return text


def parse_whatsapp_file(input_file: str) -> List[Dict]:
    """
    Parse WhatsApp chat log file and return list of records.
    Each record represents one client with all their chat logs.
    Handles follow-up entries separately.
    """
    records = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by separator "________________"
    blocks = content.split('________________')
    
    row_no = 1
    
    for block in blocks:
        lines = block.strip().split('\n')
        
        if len(lines) < 1:
            continue
        
        # Find the first non-empty line (nama klien atau nomor)
        # Find the phone number line
        client_name = "-"
        client_phone = ""
        phone_line_idx = -1
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Check if this line is a phone number
            phone = extract_phone_number(line_stripped)
            if phone:
                client_phone = phone
                phone_line_idx = i
                # Check if there's a name before this phone line
                if i > 0:
                    prev_line = lines[i-1].strip()
                    if prev_line and not extract_phone_number(prev_line):
                        client_name = extract_client_name(prev_line)
                break
            
            # If we find a line with timestamp, no phone found yet - skip this block
            if '[' in line_stripped and ']' in line_stripped:
                break
        
        # Skip if no phone number found
        if not client_phone:
            continue
        
        # Normalize phone number: remove spaces and dashes
        client_phone_clean = client_phone.replace(" ", "").replace("-", "")
        # Add 0 prefix before 62 (format: 062xxxxxxxxxx)
        if client_phone_clean.startswith("62"):
            client_phone_clean = "0" + client_phone_clean
        
        # Split chat logs by "Follow up" marker
        chat_sections = []
        current_section = []
        
        for line in lines[phone_line_idx + 1:]:
            line_stripped = line.strip()
            
            # Check if this is "Follow up" marker
            if line_stripped.lower() == "follow up":
                # Save current section if not empty
                if current_section:
                    chat_sections.append(("main", current_section))
                # Start follow-up section
                current_section = []
                continue
            
            current_section.append(line)
        
        # Save last section
        if current_section:
            # Determine if this is follow-up or main
            section_type = "followup" if len(chat_sections) > 0 else "main"
            chat_sections.append((section_type, current_section))
        
        # Process each section as a separate record
        followup_counter = 0
        
        for section_idx, (section_type, section_lines) in enumerate(chat_sections):
            chat_logs = []
            first_datetime = None
            
            for line in section_lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is a chat log line (has timestamp)
                if '[' in line and ']' in line:
                    chat_logs.append(line)
                    
                    # Extract datetime from first chat log
                    # For main section: from CLIENT
                    # For follow-up section: from FIRST chat (any sender)
                    if first_datetime is None:
                        if section_type == "main":
                            # Only from client chat
                            if is_client_chat_line(line, client_name, client_phone):
                                tanggal, jam = extract_datetime_from_log(line)
                                if tanggal and jam:
                                    first_datetime = (tanggal, jam)
                        else:
                            # For follow-up: take first chat with timestamp
                            tanggal, jam = extract_datetime_from_log(line)
                            if tanggal and jam:
                                first_datetime = (tanggal, jam)
            
            # If no chat logs found, skip this section
            if not chat_logs:
                continue
            
            # Determine tanggal and jam
            if section_type == "main":
                if first_datetime:
                    tanggal_chat, jam_chat = first_datetime
                else:
                    tanggal_chat = ""
                    jam_chat = ""
                status = ""
                followup_ke = ""
            else:
                # Follow-up section - ambil dari chat pertama di section tersebut
                if first_datetime:
                    tanggal_chat, jam_chat = first_datetime
                else:
                    tanggal_chat = ""
                    jam_chat = ""
                status = "Follow Up"
                followup_counter += 1
                followup_ke = f"F{followup_counter}"
            
            # Combine all chat logs into keterangan
            keterangan = "\n".join(chat_logs)
            
            # Create record
            record = {
                'No': row_no,
                'Tanggal Chat': tanggal_chat,
                'Jam Chat': jam_chat,
                'Nama Klien': client_name,
                'Nomor Klien': client_phone_clean,
                'Status Customer': "",
                'Channel': "",
                'Acara': "",
                'Tempat Acara': "",
                'Tanggal Acara': "",
                'Sumber Informasi': "",
                'Follow Up Ke': followup_ke,
                'Status': status,
                'Tanggal Deal': "",
                'Produk': "",
                'Keterangan': keterangan
            }
            
            records.append(record)
            row_no += 1
    
    return records


def export_to_csv(records: List[Dict], output_file: str):
    """
    Export records to CSV file with proper encoding for Excel.
    """
    if not records:
        print("No records to export.")
        return
    
    fieldnames = [
        'No',
        'Tanggal Chat',
        'Jam Chat',
        'Nama Klien',
        'Nomor Klien',
        'Status Customer',
        'Channel',
        'Acara',
        'Tempat Acara',
        'Tanggal Acara',
        'Sumber Informasi',
        'Follow Up Ke',
        'Status',
        'Tanggal Deal',
        'Produk',
        'Keterangan'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()
        writer.writerows(records)
    
    print(f"✓ Exported {len(records)} records to {output_file}")


def main(input_file: str = None, output_file: str = None):
    """
    Main function to parse WhatsApp chat logs and export to CSV.
    
    Args:
        input_file: Path to input WhatsApp chat log file (default: Salinan Data Whatsapp Wati.txt)
        output_file: Path to output CSV file (default: auto-generated from input filename)
    """
    # Default input file
    if input_file is None:
        input_file = "Salinan Data Whatsapp Wati.txt"
    
    # Check if input file exists
    if not Path(input_file).exists():
        print(f"❌ Input file not found: {input_file}")
        return
    
    # Auto-generate output filename if not provided
    if output_file is None:
        input_path = Path(input_file)
        output_file = input_path.parent / f"{input_path.stem}-parsed.csv"
    
    print(f"📖 Parsing: {input_file}")
    
    # Parse file
    records = parse_whatsapp_file(input_file)
    
    # Export to CSV
    export_to_csv(records, str(output_file))
    
    # Print summary
    print(f"\nSummary:")
    print(f"  - Total records: {len(records)}")
    print(f"  - Output file: {output_file}")


if __name__ == "__main__":
    import sys
    
    # Check if input file provided as argument
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        main(input_file, output_file)
    else:
        main()
