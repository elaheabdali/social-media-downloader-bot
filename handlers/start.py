"""Handlers for /start, /language, /help, and language selection callbacks."""

from __future__ import annotations

import html
from typing import Literal

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from database import Database
from locales import BTN_HELP, BTN_LANGUAGE, BTN_TRENDING, BTN_YOUTUBE, get_text

router = Router(name="start")


def build_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Persistent bottom menu for Trending GIFs, YouTube Channel search, language, and help."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_TRENDING), KeyboardButton(text=BTN_YOUTUBE)],
            [KeyboardButton(text=BTN_LANGUAGE), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_language_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for choosing English or Persian."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇸 English", callback_data="lang:en"),
                InlineKeyboardButton(text="🇮🇷 فارسی", callback_data="lang:fa"),
            ]
        ]
    )


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database) -> None:
    """Greet the user and prompt for language selection."""
    user = message.from_user
    if user is None:
        return

    lang = await db.get_user_language(user.id)
    safe_name = html.escape(user.full_name or "there")

    await message.answer(
        text=get_text(lang, "welcome", name=safe_name),
        reply_markup=build_language_inline_keyboard(),
    )
    await message.answer(
        text="⬇️",
        reply_markup=build_main_menu_keyboard(),
    )


@router.message(Command("language"))
@router.message(F.text == BTN_LANGUAGE)
async def cmd_language(message: Message, db: Database) -> None:
    """Allow switching language anytime via /language or persistent button."""
    if message.from_user is None:
        return
    lang = await db.get_user_language(message.from_user.id)
    await message.answer(
        text=get_text(lang, "choose_language"),
        reply_markup=build_language_inline_keyboard(),
    )


@router.message(Command("help"))
@router.message(F.text == BTN_HELP)
async def cmd_help(message: Message, db: Database) -> None:
    """Show localized usage instructions."""
    if message.from_user is None:
        return
    lang = await db.get_user_language(message.from_user.id)
    await message.answer(
        text=get_text(lang, "help"),
        reply_markup=build_main_menu_keyboard(),
    )


@router.callback_query(F.data.startswith("lang:"))
async def cb_set_language(callback: CallbackQuery, db: Database) -> None:
    """Persist selected language in SQLite and confirm to user."""
    if callback.data is None or callback.message is None:
        return

    chosen = callback.data.split(":", maxsplit=1)[1]
    if chosen not in ("en", "fa"):
        await callback.answer("Invalid language.", show_alert=True)
        return

    lang_code: Literal["en", "fa"] = "fa" if chosen == "fa" else "en"
    await db.set_user_language(callback.from_user.id, lang_code)

    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            text=get_text(lang_code, "language_updated")
        )