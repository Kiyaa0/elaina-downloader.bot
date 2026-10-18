import os
from pathlib import Path
from dotenv import load_dotenv

# Muat variabel environment dari .env
load_dotenv()

# Konfigurasi Token Bot Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Direktori Penyimpanan Download Sementara
BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = str(BASE_DIR / "downloads")

# File Cookies untuk Autentikasi Ekstra (opsional: IG/FB/YT)
COOKIES_FILE = str(BASE_DIR / "cookies.txt")

# Batasan Download
MAX_FILE_SIZE_MB = 50
MAX_DURATION_SECONDS = 600  # 10 menit
RATE_LIMIT_PER_MINUTE = 5
