"""Handlers for YouTube channel search, latest channel videos, and one-tap video inspection."""

from __future__ import annotations

import html
import logging
import time

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import Settings
from database import Database
from handlers.media import _build_quality_keyboard
from locales import BTN_YOUTUBE, get_text
from services import (
    DownloaderError,
    PendingDownloadStore,
    YouTubeChannelResult,
    YouTubeVideoEntry,
    fetch_channel_latest_videos,
    inspect_url,
    is_youtube_channel_url,
    resolve_channel_id_from_url,
    search_youtube_channels,
)

logger = logging.getLogger(__name__)
router = Router(name="youtube")

# Tracks users who tapped "YouTube Channel" and are typing a channel name (user_id -> monotonic timestamp)
_AWAITING_CHANNEL_SEARCH: dict[int, float] = {}
_SEARCH_PROMPT_TTL = 300.0  # 5 minutes


def set_awaiting_channel_search(user_id: int) -> None:
    _AWAITING_CHANNEL_SEARCH[user_id] = time.monotonic()


def pop_awaiting_channel_search(user_id: int) -> bool:
    ts = _AWAITING_CHANNEL_SEARCH.pop(user_id, None)
    if ts is None:
        return False
    return (time.monotonic() - ts) <= _SEARCH_PROMPT_TTL


def _build_channels_keyboard(channels: list[YouTubeChannelResult]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for ch in channels:
        label = f"📺 {ch.title}"
        if ch.subscribers:
            label += f" ({ch.subscribers})"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label[:60],
                    callback_data=f"ytch:id:{ch.channel_id}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_latest_videos_keyboard(videos: list[YouTubeVideoEntry]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for idx, vid in enumerate(videos, start=1):
        date_tag = f"[{vid.published}] " if vid.published else ""
        btn_text = f"{idx}. {date_tag}{vid.title}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=btn_text[:62],
                    callback_data=f"ytvid:{vid.video_id}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_channel_latest_videos(
    target_message: Message,
    channel_id: str,
    lang: str,
    edit_existing: bool = False,
) -> None:
    """Fetch a channel's latest videos and display them as clickable buttons."""
    if edit_existing:
        status_msg = target_message
        try:
            await status_msg.edit_text(text=get_text(lang, "yt_fetching_videos"))
        except TelegramBadRequest:
            pass
    else:
        status_msg = await target_message.reply(get_text(lang, "yt_fetching_videos"))

    try:
        channel_title, videos = await fetch_channel_latest_videos(channel_id, limit=8)
    except Exception:
        logger.exception("Failed to fetch latest videos for channel %s", channel_id)
        try:
            await status_msg.edit_text(text=get_text(lang, "yt_no_videos"))
        except TelegramBadRequest:
            pass
        return

    if not videos:
        try:
            await status_msg.edit_text(text=get_text(lang, "yt_no_videos"))
        except TelegramBadRequest:
            pass
        return

    text = get_text(lang, "yt_latest_videos", channel=html.escape(channel_title))
    keyboard = _build_latest_videos_keyboard(videos)
    try:
        await status_msg.edit_text(text=text, reply_markup=keyboard)
    except TelegramBadRequest:
        pass


@router.message(Command("youtube"))
@router.message(F.text == BTN_YOUTUBE)
async def cmd_youtube_channel(message: Message, db: Database) -> None:
    """Prompt the user to type a YouTube channel name or @handle."""
    if message.from_user is None:
        return
    lang = await db.get_user_language(message.from_user.id)
    set_awaiting_channel_search(message.from_user.id)
    await message.answer(text=get_text(lang, "yt_channel_prompt"))


@router.message(F.text, lambda msg: msg.from_user is not None and msg.from_user.id in _AWAITING_CHANNEL_SEARCH)
async def handle_channel_search_query(message: Message, db: Database) -> None:
    """Process channel search query when user is in YouTube channel search mode."""
    if message.from_user is None or not message.text:
        return

    if not pop_awaiting_channel_search(message.from_user.id):
        return

    query = message.text.strip()
    lang = await db.get_user_language(message.from_user.id)

    # If user pasted a direct YouTube channel URL, resolve and show its videos directly
    if query.startswith(("http://", "https://")) and is_youtube_channel_url(query):
        status_msg = await message.reply(get_text(lang, "yt_fetching_videos"))
        channel_id = await resolve_channel_id_from_url(query)
        if not channel_id:
            try:
                await status_msg.edit_text(text=get_text(lang, "yt_channel_not_found"))
            except TelegramBadRequest:
                pass
            return
        await show_channel_latest_videos(status_msg, channel_id, lang, edit_existing=True)
        return

    status_msg = await message.reply(get_text(lang, "yt_searching_channel"))
    channels = await search_youtube_channels(query)
    if not channels:
        try:
            await status_msg.edit_text(text=get_text(lang, "yt_channel_not_found"))
        except TelegramBadRequest:
            pass
        return

    # If exact @handle match or single result, open its latest videos immediately
    if len(channels) == 1:
        await show_channel_latest_videos(
            status_msg, channels[0].channel_id, lang, edit_existing=True
        )
        return

    try:
        await status_msg.edit_text(
            text=get_text(lang, "yt_select_channel"),
            reply_markup=_build_channels_keyboard(channels),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("ytch:id:"))
async def cb_select_youtube_channel(callback: CallbackQuery, db: Database) -> None:
    """Show latest videos when user picks a channel from search results."""
    if callback.data is None or callback.message is None:
        return

    lang = await db.get_user_language(callback.from_user.id)
    channel_id = callback.data.split(":", 2)[2]
    await callback.answer()

    if isinstance(callback.message, Message):
        await show_channel_latest_videos(
            callback.message, channel_id, lang, edit_existing=True
        )


@router.callback_query(F.data.startswith("ytvid:"))
async def cb_select_channel_video(
    callback: CallbackQuery,
    db: Database,
    settings: Settings,
    pending_store: PendingDownloadStore,
    bot: Bot,
) -> None:
    """Inspect a selected video from a channel's latest uploads and show quality options."""
    if callback.data is None or callback.message is None:
        return

    lang = await db.get_user_language(callback.from_user.id)
    video_id = callback.data.split(":", 1)[1]
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    status_msg = await callback.message.answer(text=get_text(lang, "inspecting"))

    try:
        media_items = await inspect_url(
            video_url,
            cookies_file=settings.instagram_cookies_file,
            yt_cookies_file=settings.youtube_cookies_file,
        )
    except DownloaderError as exc:
        try:
            await status_msg.edit_text(text=get_text(lang, exc.error_key))
        except TelegramBadRequest:
            pass
        return
    except Exception:
        logger.exception("Failed to inspect selected YouTube video %s", video_id)
        try:
            await status_msg.edit_text(text=get_text(lang, "err_generic"))
        except TelegramBadRequest:
            pass
        return

    media = media_items[0]
    token = pending_store.put(callback.from_user.id, media)
    keyboard, has_over_limit = _build_quality_keyboard(token, media, lang)
    prompt = get_text(
        lang,
        "select_quality",
        title=html.escape(media.title),
    )
    if has_over_limit:
        prompt += get_text(lang, "select_quality_limit_note")

    try:
        await status_msg.edit_text(text=prompt, reply_markup=keyboard)
    except TelegramBadRequest:
        pass