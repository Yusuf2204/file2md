# File2MD --- Product Requirements Document (PRD)

**Nama kerja:** File2MD\
**Produk:** Universal File-to-Markdown Converter\
**Versi:** 1.0\
**Status:** Draft untuk implementasi MVP\
**Tanggal:** 19 Oktober 2026

## 1. Ringkasan Produk

File2MD adalah aplikasi lokal berbasis web untuk mengonversi berbagai
jenis file menjadi Markdown (`.md`) yang mudah dibaca, diperiksa,
disalin, dan diberikan sebagai konteks kepada AI lain. Versi awal tidak
menggunakan model AI. Sistem memanfaatkan parser dan library khusus
untuk mengekstrak konten, menormalkan struktur, dan membentuk output
Markdown.

Conversion engine harus modular dan terpisah dari UI/API sehingga dapat
digunakan melalui web, CLI, atau layanan lain, serta dipindahkan ke
server pribadi menggunakan Docker.

## 2. Masalah yang Ingin Diselesaikan

-   Konten PDF, dokumen, spreadsheet, gambar, dan source code sulit
    disiapkan sebagai konteks AI secara konsisten.
-   Menyalin konten secara manual memakan waktu dan berisiko
    menghilangkan struktur, tabel, atau informasi sumber.
-   Konversi perlu mempertahankan isi sumber tanpa mengarang
    interpretasi.
-   Pemrosesan tanpa AI mengurangi kebutuhan resource dan memungkinkan
    proses lokal tanpa layanan eksternal.

## 3. Tujuan Produk & Strategi Nilai Jual

### 3.1 Tujuan Inti Produk
1.  Mengonversi file yang didukung menjadi Markdown dengan isi sedekat
    mungkin dengan sumber.
2.  Menggabungkan beberapa file menjadi satu dokumen Markdown dengan
    indeks dan batas sumber yang jelas.
3.  Menyediakan dual view (Raw Console & GitHub Rendered), edit hasil,
    copy ke clipboard, dan download `.md`.
4.  Memproses file secara lokal dengan privasi tinggi (Zero-Retention default).
5.  Menyiapkan fondasi modular untuk Docker, server pribadi, OCR, format
    baru, CLI, dan integrasi Vision AI lokal.

### 3.2 Strategi Nilai Jual & Model Freemium
Aplikasi dirancang dengan strategi 3-Tier untuk akuisisi, retensi, dan monetisasi:

-   **Tier 1: Guest (Tanpa Login — Bebas Pakai):**
    - Akses instan tanpa registrasi via Web UI dan Clipboard Paste (`Ctrl + V`).
    - Batas ukuran file 10 MB per file, bundle maksimal 3 file.
    - Zero-retention: data langsung dihapus dari memori/disk setelah konversi.
    - Rate limit harian moderat per IP.
-   **Tier 2: Registered User (Free Login):**
    - Meningkatkan batas upload (50 MB per file, bundle hingga 15 file).
    - Cloud/Local Temporary History: riwayat konversi tersimpan selama 24 jam sebelum dihapus otomatis (TTL).
    - Custom Export Presets: template pembungkus prompt AI (ChatGPT, Claude, Notion/Obsidian).
    - Kuota Personal API Key gratis (100 request/bulan).
-   **Tier 3: Pro / Enterprise (Premium Berbayar):**
    - Diagram-to-Mermaid AI: mengubah foto flowchart/arsitektur menjadi kode Mermaid.js.
    - Bulk Folder/ZIP Ingestion tanpa batas ukuran.
    - Lisensi Self-Hosted Enterprise: paket Docker on-premise siap pakai untuk perusahaan/instansi dengan SSO dan audit log.
    - Unlimited API Access.

### 3.3 Kebijakan Penyimpanan & Auto-Cleanup (Hygiene)
-   File upload sementara di `temp/` wajib dihapus seketika via `finally:` setelah proses selesai.
-   Background janitor task membersihkan orphan temp files yang berumur > 30 menit.
-   Riwayat konversi akun terdaftar memiliki masa kadaluarsa otomatis 24 jam (Time-To-Live).

## 4. Pengguna Sasaran

-   Developer yang ingin menggabungkan source code, konfigurasi, log,
    dan SQL sebagai konteks AI.
-   Pengguna yang ingin mengubah dokumen dan data menjadi Markdown.
-   Pengguna yang ingin mengemas beberapa file sebagai satu konteks
    dengan sumber yang tetap jelas.
