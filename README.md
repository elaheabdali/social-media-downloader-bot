
# X (Twitter) GIF & Video Downloader Bot

An asynchronous Telegram bot for downloading GIFs and videos from X (Twitter).

## Try the Bot

[Start the Telegram Bot](https://t.me/bezanDownld_bot)

## Features

- Download videos from X (Twitter).
- Automatically detect and send GIFs.
- Select video quality.
- English and Persian language support.
- Asynchronous processing with aiogram.

## Tech Stack

- Python 3.11+
- aiogram 3
- yt-dlp
- SQLite
- aiosqlite
- python-dotenv

## Installation

1. Clone the repository.
2. Create a virtual environment.
3. Install dependencies.
4. Configure your `.env` file.
5. Run the bot.


Production-ready, asynchronous Telegram bot built with **Python 3.11+**, **aiogram v3**, **yt-dlp**, **aiosqlite**, and **python-dotenv**.

## Features
- **Bilingual (English & Persian / فارسی):** Language selection on `/start`, `/language`, or via persistent menu buttons, persisted per user in SQLite.
- **Smart X/Twitter Detection:** Supports `x.com`, `twitter.com`, `t.co`, `fxtwitter.com`, and `vxtwitter.com`.
- **Automatic GIF Handling:** Detects X/Twitter looping MP4 GIFs and sends them natively via `send_animation()`.
- **Interactive Video Quality Selection:** Extracts available resolutions (`1080p`, `720p`, `480p`, `360p`, etc.) with approximate file sizes and Telegram's 50 MB Bot API limit check.
- **Non-blocking & Clean:** Runs `yt-dlp` inside `asyncio.to_thread` and guarantees per-request temp directory cleanup via `try...finally`.

## Project Structure
```text
x_media_downloader_bot/
├── bot.py                  # Entry point, logging, and graceful shutdown
├── config.py               # Environment configuration loader
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── database/
│   ├── __init__.py
│   └── db.py               # Async SQLite user language storage
├── locales/
│   ├── __init__.py
│   └── i18n.py             # English & Persian translations
├── services/
│   ├── __init__.py
│   └── downloader.py       # Async yt-dlp wrapper & temp file management
└── handlers/
    ├── __init__.py
    ├── start.py            # /start, /language, /help handlers
    └── media.py            # Link detection, GIF auto-send, quality selection
```

## Quick Start
1. Install Python 3.11+ and `ffmpeg`.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and add your `BOT_TOKEN` from `@BotFather`.
5. Run the bot:
   ```bash
   python bot.py
   ```
