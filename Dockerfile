FROM python:3.11-slim

# Tidak perlu compile; hemat ruang
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies dulu agar layer cache efisien
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baru salin kode sumber
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