-   Pemilik server pribadi yang ingin menjalankan converter di jaringan
    lokal atau melalui domain pada tahap lanjutan.

## 5. Prinsip Produk

-   **Local-first:** proses inti berjalan di mesin tempat aplikasi
    dijalankan.
-   **Faithful conversion:** utamakan kesetiaan terhadap sumber, bukan
    interpretasi.
-   **Explicit provenance:** pertahankan nama file dan informasi sumber
    yang berguna.
-   **Modular parsers:** setiap format ditangani parser terpisah.
-   **Safe by default:** file dianggap tidak tepercaya, tidak
    dieksekusi, dan diproses dengan batasan.
-   **Incremental scope:** format ditambah berdasarkan kebutuhan,
    kualitas, dan test coverage.

## 6. Tech Stack

  -----------------------------------------------------------------------
  Komponen                Pilihan awal            Catatan
  ----------------------- ----------------------- -----------------------
  Bahasa                  Python 3.12+            Pastikan versi tersedia
                                                  dan kompatibel; pin
                                                  dependensi setelah
                                                  diuji.

  Web/API                 FastAPI + Uvicorn       REST API dan OpenAPI
                                                  otomatis.

  UI                      Jinja2 + HTMX + CSS     Tidak memerlukan
                                                  frontend build system
                                                  pada MVP.

  Upload                  `python-multipart`      Menerima file dari
                                                  form.

  PDF                     PyMuPDF                 Ekstraksi teks; PDF
                                                  scan membutuhkan OCR.

  DOCX                    `python-docx`           Heading, paragraf,
                                                  daftar, dan tabel yang
                                                  didukung.

  XLSX                    `openpyxl`              Ekstraksi per
                                                  worksheet; tangani
                                                  formula dan tabel besar
                                                  secara eksplisit.

  CSV                     `csv` dari standard     Validasi
                          library                 delimiter/encoding dan
                                                  laporkan ambiguitas.

  TXT/JSON/XML            Standard library Python Pertahankan isi dan
                                                  struktur data.

  HTML                    `markdownify` atau      Konversi struktur HTML
                          parser setara           ke Markdown.

  Gambar/OCR              Pillow + Tesseract      OCR bersifat opsional
                          (fase lanjutan)         dan dapat memerlukan
                                                  instalasi terpisah.

  Testing                 pytest + httpx          Unit test parser dan
                                                  integration test API.

  Deployment              Docker + Docker Compose Untuk pemindahan ke
                                                  server pribadi.
  -----------------------------------------------------------------------

Referensi: - Python: https://docs.python.org/3/ - FastAPI:
https://fastapi.tiangolo.com/ - PyMuPDF:
https://pymupdf.readthedocs.io/ - Docker Compose:
https://docs.docker.com/compose/

## 7. Ruang Lingkup MVP

### Prioritas format

  -----------------------------------------------------------------------
  Prioritas               Format                  Perilaku
  ----------------------- ----------------------- -----------------------
  P0                      TXT, MD                 Pertahankan isi dengan
                                                  normalisasi minimal.

  P0                      JSON                    Validasi dan tampilkan
                                                  secara konsisten tanpa
                                                  mengubah semantik.

  P0                      CSV                     Konversi menjadi tabel
                                                  Markdown untuk ukuran
                                                  yang wajar.

  P1                      PDF berbasis teks       Ekstraksi teks dan
                                                  pemisah halaman jika
                                                  relevan.

  P1                      DOCX                    Pertahankan heading,
                                                  paragraf, daftar, dan
                                                  tabel yang didukung.

  P1                      XLSX                    Setiap worksheet
                                                  menjadi bagian
                                                  terpisah.

  P1                      Source code             Pertahankan isi, nama
                                                  file, dan ekstensi.

  P2                      HTML                    Konversi heading,
                                                  paragraf, daftar, link,
                                                  dan tabel.

  P2                      PNG/JPG/JPEG            Metadata; OCR lokal
                                                  sebagai fitur terpisah.

  P3                      PPTX                    Ekstraksi teks dan
                                                  tabel per slide.

  P3                      PDF scan                OCR bila diaktifkan dan
                                                  tersedia.
  -----------------------------------------------------------------------

MVP tidak harus merilis semua prioritas sekaligus. Selesaikan dan uji P0
sebelum beralih ke P1.

### Mode pemrosesan

**Convert:** mengubah satu file menjadi satu output Markdown, dengan
fokus pada mempertahankan konten sumber.

