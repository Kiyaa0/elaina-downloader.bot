import os
import logging
from config import BOT_TOKEN, TELEGRAM_API_ID, TELEGRAM_API_HASH, HAS_MTPROTO

logger = logging.getLogger(__name__)

_pyro_client = None

async def get_pyrogram_client():
    """
    Mengambil atau menginisialisasi instance Pyrogram Client secara singleton.
    """
    global _pyro_client
    if not HAS_MTPROTO:
        return None

    if _pyro_client is None:
        from pyrogram import Client
        _pyro_client = Client(
            name="uploader_bot_session",
            api_id=int(TELEGRAM_API_ID),
            api_hash=TELEGRAM_API_HASH,
            bot_token=BOT_TOKEN,
            workdir="downloads",
            workers=16,
            max_concurrent_transmissions=8
        )
    if not _pyro_client.is_connected:
        await _pyro_client.start()
        logger.info("Koneksi MTProto Pyrogram multi-connection (akselerasi IDM) berhasil terhubung.")

    return _pyro_client

async def send_large_media(
    chat_id: int,
    file_path: str,
    is_audio: bool,
    caption: str = "",
    title: str = None,
    performer: str = None,
    duration: int = None,
    width: int = None,
    height: int = None,
    thumb_path: str = None
) -> bool:
    """
    Mengirim file besar (hingga 2000 MB) melalui protokol native MTProto Pyrogram.
    Mengembalikan True jika berhasil, False jika gagal.
    """
    client = await get_pyrogram_client()
    if not client:
        return False

    try:
        if is_audio:
            await client.send_audio(
                chat_id=chat_id,
                audio=file_path,
                caption=caption,
                title=title,
                performer=performer,
                duration=duration or 0,
                thumb=thumb_path
            )
        else:
            await client.send_video(
                chat_id=chat_id,
                video=file_path,
                caption=caption,
                duration=duration or 0,
                width=width or 0,
                height=height or 0,
                thumb=thumb_path,
                supports_streaming=True
            )
        return True
    except Exception as e:
        logger.error(f"Gagal mengirim media via MTProto Pyrogram: {e}", exc_info=True)
        return False
