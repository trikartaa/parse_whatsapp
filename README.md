# 📊 WhatsApp Marketing Data Parser

Tool untuk menganalisis data chat WhatsApp dari file `.docx` dan mengekspor hasilnya ke format `.csv` yang terstruktur.

## 📋 Fitur

- Mengekstrak informasi klien (Nama & Nomor)
- Menghitung **kecepatan membalas** pesan (dalam jam)
- Mendeteksi jumlah **follow up** yang dilakukan
- Menentukan status **Closing** (Deal / Not Deal / Pending)
- Mengidentifikasi **Produk** yang diminati
- Menyimpan seluruh **riwayat chat** sebagai keterangan

## 🚀 Cara Clone & Setup

### 1. Clone Repository

```bash
git clone [url-repositori-anda]
cd Marketing
```

### 2. Buat Virtual Environment

```bash
python -m venv .venv
```

### 3. Aktifkan Virtual Environment

**Windows:**
```powershell
.venv\Scripts\activate
```

**Mac/Linux:**
```bash
source .venv/bin/activate
```

### 4. Instal Library yang Dibutuhkan

```bash
pip install -r requirements.txt
```

---

## ⚙️ Cara Menjalankan Tool

Semua perintah dijalankan melalui `main.py` dengan dua mode: **parse** dan **inspect**.

### 1. Mode `parse` — Analisis & Ekspor ke CSV

Menganalisis file `.docx` dan menghasilkan laporan `.csv`.

```powershell
.venv\Scripts\python main.py parse "NamaFile.docx"
```

> Output CSV akan otomatis dibuat di folder yang sama dengan nama `NamaFile_Analysis.csv`.

**Dengan nama output kustom:**
```powershell
.venv\Scripts\python main.py parse "NamaFile.docx" -o "Hasil_Analisis.csv"
```

**Contoh:**
```powershell
.venv\Scripts\python main.py parse "Data Whatsapp Devi.docx" -o "Laporan_Devi.csv"
```

---

### 2. Mode `inspect` — Lihat Struktur File

Menampilkan isi mentah file `.docx` untuk memverifikasi struktur data sebelum diproses.

```powershell
.venv\Scripts\python main.py inspect "NamaFile.docx"
```

**Menentukan jumlah baris yang ditampilkan (default: 50):**
```powershell
.venv\Scripts\python main.py inspect "NamaFile.docx" -n 30
```

---

## 📂 Struktur File

```
Marketing/
├── main.py                  # Pintu masuk utama, menjalankan semua perintah
├── whatsapp_parser.py       # Logika inti analisis data
├── inspect_whatsapp_data.py # Alat untuk mengintip struktur file Word
├── requirements.txt         # Daftar library yang dibutuhkan
├── .gitignore               # File-file yang dikecualikan dari Git
└── .venv/                   # Virtual environment (tidak diikutkan ke Git)
```

## 📄 Format Output CSV

| Kolom | Keterangan |
|---|---|
| No | Nomor urut |
| Tanggal Chat | Tanggal pesan pertama |
| Jam Chat | Jam pesan pertama |
| Nama Klien | Nama klien dari data |
| Nomor Klien | Nomor WhatsApp klien |
| Acara | Jenis acara (jika terdeteksi) |
| Tempat Acara | Lokasi acara (jika terdeteksi) |
| Tanggal Acara | Tanggal acara (jika terdeteksi) |
| Sumber Informasi | Asal informasi (Instagram, dll.) |
| Follow Up Ke- | Berapa kali staff melakukan follow up |
| Closing | Status: **Deal** / **Not Deal** / **Pending** |
| Produk | Produk yang diminati klien |
| Keterangan | Seluruh isi percakapan |
| Kecepatan Membalas (Jam) | Rata-rata waktu staff membalas pesan |