**Bundle:** menggabungkan beberapa file menjadi satu Markdown dengan
judul, indeks sumber, nama file, dan pemisah yang konsisten. Mode ini
tidak menyimpulkan hubungan antardokumen.

## 8. Kebutuhan Fungsional

  -----------------------------------------------------------------------
  ID                      Fitur                   Kriteria
  ----------------------- ----------------------- -----------------------
  FR-01                   Upload                  Memilih satu atau
                                                  beberapa file melalui
                                                  UI.

  FR-02                   Validasi                Validasi ukuran, tipe,
                                                  dan format; ekstensi
                                                  bukan satu-satunya
                                                  dasar kepercayaan.

  FR-03                   Deteksi format          Memilih parser yang
                                                  sesuai dan menjelaskan
                                                  format yang tidak
                                                  didukung.

  FR-04                   Konversi satu file      Menghasilkan Markdown
                                                  dan melaporkan error
                                                  tanpa mengubah file
                                                  sumber.

  FR-05                   Bundle                  Menggabungkan beberapa
                                                  output dengan indeks
                                                  dan batas sumber.

  FR-06                   Preview                 Melihat hasil Markdown
                                                  sebelum ekspor.

  FR-07                   Edit                    Mengedit hasil Markdown
                                                  sebelum disalin atau
                                                  diunduh.

  FR-08                   Copy                    Menyalin hasil ke
                                                  clipboard.

  FR-09                   Download                Mengunduh hasil sebagai
                                                  `.md`.

  FR-10                   Status/error            Menampilkan status,
                                                  file yang gagal, dan
                                                  alasan yang dapat
                                                  dipahami.

  FR-11                   Cleanup                 Menghapus file
                                                  sementara setelah
                                                  proses sukses atau
                                                  gagal.

  FR-12                   API docs                Endpoint dapat diuji
                                                  melalui dokumentasi
                                                  OpenAPI FastAPI.

  FR-13                   Offline core            Konversi inti tidak
                                                  memanggil layanan
                                                  eksternal.
  -----------------------------------------------------------------------

## 9. Kebutuhan Nonfungsional

-   **Privasi:** konten file tidak dikirim ke layanan eksternal oleh
    alur inti.
-   **Keamanan:** batas upload, nama file, tipe file, waktu proses, dan
    akses direktori sementara.
-   **Integritas:** file sumber tidak diubah.
-   **Kualitas:** parser memiliki unit test dan fixture.
-   **Maintainability:** parser, service, route, UI, dan builder
    dipisahkan.
-   **Portabilitas:** berjalan lokal dan dapat dikemas dengan Docker.
-   **Logging:** log error teknis secukupnya tanpa mencatat isi dokumen
    sensitif secara default.
-   **Usability:** pesan error menjelaskan file yang bermasalah dan
    tindakan yang dapat dilakukan.
-   **Resource limits:** batas ukuran, jumlah file, baris/sel, dan waktu
    proses dapat dikonfigurasi.

## 10. Desain Output Markdown

### Convert

Output harus sedekat mungkin dengan isi sumber. Metadata tambahan hanya
digunakan jika berguna dan tidak mengaburkan konten. Pertahankan pemisah
halaman atau struktur tabel bila relevan.

### Bundle

Contoh struktur:

``` markdown
# Project Context

## Source Index
- `src/example.py` — Python source
- `docs/guide.pdf` — PDF document

---

## File: src/example.py
```python
# source content
```

------------------------------------------------------------------------

## File: docs/guide.pdf

\[Extracted content, with page boundaries where applicable\]


    ### Aturan output

    - Jangan mengarang teks, nilai tabel, nama file, atau penjelasan yang tidak ada pada sumber.
    - Bedakan hasil ekstraksi dengan metadata yang ditambahkan aplikasi.
    - Pilih pagar kode yang aman jika sumber mengandung backtick.
    - Escape karakter tabel Markdown yang dapat merusak struktur.
    - Untuk tabel terlalu besar/lebar, gunakan fallback dan jangan menghilangkan data secara diam-diam.
    - Laporkan keterbatasan ekstraksi untuk layout, gambar, formula, atau elemen yang tidak didukung.
    - Jangan meringkas atau membuang isi hanya agar output lebih pendek.

    ## 11. Arsitektur dan Struktur Direktori

    Conversion engine tidak boleh bergantung pada FastAPI atau objek request. Route memanggil service; service memilih parser; builder menyusun hasil Markdown. Engine dapat digunakan kembali oleh CLI atau worker di masa depan.

    ```text
    file2md/
    ├── app/
    │   ├── main.py
    │   ├── routes/
    │   │   ├── pages.py
    │   │   └── conversion.py
    │   ├── services/
    │   │   ├── converter.py
    │   │   ├── detector.py
    │   │   └── markdown_builder.py
    │   ├── parsers/
    │   │   ├── text.py
    │   │   ├── json_parser.py
    │   │   ├── csv_parser.py
    │   │   ├── pdf.py
    │   │   ├── docx.py
    │   │   └── code.py
    │   ├── templates/
    │   └── static/
    ├── tests/
    ├── temp/                 # runtime only; ignored by git
    ├── requirements.txt
    ├── Dockerfile
    ├── compose.yaml
    ├── .env.example
    ├── .gitignore
    └── README.md

