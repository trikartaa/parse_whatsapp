import docx
import os
import re
import csv
from datetime import datetime
import argparse

# Staff identifier
STAFF_NAME = "trikartainvitationsouvenir"

# Heuristic keywords
DEAL_KEYWORDS = ["deal", "order", "siap", "oke", "transfer", "kirim alamat", "dp", "lunas", "fix", "setuju"]
NOT_DEAL_KEYWORDS = ["batal", "maaf", "mahal", "nanti dulu", "tanya dulu", "pending", "cancel", "tidak jadi"]

def parse_timestamp(text):
    # Format: [18.18, 6/2/2026]
    match = re.search(r"\[(\d{1,2}\.\d{2}),\s+(\d{1,2}/\d{1,2}/\d{4})\]", text)
    if match:
        time_str, date_str = match.groups()
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H.%M")
        except ValueError:
            return None
    return None

def analyze_whatsapp_data(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    doc = docx.Document(input_path)
    
    clients = []
    current_client = None
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
            
        # Detect new client block
        has_name_label = "Nama klien:" in text
        has_number_label = "Nomor klien:" in text
        
        if has_name_label or has_number_label:
            # Extract name and number from the text which might have both or just one
            name = ""
            number = ""
            
            # Use regex to find values after labels, handling multi-line strings within the paragraph
            name_match = re.search(r"Nama klien:\s*(.*?)(?=\s*Nomor klien:|$)", text, re.DOTALL | re.IGNORECASE)
            if name_match:
                name = name_match.group(1).strip()
            
            number_match = re.search(r"Nomor klien:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
            if number_match:
                number = number_match.group(1).strip()

            # Logic to decide if we start a new client or update current
            if has_name_label or (has_number_label and not current_client):
                if current_client:
                    # Final check before appending: if name is a phone number and number is a name, swap them
                    if re.match(r"^\+?[\d\s\-]{7,}$", current_client["name"]) and any(c.isalpha() for c in current_client["number"]):
                        current_client["name"], current_client["number"] = current_client["number"], current_client["name"]
                    clients.append(current_client)
                
                current_client = {
                    "name": name if name else "Unknown",
                    "number": number,
                    "messages": []
                }
            elif has_number_label and current_client:
                # Update current client's number if it was missing
                if not current_client["number"]:
                    current_client["number"] = number
                # If name was "Unknown" but we have a name now, update it
                if name and current_client["name"] == "Unknown":
                    current_client["name"] = name
            
            continue
            
        if not current_client:
            continue
            
        # Check if line has a timestamp
        ts = parse_timestamp(text)
        if ts:
            # Extract sender and content
            header_match = re.search(r"\]\s*([^:]+):\s*(.*)", text)
            if header_match:
                sender = header_match.group(1).strip()
                content = header_match.group(2).strip()
                current_client["messages"].append({
                    "timestamp": ts,
                    "sender": sender,
                    "content": content
                })
            else:
                current_client["messages"].append({
                    "timestamp": ts,
                    "sender": "Unknown",
                    "content": text
                })
        else:
            # Continuation of previous message
            if current_client["messages"]:
                current_client["messages"][-1]["content"] += " " + text
                
    if current_client:
        # Final check for the last client: swap if labels were reversed
        if re.match(r"^\+?[\d\s\-]{7,}$", current_client["name"]) and any(c.isalpha() for c in current_client["number"]):
            current_client["name"], current_client["number"] = current_client["number"], current_client["name"]
        clients.append(current_client)
        
    # Processing each client for metrics
    results = []
    for client in clients:
        msg_list = client["messages"]
        if not msg_list:
            continue
            
        total_client_msg = sum(1 for m in msg_list if STAFF_NAME not in m["sender"].lower())
        total_staff_msg = sum(1 for m in msg_list if STAFF_NAME in m["sender"].lower())
        
        reply_speeds = [] # in minutes
        follow_ups = 0
        
        last_sender_was_client = False
        last_client_msg_time = None
        
        for i, m in enumerate(msg_list):
            is_staff = STAFF_NAME in m["sender"].lower()
            
            if not is_staff:
                last_sender_was_client = True
                last_client_msg_time = m["timestamp"]
            else:
                if last_sender_was_client:
                    # Staff replied to client
                    delta = (m["timestamp"] - last_client_msg_time).total_seconds() / 60
                    reply_speeds.append(max(0, delta))
                    last_sender_was_client = False
                
                # Check for follow up
                if i > 0:
                    prev_m = msg_list[i-1]
                    if STAFF_NAME in prev_m["sender"].lower():
                        delta = (m["timestamp"] - prev_m["timestamp"]).total_seconds() / 3600 # in hours
                        if delta > 12:
                            follow_ups += 1
                            
        avg_reply_speed = sum(reply_speeds) / len(reply_speeds) if reply_speeds else 0
        avg_reply_speed_hours = avg_reply_speed / 60
        
        # Determine status (Closing)
        full_text = " ".join([m["content"] for m in msg_list]).lower()
        closing = "Pending"
        if any(kw in full_text for kw in NOT_DEAL_KEYWORDS):
            closing = "Not Deal"
        if any(kw in full_text for kw in DEAL_KEYWORDS):
            last_text = " ".join([m["content"] for m in msg_list[-5:]]).lower()
            if any(kw in last_text for kw in DEAL_KEYWORDS):
                closing = "Deal"
            elif any(kw in last_text for kw in NOT_DEAL_KEYWORDS):
                closing = "Not Deal"

        # Extract extra info
        first_msg = msg_list[0]
        tanggal_chat = first_msg["timestamp"].strftime("%d/%m/%Y")
        jam_chat = first_msg["timestamp"].strftime("%H.%M")

        acara = ""
        tanggal_acara = ""
        date_pattern = re.search(r"(?:tanggal|tgl|acara)\s*(\d{1,2}[-/ ](?:\d{1,2}|[a-zA-Z]+)[-/ ]\d{2,4})", full_text)
        if date_pattern:
            tanggal_acara = date_pattern.group(1)
        
        produk_found = []
        if "undangan" in full_text: produk_found.append("Undangan")
        if "souvenir" in full_text: produk_found.append("Souvenir")
        if "hampers" in full_text: produk_found.append("Hampers")
        if "akrilik" in full_text: produk_found.append("Akrilik")
        if any(kw in full_text for kw in ["piring", "mug", "mangkok", "bowl"]): produk_found.append("Souvenir (Dinnerware)")
        produk = ", ".join(list(set(produk_found))) if produk_found else "Belum diketahui"

        sumber = "Belum diketahui"
        if "instagram" in full_text or " ig " in full_text: sumber = "Instagram"
        elif "facebook" in full_text or " fb " in full_text: sumber = "Facebook"
        elif "tiktok" in full_text: sumber = "TikTok"
        elif "website" in full_text: sumber = "Website"

        keterangan = " | ".join([f"{m['sender']}: {m['content']}" for m in msg_list])

        results.append({
            "No": len(results) + 1,
            "Tanggal Chat": tanggal_chat,
            "Jam Chat": jam_chat,
            "Nama Klien": client["name"],
            "Nomor Klien": client["number"],
            "Acara": acara,
            "Tempat Acara": "",
            "Tanggal Acara": tanggal_acara,
            "Sumber Informasi": sumber,
            "Follow Up Ke-": follow_ups,
            "Closing": closing,
            "Produk": produk,
            "Keterangan": keterangan,
            "Kecepatan Membalas (Jam)": round(avg_reply_speed_hours, 2)
        })
        
    # Write to CSV
    keys = ["No", "Tanggal Chat", "Jam Chat", "Nama Klien", "Nomor Klien", "Acara", "Tempat Acara", "Tanggal Acara", "Sumber Informasi", "Follow Up Ke-", "Closing", "Produk", "Keterangan", "Kecepatan Membalas (Jam)"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(results)
        
    print(f"Analysis complete. Results saved to {output_path}")
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse WhatsApp chat data from DOCX files.")
    parser.add_argument("input", help="Path to the input .docx file")
    parser.add_argument("-o", "--output", help="Path to the output .csv file (optional)")
    
    args = parser.parse_args()
    
    input_file = args.input
    output_file = args.output
    
    if not output_file:
        base = os.path.splitext(input_file)[0]
        output_file = f"{base}_Analysis.csv"
        
    analyze_whatsapp_data(input_file, output_file)
