import os
import sys
import time
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from config import BOT_TOKEN, DOWNLOAD_DIR
from handlers.start import (
    start_command, help_command, menu_command, ping_command, about_command, id_command,
    vip_command, redeem_command, addvip_command, makecode_command, listcode_command
)
from handlers.download import handle_message
from handlers.callbacks import handle_callback_query

# Pastikan folder unduhan tersedia
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Konfigurasi Logging ke file bot.log dan konsol terminal
log_formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

file_handler = logging.FileHandler("bot.log", encoding="utf-8")
file_handler.setFormatter(log_formatter)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(log_formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, stream_handler]
)

# Kurangi kebisingan log dari pustaka pihak ketiga
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.INFO)

logger = logging.getLogger("BotDownloader")

async def cleanup_downloads_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Job berkala untuk membersihkan file dan sub-folder sementara di folder downloads/
    yang tertinggal atau lebih lama dari 10 menit (agar disk tidak penuh).
    """
    import shutil
    logger.info("Memulai pembersihan otomatis folder downloads/...")
    now = time.time()
    max_age_seconds = 10 * 60  # 10 menit (lebih cepat dibersihkan)
    files_deleted = 0
    dirs_deleted = 0

    if not os.path.exists(DOWNLOAD_DIR):
        return

    for item in os.listdir(DOWNLOAD_DIR):
        item_path = os.path.join(DOWNLOAD_DIR, item)
        try:
            # Jika berupa file
            if os.path.isfile(item_path):
                file_age = now - os.path.getmtime(item_path)
                if file_age > max_age_seconds:
                    os.remove(item_path)
                    files_deleted += 1
                    logger.info(f"File sementara dibersihkan: {item}")
            # Jika berupa folder/direktori sisa job
            elif os.path.isdir(item_path):
                dir_age = now - os.path.getmtime(item_path)
                # Bersihkan jika folder kosong atau berumur > 10 menit
                if len(os.listdir(item_path)) == 0 or dir_age > max_age_seconds:
                    shutil.rmtree(item_path, ignore_errors=True)
                    dirs_deleted += 1
                    logger.info(f"Folder sementara dibersihkan: {item}")
        except Exception as e:
            logger.warning(f"Gagal membersihkan item {item_path}: {e}")

    logger.info(f"Pembersihan selesai. {files_deleted} file dan {dirs_deleted} folder berhasil dihapus.")

def main() -> None:
    """
    Entry point utama untuk menjalankan bot telegram downloader.
    """
    if not BOT_TOKEN or BOT_TOKEN == "masukkan_token_bot_telegram_anda_disini":
        logger.error(
            "BOT_TOKEN belum diatur dengan benar di file .env! "
            "Silakan edit file .env dan isi dengan token bot yang diperoleh dari @BotFather."
        )
        print("\n[PERINGATAN] Silakan isi BOT_TOKEN di file .env terlebih dahulu!\n")
        return

    async def post_init(application) -> None:
        """Mendaftarkan menu tombol command resmi di antarmuka Telegram dan menjalankan Webhook Trakteer"""
        from telegram import BotCommand
        commands = [
            BotCommand("start", "Mulai bot & buka menu utama"),
            BotCommand("menu", "Tampilkan daftar menu navigasi"),
            BotCommand("help", "Panduan lengkap penggunaan & batas bot"),
            BotCommand("vip", "Panduan VIP & link donasi Trakteer"),
            BotCommand("ping", "Cek status & kecepatan respon server"),
            BotCommand("id", "Lihat User ID Telegram Anda & status admin"),
            BotCommand("about", "Informasi engine & versi bot"),
        ]
        await application.bot.set_my_commands(commands)
        logger.info("Daftar command menu Telegram berhasil didaftarkan ke @BotFather.")

        # Jalankan background web server untuk Webhook Trakteer
        try:
            from aiohttp import web
            from trakteer_webhook import create_trakteer_app
            from config import TRAKTEER_WEBHOOK_PORT
            trakteer_app = create_trakteer_app(application.bot)
            runner = web.AppRunner(trakteer_app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", TRAKTEER_WEBHOOK_PORT)
            await site.start()
            application.bot_data["trakteer_runner"] = runner
            logger.info(f"🚀 Webhook Trakteer aktif di port {TRAKTEER_WEBHOOK_PORT} (Endpoint: POST /webhook/trakteer)")
        except Exception as th_err:
            logger.warning(f"Gagal menjalankan server Webhook Trakteer: {th_err}")

    async def post_shutdown(application) -> None:
        """Membersihkan web runner saat bot dimatikan"""
        runner = application.bot_data.get("trakteer_runner")
        if runner:
            try:
                await runner.cleanup()
                logger.info("Server Webhook Trakteer berhasil dihentikan.")
            except Exception:
                pass

    # Inisialisasi Application telegram dengan HTTPXRequest yang dioptimalkan
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(
        connection_pool_size=16,
        read_timeout=300.0,
        write_timeout=300.0,
        connect_timeout=60.0,
        pool_timeout=60.0,
    )
    app = ApplicationBuilder().token(BOT_TOKEN).request(request).post_init(post_init).post_shutdown(post_shutdown).build()

    # Daftarkan Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("vip", vip_command))
    app.add_handler(CommandHandler("redeem", redeem_command))
    app.add_handler(CommandHandler("addvip", addvip_command))
    app.add_handler(CommandHandler("makecode", makecode_command))
    app.add_handler(CommandHandler("listcode", listcode_command))
    app.add_handler(CommandHandler("about", about_command))

    # Daftarkan Callback Query Handler untuk tombol pilihan format/resolusi
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Daftarkan Message Handler untuk menerima link teks
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Global Error Handler untuk keamanan & stabilitas bot
    async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(f"Pengecualian tidak tertangani (Unhandled Exception): {context.error}", exc_info=context.error)
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ <i>Terjadi kendala sementara pada koneksi server. Silakan coba kembali dalam beberapa saat.</i>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    app.add_error_handler(global_error_handler)

    # Jadwalkan Job Pembersihan downloads/ setiap 30 menit (1800 detik)
    if app.job_queue:
        app.job_queue.run_repeating(cleanup_downloads_job, interval=1800, first=60)
        logger.info("Job scheduler pembersihan berkala berhasil didaftarkan.")
    else:
        logger.warning("JobQueue tidak aktif. Pembersihan berkala tidak dapat dijadwalkan otomatis.")

    logger.info("Bot Telegram Downloader berhasil dimulai. Menunggu pesan masuk...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
