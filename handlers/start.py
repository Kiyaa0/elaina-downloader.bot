from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import MAX_FILE_SIZE_MB, MAX_DURATION_SECONDS
from utils import format_duration
import time

def get_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Membuat keyboard navigasi menu utama.
    """
    from config import TRAKTEER_URL
    keyboard = [
        [
            InlineKeyboardButton("📖 Panduan Lengkap", callback_data="menu|help"),
            InlineKeyboardButton("🌐 Platform Didukung", callback_data="menu|platforms")
        ],
        [
            InlineKeyboardButton("⚡ Cek Status Bot", callback_data="menu|ping"),
            InlineKeyboardButton("ℹ️ Tentang Bot", callback_data="menu|about")
        ],
        [
            InlineKeyboardButton("☕ Dukung & Beli VIP (Trakteer)", url=TRAKTEER_URL)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk perintah /start.
    """
    user_name = update.effective_user.first_name if update.effective_user else "Pengguna"
    pesan = (
        f"👋 Halo, <b>{user_name}</b>!\n\n"
        "Selamat datang di <b>Media Downloader Bot</b> 🚀\n\n"
        "Kirimkan tautan link video atau lagu langsung ke chat ini, atau pilih menu di bawah:"
    )
    await update.message.reply_text(pesan, reply_markup=get_menu_keyboard(), parse_mode="HTML")

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk perintah /menu.
    """
    pesan = (
        "📋 <b>MENU UTAMA BOT DOWNLOADER</b>\n\n"
        "Silakan pilih menu bantuan atau informasi di bawah ini:"
    )
    await update.message.reply_text(pesan, reply_markup=get_menu_keyboard(), parse_mode="HTML")

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk perintah /ping mengecek latensi server.
    """
    start_time = time.time()
    msg = await update.message.reply_text("🏓 <i>Pinging server...</i>", parse_mode="HTML")
    latency_ms = int((time.time() - start_time) * 1000)
    await msg.edit_text(
        f"🏓 <b>Pong!</b>\n"
        f"⚡ Kecepatan Respon: <b>{latency_ms} ms</b>\n"
        f"🟢 Status: <b>Online & Siap Mengunduh</b>",
        parse_mode="HTML"
    )

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk perintah /id agar user bisa mengetahui User ID Telegram dan status perannya.
    """
    user = update.effective_user
    chat = update.effective_chat
    user_id = user.id if user else 0
    chat_id = chat.id if chat else 0
    from config import is_admin, is_vip
    from database import get_vip_info

    if is_admin(user_id):
        role = "👑 <b>Admin (Owner / No Limit)</b>"
        extra_info = "⚡ <i>Anda memiliki otoritas penuh atas bot ini.</i>"
    elif is_vip(user_id):
        v_info = get_vip_info(user_id)
        if v_info and v_info["expires_at"] == -1:
            exp_str = "Permanen"
        elif v_info:
            import datetime
            exp_str = datetime.datetime.fromtimestamp(v_info["expires_at"]).strftime("%d-%m-%Y %H:%M")
        else:
            exp_str = "Aktif"
        role = f"⭐ <b>VIP Member</b> (Berlaku hingga: {exp_str})"
        extra_info = "✨ <i>Terima kasih atas dukungannya! Anda menikmati akses unduhan tanpa batas.</i>"
    else:
        role = "👤 <b>User Reguler</b> (Maks 3 link/15 menit)"
        extra_info = "💡 <i>Ketik /vip untuk melihat panduan upgrade ke VIP tanpa limit.</i>"

    pesan = (
        f"🆔 <b>Informasi Akun Telegram:</b>\n\n"
        f"• <b>User ID:</b> <code>{user_id}</code>\n"
        f"• <b>Username:</b> @{user.username if user and user.username else '-'}\n"
        f"• <b>Chat ID:</b> <code>{chat_id}</code>\n"
        f"• <b>Status Peran:</b> {role}\n\n"
        f"{extra_info}"
    )
    await update.message.reply_text(pesan, parse_mode="HTML")

async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk perintah /vip: panduan donasi dan redeem voucher VIP.
    """
    from config import TRAKTEER_URL
    pesan = (
        "⭐ <b>PROGRAM VIP MEMBER (UNLIMITED ACCESS)</b>\n\n"
        "Nikmati fitur eksklusif tanpa batasan:\n"
        "• ⚡ <b>Tanpa Antrian:</b> File langsung diunduh secara instan.\n"
        "• ♾️ <b>Tanpa Batasan Link:</b> Bebas unduh sebanyak-banyaknya (No Rate Limit).\n"
        "• ⏱️ <b>Durasi Panjang:</b> Unduh video panjang (> 10 menit).\n"
        "• 🎬 <b>Resolusi Tertinggi:</b> Mendukung hingga Full HD 1080p & FLAC Lossless.\n"
        "• 📦 <b>File Besar:</b> Dukungan transfer hingga 2.000 MB (2 GB).\n\n"
        "💰 <b>Biaya VIP:</b> <b>Rp 10.000 / Bulan</b> (Rp 10.000 per bulan)\n\n"
        f"💳 <b>Cara Otomatis via Trakteer:</b>\n"
        f"1. Buka halaman Trakteer: <a href='{TRAKTEER_URL}'>teer.id/Kiyawi</a>\n"
        "2. Masukkan nominal <b>Rp 10.000</b> (atau kelipatannya untuk beberapa bulan).\n"
        f"3. <b>PENTING:</b> Di kolom <b>Pesan Dukungan</b>, ketik User ID Telegram Anda:\n"
        f"   <code>{update.effective_user.id}</code>\n"
        "4. Setelah pembayaran sukses, bot akan otomatis mengaktifkan status VIP ke akun Anda!\n\n"
        "<i>Atau jika menggunakan Kode Voucher dari Reward Trakteer:</i>\n"
        "<code>/redeem KODE-VOUCHER-ANDA</code>"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("☕ Beli VIP Rp 10.000 / Bulan di teer.id/Kiyawi", url=TRAKTEER_URL)]
    ])
    await update.message.reply_text(pesan, reply_markup=keyboard, parse_mode="HTML")

