<div align="center">

# 🚀 All-in-One Media Downloader Bot

**Paste a link. Pick a quality. Get your media in seconds.**

A fast, asynchronous Telegram bot that downloads video and audio from **YouTube, TikTok, Instagram, Facebook, X (Twitter), and Spotify**.

[![Open in Telegram](https://img.shields.io/badge/Try%20it%20now-%40CihuyDownloaderBot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/CihuyDownloaderBot)

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white)
![yt-dlp](https://img.shields.io/badge/Powered%20by-yt--dlp-red)
[![Trakteer](https://img.shields.io/badge/Support-Trakteer-red?logo=kofi&logoColor=white)](https://trakteer.id/Kiyawi)
![License](https://img.shields.io/badge/Use-Personal%20%26%20Educational-lightgrey)

[Live Bot](#-try-the-bot) · [Features](#-features) · [Quick Start](#-quick-start) · [Usage](#-usage) · [VIP & Monetization](#-role-hierarchy-admin-vs-vip-vs-regular) · [FAQ](#-faq--troubleshooting) · [Credits](#-credits--acknowledgements)

</div>

---

## 🤖 Try the Bot

No installation needed. Just open Telegram and start chatting:

<div align="center">

### 👉 [**@CihuyDownloaderBot**](https://t.me/CihuyDownloaderBot) 👈

</div>

1. Open [t.me/CihuyDownloaderBot](https://t.me/CihuyDownloaderBot)
2. Press **Start**
3. Paste any supported link and pick your quality

> Want to host your own copy? Follow the [Quick Start](#-quick-start) guide below.

---

## ✨ Features

### 🌐 Supported Platforms

| Platform | What you can download | Output |
|---|---|---|
| 📺 **YouTube** | Videos, audio, high-res thumbnail | MP4 (360p - 1080p), MP3, HD Photo |
| 🎵 **TikTok** | Watermark-free videos & Photo slides | MP4, Media Group / HD Photo |
| 📸 **Instagram** | Reels, post videos, photos | MP4, HD Photo |
| 👥 **Facebook** | Public videos, Watch clips, photos | MP4, HD Photo |
| 🐦 **X / Twitter** | Video tweets, clips, pictures | MP4, HD Photo |
| 🎧 **Spotify** | Tracks & Cover Art | Lossless FLAC or MP3 (320 kbps) with cover art and ID3 tags |

### ⚡ Performance

- **Fast uploads** – HTTPX connection pool with 16 parallel workers and an 8 MB streaming chunk buffer.
- **Instant previews** – MP4 `+faststart` (moov atom at the head) so videos can start playing in Telegram right away.
- **Fully asynchronous** – built on `python-telegram-bot` with non-blocking I/O.

### 🧠 Smart Queue (Zero Database)

- In-memory `asyncio.Semaphore` limits heavy jobs to **2 at a time**, protecting server bandwidth and CPU.
- Live queue updates, e.g. `⏳ In Queue (Position #1)`.

### 👑 VIP Admin Privileges

- ⚡ Queue bypass for instant processing
- ♾️ No rate limit
- ⏱️ Extended video duration limits

### 🔒 Security & Stability

- Global error handler that never leaks server tracebacks to users.
- Per-user rate limiting.
- Automatic disk cleanup every 30 minutes.

---

## 🧰 Tech Stack

| Component | Purpose |
|---|---|
| [`python-telegram-bot`](https://python-telegram-bot.org/) | Telegram Bot API framework |
| [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) | Video/audio extraction |
| [`SpotiFLAC`](https://pypi.org/project/SpotiFLAC/) | Spotify downloads (FLAC / MP3) |
| [`HTTPX`](https://www.python-httpx.org/) | Fast async HTTP & uploads |
| [`FFmpeg`](https://ffmpeg.org/) | Conversion, merging, `+faststart` |
| [`Pyrogram`](https://github.com/pyrogram/pyrogram) | MTProto client for 2 GB parallel uploads _(optional)_ |
| [`TgCrypto`](https://github.com/pyrogram/tgcrypto) | Fast AES encryption for MTProto _(optional)_ |

---

## 📋 Requirements

- **Python 3.10+**
- **FFmpeg** – installed on your system, or provided through the `imageio-ffmpeg` package
- A **Telegram Bot Token** from [@BotFather](https://t.me/BotFather)

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <repo-folder>
```

### 2. Create a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file:

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

Then edit `.env`:

```env
# Telegram Bot Token from @BotFather
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ

# Admin Telegram User IDs (comma-separated for multiple admins)
ADMIN_IDS=123456789,987654321

# (Optional) MTProto API credentials from https://my.telegram.org
# Unlocks 2000 MB (2 GB) file uploads with IDM-like parallel chunk speed
TELEGRAM_API_ID=
TELEGRAM_API_HASH=

# Optional limits & integrations
MAX_FILE_SIZE_MB=50
MAX_DURATION_SECONDS=600
RATE_LIMIT_MAX_REQUESTS=3
RATE_LIMIT_WINDOW_SECONDS=900
COOKIES_FILE=cookies.txt
TRAKTEER_URL=https://trakteer.id/your_username
```

<details>
<summary><b>⚙️ Configuration reference</b></summary>

| Variable | Required | Description | Example |
|---|:---:|---|---|
| `BOT_TOKEN` | ✅ | Token from @BotFather | `123456789:ABC...` |
| `ADMIN_IDS` | ❌ | Comma-separated admin user IDs | `123456789,987654321` |
| `TELEGRAM_API_ID` | ❌ | API ID from my.telegram.org for 2 GB uploads | `12345678` |
| `TELEGRAM_API_HASH` | ❌ | API Hash from my.telegram.org for 2 GB uploads | `0123456789abcdef...` |
| `TRAKTEER_URL` | ❌ | Your Trakteer page for donations / VIP rewards | `https://trakteer.id/mychannel` |
| `MAX_FILE_SIZE_MB` | ❌ | Maximum file size for standard HTTP API | `50` |
| `MAX_DURATION_SECONDS` | ❌ | Maximum video length for regular users (seconds) | `600` |
| `RATE_LIMIT_MAX_REQUESTS` | ❌ | Maximum download links allowed per window | `3` |
| `RATE_LIMIT_WINDOW_SECONDS` | ❌ | Rate limit time window in seconds | `900` (15 min) |
| `COOKIES_FILE` | ❌ | Path to an exported cookies file | `cookies.txt` |

</details>

### 5. Run the bot

```bash
python bot.py
```

> 💡 On Windows you can also run it with the venv explicitly: `.venv\Scripts\python.exe bot.py`

---

## 📖 Usage

### Commands

| Command | Description | Permission |
|---|---|:---:|
| `/start` | Start the bot and open the welcome menu | Everyone |
| `/menu` | Show interactive navigation buttons | Everyone |
| `/help` | Usage guide and platform rules | Everyone |
| `/ping` | Check server responsiveness and latency | Everyone |
| `/id` | Show your Telegram User ID, role, and quota status | Everyone |
| `/vip` | View VIP membership benefits & donation guide | Everyone |
| `/redeem <CODE>` | Redeem a voucher code to activate VIP access | Everyone |
| `/addvip <ID> [DAYS]` | Grant VIP access to a user ID directly | 👑 Admin Only |
| `/makecode [DAYS]` | Generate a redeemable VIP voucher code | 👑 Admin Only |
| `/about` | Bot version and engine information | Everyone |

### Downloading media

```text
1️⃣  Copy a link from YouTube, TikTok, Instagram, Facebook, X, or Spotify
2️⃣  Paste it into the bot chat
3️⃣  Choose a quality from the inline buttons
4️⃣  Receive your file directly in Telegram ✅
```

**Quality options**

- 📸 **Photo:** `Full HD Photo` · `Media Group Carousel` _(TikTok Slides & Instagram Posts/Albums)_
- 🎬 **Video:** `360p (SD)` · `480p (HQ)` · `720p (HD)` · `1080p (Full HD)`
- 🎵 **Audio:** `MP3 (192 kbps)` · `FLAC (Lossless)` _(Spotify with embedded cover & tags)_

---

## 👥 Role Hierarchy: Admin vs VIP vs Regular

| Feature | 👤 Regular User | ⭐ VIP Member | 👑 Admin (Owner) |
|---|:---:|:---:|:---:|
| **Rate Limit** | 3 links / 15 minutes | ♾️ Unlimited | ♾️ Unlimited |
| **Download Queue** | Wait in queue (max 2) | ⚡ Instant bypass | ⚡ Instant bypass |
| **Video Duration** | Max 10 minutes | ⏱️ Unlimited | ⏱️ Unlimited |
| **Quality** | Up to 720p & MP3 | **Full HD 1080p & FLAC** | **Full HD 1080p & FLAC** |
| **Max File Size** | 50 MB | **Up to 2000 MB (2 GB)** | **Up to 2000 MB (2 GB)** |
| **Parallel Acceleration** | Standard HTTP | **Multi-Part IDM Engine** | **Multi-Part IDM Engine** |
| **Management Commands** | ❌ | ❌ | **`/addvip` & `/makecode`** |

### 👑 Setting Up Admin (Owner)

1. Send `/id` to the bot to get your **Telegram User ID**.
2. Add your ID to `.env`:
   ```env
   ADMIN_IDS=123456789
   ```
3. Restart the bot.

### ☕ Monetization with Trakteer (Rp 10.000 / Bulan)

The bot supports automatic VIP activation and voucher redemption for **Rp 10.000 / month**:

1. **Automatic Webhook Upgrade:**
   - Supporter sends a tip of **Rp 10.000** at [`teer.id/Kiyawi`](https://trakteer.id/Kiyawi).
   - In the support message, they include their Telegram User ID.
   - The bot receives the Trakteer webhook and activates their 1-month VIP perks immediately.

2. **Voucher System:**
   - Admin generates vouchers using `/makecode`:
     ```text
     /makecode 30
     ```
     _The bot replies with a voucher code, e.g._ `VIP-30D-A7B8C9`.
   - Admin places the code in a Trakteer Exclusive Reward (Rp 10.000).
   - Supporter redeems the voucher inside Telegram:
     ```text
     /redeem VIP-30D-A7B8C9
     ```
   - The bot activates their VIP perks and logs it into `database.db`.

---

## ⚡ Multi-Part Parallel Upload Engine

When `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` are provided in `.env`:

- Bot bypasses the traditional single-connection HTTP limit.
- Files are sliced into 512 KB chunks and transferred over **8 concurrent TCP streams** directly to Telegram Data Centers using native `Pyrogram MTProto` and `TgCrypto` (AES-NI hardware acceleration).
- Upload speeds increase by up to **300% - 500%**.

---

## 🔐 Security Best Practices

- **Keep secrets private.** Never commit `.env` or `cookies.txt` (both are already in `.gitignore`).
- **Use cookies only when needed.** If YouTube or Instagram asks for a captcha or login, export your cookies to `cookies.txt` in the project root.
- **Disk stays clean.** Temporary files in `downloads/` are purged every 30 minutes by the background scheduler.

---

## ❓ FAQ & Troubleshooting

<details>
<summary><b>The bot doesn't respond at all</b></summary>

Check that `BOT_TOKEN` is correct, the bot is running, and you have started a chat with it using `/start`.

</details>

<details>
<summary><b>"FFmpeg not found" error</b></summary>

Install FFmpeg on your system and make sure it is on your `PATH`, or install the `imageio-ffmpeg` package.

</details>

<details>
<summary><b>YouTube or Instagram asks me to log in / solve a captcha</b></summary>

Export your browser cookies to `cookies.txt` in the project root and set `COOKIES_FILE=cookies.txt` in `.env`.

</details>

<details>
<summary><b>My download is rejected as too large or too long</b></summary>

Regular users are limited by `MAX_FILE_SIZE_MB` and `MAX_DURATION_SECONDS`. Choose a lower quality, or get VIP access with `/vip`.

</details>

<details>
<summary><b>A download suddenly stopped working</b></summary>

Platforms change often. Update the extractor with `pip install -U yt-dlp` and restart the bot.

</details>

---

## 🗺️ Roadmap

- [ ] Playlist support
- [ ] More audio formats
- [ ] Per-user download history
- [ ] Docker image for one-command deployment

_Edit this list to match your real plans._

---

## 🤝 Contributing

Issues and pull requests are welcome. For larger changes, please open an issue first to discuss what you would like to change.

---

## 🙏 Credits & Acknowledgements

This bot stands on the shoulders of amazing open-source projects. Huge thanks to their authors and contributors:

| Project | Role in this bot | Link |
|---|---|---|
| **SpotiFLAC (Python Module)** | Spotify track downloads in FLAC / MP3 | [PyPI](https://pypi.org/project/SpotiFLAC/) · [GitHub](https://github.com/BartolomeoRusso9/SpotiFLAC-Module-Version) |
| **SpotiFLAC (Desktop)** | The original SpotiFLAC project | [GitHub](https://github.com/spotbye/SpotiFLAC) |
| **SpotiFLAC (Mobile)** | Android & iOS version, maintained by @zarzet | [GitHub](https://github.com/spotiflacapp/SpotiFLAC-Mobile) |
| **yt-dlp** | Video and audio extraction | [GitHub](https://github.com/yt-dlp/yt-dlp) |
| **python-telegram-bot** | Telegram Bot API framework | [GitHub](https://github.com/python-telegram-bot/python-telegram-bot) |
| **HTTPX** | Async HTTP client and fast uploads | [GitHub](https://github.com/encode/httpx) |
| **FFmpeg** | Media conversion and `+faststart` | [ffmpeg.org](https://ffmpeg.org/) |
| **Pyrogram** | MTProto client for 2 GB parallel uploads | [GitHub](https://github.com/pyrogram/pyrogram) |
| **TgCrypto** | Fast cryptography for MTProto | [GitHub](https://github.com/pyrogram/tgcrypto) |

All trademarks, platform names, and content belong to their respective owners. This project is not affiliated with or endorsed by YouTube, TikTok, Instagram, Facebook, X, Spotify, or Telegram.

---

## ⚠️ Disclaimer

This project is for **educational and personal archiving purposes only**. Please respect copyright laws and the terms of service of each content provider. The author is not responsible for any misuse.

---

<div align="center">

Made with ❤️ using Python · Try it on Telegram: [@CihuyDownloaderBot](https://t.me/CihuyDownloaderBot)

If this project helps you, consider giving it a ⭐

</div>