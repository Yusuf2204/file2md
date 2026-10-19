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

# Copy requirements dan install dependensi
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code project
COPY app/ ./app/
COPY docs/ ./docs/

# Siapkan direktori temp untuk runtime dan atur permission
RUN mkdir -p temp && chown -R appuser:appuser /app

# Beralih ke user non-root
USER appuser

# Healthcheck menggunakan endpoint /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]