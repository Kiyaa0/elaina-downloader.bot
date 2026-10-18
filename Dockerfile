FROM python:3.11-slim

# Install dependency sistem yang dibutuhkan (FFmpeg & Git)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Salin requirements dan install library Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh kode proyek
COPY . .

# Buat folder penyimpanan downloads sementara
RUN mkdir -p downloads

# Jalankan bot
CMD ["python", "bot.py"]
