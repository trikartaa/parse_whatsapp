import docx
import os
import re
import csv
from datetime import datetime, timedelta
import argparse

# Default staff keyword (case-insensitive, partial match)
DEFAULT_STAFF_KEYWORD = "trikarta"
FOLLOWUP_GAP_HOURS = 5  # Gap (jam) antara dua pesan marketing yang menandai follow up baru

# Heuristic keywords (Opsi 1: Lebih spesifik)
DEAL_KEYWORDS = [
    "jadi order", "sudah dp", "bukti transfer", "sudah transfer", 
    "lanjut proses", "aku ambil", "saya ambil", "fix order", "jadi ya",
    "sudah tak transfer", "sdh transfer"
]
NOT_DEAL_KEYWORDS = [
    "tidak jadi", "batal saja", "cancel", "terlalu mahal", "nanti dulu", 
    "tanya suami dulu", "tanya istri dulu", "tanya keluarga", "pending dulu", 
    "belum jadi", "gak jadi", "cancel dulu", "batal"
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def parse_timestamp(text):
    """Parse timestamp dari format [HH.MM, DD/MM/YYYY]"""
    match = re.search(r"\[(\d{1,2}\.\d{2}),\s+(\d{1,2}/\d{1,2}/\d{4})\]", text)
    if match:
        time_str, date_str = match.groups()
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H.%M")
        except ValueError:
            return None
    return None


def is_staff_sender(sender: str, keyword: str) -> bool:
    """True jika sender mengandung keyword (case-insensitive)."""
    return keyword.lower() in sender.lower()


def fmt_gap(delta_seconds: float) -> str:
    """Format gap waktu ke string yang mudah dibaca."""
    hours = delta_seconds / 3600
    if hours < 1:
        return f"{int(delta_seconds / 60)} menit"
    elif hours < 24:
        return f"{hours:.1f} jam"
    else:
        days = hours / 24
        return f"{days:.1f} hari"


# ─── Parsing dokumen ──────────────────────────────────────────────────────────

def parse_docx_clients(doc, staff_keyword):
    """Baca dokumen dan kelompokkan pesan per klien."""
    clients = []
    current_client = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        has_name_label   = "Nama klien:"   in text
        has_number_label = "Nomor klien:"  in text

        if has_name_label or has_number_label:
            name, number = "", ""

            name_match = re.search(r"Nama klien:\s*(.*?)(?=\s*Nomor klien:|$)", text, re.DOTALL | re.IGNORECASE)
            if name_match:
                name = name_match.group(1).strip()

            number_match = re.search(r"Nomor klien:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
            if number_match:
                number = number_match.group(1).strip()

            if has_name_label or (has_number_label and not current_client):
                if current_client:
                    # Swap jika label terbalik
                    if re.match(r"^\+?[\d\s\-]{7,}$", current_client["name"]) and \
                       any(c.isalpha() for c in current_client["number"]):
                        current_client["name"], current_client["number"] = \
                            current_client["number"], current_client["name"]
                    clients.append(current_client)

                current_client = {
                    "name":     name if name else "Unknown",
                    "number":   number,
                    "messages": []
                }
            elif has_number_label and current_client:
                if not current_client["number"]:
                    current_client["number"] = number
                if name and current_client["name"] == "Unknown":
                    current_client["name"] = name
            continue

        if not current_client:
            continue

        ts = parse_timestamp(text)
        if ts:
            header_match = re.search(r"\]\s*([^:]+):\s*(.*)", text)
            if header_match:
                sender  = header_match.group(1).strip()
                content = header_match.group(2).strip()
            else:
                sender  = "Unknown"
                content = text

            current_client["messages"].append({
                "timestamp": ts,
                "sender":    sender,
                "content":   content,
                "is_staff":  is_staff_sender(sender, staff_keyword)
            })
        else:
            if current_client["messages"]:
                current_client["messages"][-1]["content"] += " " + text

    if current_client:
        if re.match(r"^\+?[\d\s\-]{7,}$", current_client["name"]) and \
           any(c.isalpha() for c in current_client["number"]):
            current_client["name"], current_client["number"] = \
                current_client["number"], current_client["name"]
        clients.append(current_client)

    return clients


# ─── Segmentasi sesi ──────────────────────────────────────────────────────────

def segment_sessions(messages, gap_hours=FOLLOWUP_GAP_HOURS):
    """
    Pecah daftar pesan menjadi sesi-sesi.
    Sesi baru dimulai ketika staff mengirim pesan setelah gap > gap_hours
    dari pesan staff sebelumnya.

    Returns: list of list of messages
    """
    if not messages:
        return []

    sessions          = []
    current_session   = []
    last_staff_time   = None

    for msg in messages:
        if msg["is_staff"]:
            if last_staff_time is not None:
                gap_secs = (msg["timestamp"] - last_staff_time).total_seconds()
                if gap_secs / 3600 > gap_hours:
                    # Mulai sesi baru (Follow Up)
                    sessions.append(current_session)
                    current_session = []
            last_staff_time = msg["timestamp"]

        current_session.append(msg)

    if current_session:
        sessions.append(current_session)

    return sessions


# ─── Analisis per sesi ────────────────────────────────────────────────────────

def analyze_session(session_msgs, staff_keyword):
    """
    Hitung metrik untuk satu sesi percakapan.

    Kecepatan balas: dari pesan PERTAMA klien (dalam blok klien berurutan)
    ke pesan pertama staff setelahnya.
    """
    reply_times   = []   # list of (client_first_ts, staff_reply_ts)
    last_client_first_ts = None
    waiting_for_staff    = False

    for msg in session_msgs:
        if not msg["is_staff"]:
            # Blok klien baru: catat waktu pesan PERTAMA dalam blok ini
            if not waiting_for_staff:
                last_client_first_ts = msg["timestamp"]
                waiting_for_staff    = True
        else:
            if waiting_for_staff and last_client_first_ts is not None:
                delta = (msg["timestamp"] - last_client_first_ts).total_seconds()
                reply_times.append(max(0, delta))
                waiting_for_staff    = False
                last_client_first_ts = None

    avg_reply_secs  = sum(reply_times) / len(reply_times) if reply_times else 0
    avg_reply_hours = avg_reply_secs / 3600

    # ── Log chat sesi (format ringkas) ──────────────────────────────────
    log_parts = []
    for msg in session_msgs:
        log_parts.append(f"{msg['sender']}: {msg['content']}")
    keterangan = " | ".join(log_parts)

    # ── Pesan terakhir marketing dan gap-nya ────────────────────────────
    last_staff_msgs = [m for m in session_msgs if m["is_staff"]]
    pesan_terakhir  = ""
    gap_terakhir    = ""
    if last_staff_msgs:
        last_staff = last_staff_msgs[-1]
        pesan_terakhir = f"{last_staff['sender']}: {last_staff['content']}"

        # Gap antara pengirim marketing terakhir dan yang sebelum itu
        if len(last_staff_msgs) >= 2:
            prev_staff = last_staff_msgs[-2]
            gap_secs   = (last_staff["timestamp"] - prev_staff["timestamp"]).total_seconds()
            gap_terakhir = fmt_gap(gap_secs)
        else:
            # Hitung gap dari pesan apapun sebelum pesan terakhir marketing
            idx = session_msgs.index(last_staff)
            if idx > 0:
                gap_secs = (last_staff["timestamp"] - session_msgs[idx-1]["timestamp"]).total_seconds()
                gap_terakhir = fmt_gap(gap_secs)

    return {
        "kecepatan_membalas_jam": round(avg_reply_hours, 4),
        "keterangan":             keterangan,
        "pesan_terakhir_staff":   pesan_terakhir,
        "gap_terakhir":           gap_terakhir,
        "n_client_msg":           sum(1 for m in session_msgs if not m["is_staff"]),
        "n_staff_msg":            sum(1 for m in session_msgs if     m["is_staff"]),
    }


# ─── Ekstrasi info produk / acara / sumber ────────────────────────────────────

def extract_meta(full_text_lower):
    # ── Acara (dropdown) ───────────────────────────────────────────────
    acara = "Lainnya"
    if any(kw in full_text_lower for kw in ["pernikahan", "wedding", "nikah", "akad", "resepsi", "mempelai"]):
        acara = "Pernikahan"
    elif any(kw in full_text_lower for kw in ["corporate", "perusahaan", "kantor", "office", "instansi"]):
        acara = "Corporate"
    elif any(kw in full_text_lower for kw in ["ulang tahun", "birthday", "ultah", "hut "]):
        acara = "Ulang Tahun"

    # ── Produk (dropdown, bisa lebih dari 1) ───────────────────────────
    produk_found = []
    if any(kw in full_text_lower for kw in ["souvenir", "hampers", "akrilik", "piring", "mug", "mangkok"]):
        produk_found.append("Souvenir")
    if "undangan" in full_text_lower:
        produk_found.append("Undangan")
    if any(kw in full_text_lower for kw in ["kemasan", "packaging", "hardbox", "paperbox", "box", "kotak"]):
        produk_found.append("Kemasan")
    if "pita" in full_text_lower:
        produk_found.append("Pita")
    produk = ", ".join(list(dict.fromkeys(produk_found))) if produk_found else "Lainnya"

    # ── Sumber Informasi ──────────────────────────────────────────────
    sumber = "Belum diketahui"
    if "instagram" in full_text_lower or " ig " in full_text_lower:
        sumber = "Instagram"
    elif "facebook" in full_text_lower or " fb " in full_text_lower:
        sumber = "Facebook"
    elif "tiktok"  in full_text_lower:
        sumber = "TikTok"
    elif "website" in full_text_lower:
        sumber = "Website"

    # ── Tanggal Acara (ekstrak dari teks) ─────────────────────────────
    tanggal_acara = ""
    date_match = re.search(
        r"(?:tanggal|tgl|acara)\s*(\d{1,2}[-/ ](?:\d{1,2}|[a-zA-Z]+)[-/ ]\d{2,4})",
        full_text_lower
    )
    if date_match:
        tanggal_acara = date_match.group(1)

    return acara, produk, sumber, tanggal_acara


def determine_closing(full_text_lower, msg_list):
    closing = "Pending"
    
    # Ambil pesan dari klien saja
    client_msgs = [m["content"].lower() for m in msg_list if not m["is_staff"]]
    
    if not client_msgs:
        return closing
        
    # Gabungkan 3 pesan terakhir dari klien (Opsi 2: Fokus pesan terakhir klien)
    last_client_text = " ".join(client_msgs[-3:])
    full_client_text = " ".join(client_msgs)
    
    # Cek pesan terakhir klien dulu (Prioritas tinggi)
    if any(kw in last_client_text for kw in NOT_DEAL_KEYWORDS):
        closing = "Not Deal"
    elif any(kw in last_client_text for kw in DEAL_KEYWORDS):
        closing = "Deal"
    else:
        # Jika tidak ada di pesan terakhir, cek keseluruhan pesan klien
        if any(kw in full_client_text for kw in NOT_DEAL_KEYWORDS):
            closing = "Not Deal"
        elif any(kw in full_client_text for kw in DEAL_KEYWORDS):
            closing = "Deal"
            
    return closing


# ─── Entry point ──────────────────────────────────────────────────────────────

def analyze_whatsapp_data(input_path, output_path, staff_keyword=DEFAULT_STAFF_KEYWORD,
                          gap_hours=FOLLOWUP_GAP_HOURS):
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    doc     = docx.Document(input_path)
    clients = parse_docx_clients(doc, staff_keyword)

    CSV_KEYS = [
        "No", "Tanggal Chat", "Jam Chat",
        "Nama Klien", "Nomor Klien",
        "Acara", "Tempat Acara", "Tanggal Acara",
        "Sumber Informasi",
        "Follow Up Ke-",
        "Closing", "Produk",
        "Keterangan",
        "Kecepatan Membalas (Jam)",
    ]

    rows   = []
    row_no = 0

    for client in clients:
        msg_list = client["messages"]
        if not msg_list:
            continue

        # Meta dari keseluruhan percakapan
        full_text  = " ".join(m["content"] for m in msg_list).lower()
        acara, produk, sumber, tanggal_acara = extract_meta(full_text)
        closing = determine_closing(full_text, msg_list)

        # Segmentasi sesi
        sessions = segment_sessions(msg_list, gap_hours=gap_hours)

        for ses_idx, session in enumerate(sessions):
            if not session:
                continue

            row_no += 1
            first_msg = session[0]
            tanggal   = first_msg["timestamp"].strftime("%d/%m/%Y")
            jam       = first_msg["timestamp"].strftime("%H.%M")

            # Follow Up Ke- label: kosong untuk Chat Pertama, F1/F2/F3 untuk follow up
            if ses_idx == 0:
                followup_label = ""
            else:
                followup_label = f"F{ses_idx}"

            metrics = analyze_session(session, staff_keyword)

            # Keterangan: hanya log pesan dari sesi ini
            keterangan = metrics["keterangan"]

            rows.append({
                "No":                       row_no,
                "Tanggal Chat":             tanggal,
                "Jam Chat":                 jam,
                "Nama Klien":               client["name"],
                "Nomor Klien":              client["number"],
                "Acara":                    acara,
                "Tempat Acara":             "",
                "Tanggal Acara":            tanggal_acara,
                "Sumber Informasi":         sumber,
                "Follow Up Ke-":            followup_label,
                "Closing":                  closing,
                "Produk":                   produk,
                "Keterangan":               keterangan,
                "Kecepatan Membalas (Jam)": metrics["kecepatan_membalas_jam"],
            })

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_KEYS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Selesai. {len(rows)} baris disimpan ke: {output_path}")
    return rows


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Parse WhatsApp marketing data dari DOCX ke CSV.")
    ap.add_argument("input",  help="Path ke file .docx")
    ap.add_argument("-o", "--output",  help="Path ke file .csv output (opsional)")
    ap.add_argument("--staff",  default=DEFAULT_STAFF_KEYWORD,
                    help=f"Keyword nama staff (default: '{DEFAULT_STAFF_KEYWORD}')")
    ap.add_argument("--gap",  type=float, default=FOLLOWUP_GAP_HOURS,
                    help=f"Gap jam untuk mendeteksi follow up (default: {FOLLOWUP_GAP_HOURS})")

    args = ap.parse_args()

    out = args.output
    if not out:
        base = os.path.splitext(args.input)[0]
        out  = f"{base}_Analysis.csv"

    analyze_whatsapp_data(args.input, out,
                          staff_keyword=args.staff,
                          gap_hours=args.gap)
