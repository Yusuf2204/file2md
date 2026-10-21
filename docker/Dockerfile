# ==========================================
# Stage 1: Base / Lite Image (~350 MB - 400 MB)
# Mendukung konversi PDF, DOCX, XLSX, TXT, OCR gambar (Tesseract ID/EN),
# Web UI, API Keys, Riwayat, Presets tanpa overhead PyTorch.
# ==========================================
FROM python:3.12-slim AS lite

# Hindari pembuatan file .pyc yang tidak perlu saat build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Tesseract OCR, data bahasa, dan curl untuk healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ind \
    curl \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* /usr/share/doc/* /usr/share/man/*

# Buat user non-root untuk keamanan (PRD Bab 13)
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install base requirements (mengunci pymupdf<2.0.0 agar bebas dari onnxruntime)
COPY requirements-base.txt .
RUN pip install --no-cache-dir -r requirements-base.txt \
    && find /usr/local/lib/python3.12 -type d \( -name "tests" -o -name "test" \) -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.12 -name "*.pyc" -delete 2>/dev/null || true \
    && find /usr/local/lib/python3.12 -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Copy source code project
COPY app/ ./app/
COPY docs/ ./docs/

# Siapkan direktori data dan temp dengan hak milik appuser
RUN mkdir -p data temp \
    && chown -R appuser:appuser /app /home/appuser

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ==========================================
# Stage 2: Full AI Image (~1.6 GB)
# Menyertakan PyTorch CPU + Transformers teroptimasi
# untuk inferensi Salesforce BLIP image captioning lokal 100% offline.
# ==========================================
FROM lite AS full

USER root

# Install PyTorch CPU & Transformers lalu bersihkan file test, C++ headers, dan tools internal
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir transformers \
    && rm -rf /usr/local/lib/python3.12/site-packages/torch/test \
              /usr/local/lib/python3.12/site-packages/torch/testing \
              /usr/local/lib/python3.12/site-packages/torch/include \
              /usr/local/lib/python3.12/site-packages/torch/bin \
    && find /usr/local/lib/python3.12 -type d \( -name "tests" -o -name "test" \) -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.12 -name "*.pyc" -delete 2>/dev/null || true \
    && find /usr/local/lib/python3.12 -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Siapkan direktori cache Hugging Face dengan hak milik appuser
RUN mkdir -p /home/appuser/.cache/huggingface \
    && chown -R appuser:appuser /home/appuser

ENV HF_HOME=/home/appuser/.cache/huggingface

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
