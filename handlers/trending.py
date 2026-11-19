"""Handlers for Trending GIFs menu, categories, and Next GIF pagination."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import TELEGRAM_MAX_FILE_SIZE_BYTES, Settings
from database import Database
from locales import BTN_TRENDING, get_text
from services import (
    CATEGORY_LABEL_KEYS,
    VALID_CATEGORIES,
    get_next_trending_gif,
)
from services.downloader import download_direct_file

logger = logging.getLogger(__name__)
router = Router(name="trending")


def build_trending_categories_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Build inline keyboard with the 4 trending GIF categories."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "cat_fa_twitter"),
                    callback_data="trend:cat:fa_twitter",
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text(lang, "cat_en_twitter"),
                    callback_data="trend:cat:en_twitter",
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text(lang, "cat_romantic"),
                    callback_data="trend:cat:romantic",
                ),
                InlineKeyboardButton(
                    text=get_text(lang, "cat_memes"),
                    callback_data="trend:cat:memes",
                ),
            ],
        ]
    )


def build_after_gif_keyboard(category: str, lang: str) -> InlineKeyboardMarkup:
    """Build inline keyboard attached under each sent trending GIF."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_next_gif"),
                    callback_data=f"trend:next:{category}",
                ),
                InlineKeyboardButton(
                    text=get_text(lang, "btn_change_category"),
                    callback_data="trend:menu",
                ),
            ]
        ]
    )


async def _send_trending_gif(
    target_message: Message,
    status_msg: Message,
    user_id: int,
    category: str,
    lang: str,
    db: Database,
    settings: Settings,
    bot: Bot,
) -> None:
    """Fetch an unseen trending GIF for the category and send it to the user."""
    gif_url = await get_next_trending_gif(db, user_id, category)
    if not gif_url:
        try:
            await status_msg.edit_text(
                text=get_text(lang, "err_trending_empty"),
                reply_markup=build_trending_categories_keyboard(lang),
            )
        except TelegramBadRequest:
            pass
        return

    me = await bot.get_me()
    category_title = get_text(lang, CATEGORY_LABEL_KEYS[category])
    caption = get_text(
        lang,
        "trending_caption",
        category=category_title,
        bot_username=me.username or "bot",
    )
    reply_markup = build_after_gif_keyboard(category, lang)

    # 1. Try direct URL animation send first (instant, zero disk overhead)
    try:
        await target_message.answer_animation(
            animation=gif_url,
            caption=caption,
            reply_markup=reply_markup,
        )
        await status_msg.delete()
        return
    except Exception:
        logger.debug("Direct URL animation send failed for %s, falling back to local download", gif_url)

    # 2. Fallback: download locally and upload via FSInputFile
    req_dir: Path | None = None
    try:
        file_path, req_dir = await download_direct_file(
            direct_url=gif_url,
            temp_root=settings.temp_dir,
            default_ext=".mp4",
        )
        if file_path.stat().st_size > TELEGRAM_MAX_FILE_SIZE_BYTES:
            raise ValueError("Trending GIF exceeded 50MB Telegram limit")

        await target_message.answer_animation(
            animation=FSInputFile(file_path),
            caption=caption,
            reply_markup=reply_markup,
        )
        await status_msg.delete()
    except Exception:
        logger.exception("Failed to send trending GIF")
        try:
            await status_msg.edit_text(
                text=get_text(lang, "err_trending_empty"),
                reply_markup=build_trending_categories_keyboard(lang),
            )
        except TelegramBadRequest:
            pass
    finally:
        if req_dir is not None:
            shutil.rmtree(req_dir, ignore_errors=True)


@router.message(Command("trending"))
@router.message(F.text == BTN_TRENDING)
async def cmd_trending(message: Message, db: Database) -> None:
    """Open the Trending GIFs category selection menu."""
    if message.from_user is None:
        return
    lang = await db.get_user_language(message.from_user.id)
    await message.answer(
        text=get_text(lang, "trending_menu_title"),
        reply_markup=build_trending_categories_keyboard(lang),
    )


@router.callback_query(F.data == "trend:menu")
async def cb_trending_menu(callback: CallbackQuery, db: Database) -> None:
    """Show the category menu when user taps 'Categories' under a GIF."""
    if callback.message is None:
        return
    lang = await db.get_user_language(callback.from_user.id)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            text=get_text(lang, "trending_menu_title"),
            reply_markup=build_trending_categories_keyboard(lang),
        )


@router.callback_query(F.data.startswith("trend:"))
async def cb_trending_category(
    callback: CallbackQuery,
    db: Database,
    settings: Settings,
    bot: Bot,
) -> None:
    """Handle category selection (trend:cat:<key>) and Next GIF button (trend:next:<key>)."""
    if callback.data is None or callback.message is None:
        return

    lang = await db.get_user_language(callback.from_user.id)
    parts = callback.data.split(":")
    if len(parts) != 3 or parts[1] not in ("cat", "next"):
        await callback.answer(get_text(lang, "err_generic"), show_alert=True)
        return

    action = parts[1]
    category = parts[2]
    if category not in VALID_CATEGORIES:
        await callback.answer(get_text(lang, "err_generic"), show_alert=True)
        return

    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    if action == "cat":
        status_msg = callback.message
        try:
            await status_msg.edit_text(text=get_text(lang, "fetching_trending"))
        except TelegramBadRequest:
            pass
    else:
        status_msg = await callback.message.answer(
            text=get_text(lang, "fetching_trending")
        )

    await _send_trending_gif(
        target_message=callback.message,
        status_msg=status_msg,
        user_id=callback.from_user.id,
        category=category,
        lang=lang,
        db=db,
        settings=settings,
        bot=bot,
    )