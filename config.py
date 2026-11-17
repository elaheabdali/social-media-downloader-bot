"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB standard Bot API limit


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings for the Telegram bot."""

    bot_token: str
    owner_handle: str
    db_path: Path
    temp_dir: Path
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token or bot_token == "your_telegram_bot_token_here":
            raise ValueError(
                "BOT_TOKEN is missing or not configured. "
                "Please copy .env.example to .env and set your @BotFather token."
            )

        owner_handle = os.getenv("OWNER_HANDLE", "@elaheabdli").strip()
        db_path = Path(os.getenv("DB_PATH", "data/bot.db")).resolve()
        temp_dir = Path(os.getenv("TEMP_DIR", "temp_downloads")).resolve()
        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

        db_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            bot_token=bot_token,
            owner_handle=owner_handle,
            db_path=db_path,
            temp_dir=temp_dir,
            log_level=log_level,
        )
