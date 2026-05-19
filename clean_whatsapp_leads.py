import pandas as pd
import argparse
import os
import sys

# Memastikan terminal bisa mencetak karakter khusus / emoji
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def analyze_outbound_leads(input_file):
    """
    Fungsi untuk menganalisa file CSV Whatsapp dan menampilkan
    LEAD NEW (Outbound) yaitu Lead Baru yang chat pertamanya 
    diinisiasi oleh pihak Trikarta.
    """
    if not os.path.exists(input_file):
        print(f"Error: File tidak ditemukan di {input_file}")
        return

    print(f"Membaca file: {input_file}")
    
    try:
        # Membaca data CSV
        df = pd.read_csv(input_file)
        
        # Membersihkan spasi pada nama kolom untuk mencegah error
        df.columns = df.columns.str.strip()
        
        # Memastikan kolom yang dibutuhkan tersedia
        required_columns = ['Status', 'Status Customer', 'Keterangan', 'Nama Klien', 'Nomor Klien']
        for col in required_columns:
            if col not in df.columns:
                print(f"Error: Kolom '{col}' tidak ditemukan dalam file CSV.")
                return
        
        # Filter: Status = "Lead" dan Status Customer = "New"
        mask_status = df['Status'].astype(str).str.strip().str.lower() == 'lead'
        mask_customer_new = df['Status Customer'].astype(str).str.strip().str.lower() == 'new'
        
        filtered_df = df[mask_status & mask_customer_new].copy()
        
        print(f"Ditemukan {len(filtered_df)} baris dengan Status: Lead dan Customer: New.")
        print("\n" + "=" * 80)
        print("DAFTAR [LEAD NEW (Outbound)] - Chat Pertama dari Trikarta:")
        print("=" * 80)
        
        count = 1
        for idx, row in filtered_df.iterrows():
            keterangan_asli = str(row['Keterangan']) if pd.notna(row['Keterangan']) else ""
            
            # Ekstrak baris chat, abaikan baris kosong atau label tambahan jika ada
            # Gunakan replace('\r', '') untuk mencegah error tumpuk teks (carriage return) di terminal Windows
            lines = keterangan_asli.split('\n')
            chat_lines = [line.replace('\r', '').strip() for line in lines if line.strip() and not line.strip().startswith('[LEAD')]
            
            if chat_lines:
                first_chat = chat_lines[0].lower()
                # Cek apakah pengirim chat pertama adalah trikarta
                if '] trikarta' in first_chat:
                    nama = str(row.get('Nama Klien', 'Tidak Diketahui')).replace('\r', '').replace('\n', '').strip()
                    nomor = str(row.get('Nomor Klien', 'Tidak Diketahui')).replace('\r', '').replace('\n', '').strip()
                    marketing = str(row.get('Marketing', 'Tidak Diketahui')).replace('\r', '').replace('\n', '').strip()
                    
                    print(f"{count}. Nama Klien: {nama}")
                    print(f"   Nomor HP  : {nomor}")
                    print(f"   Marketing : {marketing}")
                    print(f"   Log Chat  : {chat_lines[0]}")
                    print("-" * 80)
                    count += 1
                    
        if count == 1:
            print("Tidak ada Lead New (Outbound) yang ditemukan di file ini.")
            
        print("Selesai.\n")
            
    except Exception as e:
        print(f"Terjadi kesalahan saat memproses file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Mencari LEAD NEW (Outbound) dari file CSV Whatsapp.')
    parser.add_argument('file', help='Path ke file CSV tujuan (Wajib)')
    
    args = parser.parse_args()
    analyze_outbound_leads(args.file)
