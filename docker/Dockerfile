FROM python:3.12-slim

# Install Tesseract OCR dan curl untuk healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ind \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Buat user non-root untuk keamanan (PRD Bab 13)
RUN useradd -m -u 1000 appuser

WORKDIR /app

# 1. Install PyTorch khusus CPU terlebih dahulu (Hemat 2.3 GB!)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 2. Install requirements lainnya (termasuk SQLAlchemy)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code project
COPY app/ ./app/
COPY docs/ ./docs/

# Siapkan direktori data, temp, dan cache Hugging Face dengan hak milik appuser
RUN mkdir -p data temp /home/appuser/.cache/huggingface \
    && chown -R appuser:appuser /app /home/appuser

ENV HF_HOME=/home/appuser/.cache/huggingface

# Beralih ke user non-root
USER appuser

# Healthcheck menggunakan endpoint /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]