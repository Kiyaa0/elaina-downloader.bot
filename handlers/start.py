from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import MAX_FILE_SIZE_MB, MAX_DURATION_SECONDS
from utils import format_duration
import time

def get_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Membuat keyboard navigasi menu utama.
    """
    keyboard = [
        [
            InlineKeyboardButton("📖 Panduan Lengkap", callback_data="menu|help"),
            InlineKeyboardButton("🌐 Platform Didukung", callback_data="menu|platforms")
        ],
        [
            InlineKeyboardButton("⚡ Cek Status Bot", callback_data="menu|ping"),
            InlineKeyboardButton("ℹ️ Tentang Bot", callback_data="menu|about")
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
        "  - Anti-Spam Rate Limiter (5 req/menit)\n"
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
        "4. Pilih format dan kualitas yang diinginkan (MP4 360p/480p/720p, FLAC Lossless, atau MP3).\n"
        "5. File akan dikirimkan otomatis ke obrolan Anda.\n\n"
        "⚠️ <b>Batasan Sistem:</b>\n"
        f"• Maksimal ukuran file: {MAX_FILE_SIZE_MB} MB\n"
        f"• Maksimal durasi video: {format_duration(MAX_DURATION_SECONDS)}\n"
        "• Batas permintaan: Maksimal 5 permintaan per menit per pengguna.\n\n"
        "⚖️ <b>Disclaimer:</b>\n"
        "Bot ini ditujukan hanya untuk keperluan pengarsipan dan penggunaan pribadi (personal use only). "
        "Dilarang menggunakan bot ini untuk tujuan komersial atau melanggar hak cipta milik pembuat konten asli."
    )
    await update.message.reply_text(pesan, parse_mode="HTML")
