"""
Logika Baru Segmentasi Percakapan WhatsApp
===========================================

DEFINISI SESSION/SESI:
- Satu sesi = satu "babak" percakapan
- Sesi baru dimulai ketika:
  → Marketing mengirim pesan setelah GAP > 5 jam dari pesan marketing sebelumnya
    (ini adalah Follow Up)
- Sesi pertama = Chat Pertama (tidak dihitung sebagai Follow Up)
- Sesi ke-2 dst = Follow Up ke-1, Follow Up ke-2, dll.

KECEPATAN MEMBALAS (per sesi):
- Dihitung dari PESAN PERTAMA klien dalam sesi tersebut
  → Jika klien kirim 10:30, lalu 11:00, lalu marketing balas 13:00
  → Kecepatan = 13:00 - 10:30 = 2.5 jam (diambil dari pesan PERTAMA klien)
- Dihitung setiap kali ada exchange baru dalam sesi

KETERANGAN:
- Chat paling akhir dari marketing
- Sertakan gap waktu dari pesan marketing sebelumnya

CONTOH TIMELINE:
  10:30 Klien: "Halo"
  11:00 Klien: "Ada?"
  13:00 Marketing: "Halo kak"      ← reply speed = 2.5 jam (dari 10:30)
  13:05 Marketing: "Butuh apa?"    ← ini masih sesi yang sama (gap < 5 jam)
  13:10 Klien: "Mau order"
  13:15 Marketing: "Oke"           ← reply speed = 5 menit (dari 13:10)
  
  [gap 6 jam]
  
  19:15 Marketing: "Halo kak, gimana?"  ← FOLLOW UP ke-1 (gap > 5 jam dari 13:15)
  
  [gap 10 jam]
  
  05:15+1 Marketing: "Halo kak"        ← FOLLOW UP ke-2

OUTPUT PER BARIS (1 baris per sesi):
- No
- Tanggal Chat / Jam Chat (dari pesan pertama sesi)
- Nama Klien / Nomor Klien
- Acara / Tempat Acara / Tanggal Acara
- Sumber Informasi
- Sesi (Chat Pertama / Follow Up ke-1 / ...)
- Closing
- Produk
- Keterangan (log chat sesi ini)
- Kecepatan Membalas Rata-rata (Jam) dalam sesi ini
- Pesan Terakhir Marketing
- Gap Terakhir (jam)
"""
