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

## 3. Tujuan Produk

1.  Mengonversi file yang didukung menjadi Markdown dengan isi sedekat
    mungkin dengan sumber.
2.  Menggabungkan beberapa file menjadi satu dokumen Markdown dengan
    indeks dan batas sumber yang jelas.
3.  Menyediakan preview, edit hasil, copy ke clipboard, dan download
    `.md`.
4.  Memproses file secara lokal tanpa mengirim data ke layanan
    eksternal.
5.  Menyiapkan fondasi modular untuk Docker, server pribadi, OCR, format
    baru, CLI, dan integrasi AI opsional di masa depan.

### Bukan tujuan MVP

-   Interpretasi semantik atau ringkasan yang dihasilkan AI.
-   Akun pengguna, multi-user, histori permanen, atau kolaborasi.
-   Penyimpanan file permanen.
-   Rekonstruksi sempurna layout visual, grafik, atau diagram kompleks.
-   Dukungan untuk semua format sejak rilis pertama.

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

## 15. Roadmap

  -----------------------------------------------------------------------------------------
  Fase                    Cakupan                 Definisi selesai          Status
  ----------------------- ----------------------- ------------------------- ---------------
  0\. Setup               Repo, venv, FastAPI,    Aplikasi berjalan lokal   ✅ Selesai
                          konfigurasi, struktur   dan struktur dasar
                          modular, health check   diuji.

  1\. MVP Core            TXT, JSON, CSV;         Acceptance criteria P0    ✅ Selesai
                          Convert; preview, edit, lulus.
                          copy, download          

  2\. Dokumen             PDF teks, DOCX, XLSX,   Parser punya fixture      ✅ Selesai
                          source code             dan test.

  3\. Bundle              Multi-file, source      Satu `.md` memuat         ✅ Selesai
                          index, delimiter aman,  banyak sumber dengan
                          laporan parsial         jelas.

  4\. Image/OCR           Metadata gambar dan OCR OCR tidak menjadi         ✅ Selesai
                          lokal opsional          dependensi konversi
                                                  inti.

  5\. Container           Dockerfile, Compose,    Aplikasi dapat            ✅ Selesai
                          health check, kebijakan dijalankan di
                          temp                    container.

  6\. Server pribadi      Deployment LAN, reverse Akses terkendali dari     ⏳ Belum Mulai
                          proxy/tunnel, kontrol   perangkat yang
                          akses                   diizinkan.

  7\. Ekstensi            CLI, format tambahan,   Fitur baru tidak          ⏳ Belum Mulai
                          AI enhancement opsional merusak conversion
                                                  engine.
  -----------------------------------------------------------------------------------------

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
