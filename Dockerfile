FROM python:3.11-slim

# Tidak perlu compile; hemat ruang
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Dependency sistem untuk OpenCV headless (baca gambar JPEG/PNG)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies dulu agar layer cache efisien
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baru salin kode sumber
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
