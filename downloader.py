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
        # Extractor args untuk menghindari HTTP Error 403 dari YouTube player web
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios"]
            }
        },
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
        images = res.get("images", [])
        return {
            "id": res.get("id"),
            "title": res.get("title", "TikTok Media"),
            "duration": res.get("duration"),
            "filesize": res.get("size"),
            "thumbnail": res.get("cover"),
            "images": images,
            "is_slide": bool(images),
            "uploader": res.get("author", {}).get("nickname", "TikTok User"),
            "url": clean_url,
            "play_url": res.get("play"),
            "is_tiktok_direct": True
        }
    raise RuntimeError(f"TikWM API failed: {data.get('msg')}")

def _get_instagram_info(url: str) -> dict:
    """
    Mengekstrak informasi postingan foto atau carousel Instagram menggunakan instaloader.
    """
    import instaloader
    clean_url = url.split("?")[0].rstrip("/")
    # Ambil shortcode dari /p/SHORTCODE/ atau /reel/SHORTCODE/
    parts = clean_url.split("/")
    shortcode = parts[-1]
    if shortcode in ("p", "reel", "reels", "tv") and len(parts) >= 2:
        shortcode = parts[-2]

    L = instaloader.Instaloader(download_videos=False, save_metadata=False, download_comments=False)
    post = instaloader.Post.from_shortcode(L.context, shortcode)
    
    # Kumpulkan semua gambar (single image atau carousel / sidecar nodes)
    images = []
    sidecars = list(post.get_sidecar_nodes())
    if sidecars:
        for s in sidecars:
            if not s.is_video and s.display_url:
                images.append(s.display_url)
    elif post.url:
        images.append(post.url)

    caption_title = (post.caption or "").strip().split("\n")[0][:80] or f"Instagram Post by {post.owner_username}"
    return {
        "id": shortcode,
        "title": caption_title,
        "uploader": f"@{post.owner_username}",
        "thumbnail": post.url,
        "images": images,
        "is_photo_post": True,
        "is_slide": len(images) > 1,
        "url": clean_url,
        "is_spotify": False
    }

