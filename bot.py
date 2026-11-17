"""Main entry point for the X/Twitter Media Downloader Telegram Bot."""

from __future__ import annotations

import asyncio
import logging
import shutil

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config import Settings
from database import Database
from handlers import media_router, start_router
from services import PendingDownloadStore


def setup_logging(level: str) -> None:
    """Configure structured application logging."""
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Reduce noisy third-party logs
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


async def set_bot_commands(bot: Bot) -> None:
    """Register slash commands in Telegram's command menu."""
    commands = [
        BotCommand(command="start", description="Start the bot / شروع ربات"),
        BotCommand(command="language", description="Switch language / تغییر زبان"),
        BotCommand(command="help", description="Usage guide / راهنما"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    settings = Settings.from_env()
    setup_logging(settings.log_level)
    logger = logging.getLogger("bot")

    db = Database(settings.db_path)
    pending_store = PendingDownloadStore(ttl_seconds=1800)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Inject shared dependencies into all handlers
    dp["db"] = db
    dp["settings"] = settings
    dp["pending_store"] = pending_store

    dp.include_routers(start_router, media_router)

    @dp.startup()
    async def on_startup() -> None:
        await db.connect()
        await set_bot_commands(bot)
        logger.info("Bot started successfully (owner: %s).", settings.owner_handle)

    @dp.shutdown()
    async def on_shutdown() -> None:
        await db.close()
        if settings.temp_dir.exists():
            for child in settings.temp_dir.iterdir():
                if child.is_dir() and child.name.startswith("xbot_"):
                    shutil.rmtree(child, ignore_errors=True)
        logger.info("Graceful shutdown complete.")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
