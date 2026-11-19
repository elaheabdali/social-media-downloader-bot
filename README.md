# 🚀 Social Media Downloader Telegram Bot

An asynchronous, bilingual (**English & Persian**) Telegram bot built with **Python**, **aiogram 3**, and **yt-dlp** for downloading media from **YouTube**, **X (Twitter)**, and **Instagram**.

---

## ✨ Features

### 📺 YouTube
- **Multi-Resolution Downloads:** Download YouTube videos and Shorts in `1080p`, `720p`, `480p`, `360p`, etc., with automatic Telegram 50 MB size checks.
- **MP3 Audio Extraction:** Extract crisp `192kbps` MP3 audio from any video using bundled FFmpeg.
- **YouTube Channel Search:** Search any channel by name or `@handle` (or paste a channel link) to browse and download its latest uploads.

### 🐦 X (Twitter)
- **Videos & Native GIFs:** Automatically detects Twitter GIFs and sends them as looping Telegram animations.
- **Video-to-GIF Converter:** Convert any X video clip into a lightweight, muted Telegram GIF with one tap.
- **Resilient Fallback:** Uses `FxTwitter` fallback for age-restricted (NSFW) and `/photo/1` status URLs.

### 📸 Instagram
- **Reels, Posts & Carousels:** Downloads single and multi-slide photo/video posts.
- **HD Profile Pictures:** Send any public or private Instagram profile link to fetch its full-resolution avatar.

### 🔥 Trending GIFs Menu
- Browse curated, non-repeating trending GIFs across **Persian X**, **English X**, **Romantic**, and **Memes & Funny** categories.

---

## 🛠️ Tech Stack
- **Framework:** `aiogram` (v3)
- **Media Engine:** `yt-dlp` + `imageio-ffmpeg` + `aiohttp`
- **Database:** `aiosqlite` (user language preferences & seen GIF history)
- **Deployment:** Ready for Render Web Service (`keep_alive.py` health-check server included)

---

## ⚙️ Environment Variables

| Variable | Required | Description |
| :--- | :---: | :--- |
| `BOT_TOKEN` | Yes | Telegram Bot API token from `@BotFather` |
| `OWNER_HANDLE` | No | Owner handle shown in startup logs (default: `@elaheabdli`) |
| `INSTAGRAM_COOKIES` | No | Netscape-formatted `cookies.txt` content for Instagram profile/post auth |
| `YOUTUBE_COOKIES` | No | Optional Netscape-formatted `cookies.txt` content for YouTube |
