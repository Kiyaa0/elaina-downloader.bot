import os
import re
import uuid
import yt_dlp
from config import DOWNLOAD_DIR, COOKIES_FILE, MAX_DURATION_SECONDS

# Pastikan folder downloads tersedia
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def _get_base_ydl_opts() -> dict:
    """
    Opsi dasar untuk yt-dlp termasuk timeout, multi-threading, fragment speedup, dan cookie file jika ada.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 20,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "extract_flat": False,
        # Akselerasi download fragment & chunk HTTP
        "concurrent_fragment_downloads": 4,
        "buffersize": 1024 * 1024,
        "http_chunk_size": 10485760,  # 10MB chunk
        # Optimasi performa FFmpeg: gunakan semua thread CPU
        "postprocessor_args": {
            "ffmpeg": ["-threads", "0"]
        },
    }
    try:
        import imageio_ffmpeg
        opts["ffmpeg_location"] = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass

    if os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    return opts

def _get_spotify_info(url: str) -> dict:
    """
    Mengambil metadata track Spotify melalui halaman og-meta & oEmbed agar judul dan nama artis akurat.
    """
    import urllib.request
    import json
    import re
    
    clean_url = url.split("?")[0]
    # Normalisasi tautan internasional Spotify misal /intl-id/track/ -> /track/
    clean_url = re.sub(r"/intl-[a-zA-Z]{2}/", "/", clean_url)
    
    title = "Spotify Track"
    artist = ""
    thumbnail = None

    # 1. Gunakan SpotiFLAC spotfetch resmi untuk membaca data track, artis, dan album Spotify
    try:
        from SpotiFLAC.client import AsyncSpotiFLAC
        
        async def _fetch():
            async with AsyncSpotiFLAC(output_dir=DOWNLOAD_DIR, log_level=40) as client:
                return await client.get_track_metadata(clean_url)
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Jika sudah di dalam running loop, jalankan di event loop terpisah
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    meta = pool.submit(asyncio.run, _fetch()).result(timeout=15)
            else:
                meta = loop.run_until_complete(_fetch())
        except RuntimeError:
            meta = asyncio.run(_fetch())

        if meta and meta.title:
            title = meta.title
            artist = ", ".join(meta.artist_names) if meta.artist_names else ""
            thumbnail = meta.cover_url
    except Exception:
        pass
        # Fallback ke scraping Open Graph
        try:
            req_page = urllib.request.Request(
                clean_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req_page, timeout=10) as resp:
                html = resp.read().decode("utf-8")
                
            t_match = re.search(r'property="og:title"\s+content="([^"]+)"', html)
            d_match = re.search(r'property="og:description"\s+content="([^"]+)"', html)
            img_match = re.search(r'property="og:image"\s+content="([^"]+)"', html)

            if t_match:
                title = t_match.group(1).strip()
            if d_match:
                desc = d_match.group(1).strip()
                if "·" in desc:
                    artist = desc.split("·")[0].strip()
                else:
                    artist = desc
            if img_match:
                thumbnail = img_match.group(1).strip()
        except Exception:
            pass

    # 2. Fallback ke Spotify oEmbed jika title masih default
    if title == "Spotify Track" or not thumbnail:
        try:
            api_url = f"https://open.spotify.com/oembed?url={clean_url}"
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            title = data.get("title", title)
            thumbnail = data.get("thumbnail_url", thumbnail)
        except Exception:
            pass

    uploader_name = artist if artist else "Spotify"
    full_display = f"{artist} - {title}" if artist and artist.lower() not in title.lower() else title

    return {
        "id": clean_url.split("/")[-1],
        "title": full_display,
        "raw_title": title,
        "artist": artist,
        "duration": None,
        "filesize": None,
        "thumbnail": thumbnail,
        "uploader": uploader_name,
        "url": clean_url,
        "is_spotify": True
    }

def _get_tiktok_info(url: str) -> dict:
    """
    Mengambil info video TikTok melalui TikWM API tanpa watermark.
    """
    import urllib.request
    import json
    
    clean_url = url.split("?")[0]
    # Jika link pendek (vt.tiktok.com), ikuti redirect ke URL penuhnya
    if "vt.tiktok.com" in clean_url:
        try:
            head_req = urllib.request.Request(clean_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(head_req, timeout=10) as head_resp:
                clean_url = head_resp.geturl().split("?")[0]
        except Exception:
            pass

    api_url = f"https://www.tikwm.com/api/?url={clean_url}"
    req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        
    if data.get("code") == 0:
        res = data.get("data", {})
        return {
            "id": res.get("id"),
            "title": res.get("title", "TikTok Video"),
            "duration": res.get("duration"),
            "filesize": res.get("size"),
            "thumbnail": res.get("cover"),
            "uploader": res.get("author", {}).get("nickname", "TikTok User"),
            "url": clean_url,
            "play_url": res.get("play"),
            "is_tiktok_direct": True
        }
    raise RuntimeError(f"TikWM API failed: {data.get('msg')}")

def extract_video_info(url: str) -> dict:
    """
    Mengekstrak informasi metadata media tanpa mengunduh konten file.
    Mendukung YouTube, TikTok, IG, FB, X/Twitter, dan Spotify.
    """
    if "spotify.com" in url:
        return _get_spotify_info(url)

    # Khusus TikTok: Coba yt-dlp terlebih dahulu, jika kena captcha challenge coba TikWM API
    if "tiktok.com" in url:
        try:
            opts = _get_base_ydl_opts()
            opts["noplaylist"] = True
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if "entries" in info and info["entries"]:
                    info = info["entries"][0]
                return {
                    "id": info.get("id"),
                    "title": info.get("title", "TikTok Video"),
                    "duration": info.get("duration"),
                    "filesize": info.get("filesize") or info.get("filesize_approx"),
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader", "TikTok Creator"),
                    "url": url,
                    "is_spotify": False
                }
        except Exception:
            return _get_tiktok_info(url)

    opts = _get_base_ydl_opts()
    opts["noplaylist"] = True
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # Tangani jika info mengembalikan playlist/entries
        if "entries" in info and info["entries"]:
            info = info["entries"][0]
            
        title = info.get("title", "Unknown Title")
        duration = info.get("duration")
        filesize = info.get("filesize") or info.get("filesize_approx")
        thumbnail = info.get("thumbnail")
        uploader = info.get("uploader", "Unknown Creator")
        
        return {
            "id": info.get("id"),
            "title": title,
            "duration": duration,
            "filesize": filesize,
            "thumbnail": thumbnail,
            "uploader": uploader,
            "url": url,
            "is_spotify": False
        }

def _download_spotify_track(url: str, mode: str = "flac") -> str:
    """
    Mengunduh lagu Spotify menggunakan SpotiFLAC dengan fallback ke audio yt-dlp.
    """
    # Unduh audio presisi dengan format FLAC (Lossless) atau MP3 (320kbps) sesuai permintaan
    spot_info = _get_spotify_info(url)
    title = spot_info.get("raw_title") or spot_info.get("title", "Spotify Track")
    artist = spot_info.get("artist", "")
    
    if artist and artist.lower() not in title.lower():
        search_query = f"ytsearch1:{artist} - {title}"
    else:
        search_query = f"ytsearch1:{title}"
    
    target_codec = "flac" if mode == "flac" else "mp3"
    target_ext = "flac" if mode == "flac" else "mp3"

    unique_id = uuid.uuid4().hex[:8]
    job_dir = os.path.join(DOWNLOAD_DIR, unique_id)
    os.makedirs(job_dir, exist_ok=True)
    output_template = os.path.join(job_dir, "%(title).80s.%(ext)s")
    opts = _get_base_ydl_opts()
    opts["outtmpl"] = output_template
    opts["noplaylist"] = True
    # Gunakan compression level 5 untuk FLAC (kecepatan encode jauh lebih tinggi tanpa mengurangi kualitas lossless)
    opts["postprocessors"] = [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": target_codec,
            "preferredquality": "5" if mode == "flac" else "320",
        }
    ]
    opts["postprocessor_args"] = {
        "ffmpeg": ["-threads", "0", "-compression_level", "5"] if mode == "flac" else ["-threads", "0"]
    }
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        result = ydl.extract_info(search_query, download=True)
        if "entries" in result and result["entries"]:
            result = result["entries"][0]
        
        filename = ydl.prepare_filename(result)
        base, _ = os.path.splitext(filename)
        downloaded_file = f"{base}.{target_ext}"
        
        if not os.path.exists(downloaded_file):
            for f in os.listdir(job_dir):
                if f.endswith(f".{target_ext}"):
                    downloaded_file = os.path.join(job_dir, f)
                    break

        if not os.path.exists(downloaded_file):
            raise FileNotFoundError("Gagal menemukan file lagu Spotify hasil download.")

        # Pindahkan ke root DOWNLOAD_DIR dengan nama aslinya
        clean_name = os.path.basename(downloaded_file)
        final_path = os.path.join(DOWNLOAD_DIR, clean_name)
        if os.path.exists(final_path):
            try:
                os.remove(final_path)
            except Exception:
                pass
        os.replace(downloaded_file, final_path)
        try:
            import shutil
            shutil.rmtree(job_dir, ignore_errors=True)
        except Exception:
            pass

        return final_path

def download_media(url: str, mode: str = "video", quality: str = "720") -> str:
    """
    Mengunduh media menggunakan yt-dlp atau SpotiFLAC.
    mode: "video" (mp4), "audio" (mp3), atau "spotify_flac" / "spotify_mp3"
    quality: "360", "480", "720", "flac", atau "mp3"
    Mengembalikan: path absolut file yang berhasil diunduh.
    """
    if "spotify.com" in url or mode in ("spotify_flac", "spotify_mp3"):
        spot_mode = "flac" if mode == "spotify_flac" or quality == "flac" else "mp3"
        return _download_spotify_track(url, mode=spot_mode)

    # Khusus TikTok jika yt-dlp terblokir
    if "tiktok.com" in url:
        try:
            tik_info = _get_tiktok_info(url)
            play_url = tik_info.get("play_url")
            raw_title = tik_info.get("title", "tiktok_video")[:50]
            clean_title = re.sub(r'[\\/*?:"<>|]', "", raw_title).strip() or "tiktok_video"
            if play_url:
                import urllib.request
                out_path = os.path.join(DOWNLOAD_DIR, f"{clean_title}.mp4")
                req = urllib.request.Request(play_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp, open(out_path, "wb") as f:
                    f.write(resp.read())
                return out_path
        except Exception:
            pass

    unique_id = uuid.uuid4().hex[:8]
    job_dir = os.path.join(DOWNLOAD_DIR, unique_id)
    os.makedirs(job_dir, exist_ok=True)
    output_template = os.path.join(job_dir, "%(title).80s.%(ext)s")
    
    opts = _get_base_ydl_opts()
    opts["outtmpl"] = output_template
    opts["noplaylist"] = True

    if mode == "audio":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    else:
        # Mode video MP4 dengan batasan resolusi
        height_map = {
            "360": "360",
            "480": "480",
            "720": "720",
        }
        max_height = height_map.get(quality, "720")
        
        opts["format"] = (
            f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"best[height<={max_height}][ext=mp4]/"
            f"bestvideo[height<={max_height}]+bestaudio/"
            f"best[height<={max_height}]/best"
        )
        opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(opts) as ydl:
        result = ydl.extract_info(url, download=True)
        
        if "entries" in result and result["entries"]:
            result = result["entries"][0]
            
        # Ambil nama file hasil unduh
        if "_filename" in result:
            downloaded_file = result["_filename"]
        else:
            downloaded_file = ydl.prepare_filename(result)
            
        # Jika audio dikonversi ke mp3, ekstensi file berubah
        if mode == "audio":
            base, _ = os.path.splitext(downloaded_file)
            downloaded_file = f"{base}.mp3"
            
        # Periksa file di filesystem jika ekstensi sedikit berbeda
        if not os.path.exists(downloaded_file):
            for f in os.listdir(job_dir):
                downloaded_file = os.path.join(job_dir, f)
                break

        if not os.path.exists(downloaded_file):
            raise FileNotFoundError(f"File hasil unduhan tidak ditemukan di: {downloaded_file}")

        # Pindahkan ke root DOWNLOAD_DIR dengan nama judul asli yang bersih
        clean_name = os.path.basename(downloaded_file)
        final_path = os.path.join(DOWNLOAD_DIR, clean_name)
        if os.path.exists(final_path):
            try:
                os.remove(final_path)
            except Exception:
                pass
        os.replace(downloaded_file, final_path)
        try:
            import shutil
            shutil.rmtree(job_dir, ignore_errors=True)
        except Exception:
            pass

        return final_path
