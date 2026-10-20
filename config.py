import os
from pathlib import Path
from dotenv import load_dotenv

# Muat variabel environment dari .env
load_dotenv()

# Konfigurasi Token Bot Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Konfigurasi MTProto (Opsional: untuk upload file besar hingga 2000 MB / 2 GB)
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "").strip()
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "").strip()
HAS_MTPROTO = bool(TELEGRAM_API_ID and TELEGRAM_API_HASH and TELEGRAM_API_ID.isdigit())


# Konfigurasi Trakteer
TRAKTEER_URL = os.getenv("TRAKTEER_URL", "https://trakteer.id/Kiyawi").strip()
TRAKTEER_WEBHOOK_SECRET = os.getenv("TRAKTEER_WEBHOOK_SECRET", "").strip()
TRAKTEER_WEBHOOK_PORT = int(os.getenv("TRAKTEER_WEBHOOK_PORT", "8080"))

# Konfigurasi Kontak Admin
ADMIN_CONTACT = os.getenv("ADMIN_CONTACT", "https://t.me/Kiyaawi").strip()

# Direktori Penyimpanan Download Sementara
BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = str(BASE_DIR / "downloads")

# File Cookies untuk Autentikasi Ekstra (opsional: IG/FB/YT)
COOKIES_FILE = str(BASE_DIR / "cookies.txt")

# Daftar Telegram User ID Admin (dipisahkan koma di .env, misal: ADMIN_IDS=12345678,87654321)
ADMIN_IDS = set()
admin_env = os.getenv("ADMIN_IDS", "").strip()
if admin_env:
    for aid in admin_env.split(","):
        aid = aid.strip()
        if aid.isdigit():
            ADMIN_IDS.add(int(aid))

def is_admin(user_id: int) -> bool:
    """Mengecek apakah user_id adalah Admin/Owner bot"""
    return user_id in ADMIN_IDS

def is_vip(user_id: int) -> bool:
    """Mengecek apakah user_id memiliki status VIP aktif (dari database)"""
    try:
        from database import is_vip_user
        return is_vip_user(user_id)
    except Exception:
        return False

def has_premium_access(user_id: int) -> bool:
    """Mengecek apakah user memiliki hak akses istimewa (Admin ATAU VIP)"""
    return is_admin(user_id) or is_vip(user_id)

# Batasan Download (User Biasa)
MAX_FILE_SIZE_MB = 50
MAX_DURATION_SECONDS = 600  # 10 menit
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "3"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "900"))  # 15 menit (900 detik)


