import re
import time
from collections import defaultdict
from config import RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS, is_admin

# Tracker rate limit memori: user_id -> list of timestamps
_user_requests = defaultdict(list)

# Mapping URL ke Platform
PLATFORM_PATTERNS = [
    (r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/.+", "YouTube", "📺"),
    (r"(?:https?:\/\/)?(?:www\.)?(?:tiktok\.com|vt\.tiktok\.com)\/.+", "TikTok", "🎵"),
    (r"(?:https?:\/\/)?(?:www\.)?(?:instagram\.com)\/.+", "Instagram", "📸"),
    (r"(?:https?:\/\/)?(?:www\.)?(?:facebook\.com|fb\.watch)\/.+", "Facebook", "👥"),
    (r"(?:https?:\/\/)?(?:www\.)?(?:twitter\.com|x\.com)\/.+", "X/Twitter", "🐦"),
    (r"(?:https?:\/\/)?(?:open\.)?spotify\.com\/(?:track|album|playlist|intl-[a-z]{2}\/track)\/.+", "Spotify", "🎧"),
]

def extract_url(text: str) -> str | None:
    """
    Mengekstrak URL pertama yang ditemukan di dalam teks pesan.
    """
    if not text:
        return None
    url_pattern = r"(https?:\/\/[^\s]+)"
    match = re.search(url_pattern, text.strip())
    if match:
        return match.group(0)
    return None

def detect_platform(url: str) -> tuple[str, str]:
    """
    Mendeteksi platform media sosial dari URL.
    Mengembalikan tuple: (platform_name, icon)
    """
    if not url:
        return ("Unknown", "🌐")
    
    for pattern, name, icon in PLATFORM_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return (name, icon)
            
    return ("Unknown", "🌐")

def format_size(bytes_size: int | float | None) -> str:
    """
    Mengonversi ukuran bytes menjadi format yang mudah dibaca (KB, MB, GB).
    """
    if bytes_size is None or bytes_size <= 0:
        return "Tidak diketahui"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(bytes_size)
    unit_index = 0
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}"

def format_duration(seconds: int | float | None) -> str:
    """
    Mengonversi detik ke format MM:SS atau HH:MM:SS.
    """
    if seconds is None or seconds < 0:
        return "Tidak diketahui"
    
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

from config import RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS, has_premium_access

def check_rate_limit(user_id: int) -> tuple[bool, int]:
    """
    Mengecek apakah user telah melebihi batas request rate limit.
    Maks 3 link per 15 menit untuk user biasa. Admin dan VIP bebas limit.
    Mengembalikan: (is_allowed, seconds_to_wait)
    """
    if has_premium_access(user_id):
        return True, 0

    now = time.time()
    window_start = now - float(RATE_LIMIT_WINDOW_SECONDS)
    
    # Filter request yang masih dalam rentang waktu (15 menit terakhir)
    timestamps = [t for t in _user_requests[user_id] if t > window_start]
    _user_requests[user_id] = timestamps
    
    if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        oldest_request = timestamps[0]
        wait_seconds = int(float(RATE_LIMIT_WINDOW_SECONDS) - (now - oldest_request)) + 1
        return False, max(1, wait_seconds)
    
    # Catat request baru
    _user_requests[user_id].append(now)
    return True, 0

def get_user_quota_info(user_id: int) -> dict:
    """
    Mengambil informasi sisa kuota link unduhan dan waktu reset pengguna.
    Mengembalikan dict berisi:
    - is_unlimited (bool): True jika Admin/VIP
    - remaining (int): Sisa kuota link dalam window saat ini
    - max_limit (int): Batas maksimal link (3)
    - reset_in_seconds (int): Detik sampai kuota ter-reset
    - reset_in_str (str): Format menit dan detik sampai kuota reset
    """
    if has_premium_access(user_id):
        return {
            "is_unlimited": True,
            "remaining": 9999,
            "max_limit": RATE_LIMIT_MAX_REQUESTS,
            "reset_in_seconds": 0,
            "reset_in_str": "Unlimited"
        }

    now = time.time()
    window_start = now - float(RATE_LIMIT_WINDOW_SECONDS)
    timestamps = [t for t in _user_requests.get(user_id, []) if t > window_start]
    _user_requests[user_id] = timestamps

    used = len(timestamps)
    remaining = max(0, RATE_LIMIT_MAX_REQUESTS - used)

    if timestamps:
        oldest = timestamps[0]
        reset_in = max(1, int(float(RATE_LIMIT_WINDOW_SECONDS) - (now - oldest)))
    else:
        reset_in = 0

    menit = reset_in // 60
    detik = reset_in % 60
    reset_str = f"{menit}m {detik}s" if menit > 0 else f"{detik}s"

    return {
        "is_unlimited": False,
        "remaining": remaining,
        "max_limit": RATE_LIMIT_MAX_REQUESTS,
        "reset_in_seconds": reset_in,
        "reset_in_str": reset_str
    }