async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk perintah /redeem <kode_voucher>.
    """
    user = update.effective_user
    user_id = user.id if user else 0
    username = user.username or user.first_name or "User"
    args = context.args

    if not args:
        await update.message.reply_text(
            "⚠️ <b>Format salah!</b>\n"
            "Gunakan format: <code>/redeem KODE-VOUCHER</code>\n"
            "Contoh: <code>/redeem VIP-30D-XXXXX</code>",
            parse_mode="HTML"
        )
        return

    code = args[0].strip().upper()
    from database import redeem_voucher
    success, msg, days = redeem_voucher(code, user_id, username)

    if success:
        await update.message.reply_text(
            f"🎉 <b>Aktivasi Berhasil!</b>\n\n"
            f"Selamat, akun Anda telah di-upgrade menjadi <b>⭐ VIP Member ({days} Hari)</b>!\n"
            "Sekarang Anda dapat mengunduh media tanpa antrian dan tanpa batasan link.",
            parse_mode="HTML"
        )
        # Kirim notifikasi ke Admin
        from config import ADMIN_IDS
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"🔔 <b>Laporan Redeem Voucher:</b>\n"
                        f"• User: @{username} (<code>{user_id}</code>)\n"
                        f"• Kode: <code>{code}</code>\n"
                        f"• Durasi: <b>{days} Hari</b>"
                    ),
                    parse_mode="HTML"
                )
            except Exception:
                pass
    else:
        await update.message.reply_text(f"❌ <b>Gagal!</b> {msg}", parse_mode="HTML")

async def addvip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command khusus Admin untuk menambah VIP secara langsung:
    /addvip <user_id> [durasi_hari (default 30)]
    """
    sender_id = update.effective_user.id if update.effective_user else 0
    from config import is_admin
    if not is_admin(sender_id):
        await update.message.reply_text("⛔ Perintah ini hanya dapat dijalankan oleh Admin/Owner.")
        return

    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text(
            "⚠️ Format: <code>/addvip USER_ID [HARI]</code>\n"
            "Contoh: <code>/addvip 123456789 30</code> (isi -1 untuk permanen)",
            parse_mode="HTML"
        )
        return

    target_id = int(args[0])
    days = int(args[1]) if len(args) > 1 and (args[1].lstrip("-").isdigit()) else 30
    from database import add_vip_user
    exp = add_vip_user(target_id, days)

    import datetime
    exp_text = "Permanen" if days == -1 else datetime.datetime.fromtimestamp(exp).strftime("%d-%m-%Y %H:%M")
    await update.message.reply_text(
        f"✅ <b>Berhasil!</b> User <code>{target_id}</code> telah dijadikan ⭐ <b>VIP Member</b>.\n"
        f"Masa berlaku: <b>{exp_text}</b>",
        parse_mode="HTML"
    )
    # Notifikasi ke user target jika memungkinkan
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"🎉 <b>Selamat!</b> Akun Anda telah diaktifkan sebagai ⭐ <b>VIP Member</b> oleh Admin!\nMasa berlaku hingga: <b>{exp_text}</b>.",
            parse_mode="HTML"
        )
    except Exception:
        pass

