import asyncio
import logging
import uuid
from html import escape
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import extract_url, detect_platform, format_duration, format_size, check_rate_limit
from downloader import extract_video_info
from config import MAX_DURATION_SECONDS, has_premium_access

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

    # 2. Cek Rate Limit (Batas: 3 link per 15 menit untuk user biasa)
    allowed, wait_seconds = check_rate_limit(user_id)
    if not allowed:
        menit = wait_seconds // 60
        detik = wait_seconds % 60
        waktu_str = f"{menit} menit {detik} detik" if menit > 0 else f"{detik} detik"
        await update.message.reply_text(
            f"⏳ <b>Batas permintaan tercapai!</b>\n\n"
            f"Setiap pengguna dibatasi maksimal <b>3 link per 15 menit</b>.\n"
            f"Silakan tunggu <b>{waktu_str}</b> sebelum mengirim link berikutnya.\n"
            "💡 <i>Gunakan /vip untuk mengaktifkan akses VIP tanpa batas.</i>",
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
        if not has_premium_access(user_id) and duration and duration > MAX_DURATION_SECONDS:
            await status_msg.edit_text(
                f"❌ <b>Durasi video terlalu panjang!</b>\n"
                f"Durasi video: <b>{format_duration(duration)}</b>\n"
                f"Batas maksimal bot: <b>{format_duration(MAX_DURATION_SECONDS)}</b>.\n"
                "💡 <i>Akun VIP dapat mengunduh video dengan durasi tak terbatas. Ketik /vip untuk info lebih lanjut.</i>",
                parse_mode="HTML"
            )
            return

        # Simpan URL dan metadata di bot_data menggunakan session id pendek agar callback_data tidak melebihi 64 bytes
        url_id = uuid.uuid4().hex[:8]
        if "url_store" not in context.bot_data:
            context.bot_data["url_store"] = {}
        context.bot_data["url_store"][url_id] = url
        if "info_store" not in context.bot_data:
            context.bot_data["info_store"] = {}
        context.bot_data["info_store"][url_id] = info

        title = escape(info.get("title", "Unknown Title"))
        uploader = escape(info.get("uploader", "Unknown"))
        filesize_str = format_size(info.get("filesize"))
        duration_str = format_duration(duration)

        from utils import get_user_quota_info
        quota = get_user_quota_info(user_id)
        if quota["is_unlimited"]:
            quota_text = "♾️ <b>Sisa Kuota:</b> Unlimited (VIP/Admin)"
        else:
            quota_text = (
                f"🎫 <b>Sisa Kuota:</b> <b>{quota['remaining']} / {quota['max_limit']} link</b>\n"
                f"⏳ <b>Reset Kuota:</b> Dalam {quota['reset_in_str']}"
            )

        caption = (
            f"<b>{icon} {platform} Media Info</b>\n\n"
            f"📌 <b>Judul:</b> {title}\n"
            f"👤 <b>Uploader:</b> {uploader}\n"
            f"⏱️ <b>Durasi:</b> {duration_str}\n"
            f"📦 <b>Estimasi Ukuran:</b> {filesize_str}\n"
            f"{quota_text}\n\n"
            "Pilih format dan resolusi unduhan di bawah ini:"
        )

        if info.get("is_photo_post") or info.get("is_slide"):
            caption = (
                f"<b>{icon} {platform} Media Info (Foto/Slide)</b>\n\n"
                f"📌 <b>Judul:</b> {title}\n"
                f"👤 <b>Uploader:</b> {uploader}\n"
                f"{quota_text}\n\n"
                "Pilih format unduhan di bawah ini:"
            )
            keyboard = [
                [
                    InlineKeyboardButton("📸 Unduh Foto (Resolusi Penuh HD)", callback_data=f"dl|photo|hd|{url_id}")
                ]
            ]
        elif platform == "Spotify":
            keyboard = [
                [
                    InlineKeyboardButton("✨ Unduh Lossless (FLAC)", callback_data=f"dl|spotify_flac|flac|{url_id}"),
                    InlineKeyboardButton("🎵 Unduh Audio (MP3)", callback_data=f"dl|spotify_mp3|mp3|{url_id}")
                ]
            ]
        else:
            video_row = [
                InlineKeyboardButton("🎬 360p", callback_data=f"dl|video|360|{url_id}"),
                InlineKeyboardButton("🎬 480p", callback_data=f"dl|video|480|{url_id}"),
                InlineKeyboardButton("🎬 720p", callback_data=f"dl|video|720|{url_id}"),
                InlineKeyboardButton("🎬 1080p", callback_data=f"dl|video|1080|{url_id}")
            ]
            keyboard = [
                video_row,
                [
                    InlineKeyboardButton("🎵 Unduh Audio (MP3)", callback_data=f"dl|audio|mp3|{url_id}"),
                    InlineKeyboardButton("📸 Unduh Foto (HD)", callback_data=f"dl|photo|hd|{url_id}")
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
