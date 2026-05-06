#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Combined converter + parser for WhatsApp data.
Handles both standard format and 'Nama klien:' format.

Usage:
    python parse_whatsapp_combined.py "Data Whatsapp Nadine.txt"
"""

import re
import csv
from pathlib import Path
from typing import List, Tuple, Dict


def extract_datetime_from_log(log_line: str) -> Tuple[str, str]:
    """Extract tanggal and jam from chat log line."""
    match = re.search(r'\[(\d{1,2})\.(\d{2}),\s+(\d{1,2})/(\d{1,2})/(\d{4})\]', log_line)
    if match:
        hour, minute, day, month, year = match.groups()
        tanggal = f"{day}/{month}/{year}"
        jam = f"{hour}:{minute}"
        return tanggal, jam
    return None, None


def extract_phone_number(text: str) -> str:
    """Extract phone number. Handles formats: 62 xxx-xxxx-xxxx, +62, +1, etc."""
    # Try 62 format with spaces/dashes (standard)
    match = re.search(r'62\s+[\d\-]+', text.strip())
    if match:
        return match.group(0)
    
    # Try +62 or +1 format
    match = re.search(r'\+\d+\s*[\d\-\(\)]+', text.strip())
    if match:
        return match.group(0).strip()
    
    return ""


def is_client_chat_line(line: str, client_name: str, client_phone: str) -> bool:
    """Determine if a chat line is from the client."""
    phone_normalized = client_phone.replace(" ", "").replace("-", "").replace("+", "")
    line_lower = line.lower()
    
    # Try phone match
    if phone_normalized and phone_normalized in line.replace(" ", "").replace("-", "").replace("+", ""):
        return True
    
    # Try name match
    if client_name != "-":
        name_parts = client_name.split()
        if all(part.lower() in line_lower for part in name_parts):
            return True
    
    return False


def extract_client_name(text: str) -> str:
    """Extract client name, removing BOM if present."""
    text = text.strip()
    text = text.lstrip('\ufeff')
    
    if not text:
        return "-"
    
    # Remove "Nama klien:" prefix if present
    if 'Nama klien:' in text:
        text = text.split('Nama klien:', 1)[1].strip()
    
    if not text:
        return "-"
    
    # If it's a phone number, return "-"
    if re.match(r'^[\+]?[0-9\s\-\(\)]+$', text):
        return "-"
    
    return text


def parse_whatsapp_file(input_file: str) -> List[Dict]:
    """Parse WhatsApp chat log file (handles both formats)."""
    records = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = content.split('________________')
    row_no = 1
    
    for block in blocks:
        lines = block.strip().split('\n')
        
        if len(lines) < 1:
            continue
        
        client_name = "-"
        client_phone = ""
        phone_line_idx = -1
        
        # Find phone number and name
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Remove "Nomor klien:" prefix if present
            check_line = line_stripped.replace('Nomor klien:', '').strip()
            
            phone = extract_phone_number(check_line)
            if phone:
                client_phone = phone
                phone_line_idx = i
                
                # Check if there's a name before this phone line
                if i > 0:
                    prev_line = lines[i-1].strip()
                    if prev_line and not extract_phone_number(prev_line):
                        client_name = extract_client_name(prev_line)
                break
            
            # If we find a timestamp, no phone found yet - skip this block
            if '[' in line_stripped and ']' in line_stripped:
                break
        
        # Skip if no phone number found
        if not client_phone:
            continue
        
        # Normalize phone number
        client_phone_clean = client_phone.replace(" ", "").replace("-", "").replace("+", "")
        if client_phone_clean.startswith("62"):
            client_phone_clean = "0" + client_phone_clean
        
        # Split by "Follow up" marker
        chat_sections = []
        current_section = []
        
        for line in lines[phone_line_idx + 1:]:
            line_stripped = line.strip()
            
            if line_stripped.lower() == "follow up":
                if current_section:
                    chat_sections.append(("main", current_section))
                current_section = []
                continue
            
            current_section.append(line)
        
        if current_section:
            section_type = "followup" if len(chat_sections) > 0 else "main"
            chat_sections.append((section_type, current_section))
        
        # Process sections
        followup_counter = 0
        
        for section_idx, (section_type, section_lines) in enumerate(chat_sections):
            chat_logs = []
            first_datetime = None
            
            for line in section_lines:
                line = line.strip()
                if not line:
                    continue
                
                if '[' in line and ']' in line:
                    chat_logs.append(line)
                    
                    if first_datetime is None:
                        if section_type == "main":
                            if is_client_chat_line(line, client_name, client_phone):
                                tanggal, jam = extract_datetime_from_log(line)
                                if tanggal and jam:
                                    first_datetime = (tanggal, jam)
                        else:
                            tanggal, jam = extract_datetime_from_log(line)
                            if tanggal and jam:
                                first_datetime = (tanggal, jam)
            
            # Skip if no chat logs
            if not chat_logs:
                continue
            
            # Determine status
            if section_type == "main":
                if first_datetime:
                    tanggal_chat, jam_chat = first_datetime
                else:
                    tanggal_chat = ""
                    jam_chat = ""
                status = ""
                followup_ke = ""
            else:
                if first_datetime:
                    tanggal_chat, jam_chat = first_datetime
                else:
                    tanggal_chat = ""
                    jam_chat = ""
                status = "Follow Up"
                followup_counter += 1
                followup_ke = f"F{followup_counter}"
            
            keterangan = "\n".join(chat_logs)
            
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
    """Export records to CSV."""
    fieldnames = [
        'No', 'Tanggal Chat', 'Jam Chat', 'Nama Klien', 'Nomor Klien',
        'Status Customer', 'Channel', 'Acara', 'Tempat Acara', 'Tanggal Acara',
        'Sumber Informasi', 'Follow Up Ke', 'Status', 'Tanggal Deal', 'Produk', 'Keterangan'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()
        writer.writerows(records)


def main(input_file: str = None, output_file: str = None):
    """Main entry point."""
    if input_file is None:
        input_file = "Salinan Data Whatsapp Wati.txt"
    
    if output_file is None:
        input_path = Path(input_file)
        output_file = str(input_path.stem) + "-parsed.csv"
    
    try:
        print(f"Parsing: {input_file}")
        records = parse_whatsapp_file(input_file)
        
        export_to_csv(records, output_file)
        
        print(f"Exported {len(records)} records to {output_file}\n")
        print("Summary:")
        print(f"  - Total records: {len(records)}")
        print(f"  - Output file: {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    import sys
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else None
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    main(input_file, output_file)
