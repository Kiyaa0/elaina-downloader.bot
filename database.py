import sqlite3
import time
import os
from config import BASE_DIR

DB_PATH = os.path.join(str(BASE_DIR), "database.db")

def init_db():
    """Inisialisasi tabel database SQLite untuk data VIP dan Voucher"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vip_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                added_at REAL,
                expires_at REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vouchers (
                code TEXT PRIMARY KEY,
                duration_days INTEGER,
                created_at REAL,
                used_by INTEGER,
                used_at REAL
            )
        """)
        conn.commit()

# Inisialisasi DB saat modul dimuat
init_db()

def is_vip_user(user_id: int) -> bool:
    """Mengecek apakah user_id memiliki status VIP yang masih aktif"""
    now = time.time()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT expires_at FROM vip_users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            expires_at = row[0]
            if expires_at == -1 or expires_at > now:  # -1 = Permanen
                return True
    return False

def get_vip_info(user_id: int) -> dict | None:
    """Mengambil detail data VIP user"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, added_at, expires_at FROM vip_users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return {
                "user_id": row[0],
                "username": row[1],
                "added_at": row[2],
                "expires_at": row[3]
            }
    return None

def add_vip_user(user_id: int, duration_days: int = 30, username: str = "") -> float:
    """
    Menambahkan atau memperpanjang masa aktif VIP user.
    duration_days = -1 untuk permanen.
    Mengembalikan timestamp kedaluwarsa.
    """
    now = time.time()
    current = get_vip_info(user_id)
    if current and current["expires_at"] > now and current["expires_at"] != -1:
        # Perpanjang dari tanggal expired yang sudah ada
        new_expires = current["expires_at"] + (duration_days * 86400) if duration_days > 0 else -1
    else:
        new_expires = now + (duration_days * 86400) if duration_days > 0 else -1

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO vip_users (user_id, username, added_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, now, new_expires))
        conn.commit()
    return new_expires

def remove_vip_user(user_id: int) -> bool:
    """Menghapus status VIP user"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vip_users WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0

def create_voucher(code: str, duration_days: int = 30) -> str:
    """Membuat voucher baru oleh admin"""
    now = time.time()
    code = code.strip().upper()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vouchers (code, duration_days, created_at, used_by, used_at)
            VALUES (?, ?, ?, NULL, NULL)
        """, (code, duration_days, now))
        conn.commit()
    return code

def redeem_voucher(code: str, user_id: int, username: str = "") -> tuple[bool, str, int]:
    """
    Menebus kode voucher untuk mengaktifkan VIP.
    Mengembalikan (success: bool, message: str, duration_days: int)
    """
    code = code.strip().upper()
    now = time.time()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT duration_days, used_by FROM vouchers WHERE code = ?", (code,))
        row = cursor.fetchone()
        if not row:
            return False, "Kode voucher tidak ditemukan atau salah ketik.", 0
        if row[1] is not None:
            return False, "Kode voucher ini sudah pernah digunakan.", 0

        duration_days = row[0]
        cursor.execute("UPDATE vouchers SET used_by = ?, used_at = ? WHERE code = ?", (user_id, now, code))
        conn.commit()

    add_vip_user(user_id, duration_days, username)
    return True, f"Selamat! Voucher aktif. Anda mendapatkan status VIP selama {duration_days} hari.", duration_days
