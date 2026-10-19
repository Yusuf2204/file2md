# 📄➡️📝 File2MD

**Universal File-to-Markdown Converter** — Aplikasi lokal berbasis web untuk mengonversi berbagai jenis dokumen, spreadsheet, data, source code, dan gambar menjadi Markdown (`.md`) yang bersih, terstruktur, dan siap dijadikan konteks bagi model AI.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)
![Tests](https://img.shields.io/badge/Tests-35%20Passed-success.svg)
![Privacy](https://img.shields.io/badge/Privacy-100%25%20Local--First-orange.svg)

---

## 🌟 Fitur Unggulan

- **🔒 100% Local-First & Privacy-Focused:** Seluruh proses konversi berjalan di mesin lokal Anda. Tidak ada data atau file yang dikirim ke cloud/pihak ketiga.
- **📑 Multi-Format Parsing:**
  - **Dokumen:** PDF teks (`PyMuPDF`) dengan batas halaman, Word (`.docx`) dengan heading & tabel, Excel (`.xlsx`) dengan ekstraksi multi-worksheet.
  - **Data:** CSV & TSV dengan deteksi otomatis delimiter (koma, titik koma, tab) dan escaping pipa (`|`), JSON tervalidasi dan terformat rapi.
  - **Source Code & Teks:** TXT, MD, serta 20+ bahasa pemrograman (`.py`, `.js`, `.ts`, `.sql`, `.sh`, `.html`, `.css`, dll.) dengan *safe backtick fencing*.
- **📦 Bundle Mode (Multi-File Context):** Gabungkan banyak file sekaligus ke dalam satu dokumen Markdown terstruktur lengkap dengan **Source Index** otomatis dan penanganan kegagalan parsial.
- **👁️ Visual & Image Intelligence:**
  - Ekstraksi metadata teknis gambar (resolusi, rasio aspek, color mode, ukuran file).
  - **Local OCR (Tesseract)** dengan pipeline optimasi preprocessing (Grayscale + Kontras + Upscaling).
  - **On-Device Vision AI (Salesforce BLIP):** Model AI lokal mandiri untuk mendeskripsikan isi visual gambar ke dalam Markdown tanpa butuh API eksternal.
- **📋 Seamless Clipboard UX:**
  - Drag-and-drop & file picker.
  - **Paste Langsung (`Ctrl + V`):** Salin gambar atau screenshot dari web/clipboard dan langsung tempelkan ke aplikasi tanpa perlu menyimpan ke disk.
  - Live Markdown Editor, 1-Click Copy ke clipboard, dan download `.md`.

---

## 🏗️ Arsitektur & Tech Stack

```text
file2md/
├── app/
│   ├── main.py                  # Inisialisasi FastAPI & route registration
│   ├── routes/
│   │   ├── pages.py             # Route UI (Jinja2 + HTMX)
│   │   └── conversion.py        # REST API (/api/convert, /api/bundle)
│   ├── services/
│   │   ├── converter.py         # Orchestrator konversi & lifecycle cleanup
│   │   ├── detector.py          # Format detector (magic bytes & mime)
│   │   ├── markdown_builder.py  # Bundle composer & Source Index
│   │   └── vision.py            # Local Vision AI (HuggingFace BLIP Lazy Singleton)
│   ├── parsers/                 # Modular parsers (BaseParser ABC)
│   │   ├── text.py, json_parser.py, csv_parser.py
│   │   ├── code.py, pdf.py, docx.py, xlsx.py, image_parser.py
│   ├── templates/               # Jinja2 HTML templates
│   └── static/                  # Vanilla CSS styling
├── docker/
│   ├── Dockerfile               # Production image (Python 3.12 slim + Tesseract + Non-root)
│   └── compose.yaml             # Docker Compose setup (Port 8031)
├── tests/                       # 35 Pytest unit & integration tests
├── requirements.txt             # Dependensi Python
└── docs/file2md.md              # Product Requirements Document (PRD)
```

---

## 🚀 Cara Menjalankan

### Opsi 1: Menggunakan Docker (Direkomendasikan)

Aplikasi sudah dikemas dengan Docker Compose yang terisolasi di port **`8031`** dan user non-root yang aman:

```bash
# Jalankan container di latar belakang
docker compose -f docker/compose.yaml up -d

# Periksa status
docker compose -f docker/compose.yaml ps
```

Buka browser di: **`http://localhost:8031`**

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
   # Install PyTorch CPU (hemat kuota)
   pip install torch --index-url https://download.pytorch.org/whl/cpu

   # Install dependensi lainnya
   pip install -r requirements.txt
   ```

3. **Install Tesseract OCR (Opsional untuk fitur OCR gambar):**
   ```bash
   # Ubuntu / Debian
   sudo apt update && sudo apt install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-ind
   ```

4. **Jalankan server aplikasi:**
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

Buka browser di: **`http://localhost:8000`**

---

## 🧪 Menjalankan Automated Tests

Seluruh parser, service, dan endpoint API diuji menggunakan Pytest:

```bash
pytest
```
*Hasil: 35 passed test cases (100% green).*

---

## 📡 REST API Reference

File2MD menyediakan REST API lengkap dengan dokumentasi OpenAPI interaktif di **`/docs`**:

| Method | Endpoint | Deskripsi |
| :--- | :--- | :--- |
| `GET` | `/health` | Healthcheck server (mengembalikan status `ok`) |
| `POST` | `/api/convert` | Mengonversi 1 file multipart menjadi Markdown & metadata |
| `POST` | `/api/bundle` | Menggabungkan multi-file menjadi 1 dokumen Markdown lengkap |
| `GET` | `/` | Web UI Dashboard |

### Contoh Request API (`curl`):

```bash
# Konversi satu file
curl -X POST "http://localhost:8031/api/convert" \
     -F "file=@laporan.docx"

# Gabungkan beberapa file (Bundle)
curl -X POST "http://localhost:8031/api/bundle" \
     -F "files=@script.py" \
     -F "files=@data.csv" \
     -F "title=Backend Context"
```

---

## 🗺️ Roadmap & Status Pengembangan

- [x] **Fase 0: Setup** (Struktur modular, virtual env, testing harness, healthcheck)
- [x] **Fase 1: MVP Core** (Parser TXT, JSON, CSV; Web UI live editor, copy, download)
- [x] **Fase 2: Dokumen & Kode** (Parser Source Code, PDF teks PyMuPDF, Word DOCX, Excel XLSX)
- [x] **Fase 3: Bundle Mode** (Multi-file grouping, Source Index, partial failure reporting)
- [x] **Fase 4: Image & Vision** (Metadata gambar, Tesseract OCR, Local Vision AI BLIP, Clipboard Paste)
- [x] **Fase 5: Containerization** (Dockerfile non-root, Compose port 8031, persistent volume cache)
- [ ] **Fase 6: Server Pribadi** (Deployment LAN, reverse proxy Nginx, kontrol akses)
- [ ] **Fase 7: Ekstensi** (CLI Tool `file2md`, format lanjutan, integrasi LLM eksternal)

---

## 📄 Lisensi

Project ini dirancang untuk penggunaan lokal dan personal dalam pengembangan konteks AI secara mandiri dan aman.

