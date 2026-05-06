#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert WhatsApp data from 'Nama klien:' format to standard format.

Format input (Nadine):
    Nama klien: Marvel Gryna
    Nomor klien: +1 (213) 509-7238
    [chat logs...]

Format output (standard):
    Marvel Gryna
    +1 (213) 509-7238
    [chat logs...]
"""

import re
from pathlib import Path


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to format: 62 xxx-xxxx-xxxx
    Handle formats like:
    - +62 81256788147 → 62 812-5678-8147
    - +1 (213) 509-7238 → 1 213-509-7238 (keep as-is, non-Indonesian)
    """
    phone = phone.strip()
    
    # Remove parentheses
    phone = phone.replace('(', '').replace(')', '')
    
    # Extract digits and +/- signs
    phone_clean = re.sub(r'[^\d\+\-]', '', phone)
    
    # Remove leading +
    if phone_clean.startswith('+'):
        phone_clean = phone_clean[1:]
    
    # Get digits only
    digits = re.sub(r'[^\d]', '', phone_clean)
    
    if not digits:
        return phone  # Return as-is if can't parse
    
    # Get country code and number
    if digits.startswith('62'):
        # Indonesian number
        country = '62'
        number = digits[2:]
    elif digits.startswith('1'):
        # US/international number
        country = '1'
        number = digits[1:]
    else:
        # Unknown format, return as-is
        return phone
    
    # Format as: XX xxx-xxxx-xxxx
    if len(number) >= 10:
        # Standard format: xxx-xxxx-xxxx
        formatted = f"{country} {number[0:3]}-{number[3:7]}-{number[7:11]}"
    else:
        # If shorter, just add hyphens where sensible
        formatted = f"{country} {number}"
    
    return formatted


def convert_format(input_file: str, output_file: str = None):
    """
    Convert WhatsApp export from 'Nama klien:' format to standard format.
    """
    if output_file is None:
        input_path = Path(input_file)
        output_file = str(input_path.stem) + "-converted.txt"
    
    # Read input file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by separator
    blocks = content.split('________________')
    converted_blocks = []
    
    for block in blocks:
        lines = block.strip().split('\n')
        if not lines or not lines[0].strip():
            continue
        
        converted_lines = []
        header_count = 0  # Track how many header lines we've processed
        
        for line in lines:
            line = line.rstrip()
            
            # Skip empty lines at start
            if not line.strip() and header_count < 2:
                continue
            
            # Extract name from "Nama klien:" line
            if 'Nama klien:' in line:
                nama = line.split('Nama klien:', 1)[1].strip()
                converted_lines.append(nama)
                header_count += 1
                continue
            
            # Extract phone from "Nomor klien:" line
            if 'Nomor klien:' in line:
                nomor = line.split('Nomor klien:', 1)[1].strip()
                nomor_normalized = normalize_phone_number(nomor)
                converted_lines.append(nomor_normalized)
                header_count += 1
                continue
            
            # Keep all other lines (chat logs, etc.)
            if line.strip():
                converted_lines.append(line)
                header_count = max(header_count, 2)  # Past headers now
        
        # Join and add to output
        if converted_lines:
            converted_blocks.append('\n'.join(converted_lines))
    
    # Write output file
    output_content = '________________\n\n'.join(converted_blocks)
    output_content += '\n\n________________'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_content)
    
    print(f"✓ Converted: {input_file}")
    print(f"✓ Output: {output_file}")
    print(f"✓ Blocks processed: {len(converted_blocks)}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python convert_whatsapp_format.py <input_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    convert_format(input_file, output_file)
