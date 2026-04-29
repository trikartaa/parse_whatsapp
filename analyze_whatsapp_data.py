import docx
import os
import re

file_path = r"D:\Kerja\trikarta\Marketing\Data Whatsapp Devi.docx"

def analyze_docx(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    doc = docx.Document(path)
    
    clients = []
    current_client = None
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
            
        if text.startswith("Nama klien:"):
            if current_client:
                clients.append(current_client)
            current_client = {
                "name": text.replace("Nama klien:", "").strip(),
                "number": "",
                "messages": [],
                "status": "Unknown"
            }
        elif text.startswith("Nomor klien:") and current_client:
            current_client["number"] = text.replace("Nomor klien:", "").strip()
        elif current_client:
            current_client["messages"].append(text)
            
    if current_client:
        clients.append(current_client)
        
    print(f"Found {len(clients)} clients.")
    
    for client in clients[:5]: # Check first 5
        print(f"\n--- Client: {client['name']} ({client['number']}) ---")
        # Print last 5 messages to see how it ends
        last_msgs = client["messages"][-5:]
        for m in last_msgs:
            print(f"  {m}")
            
    # Search for "deal" or "batal" in all messages
    deal_count = 0
    batal_count = 0
    for client in clients:
        full_text = " ".join(client["messages"]).lower()
        if "deal" in full_text or "order" in full_text or "siap" in full_text:
            deal_count += 1
        if "batal" in full_text or "maaf" in full_text or "mahal" in full_text:
            batal_count += 1
            
    print(f"\nPotential Deals: {deal_count}")
    print(f"Potential Cancellations: {batal_count}")

if __name__ == "__main__":
    analyze_docx(file_path)