Struktur ini adalah titik awal, bukan kontrak kaku. Tambahkan parser
sesuai kebutuhan; hindari abstraksi/plugin system yang rumit sampai
benar-benar diperlukan.

## 12. Rancangan API Awal

  -----------------------------------------------------------------------
  Method & path           Fungsi                  Catatan
  ----------------------- ----------------------- -----------------------
  `GET /`                 Halaman utama           Form upload dan
                                                  penjelasan singkat.

  `POST /api/convert`     Konversi satu file      Mengembalikan Markdown
                                                  dan metadata dasar.

  `POST /api/bundle`      Gabungkan beberapa file Mengembalikan satu
                                                  dokumen Markdown.

  `GET /health`           Health check            Tidak membocorkan
                                                  konfigurasi.

  `GET /docs`             Dokumentasi API         OpenAPI interaktif
                                                  FastAPI pada mode yang
                                                  diaktifkan.
  -----------------------------------------------------------------------

Payload dan response schema difinalisasi saat implementasi. MVP tidak
menjanjikan background jobs atau penyimpanan persisten.

## 13. Keamanan dan Privasi

-   Gunakan allowlist format dan batas upload yang dapat dikonfigurasi.
-   Buat nama file sementara secara acak; jangan menggunakan nama upload
    langsung sebagai path.
-   Jangan mengeksekusi file, macro, script, atau konten upload.
-   Bersihkan file sementara pada jalur sukses maupun exception.
-   Perlakukan parser sebagai pemroses input tidak tepercaya; perbarui
    dependensi dan batasi resource.
-   Bind ke localhost saat pengembangan; jangan expose ke jaringan
    publik secara default.
-   Sebelum deployment online, tambahkan kontrol akses/autentikasi, rate
    limiting, batas penggunaan, HTTPS, dan kebijakan retensi file.
-   Jangan log isi file atau data sensitif secara default.

## 14. Pengujian dan Acceptance Criteria

-   TXT: isi sumber dapat dikonversi tanpa perubahan yang tidak
    disengaja.
-   JSON: input valid menghasilkan output konsisten; input invalid
    menghasilkan error yang jelas.
-   CSV: baris/kolom tidak hilang pada sampel yang didukung; karakter
    pemisah di-escape.
-   Bundle: semua file sukses tercantum di indeks dan dipisahkan dengan
    benar.
-   Format tidak didukung: dilaporkan dengan jelas, bukan menghasilkan
    output kosong seolah berhasil.
-   File rusak: kegagalan satu file tidak membuat aplikasi crash secara
    keseluruhan.
-   Upload berlebih: ditolak sesuai batas.
-   Privasi: konversi tidak memerlukan layanan eksternal.
-   UI: preview, edit, copy, dan download bekerja pada output yang sama.
-   Cleanup: file sementara dibersihkan setelah sukses maupun gagal.

Target performa dan batas ukuran ditentukan berdasarkan pengujian lokal,
bukan asumsi sebelum implementasi.

