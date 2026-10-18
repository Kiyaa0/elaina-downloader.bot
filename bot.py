import os
import sys
import time
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from config import BOT_TOKEN, DOWNLOAD_DIR
from handlers.start import start_command, help_command, menu_command, ping_command, about_command
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
    Job berkala untuk membersihkan file sementara di folder downloads/ yang lebih lama dari 30 menit.
    """
    logger.info("Memulai pembersihan otomatis folder downloads/...")
    now = time.time()
    max_age_seconds = 30 * 60  # 30 menit
    count = 0

    if not os.path.exists(DOWNLOAD_DIR):
        return

    for filename in os.listdir(DOWNLOAD_DIR):
        file_path = os.path.join(DOWNLOAD_DIR, filename)
        try:
            if os.path.isfile(file_path):
                file_age = now - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    count += 1
                    logger.info(f"File lama dibersihkan: {filename}")
        except Exception as e:
            logger.warning(f"Gagal menghapus file saat pembersihan {file_path}: {e}")

    logger.info(f"Pembersihan selesai. Total {count} file dihapus.")

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
        """Mendaftarkan menu tombol command resmi di antarmuka Telegram"""
        from telegram import BotCommand
        commands = [
            BotCommand("start", "Mulai bot & buka menu utama"),
            BotCommand("menu", "Tampilkan daftar menu navigasi"),
            BotCommand("help", "Panduan lengkap penggunaan & batas bot"),
            BotCommand("ping", "Cek status & kecepatan respon server"),
            BotCommand("about", "Informasi engine & versi bot"),
        ]
        await application.bot.set_my_commands(commands)
        logger.info("Daftar command menu Telegram berhasil didaftarkan ke @BotFather.")

    # Inisialisasi Application telegram
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # Daftarkan Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("about", about_command))

    # Daftarkan Callback Query Handler untuk tombol pilihan format/resolusi
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Daftarkan Message Handler untuk menerima link teks
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

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
