# 📄➡️📝 File2MD

**Universal File-to-Markdown Converter** — Solusi lokal mandiri (*local-first*) berbasis web & CLI untuk mengonversi dokumen kompleks, spreadsheet, data tabular, source code, dan gambar menjadi Markdown (`.md`) yang bersih, terstruktur, hemat token, dan siap dijadikan konteks bagi model AI (LLM).

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)
![Tests](https://img.shields.io/badge/Tests-68%20Passed-success.svg)
![i18n](https://img.shields.io/badge/i18n-ID%20%7C%20EN-blue.svg)
![Privacy](https://img.shields.io/badge/Privacy-100%25%20Local--First-orange.svg)

---

## 🌟 Fitur Unggulan

- **🔒 100% Local-First & Zero-Cloud Retention:** Seluruh proses parsing dan konversi berjalan langsung di mesin lokal / Docker Anda. Tanpa kebocoran data ke cloud atau pihak ketiga.
- **📑 Multi-Format Document Ingestion:**
  - **Dokumen:** PDF teks (`PyMuPDF`) dengan batas halaman & metadata, Word (`.docx`) dengan heading & tabel, Excel (`.xlsx`) dengan multi-sheet extraction.
  - **Data:** CSV & TSV dengan deteksi otomatis delimiter (koma, titik koma, tab) dan escaping pipa (`|`), JSON tervalidasi dan terformat rapi.
  - **Source Code & Teks:** TXT, MD, serta 20+ bahasa pemrograman (`.py`, `.js`, `.ts`, `.sql`, `.sh`, `.html`, `.css`, dll.) dengan *safe backtick fencing*.
  - **Arsip ZIP:** Unggah arsip `.zip` dan sistem akan otomatis mengekstrak, memvalidasi ukuran, dan menyusunnya menjadi Bundle Markdown.
- **📦 Bundle Mode (Multi-File Context):** Gabungkan puluhan file sekaligus menjadi satu dokumen Markdown terstruktur lengkap dengan **Source Index** interaktif dan pelaporan kegagalan parsial (*partial failure reporting*).
- **👁️ On-Device Visual & OCR Intelligence:**
  - Ekstraksi metadata teknis gambar (resolusi, aspek rasio, color mode, ukuran file).
  - **Local OCR (Tesseract):** Pipeline preprocessing gambar (Grayscale + Kontras + Upscaling) untuk akurasi maksimal.
  - **Offline Vision AI (Salesforce BLIP):** Model vision mandiri on-device untuk menghasilkan caption dan deskripsi isi gambar tanpa membutuhkan koneksi internet atau kuota API berbayar.
- **🚀 Token-Efficient Image Markdown (Anti-Bloat):**
  - Mengeliminasi string data URI Base64 raksasa yang sering membuat model AI (ChatGPT, Claude, Gemini) mengalami *context limit choke*.
  - Menghasilkan format Markdown bersih: `![filename](filename)` disertai caption AI dan teks OCR yang hemat token.
- **🎨 Custom Export Presets Bar:**
  - **🤖 ChatGPT:** Markdown standar dengan pembatas blok konteks yang optimal.
  - **🧠 Claude XML:** Dibungkus dalam tag struktural `<document>` dan `<source>` sesuai standar prompt engineering Anthropic.
  - **🔮 Obsidian Note:** Dilengkapi YAML frontmatter (`tags`, `date`, `source`) dan callout boxes (`[!note]`).
  - **🌐 HTML Rich:** Format HTML bersih untuk pratinjau langsung di web atau platform CMS.
- **🖥️ Dual View Switcher:**
  - **📝 Raw Editor:** Editor monospace untuk menyalin atau mengedit langsung teks mentah.
  - **👁️ GitHub Preview:** Live render Markdown ala GitHub dengan syntax highlighting, tabel, dan formatting visual.
- **🕒 Riwayat Sementara 24 Jam & Janitor Auto-Purge:**
  - Penyimpanan riwayat konversi lokal berbasis SQLite dengan masa berlaku 24 jam (*TTL*).
  - Background task janitor loop yang otomatis membersihkan berkas temp dan entri riwayat yang kedaluwarsa.
  - Real-time sidebar update via HTMX, format waktu lokal browser pengguna (`HH:MM`), dan custom Context7 Toast/Confirm modal.
- **🔑 Personal API Key & PRO Tier Gating:**
  - Akses konversi langsung via terminal menggunakan header `X-API-Key: f2md_live_...`.
  - Keamanan enterprise: kunci disimpan dalam bentuk hash **SHA-256** (zero plaintext retention di database).
  - PRO Tier Gating: membatasi pembuatan API Key eksklusif untuk pengguna tier PRO dengan kartu promosi Context7.
- **🛡️ Sistem Autentikasi & Kuota Bertingkat:**
  - **Tamu (Guest):** Maksimal 10 MB per file, 5 file per bundle.
  - **Free Member:** Maksimal 50 MB per file, 15 file per bundle, riwayat 24 jam.
  - **PRO Member:** Maksimal 100 MB per file, 50 file per bundle, akses Personal API Key tak terbatas.
  - Dilengkapi toggle visibilitas password (ikon mata 👁️) dan tombol integrasi Social Login (Google & GitHub).
- **🌐 Bilingual Language Switcher (ID 🇮🇩 / EN 🇬🇧):**
  - Pengalih bahasa instan di navbar dengan penyimpanan preferensi di `localStorage`.
  - Mendukung terjemahan otomatis ke seluruh antarmuka, modal, notifikasi toast, dan hasil konversi HTMX.
- **💻 Headless CLI Tool:**
  - CLI mandiri berbasis Python (`./file2md` / `python -m app.cli`) untuk konversi dan bundling langsung dari terminal tanpa membuka browser.

---

## 🏗️ Struktur & Arsitektur Proyek

```text
file2md/
├── app/
│   ├── main.py                  # Inisialisasi FastAPI, lifespan janitor, & routes
│   ├── database.py              # Koneksi SQLite & SQLAlchemy engine
│   ├── cli.py                   # Interface Command Line Tool (file2md)
│   ├── models/                  # SQLAlchemy Database Models
│   │   ├── user.py              # Model User & tier status
│   │   ├── history.py           # Model ConversionHistory (24h TTL)
│   │   └── api_key.py           # Model ApiKey (SHA-256 hashed)
│   ├── routes/                  # API & Web Routers
│   │   ├── pages.py             # Route Web UI (Dashboard & convert-ui)
│   │   ├── conversion.py        # REST API (/api/convert, /api/bundle)
│   │   ├── auth.py              # Autentikasi JWT, cookie session, & toggle-tier
│   │   ├── history.py           # Riwayat konversi (/api/history)
│   │   ├── api_keys.py          # Manajemen Personal API Key (/api/keys)
│   │   └── oauth.py             # Social login redirect boilerplate (Google/GitHub)
│   ├── services/                # Business Logic & Orchestrators
│   │   ├── converter.py         # Main conversion orchestrator
│   │   ├── detector.py          # Deteksi tipe berkas berbasis magic bytes
│   │   ├── markdown_builder.py  # Bundle composer & Source Index generator
│   │   ├── presets.py           # Formatter presets (ChatGPT, Claude, Obsidian, HTML)
│   │   ├── security.py          # Hash password (bcrypt) & JWT token handling
│   │   ├── janitor.py           # Background cleaner berkas sementara & expired history
│   │   └── vision.py            # Local Vision AI (Salesforce BLIP Lazy Singleton)
│   ├── parsers/                 # Modular parsers (BaseParser ABC)
│   │   ├── text.py, json_parser.py, csv_parser.py, zip_parser.py
│   │   ├── code.py, pdf.py, docx.py, xlsx.py, image_parser.py
│   │   └── base.py
│   ├── templates/               # Jinja2 HTML Templates
│   │   ├── index.html           # Main Context7-inspired dashboard
│   │   └── result_partial.html  # HTMX dynamic conversion preview
│   └── static/                  # Context7 Dark Theme CSS & Styling
├── docker/
│   ├── Dockerfile               # Production image (Python 3.12 slim + Tesseract + Non-root)
│   └── compose.yaml             # Docker Compose setup (Port 8031, volume cache HF)
├── tests/                       # 68 Pytest unit & integration test cases
├── requirements.txt             # Dependensi Python
├── .env.example                 # Template variabel lingkungan
└── docs/file2md.md              # Roadmap & Product Requirements Document (PRD)
```

---

## 🚀 Cara Menjalankan

### Opsi 1: Menggunakan Docker (Direkomendasikan)

Aplikasi sudah dikemas secara lengkap dengan Docker Compose pada port **`8031`**:

```bash
# 1. Jalankan container di latar belakang
docker compose -f docker/compose.yaml up -d

# 2. Periksa status dan kesehatan container
docker compose -f docker/compose.yaml ps
```

Buka peramban di: **`http://localhost:8031`**

Untuk menghentikan container:
```bash
docker compose -f docker/compose.yaml down
```

---

### Opsi 2: Menjalankan Langsung di Lokal (Python 3.12+)

1. **Clone repository & siapkan virtual environment:**
   ```bash
   git clone https://github.com/Yusuf2204/file2md.git
   cd file2md
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependensi:**
   ```bash
   # Install PyTorch CPU (hemat bandwidth dan ramah resource)
   pip install torch --index-url https://download.pytorch.org/whl/cpu

   # Install dependensi lainnya
   pip install -r requirements.txt
   ```

3. **Install Tesseract OCR (Opsional untuk OCR gambar):**
   ```bash
   # Ubuntu / Debian
   sudo apt update && sudo apt install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-ind
   ```

4. **Konfigurasi environment:**
   ```bash
   cp .env.example .env
   ```

5. **Jalankan server aplikasi:**
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

---

## 💻 Menggunakan CLI Tool (`file2md`)

File2MD dilengkapi CLI mandiri untuk otomasi scripting di terminal:

```bash
# 1. Konversi berkas tunggal dan tampilkan di terminal
./file2md convert dokumen.pdf

# 2. Konversi dan simpan ke berkas .md
./file2md convert laporan.docx -o output.md

# 3. Gabungkan beberapa berkas sekaligus (Bundle)
./file2md bundle main.py utils.py database.py -t "Backend Context" -o bundle.md

# 4. Tentukan export preset (chatgpt, claude, obsidian, html)
./file2md convert data.xlsx --preset obsidian
```

---

## 🧪 Menjalankan Automated Tests

Seluruh parser, route autentikasi, API Key, history janitor, presets, dan endpoint diuji menggunakan Pytest:

```bash
pytest
```
*Hasil saat ini: **68 passed test cases (100% green)**.*

---

## 📡 REST API & API Key Reference

File2MD menyediakan REST API lengkap dengan dokumentasi OpenAPI interaktif di **`/docs`**:

| Method | Endpoint | Deskripsi |
| :--- | :--- | :--- |
| `GET` | `/health` | Healthcheck server (mengembalikan `{"status": "ok"}`) |
| `POST` | `/api/convert` | Mengonversi 1 berkas multipart menjadi Markdown |
| `POST` | `/api/bundle` | Menggabungkan banyak berkas menjadi 1 Bundle Markdown |
| `POST` | `/api/auth/register` | Mendaftarkan akun pengguna baru |
| `POST` | `/api/auth/login` | Masuk dan menerbitkan JWT cookie session |
| `GET` | `/api/auth/me` | Memeriksa profil dan sisa kuota akun |
| `POST` | `/api/auth/toggle-tier` | Mengubah status tier akun (Free <-> PRO) untuk testing |
| `GET` | `/api/keys` | Menampilkan daftar API Key aktif pengguna (Khusus PRO) |
| `POST` | `/api/keys` | Membuat Personal API Key baru (Khusus PRO) |
| `DELETE` | `/api/keys/{id}` | Mencabut / menonaktifkan API Key |
| `GET` | `/api/history` | Menampilkan daftar riwayat konversi 24 jam |
| `DELETE` | `/api/history/{id}` | Menghapus entri riwayat konversi tertentu |

### Contoh Request Menggunakan Personal API Key:

```bash
curl -X POST "http://localhost:8031/api/convert" \
     -H "X-API-Key: f2md_live_YOUR_PERSONAL_KEY" \
     -F "file=@laporan.pdf"
```

---

## 🗺️ Roadmap & Status Pengembangan

- [x] **Fase 0: Setup** (Struktur modular, virtual env, testing harness, healthcheck)
- [x] **Fase 1: MVP Core** (Parser TXT, JSON, CSV; Web UI live editor, copy, download)
- [x] **Fase 2: Dokumen & Kode** (Parser Source Code, PDF teks PyMuPDF, Word DOCX, Excel XLSX)
- [x] **Fase 3: Bundle Mode** (Multi-file grouping, Source Index, partial failure reporting)
- [x] **Fase 4: Image & Vision** (Metadata gambar, Tesseract OCR, Local Vision AI BLIP, Clipboard Paste)
- [x] **Fase 5: Containerization** (Dockerfile non-root, Compose port 8031, volume cache HuggingFace)
- [x] **Fase 6: Quick Wins** (Dual View Raw/GitHub, ZIP Ingestion, Janitor cleanup)
- [x] **Fase 7: CLI Tool** (Interface `file2md convert`, `file2md bundle`, runner `./file2md`)
- [x] **Fase 8: Konsep Ulang Auth** (Database SQLite, JWT Auth, Tier Kuota, Desain UI Context7)
- [x] **Fase 9: Storage & Personalisasi** (Riwayat 24 jam, Export Presets, Anti-bloat image markdown, Personal API Keys + PRO Gating, Toggle Bahasa ID/EN)
- [ ] **Fase 10: Monetisasi & Fitur Lanjutan** (Diagram-to-Mermaid Vision AI, Integrasi Payment Gateway Midtrans, Search Riwayat)

---

## 📄 Lisensi

Project ini dirancang untuk penggunaan lokal dan personal dalam pengembangan konteks AI secara mandiri, cepat, dan aman.