def download_photo(url: str) -> list[str]:
    """
    Mengunduh foto/gambar resolusi tinggi dari tautan TikTok Slide, Instagram, X/Twitter, FB, atau thumbnail resmi.
    Mengembalikan list path absolut file foto (.jpg / .png).
    """
    import urllib.request
    
    # 1. Khusus Instagram: Gunakan Instaloader untuk single post atau carousel album
    if "instagram.com" in url:
        try:
            ig_info = _get_instagram_info(url)
            images = ig_info.get("images") or []
            if images:
                downloaded_photos = []
                for idx, img_url in enumerate(images):
                    unique_id = uuid.uuid4().hex[:8]
                    out_path = os.path.join(DOWNLOAD_DIR, f"ig_photo_{idx+1}_{unique_id}.jpg")
                    req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=20) as resp, open(out_path, "wb") as f:
                        f.write(resp.read())
                    downloaded_photos.append(out_path)
                if downloaded_photos:
                    return downloaded_photos
        except Exception:
            pass

    # 2. Khusus TikTok Photo Slide atau single photo
    if "tiktok.com" in url:
        try:
            tik_info = _get_tiktok_info(url)
            images = tik_info.get("images") or []
            if images:
                # Unduh semua foto slide TikTok
                downloaded_photos = []
                for idx, img_url in enumerate(images):
                    unique_id = uuid.uuid4().hex[:8]
                    out_path = os.path.join(DOWNLOAD_DIR, f"photo_slide_{idx+1}_{unique_id}.jpg")
                    req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=20) as resp, open(out_path, "wb") as f:
                        f.write(resp.read())
                    downloaded_photos.append(out_path)
                if downloaded_photos:
                    return downloaded_photos
            elif tik_info.get("thumbnail"):
                unique_id = uuid.uuid4().hex[:8]
                out_path = os.path.join(DOWNLOAD_DIR, f"photo_{unique_id}.jpg")
                req = urllib.request.Request(tik_info["thumbnail"], headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=20) as resp, open(out_path, "wb") as f:
                    f.write(resp.read())
                return [out_path]
        except Exception:
            pass

    # 3. Twitter / YouTube Thumbnail HD / platform lain via yt-dlp
    unique_id = uuid.uuid4().hex[:8]
    out_path = os.path.join(DOWNLOAD_DIR, f"photo_{unique_id}.jpg")
    opts = _get_base_ydl_opts()
    opts["noplaylist"] = True
    opts["skip_download"] = True
    opts["writethumbnail"] = True
    output_template = os.path.join(DOWNLOAD_DIR, f"photo_{unique_id}.%(ext)s")
    opts["outtmpl"] = output_template

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if "entries" in info and info["entries"]:
            info = info["entries"][0]
        
        # Ambil thumbnail terbaik
        thumb_url = info.get("thumbnail")
        thumbnails = info.get("thumbnails", [])
        if thumbnails:
            # Ambil thumbnail dengan resolusi tertinggi
            thumb_url = thumbnails[-1].get("url") or thumb_url

        if thumb_url:
            req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp, open(out_path, "wb") as f:
                f.write(resp.read())
            return [out_path]

    raise FileNotFoundError("Gagal mengekstrak atau mengunduh foto dari tautan ini.")

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

    # Khusus Instagram: Jika postingan foto / carousel, prioritaskan _get_instagram_info jika yt-dlp gagal
    if "instagram.com" in url:
        try:
            opts = _get_base_ydl_opts()
            opts["noplaylist"] = True
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if "entries" in info and info["entries"]:
                    info = info["entries"][0]
                return {
                    "id": info.get("id"),
                    "title": info.get("title", "Instagram Video"),
                    "duration": info.get("duration"),
                    "filesize": info.get("filesize") or info.get("filesize_approx"),
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader", "Instagram Creator"),
                    "url": url,
                    "is_spotify": False,
                    "is_photo_post": False
                }
        except Exception:
            return _get_instagram_info(url)

    opts = _get_base_ydl_opts()
    opts["noplaylist"] = True

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
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
            "is_spotify": False,
            "is_photo_post": False
        }