## 15. Roadmap Terstruktur (Berdasarkan Kecepatan & Kompleksitas Arsitektur)

  ----------------------------------------------------------------------------------------------------------
  Fase                              Cakupan                                              Status
  --------------------------------- ---------------------------------------------------- -------------------
  **Fase 0: Setup**                 Repo, venv, FastAPI, modular layout, smoke test      ✅ Selesai

  **Fase 1: MVP Core**              TXT, JSON, CSV, Web UI, copy, download               ✅ Selesai

  **Fase 2: Dokumen & Kode**        PDF teks, DOCX, XLSX, Source code 20+ bahasa         ✅ Selesai

  **Fase 3: Bundle Mode**           Multi-file bundling, Source Index, partial report    ✅ Selesai

  **Fase 4: Image & Vision**        Metadata gambar, OCR Tesseract, Local Vision AI BLIP ✅ Selesai

  **Fase 5: Container**             Dockerfile non-root, Compose port 8031, HF volume    ✅ Selesai

  ---                               ---                                                  ---

  **Fase 6: Quick Wins**            *(Paling Cepat — Frontend & Hygiene, 0 DB)*          ✅ Selesai
                                    1. Dual View (Raw Console vs GitHub Rendered)        
                                    2. Background Janitor (Auto-cleanup temp > 30 menit) 
                                    3. ZIP / Folder Ingestion (Auto-bundle archive)  

  **Fase 7: CLI Tool**              *(Menengah — Engine Extension, 0 Auth)*              ✅ Selesai (CLI)
                                    1. CLI Interface (`file2md convert`, `file2md bundle`)
                                    2. Shortcut runner `./file2md`
                                    *(Catatan: Deployment LAN/Nginx ditunda sampai server rumah aktif)*

  ---                               ---                                                  ---

  **Fase 8: Konsep Ulang — Auth**   *(Butuh Arsitektur Baru — Database & User System)*   ⏳ Siap Dikerjakan
                                    1. Database Engine (SQLite / PostgreSQL + ORM)       
                                    2. User Authentication (Register/Login JWT)          
                                    3. Rate Limiter Tier (Guest vs Free Registered)      

  **Fase 9: Storage & Personalisasi**(Value Tier 2)*                                     ⏳ Belum Mulai
                                    1. Temporary History (Auto-delete TTL 24 jam)        
                                    2. Custom Export Presets (Obsidian, Claude, ChatGPT) 
                                    3. Personal API Key generation                       

  **Fase 10: Monetisasi & Pro**     *(Fitur Komersial & Revenue)*                        ⏳ Belum Mulai
                                    1. Diagram-to-Mermaid Vision AI                      
                                    2. Payment Gateway Integration                       
                                    3. Enterprise Self-Hosted Package (On-Premise)       
  ----------------------------------------------------------------------------------------------------------

## 16. Risiko dan Mitigasi

  -----------------------------------------------------------------------
  Risiko                              Mitigasi
  ----------------------------------- -----------------------------------
  Format dokumen kompleks             Nyatakan batas parser; buat fixture
                                      dan test.

  Output Markdown terlalu besar       Batasi input dan tampilkan ukuran;
                                      jangan membuang data diam-diam.

  Tabel tidak cocok dengan Markdown   Escape pipe dan gunakan fallback
                                      untuk tabel besar/lebar.

  OCR tidak akurat                    Tandai sebagai hasil ekstraksi yang
                                      dapat mengandung kesalahan.

  File berbahaya atau parser          Allowlist, batas resource,
  bermasalah                          dependensi terbarui, pemrosesan
                                      terisolasi.

  Sulit dipindahkan ke server         Pisahkan engine dari UI,
                                      konfigurasi melalui environment,
                                      dan siapkan Docker.

  Scope melebar                       Prioritaskan P0; tunda AI dan
                                      database sampai ada kebutuhan
                                      nyata.
  -----------------------------------------------------------------------

## 17. Keputusan yang Disepakati

-   Nama kerja: **File2MD** (dapat diubah sebelum rilis).
-   Produk: Universal File-to-Markdown Converter.
-   Tidak menggunakan model AI pada MVP.
-   Pengembangan awal berjalan lokal.
-   Backend: Python + FastAPI.
-   UI: Jinja2 + HTMX + CSS.
-   Conversion engine modular dan terpisah dari web layer.
-   Prioritas awal: TXT, JSON, CSV; berikutnya PDF, DOCX, XLSX, dan
    source code.
-   Docker dan deployment server pribadi menjadi tahap berikutnya.
-   Integrasi AI hanya fitur opsional di masa depan.

## 18. Langkah Implementasi Pertama

1.  Buat repository dan virtual environment Python.
2.  Tambahkan dependensi minimal: FastAPI, Uvicorn, Jinja2,
    `python-multipart`, pytest, dan httpx.
3.  Buat `app/main.py` dengan endpoint halaman utama dan `/health`.
4.  Buat endpoint konversi serta service/parser TXT terlebih dahulu.
5.  Tambahkan unit test sebelum melanjutkan JSON dan CSV.
6.  Siapkan `.gitignore` untuk virtual environment, file sementara,
    cache, dan artefak runtime.
7.  Dokumentasikan setup dan cara menjalankan aplikasi di `README.md`.