async def makecode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command khusus Admin untuk membuat kode voucher (bisa satuan atau batch stok):
    Format: /makecode [durasi_hari (default 30)] [jumlah_voucher (default 1)]
    Contoh: /makecode 30 5 (buat 5 voucher sekaligus)
    """
    sender_id = update.effective_user.id if update.effective_user else 0
    from config import is_admin
    if not is_admin(sender_id):
        await update.message.reply_text("⛔ Perintah ini hanya dapat dijalankan oleh Admin/Owner.")
        return

    args = context.args or []
    days = int(args[0]) if len(args) >= 1 and args[0].isdigit() else 30
    count = int(args[1]) if len(args) >= 2 and args[1].isdigit() else 1
    count = max(1, min(20, count))  # Maks 20 kode per command

    import uuid
    from database import create_voucher
    generated = []
    for _ in range(count):
        code = f"VIP-{days}D-{uuid.uuid4().hex[:8].upper()}"
        create_voucher(code, days)
        generated.append(code)

    if count == 1:
        await update.message.reply_text(
            f"🎟️ <b>Kode Voucher Berhasil Dibuat:</b>\n\n"
            f"<code>{generated[0]}</code>\n\n"
            f"• Durasi: <b>{days} Hari</b>\n"
            "💡 <i>Kirimkan kode ini ke pembeli atau tempel di Reward Trakteer.</i>",
            parse_mode="HTML"
        )
    else:
        codes_text = "\n".join([f"• <code>{c}</code>" for c in generated])
        await update.message.reply_text(
            f"🎟️ <b>{count}x Kode Voucher Berhasil Dibuat:</b>\n\n"
            f"{codes_text}\n\n"
            f"• Durasi masing-masing: <b>{days} Hari</b>\n"
            "💡 <i>Kode ini tersimpan di database dan siap dipakai untuk stok Reward Trakteer.</i>",
            parse_mode="HTML"
        )

async def listcode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command khusus Admin untuk melihat stok voucher yang belum digunakan:
    /listcode
    """
    sender_id = update.effective_user.id if update.effective_user else 0
    from config import is_admin
    if not is_admin(sender_id):
        await update.message.reply_text("⛔ Perintah ini hanya dapat dijalankan oleh Admin/Owner.")
        return

    import sqlite3
    from database import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT code, duration_days FROM vouchers WHERE used_by IS NULL ORDER BY created_at DESC LIMIT 20")
        rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("📭 <b>Belum ada stok voucher yang tersedia.</b>\nBuat stok baru dengan: <code>/makecode 30 5</code>", parse_mode="HTML")
        return

    teks = f"📋 <b>DAFTAR STOK VOUCHER AKTIF ({len(rows)} item):</b>\n\n"
    for r in rows:
        teks += f"• <code>{r[0]}</code> ({r[1]} Hari)\n"
    teks += "\n💡 <i>Salin kode di atas untuk dimasukkan ke Reward Trakteer.</i>"
    await update.message.reply_text(teks, parse_mode="HTML")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk perintah /about.
    """
    pesan = (
        "🤖 <b>Tentang Media Downloader Bot</b>\n\n"
        "• <b>Versi:</b> 1.2.0\n"
        "• <b>Engine:</b> Python 3.11, yt-dlp, FFmpeg, SpotiFLAC\n"
        "• <b>Fitur Utama:</b>\n"
        "  - Download Video MP4 (360p, 480p, 720p)\n"
        "  - Download Audio MP3 (320kbps)\n"
        "  - Download Lagu Spotify (FLAC Lossless & MP3)\n"
        "  - Anti-Spam Rate Limiter (3 link/15 menit)\n"
        "  - Pembersihan file otomatis setiap 30 menit\n\n"
        "⚖️ <i>Gunakan bot secara bijak untuk kepentingan pribadi.</i>"
    )
    await update.message.reply_text(pesan, parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk perintah /help beserta disclaimer penggunaan pribadi.
    """
    pesan = (
        "📖 <b>Panduan Penggunaan Bot:</b>\n\n"
        "1. Salin link yang ingin diunduh dari YouTube, TikTok, Instagram, Facebook, X/Twitter, atau Spotify.\n"
        "2. Tempel dan kirim tautan tersebut langsung ke obrolan ini.\n"
        "3. Tunggu bot memproses metadata media.\n"
        "4. Pilih format dan kualitas yang diinginkan (MP4 360p/480p/720p/1080p, FLAC Lossless, atau MP3).\n"
        "5. File akan dikirimkan otomatis ke obrolan Anda.\n\n"
        "⚠️ <b>Batasan Sistem:</b>\n"
        f"• Maksimal ukuran file: {MAX_FILE_SIZE_MB} MB\n"
        f"• Maksimal durasi video: {format_duration(MAX_DURATION_SECONDS)}\n"
        "• Batas permintaan: Maksimal 3 link per 15 menit per pengguna.\n\n"
        "⚖️ <b>Disclaimer:</b>\n"
        "Bot ini ditujukan hanya untuk keperluan pengarsipan dan penggunaan pribadi (personal use only). "
        "Dilarang menggunakan bot ini untuk tujuan komersial atau melanggar hak cipta milik pembuat konten asli."
    )
    await update.message.reply_text(pesan, parse_mode="HTML")