def _download_spotify_track(url: str, mode: str = "flac") -> str:
    """
    Mengunduh lagu Spotify menggunakan SpotiFLAC dengan fallback ke audio yt-dlp.
    """
    # Unduh audio presisi dengan format FLAC (Lossless) atau MP3 (320kbps) sesuai permintaan
    spot_info = _get_spotify_info(url)
    import html as html_lib
    raw_title = spot_info.get("raw_title") or spot_info.get("title", "Spotify Track")
    raw_artist = spot_info.get("artist", "")
    
    # Unescape HTML entities seperti &amp; -> & dan bersihkan karakter aneh
    title = html_lib.unescape(raw_title).replace("&amp;", "&")
    artist = html_lib.unescape(raw_artist).replace("&amp;", "&")
    
    # Ambil judul inti tanpa (feat. xxx) jika pencarian penuh terlalu rumit untuk YouTube
    core_title = re.sub(r'\(feat\..*?\)', '', title, flags=re.IGNORECASE).strip()

    candidate_queries = []
    if artist and artist.lower() not in title.lower():
        candidate_queries.append(f"ytsearch1:{artist} - {title}")
        if core_title != title:
            candidate_queries.append(f"ytsearch1:{artist} - {core_title}")
        candidate_queries.append(f"ytsearch1:{title} {artist}")
    candidate_queries.append(f"ytsearch1:{title}")
    if core_title != title:
        candidate_queries.append(f"ytsearch1:{core_title}")

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

    import logging
    log = logging.getLogger(__name__)

    result = None
    with yt_dlp.YoutubeDL(opts) as ydl:
        for q in candidate_queries:
            log.info(f"Mencari lagu Spotify di YouTube: '{q}' (target: {target_ext})")
            try:
                res = ydl.extract_info(q, download=True)
                if res and "entries" in res and res["entries"]:
                    result = res["entries"][0]
                    break
                elif res and "entries" not in res:
                    result = res
                    break
            except Exception as search_err:
                log.warning(f"Query '{q}' gagal: {search_err}")

        if not result:
            raise FileNotFoundError(f"Lagu tidak ditemukan di YouTube untuk query: {candidate_queries}")

        filename = ydl.prepare_filename(result)
        base, _ = os.path.splitext(filename)
        downloaded_file = f"{base}.{target_ext}"
        
        job_files = os.listdir(job_dir)
        log.info(f"Isi folder job_dir ({job_dir}): {job_files}")

        if not os.path.exists(downloaded_file):
            for f in job_files:
                if f.endswith(f".{target_ext}"):
                    downloaded_file = os.path.join(job_dir, f)
                    break

        if not os.path.exists(downloaded_file):
            for f in job_files:
                if f.endswith((".flac", ".mp3", ".m4a", ".ogg", ".opus", ".mp4", ".webm")):
                    downloaded_file = os.path.join(job_dir, f)
                    break

        if not os.path.exists(downloaded_file):
            raise FileNotFoundError(f"Gagal menemukan file lagu Spotify hasil download. File di folder: {job_files}")

        # Sematkan metadata resmi Spotify (Cover Art, Title, Artist) menggunakan Mutagen
        thumbnail_url = spot_info.get("thumbnail")
        real_title = spot_info.get("raw_title") or spot_info.get("title", "Spotify Track")
        real_artist = spot_info.get("artist", "")
        
        cover_data = None
        if thumbnail_url:
            try:
                import urllib.request
                req_cover = urllib.request.Request(thumbnail_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req_cover, timeout=10) as c_resp:
                    cover_data = c_resp.read()
            except Exception as cov_err:
                log.warning(f"Gagal mengambil thumbnail Spotify: {cov_err}")

        try:
            if downloaded_file.endswith(".mp3"):
                from mutagen.mp3 import MP3
                from mutagen.id3 import ID3, TIT2, TPE1, APIC, ID3NoHeaderError
                try:
                    audio = MP3(downloaded_file, ID3=ID3)
                except ID3NoHeaderError:
                    audio = MP3(downloaded_file)
                    audio.add_tags()
                if audio.tags is None:
                    audio.add_tags()
                audio.tags.add(TIT2(encoding=3, text=real_title))
                if real_artist:
                    audio.tags.add(TPE1(encoding=3, text=real_artist))
                if cover_data:
                    audio.tags.add(APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,  # Front cover
                        desc="Cover",
                        data=cover_data
                    ))
                audio.save()
            elif downloaded_file.endswith(".flac"):
                from mutagen.flac import FLAC, Picture
                audio = FLAC(downloaded_file)
                audio["title"] = real_title
                if real_artist:
                    audio["artist"] = real_artist
                if cover_data:
                    pic = Picture()
                    pic.type = 3
                    pic.mime = "image/jpeg"
                    pic.desc = "Cover"
                    pic.data = cover_data
                    audio.clear_pictures()
                    audio.add_picture(pic)
                audio.save()
        except Exception as tag_err:
            log.warning(f"Gagal menyematkan tag metadata ke file audio: {tag_err}")

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
            "1080": "1080",
        }
        max_height = height_map.get(quality, "720")
        
        opts["format"] = (
            f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"best[height<={max_height}][ext=mp4]/"
            f"bestvideo[height<={max_height}]+bestaudio/"
            f"best[height<={max_height}]/best"
        )
        opts["merge_output_format"] = "mp4"
        # Pindahkan moov atom ke awal file (+faststart) agar Telegram langsung bisa streaming tanpa re-buffering lambat
        opts["postprocessor_args"] = {
            "ffmpeg": ["-threads", "0"],
            "merger": ["-movflags", "+faststart"]
        }

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
