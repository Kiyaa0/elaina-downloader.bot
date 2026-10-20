import re
import json
import logging
from aiohttp import web
from config import TRAKTEER_WEBHOOK_SECRET, ADMIN_IDS
from database import add_vip_user

logger = logging.getLogger("TrakteerWebhook")

def _extract_user_id_from_message(message: str) -> int | None:
    """Mengekstrak ID Telegram dari pesan dukungan trakteer"""
    if not message:
        return None
    # Cari angka 6 - 12 digit (format khas Telegram User ID)
    matches = re.findall(r"\b(\d{6,12})\b", message)
    if matches:
        return int(matches[0])
    return None

def create_trakteer_app(bot_instance) -> web.Application:
    """
    Membuat web app aiohttp untuk menangani Webhook resmi dari Trakteer.
    Endpoint: POST /webhook/trakteer
    """
    app = web.Application()

    async def handle_trakteer(request: web.Request) -> web.Response:
        try:
            # 1. Cek Header X-Webhook-Token jika secret dikonfigurasi
            if TRAKTEER_WEBHOOK_SECRET:
                token = request.headers.get("X-Webhook-Token", "")
                if token != TRAKTEER_WEBHOOK_SECRET:
                    logger.warning("Webhook Trakteer ditolak: Token rahasia tidak cocok.")
                    return web.Response(status=401, text="Unauthorized token")

            data = await request.json()
            logger.info(f"Menerima Webhook Trakteer: {data}")

            # Format payload Trakteer Tip:
            # {"type": "tip", "supporter_name": "...", "supporter_message": "...", "quantity": 1, "price": 5000, ...}
            supporter_name = data.get("supporter_name", "Supporter")
            message = data.get("supporter_message", "")
            quantity = int(data.get("quantity", 1))
            unit_name = data.get("unit", "Unit")
            price = data.get("price", 0)

            # Ekstrak User ID Telegram dari isi pesan dukungan
            target_user_id = _extract_user_id_from_message(message)

            # Hitung durasi VIP: Rp 10.000 = 30 hari (kelipatan dihitung proporsional)
            if price and price >= 10000:
                vip_days = int((price / 10000) * 30)
            else:
                vip_days = 30 * max(1, quantity)

            if target_user_id:
                # Tambah VIP ke database
                add_vip_user(target_user_id, duration_days=vip_days, username=supporter_name)
                logger.info(f"Sukses mengaktifkan VIP {vip_days} hari untuk User ID {target_user_id} via Trakteer!")

                # Kirim pesan notifikasi ucapan terima kasih ke user yang bersangkutan
                try:
                    await bot_instance.send_message(
                        chat_id=target_user_id,
                        text=(
                            f"🎉 <b>Terima kasih atas dukungannya di Trakteer!</b>\n\n"
                            f"👤 <b>Nama:</b> {supporter_name}\n"
                            f"☕ <b>Traktiran:</b> {quantity}x {unit_name}\n"
                            f"⭐ <b>Status VIP:</b> <b>Aktif selama {vip_days} Hari!</b>\n\n"
                            "⚡ Anda sekarang dapat menikmati unduhan tanpa batas, tanpa antrian, dan kualitas hingga Full HD 1080p."
                        ),
                        parse_mode="HTML"
                    )
                except Exception as notify_err:
                    logger.warning(f"Gagal mengirim pesan ucapan selamat ke {target_user_id}: {notify_err}")

                # Beritahu Admin
                for aid in ADMIN_IDS:
                    try:
                        await bot_instance.send_message(
                            chat_id=aid,
                            text=(
                                f"💰 <b>Dukungan Baru Masuk di Trakteer!</b>\n\n"
                                f"• Dari: <b>{supporter_name}</b>\n"
                                f"• Jumlah: <b>{quantity}x {unit_name}</b> (Rp {price:,})\n"
                                f"• Pesan: <i>{message}</i>\n"
                                f"• Target User ID: <code>{target_user_id}</code>\n"
                                f"✅ <b>Status:</b> Otomatis di-upgrade ke VIP ({vip_days} hari)."
                            ),
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass

                return web.json_response({"status": "success", "vip_activated": True, "user_id": target_user_id})
            else:
                logger.info(f"Dukungan Trakteer masuk tanpa User ID di pesan: '{message}'")
                # Beritahu Admin agar bisa mengecek manual jika user lupa nulis User ID
                for aid in ADMIN_IDS:
                    try:
                        await bot_instance.send_message(
                            chat_id=aid,
                            text=(
                                f"⚠️ <b>Dukungan Trakteer Tanpa User ID!</b>\n\n"
                                f"• Dari: <b>{supporter_name}</b>\n"
                                f"• Jumlah: <b>{quantity}x {unit_name}</b>\n"
                                f"• Pesan: <i>{message or '(tanpa pesan)'}</i>\n\n"
                                "💡 <i>User tidak menyertakan User ID di pesan. Jika user menghubungi Anda, gunakan:</i>\n"
                                f"<code>/addvip USER_ID {vip_days}</code>"
                            ),
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass

                return web.json_response({"status": "success", "vip_activated": False, "note": "No user ID found in message"})

        except Exception as e:
            logger.error(f"Error saat memproses webhook Trakteer: {e}", exc_info=True)
            return web.Response(status=500, text=f"Server error: {e}")

    app.router.add_post("/webhook/trakteer", handle_trakteer)
    app.router.add_get("/", lambda req: web.Response(text="Elaina Downloader Bot is Running."))
    return app
