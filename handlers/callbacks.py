import os
import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import MAX_FILE_SIZE_MB, is_admin
from downloader import download_media, download_photo
from utils import format_size

logger = logging.getLogger(__name__)

# Konfigurasi Concurrency / Antrian (In-Memory, Tidak Perlu Database Eksternal)
# Maksimal 2 proses download/upload berjalan serentak agar bandwidth & CPU tidak drop
MAX_CONCURRENT_DOWNLOADS = 2
download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
active_downloads_count = 0
waiting_users = []  # List antrian untuk menghitung nomor urut antrian
user_active_jobs = set()  # Mencegah user spam klik bersamaan

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler untuk interaksi tombol inline format dan resolusi download.
    Format callback_data: dl|mode|quality|url_id
    """
    global active_downloads_count
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

    user_id = query.from_user.id
    chat_id = query.message.chat_id
    from config import is_admin, is_vip, has_premium_access
    user_is_admin = is_admin(user_id)
    user_is_vip = is_vip(user_id)
    user_has_premium = user_is_admin or user_is_vip

    # Anti-Spam Lock per-user: cegah user biasa memproses 2 unduhan sekaligus (Admin & VIP bebas)
    if not user_has_premium:
        if user_id in user_active_jobs:
            await query.message.reply_text(
                "⚠️ <b>Kamu masih memiliki unduhan yang sedang berjalan!</b>\n"
                "Tunggu unduhan sebelumnya selesai sebelum meminta yang baru.",
                parse_mode="HTML"
            )
            return
        user_active_jobs.add(user_id)

    # Penentuan label status
    if mode == "photo":
        label_desc = "Foto (HD)"
    elif mode == "spotify_flac":
        label_desc = "Spotify FLAC (Lossless)"
    elif mode in ("spotify_mp3", "audio"):
        label_desc = "Audio (MP3)"
    else:
        label_desc = f"Video ({quality}p)"
    
    # Label badge peran
    if user_is_admin:
        role_tag = " 👑 <b>[Admin]</b>"
    elif user_is_vip:
        role_tag = " ⭐ <b>[VIP]</b>"
    else:
        role_tag = ""

    # Periksa antrian jika bukan Admin/VIP (Admin & VIP bebas antrian)
    in_queue = (not user_has_premium) and download_semaphore.locked()
    if in_queue:
        queue_pos = len(waiting_users) + 1
        waiting_users.append(user_id)
        status_msg = await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"⏳ <b>Dalam Antrian (Posisi #{queue_pos})</b>\n\n"
                f"🎯 <b>Target:</b> {label_desc}\n"
                "💡 <i>Server sedang memproses tugas lain agar bandwidth tidak terbagi. "
                "Unduhanmu akan otomatis diproses begitu giliran tiba...</i>"
            ),
            parse_mode="HTML"
        )
    else:
        status_msg = await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"📥 <b>Mengunduh media ({label_desc}){role_tag}...</b>\n\n"
                "⚡ <i>Sedang mengambil file dari server penyedia...</i>"
            ),
            parse_mode="HTML"
        )

    downloaded_path = None
    downloaded_photos = []
    stop_loading = asyncio.Event()

    async def animate_loading(phase="unduhan"):
        """Animasi loading indikator dinamis berkala untuk memberikan feedback visual ke user"""
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        idx = 0
        while not stop_loading.is_set():
            try:
                await asyncio.sleep(2.5)
                if stop_loading.is_set():
                    break
                spinner = frames[idx % len(frames)]
                if phase == "unduhan":
                    msg_text = (
                        f"{spinner} <b>Sedang mengunduh & memproses {label_desc}{role_tag}...</b>\n\n"
                        "⚡ <i>Menyimpan dan mengonversi format media...</i>"
                    )
                else:
                    msg_text = (
                        f"{spinner} <b>Sedang mengunggah ke Telegram{role_tag}...</b>\n\n"
                        "🚀 <i>Mengirim file ke chat Anda...</i>"
                    )
                await status_msg.edit_text(msg_text, parse_mode="HTML")
                idx += 1
            except Exception:
                pass

    try:
        # Helper untuk eksekusi proses unduh dan upload
        async def _execute_job():
            global active_downloads_count
            nonlocal downloaded_path, downloaded_photos, stop_loading
            if in_queue and user_id in waiting_users:
                waiting_users.remove(user_id)

            active_downloads_count += 1
            if in_queue:
                await status_msg.edit_text(
                    f"📥 <b>Giliranmu tiba! Sedang mengunduh {label_desc}...</b>\n\n"
                    "⚡ <i>Mengambil data dari server dengan kecepatan penuh...</i>",
                    parse_mode="HTML"
                )

            loading_task = asyncio.create_task(animate_loading("unduhan"))
            try:
                if mode == "photo":
                    downloaded_photos = await asyncio.to_thread(download_photo, url)
                else:
                    downloaded_path = await asyncio.to_thread(download_media, url, mode, quality)
            finally:
                stop_loading.set()
                await loading_task

            from utils import get_user_quota_info
            quota = get_user_quota_info(user_id)
            if quota["is_unlimited"]:
                quota_note = "♾️ <b>Sisa Kuota:</b> Unlimited"
            else:
                quota_note = f"🎫 <b>Sisa Kuota:</b> {quota['remaining']} / {quota['max_limit']} link (Reset: {quota['reset_in_str']})"

            # === JIKA MODE FOTO ===
            if mode == "photo":
                if not downloaded_photos:
                    raise FileNotFoundError("Tidak ada foto yang berhasil diunduh.")

                stop_loading = asyncio.Event()
                loading_upload_task = asyncio.create_task(animate_loading("upload"))
                try:
                    photo_tag = f"📸 <b>Foto Berhasil Diunduh ({len(downloaded_photos)} item)</b>"
                    if user_is_admin:
                        photo_tag += " 👑"
                    elif user_is_vip:
                        photo_tag += " ⭐"
                    photo_tag += f"\n{quota_note}"

                    if len(downloaded_photos) == 1:
                        with open(downloaded_photos[0], "rb") as p_file:
                            await context.bot.send_photo(
                                chat_id=chat_id,
                                photo=p_file,
                                caption=photo_tag,
                                parse_mode="HTML"
                            )
                    else:
                        from telegram import InputMediaPhoto
                        # Batasi maksimal 10 foto per media group Telegram
                        media_group = []
                        opened_files = []
                        try:
                            for idx, p_path in enumerate(downloaded_photos[:10]):
                                f = open(p_path, "rb")
                                opened_files.append(f)
                                cap = photo_tag if idx == 0 else None
                                media_group.append(InputMediaPhoto(media=f, caption=cap, parse_mode="HTML" if cap else None))
                            await context.bot.send_media_group(chat_id=chat_id, media=media_group)
                        finally:
                            for f in opened_files:
                                try:
                                    f.close()
                                except Exception:
                                    pass

                    try:
                        await status_msg.delete()
                    except Exception:
                        pass
                finally:
                    stop_loading.set()
                    await loading_upload_task
                return

            # === JIKA MODE VIDEO / AUDIO ===
            if not os.path.exists(downloaded_path):
                raise FileNotFoundError("File hasil unduhan tidak ditemukan.")

            file_size_bytes = os.path.getsize(downloaded_path)
            file_size_mb = file_size_bytes / (1024 * 1024)

            # Periksa apakah MTProto paralel (multi-chunk connection) tersedia
            use_mtproto = False
            from config import HAS_MTPROTO
            if HAS_MTPROTO:
                use_mtproto = True
            elif file_size_mb > MAX_FILE_SIZE_MB:
                if not user_has_premium:
                    await status_msg.edit_text(
                        f"❌ <b>Ukuran file melebihi batas 50 MB!</b>\n"
                        f"Ukuran file: <b>{format_size(file_size_bytes)}</b>\n"
                        "💡 <i>Untuk mengaktifkan pengiriman hingga 2000 MB (2 GB), atur TELEGRAM_API_ID & TELEGRAM_API_HASH di .env bot.</i>",
                        parse_mode="HTML"
                    )
                    return

            # Fase Upload ke Telegram
            stop_loading = asyncio.Event()
            loading_upload_task = asyncio.create_task(animate_loading("upload"))

            try:
                upload_label = " (Via 2GB MTProto)" if use_mtproto else ""
                await status_msg.edit_text(
                    f"📤 <b>Mengunggah ke Telegram{upload_label}...</b> ({format_size(file_size_bytes)})\n\n"
                    "🚀 <i>Stream langsung ke chat Anda...</i>",
                    parse_mode="HTML"
                )

                # Kirim dokumen/media ke user
                filename = os.path.basename(downloaded_path)
                is_audio = mode in ("audio", "spotify_flac", "spotify_mp3") or downloaded_path.endswith((".mp3", ".flac", ".m4a", ".ogg"))
                clean_title, _ = os.path.splitext(filename)
                # Ambil info metadata tersimpan jika ada
                info_store = context.bot_data.get("info_store", {})
                item_info = info_store.get(url_id, {})
                audio_performer = item_info.get("artist") or item_info.get("uploader") or None
                audio_title = item_info.get("raw_title") or item_info.get("title") or clean_title

                video_duration = item_info.get("duration")
                video_height = None
                try:
                    if quality and quality.isdigit():
                        video_height = int(quality)
                except Exception:
                    pass

                caption_tag = f"✅ <b>Unduhan Selesai ({quality}p)</b>"
                if user_is_admin:
                    caption_tag += " 👑"
                elif user_is_vip:
                    caption_tag += " ⭐"
                caption_tag += f"\n{quota_note}"

                # JIKA UKURAN FILE > 50MB DAN MTPROTO TERSEDIA, GUNAKAN PYROGRAM MTPROTO
                if use_mtproto:
                    from mtproto_uploader import send_large_media
                    sent_ok = await send_large_media(
                        chat_id=chat_id,
                        file_path=downloaded_path,
                        is_audio=is_audio,
                        caption=caption_tag if not is_audio else "",
                        title=audio_title if is_audio else None,
                        performer=audio_performer if is_audio else None,
                        duration=int(video_duration) if video_duration else None,
                        height=video_height
                    )
                    if not sent_ok:
                        raise RuntimeError("Pengiriman file besar via MTProto gagal.")
                else:
                    thumb_bytes = None
                    thumb_url = item_info.get("thumbnail")
                    if thumb_url:
                        try:
                            import urllib.request
                            req_t = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                            with urllib.request.urlopen(req_t, timeout=10) as t_resp:
                                thumb_bytes = t_resp.read()
                        except Exception:
                            pass

                    with open(downloaded_path, "rb", buffering=8 * 1024 * 1024) as media_file:
                        if is_audio:
                            send_kwargs = {
                                "chat_id": chat_id,
                                "audio": media_file,
                                "title": audio_title,
                                "performer": audio_performer,
                                "read_timeout": 300,
                                "write_timeout": 300,
                                "connect_timeout": 60
                            }
                            if thumb_bytes:
                                send_kwargs["thumbnail"] = thumb_bytes
                            await context.bot.send_audio(**send_kwargs)
                        else:
                            send_kwargs = {
                                "chat_id": chat_id,
                                "video": media_file,
                                "caption": caption_tag,
                                "parse_mode": "HTML",
                                "supports_streaming": True,
                                "read_timeout": 300,
                                "write_timeout": 300,
                                "connect_timeout": 60
                            }
                            if video_duration:
                                send_kwargs["duration"] = int(video_duration)
                            if video_height:
                                send_kwargs["height"] = video_height
                            if thumb_bytes:
                                send_kwargs["thumbnail"] = thumb_bytes
                            await context.bot.send_video(**send_kwargs)

                try:
                    await status_msg.delete()
                except Exception:
                    pass
            finally:
                stop_loading.set()
                await loading_upload_task

        # Admin langsung eksekusi tanpa antrian semaphore
        if user_is_admin:
            await _execute_job()
        else:
            async with download_semaphore:
                await _execute_job()

    except Exception as e:
        logger.error(f"Error saat mengunduh/mengirim file: {e}", exc_info=True)
        try:
            await status_msg.edit_text(
                f"❌ <b>Gagal memproses media!</b>\n"
                "Terjadi kendala saat mengunduh atau mengunggah ke Telegram.",
                parse_mode="HTML"
            )
        except Exception:
            pass
    finally:
        stop_loading.set()
        # Lepas status lock user dan hapus dari antrian
        user_active_jobs.discard(user_id)
        if user_id in waiting_users:
            waiting_users.remove(user_id)

        # Bersihkan file video/audio sementara
        if downloaded_path and os.path.exists(downloaded_path):
            try:
                os.remove(downloaded_path)
                logger.info(f"File sementara berhasil dihapus: {downloaded_path}")
            except Exception as e:
                logger.warning(f"Gagal menghapus file sementara {downloaded_path}: {e}")

        # Bersihkan file foto sementara jika ada
        if downloaded_photos:
            for p_path in downloaded_photos:
                if os.path.exists(p_path):
                    try:
                        os.remove(p_path)
                    except Exception:
                        pass
            logger.info("Semua file foto sementara berhasil dihapus.")
