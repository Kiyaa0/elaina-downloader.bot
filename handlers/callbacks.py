import os
import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import MAX_FILE_SIZE_MB
from downloader import download_media
from utils import format_size

logger = logging.getLogger(__name__)

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk interaksi tombol inline format dan resolusi download.
    Format callback_data: dl|mode|quality|url_id
    """
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    
    # 1. Tangani Navigasi Menu
    if data.startswith("menu|"):
        menu_type = data.split("|")[1]
        if menu_type == "help":
            help_text = (
                "📖 <b>Panduan Penggunaan Bot:</b>\n\n"
                "1. Salin tautan dari YouTube, TikTok, Instagram, FB, X/Twitter, atau Spotify.\n"
                "2. Kirim tautan langsung ke obrolan ini.\n"
                "3. Tunggu bot membaca info video/musik.\n"
                "4. Pilih resolusi MP4 atau format audio yang diinginkan."
            )
            await query.message.reply_text(help_text, parse_mode="HTML")
        elif menu_type == "platforms":
            plat_text = (
                "🌐 <b>Platform yang Didukung:</b>\n\n"
                "• 📺 <b>YouTube:</b> Video (360p, 480p, 720p) & Audio MP3\n"
                "• 🎵 <b>TikTok:</b> Video tanpa watermark & Audio\n"
                "• 📸 <b>Instagram:</b> Reels & Video Post\n"
                "• 👥 <b>Facebook:</b> Video Publik & Watch\n"
                "• 🐦 <b>X / Twitter:</b> Video Post & Clip\n"
                "• 🎧 <b>Spotify:</b> Audio FLAC Lossless & MP3 (320kbps)"
            )
            await query.message.reply_text(plat_text, parse_mode="HTML")
        elif menu_type == "ping":
            await query.message.reply_text("🏓 <b>Status Bot:</b> 🟢 Online & Siap Mengunduh!", parse_mode="HTML")
        elif menu_type == "about":
            about_text = (
                "🤖 <b>Media Downloader Bot v1.2.0</b>\n\n"
                "Dibuat untuk memudahkan pengarsipan konten media pribadi secara instan dan cepat."
            )
            await query.message.reply_text(about_text, parse_mode="HTML")
        return

    # 2. Tangani Download Media
    if not data.startswith("dl|"):
        return

    parts = data.split("|")
    if len(parts) != 4:
        await query.edit_message_text("❌ Permintaan tidak valid.")
        return

    _, mode, quality, url_id = parts
    url_store = context.bot_data.get("url_store", {})
    url = url_store.get(url_id)

    if not url:
        await query.edit_message_text("❌ Sesi download telah kedaluwarsa. Silakan kirimkan ulang link video.")
        return

    chat_id = query.message.chat_id
    # Penentuan label status
    if mode == "spotify_flac":
        label_desc = "Spotify FLAC (Lossless)"
    elif mode in ("spotify_mp3", "audio"):
        label_desc = "Audio (MP3)"
    else:
        label_desc = f"Video ({quality}p)"
    
    # Update pesan status proses download awal disertai pengingat
    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"⏳ <b>Sedang mengunduh {label_desc}...</b>\n\n"
            "💡 <i>Mohon bersabar dan jangan spam tombol. "
            "Server sedang memproses & mengonversi media, ini biasanya memerlukan beberapa detik...</i>"
        ),
        parse_mode="HTML"
    )

    downloaded_path = None
    stop_loading = asyncio.Event()

    async def animate_loading():
        """Animasi loading indikator dinamis berkala untuk memberikan feedback visual ke user"""
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        idx = 0
        while not stop_loading.is_set():
            try:
                await asyncio.sleep(2.5)
                if stop_loading.is_set():
                    break
                spinner = frames[idx % len(frames)]
                await status_msg.edit_text(
                    f"{spinner} <b>Sedang memproses unduhan {label_desc}...</b>\n\n"
                    "💡 <i>Mohon bersabar dan jangan tutup obrolan. "
                    "Server sedang mengonversi media agar siap dikirim...</i>",
                    parse_mode="HTML"
                )
                idx += 1
            except Exception:
                pass

    loading_task = asyncio.create_task(animate_loading())

    try:
        # Jalankan proses unduhan di background thread agar tidak memblokir event loop
        downloaded_path = await asyncio.to_thread(download_media, url, mode, quality)
        stop_loading.set()
        await loading_task

        # Cek ukuran file hasil unduhan
        if not os.path.exists(downloaded_path):
            raise FileNotFoundError("File hasil unduhan tidak ditemukan.")

        file_size_bytes = os.path.getsize(downloaded_path)
        file_size_mb = file_size_bytes / (1024 * 1024)

        if file_size_mb > MAX_FILE_SIZE_MB:
            await status_msg.edit_text(
                f"❌ <b>Ukuran file terlalu besar!</b>\n"
                f"Ukuran file: <b>{format_size(file_size_bytes)}</b>\n"
                f"Batas upload Telegram Bot API: <b>{MAX_FILE_SIZE_MB} MB</b>.\n"
                "Coba pilih format dengan ukuran lebih kecil.",
                parse_mode="HTML"
            )
            return

        # Kirim status upload
        await status_msg.edit_text("📤 <b>Sedang mengunggah ke Telegram...</b>", parse_mode="HTML")

        # Kirim dokumen/media ke user
        filename = os.path.basename(downloaded_path)
        is_audio = mode in ("audio", "spotify_flac", "spotify_mp3") or downloaded_path.endswith((".mp3", ".flac", ".m4a", ".ogg"))
        clean_title, _ = os.path.splitext(filename)
        with open(downloaded_path, "rb") as media_file:
            if is_audio:
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=media_file,
                    title=clean_title,
                    read_timeout=120,
                    write_timeout=120,
                    connect_timeout=30
                )
            else:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=media_file,
                    caption=f"✅ <b>Unduhan Selesai ({quality}p)</b>",
                    parse_mode="HTML",
                    supports_streaming=True,
                    read_timeout=120,
                    write_timeout=120,
                    connect_timeout=30
                )

        # Hapus pesan status setelah berhasil terkirim
        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Error saat mengunduh/mengirim file: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Gagal mengunduh media!</b>\n"
            "Terjadi kesalahan saat memproses media atau batasan dari server penyedia.",
            parse_mode="HTML"
        )
    finally:
        stop_loading.set()
        # Bersihkan file sementara
        if downloaded_path and os.path.exists(downloaded_path):
            try:
                os.remove(downloaded_path)
                logger.info(f"File sementara berhasil dihapus: {downloaded_path}")
            except Exception as e:
                logger.warning(f"Gagal menghapus file sementara {downloaded_path}: {e}")
