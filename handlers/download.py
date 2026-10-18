import asyncio
import logging
import uuid
from html import escape
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import extract_url, detect_platform, format_duration, format_size, check_rate_limit
from downloader import extract_video_info
from config import MAX_DURATION_SECONDS

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk memproses pesan teks yang berisi link unduhan.
    """
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # 1. Ekstrak URL
    url = extract_url(text)
    if not url:
        return

    # 2. Cek Rate Limit
    allowed, wait_seconds = check_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(
            f"⏳ <b>Terlalu banyak permintaan!</b>\nMohon tunggu <b>{wait_seconds}</b> detik lagi sebelum mengirim link berikutnya.",
            parse_mode="HTML"
        )
        return

    # 3. Deteksi Platform
    platform, icon = detect_platform(url)
    if platform == "Unknown":
        await update.message.reply_text(
            "❌ <b>Platform tidak didukung!</b>\n"
            "Bot saat ini hanya mendukung tautan dari:\n"
            "• 📺 YouTube\n• 🎵 TikTok\n• 📸 Instagram\n• 👥 Facebook\n• 🐦 X / Twitter\n• 🎧 Spotify",
            parse_mode="HTML"
        )
        return

    # 4. Kirim status awal
    status_msg = await update.message.reply_text(
        f"🔍 Mengambil informasi video dari <b>{icon} {platform}</b>...",
        parse_mode="HTML"
    )

    try:
        # 5. Ambil metadata via thread terpisah
        info = await asyncio.to_thread(extract_video_info, url)
        
        duration = info.get("duration")
        if duration and duration > MAX_DURATION_SECONDS:
            await status_msg.edit_text(
                f"❌ <b>Durasi video terlalu panjang!</b>\n"
                f"Durasi video: <b>{format_duration(duration)}</b>\n"
                f"Batas maksimal bot: <b>{format_duration(MAX_DURATION_SECONDS)}</b>.",
                parse_mode="HTML"
            )
            return

        # Simpan URL di bot_data menggunakan session id pendek agar callback_data tidak melebihi 64 bytes
        url_id = uuid.uuid4().hex[:8]
        if "url_store" not in context.bot_data:
            context.bot_data["url_store"] = {}
        context.bot_data["url_store"][url_id] = url

        title = escape(info.get("title", "Unknown Title"))
        uploader = escape(info.get("uploader", "Unknown"))
        filesize_str = format_size(info.get("filesize"))
        duration_str = format_duration(duration)

        caption = (
            f"<b>{icon} {platform} Media Info</b>\n\n"
            f"📌 <b>Judul:</b> {title}\n"
            f"👤 <b>Uploader:</b> {uploader}\n"
            f"⏱️ <b>Durasi:</b> {duration_str}\n"
            f"📦 <b>Estimasi Ukuran:</b> {filesize_str}\n\n"
            "Pilih format dan resolusi unduhan di bawah ini:"
        )

        if platform == "Spotify":
            keyboard = [
                [
                    InlineKeyboardButton("✨ Unduh Lossless (FLAC)", callback_data=f"dl|spotify_flac|flac|{url_id}"),
                    InlineKeyboardButton("🎵 Unduh Audio (MP3)", callback_data=f"dl|spotify_mp3|mp3|{url_id}")
                ]
            ]
        else:
            keyboard = [
                [
                    InlineKeyboardButton("🎬 MP4 (360p)", callback_data=f"dl|video|360|{url_id}"),
                    InlineKeyboardButton("🎬 MP4 (480p)", callback_data=f"dl|video|480|{url_id}"),
                    InlineKeyboardButton("🎬 MP4 (720p)", callback_data=f"dl|video|720|{url_id}"),
                ],
                [
                    InlineKeyboardButton("🎵 Unduh Audio (MP3)", callback_data=f"dl|audio|mp3|{url_id}")
                ]
            ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await status_msg.edit_text(
            caption,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Gagal mengambil info dari {url}: {e}", exc_info=True)
        await status_msg.edit_text(
            "❌ <b>Gagal memproses tautan!</b>\n"
            "Pastikan konten tersebut bersifat publik (bukan private), link valid, dan tidak diblokir.",
            parse_mode="HTML"
        )
