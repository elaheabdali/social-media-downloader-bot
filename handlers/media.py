"""Handlers for X/Twitter & Instagram link detection, photo/GIF auto-download, and video quality selection."""

from __future__ import annotations

import html
import logging
import shutil
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import TELEGRAM_MAX_FILE_SIZE_BYTES, Settings
from database import Database
from locales import get_text
from services import (
    DownloaderError,
    MediaItem,
    PendingDownloadStore,
    download_media,
    extract_x_url,
    inspect_url,
)
from services.downloader import convert_video_to_gif_mp4, download_direct_file

logger = logging.getLogger(__name__)
router = Router(name="media")


def _format_size_mb(size_bytes: int | None) -> str:
    if not size_bytes or size_bytes <= 0:
        return ""
    mb = size_bytes / (1024 * 1024)
    return f" (~{mb:.1f} MB)"


def _build_quality_keyboard(
    token: str,
    media: MediaItem,
    lang: str,
) -> tuple[InlineKeyboardMarkup, bool]:
    """Build a 2-column inline keyboard of video resolutions plus Convert to GIF button."""
    buttons: list[InlineKeyboardButton] = []
    has_over_limit = False

    for q in media.qualities:
        size_part = _format_size_mb(q.filesize_bytes)
        if q.exceeds_limit:
            has_over_limit = True
            btn_text = get_text(
                lang,
                "quality_btn_over_limit",
                label=q.label,
                size_part=size_part,
            )
        else:
            btn_text = get_text(
                lang,
                "quality_btn",
                label=q.label,
                size_part=size_part,
            )

        buttons.append(
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"dl:{token}:{q.height}",
            )
        )

    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]

    if getattr(media, "platform", "x") == "x":
        rows.append(
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_convert_gif"),
                    callback_data=f"gif:{token}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows), has_over_limit


async def _safe_edit(message: Message, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    """Edit a status message safely without crashing if unchanged or deleted."""
    try:
        await message.edit_text(text=text, reply_markup=reply_markup)
    except TelegramBadRequest:
        pass


async def _process_photo(
    origin_message: Message,
    status_msg: Message,
    media: MediaItem,
    lang: str,
    settings: Settings,
    bot: Bot,
) -> None:
    """Download an Instagram photo or profile picture and send it to Telegram."""
    if not media.direct_url:
        await _safe_edit(status_msg, get_text(lang, "err_no_media"))
        return

    await _safe_edit(status_msg, get_text(lang, "downloading_photo"))

    req_dir: Path | None = None
    try:
        file_path, req_dir = await download_direct_file(
            direct_url=media.direct_url,
            temp_root=settings.temp_dir,
            default_ext=".jpg",
        )

        size_bytes = file_path.stat().st_size
        if size_bytes > TELEGRAM_MAX_FILE_SIZE_BYTES:
            await _safe_edit(
                status_msg,
                get_text(lang, "file_too_large", size_mb=size_bytes / (1024 * 1024)),
            )
            return

        await _safe_edit(status_msg, get_text(lang, "uploading_photo"))
        me = await bot.get_me()
        caption = get_text(lang, "done_caption", bot_username=me.username or "bot")

        await origin_message.answer_photo(
            photo=FSInputFile(file_path),
            caption=caption,
        )
        await status_msg.delete()
    except DownloaderError as exc:
        await _safe_edit(status_msg, get_text(lang, exc.error_key))
    except Exception:
        logger.exception("Failed to send photo")
        await _safe_edit(status_msg, get_text(lang, "err_upload_failed"))
    finally:
        if req_dir is not None:
            shutil.rmtree(req_dir, ignore_errors=True)


async def _process_gif(
    origin_message: Message,
    status_msg: Message,
    media: MediaItem,
    lang: str,
    settings: Settings,
    bot: Bot,
) -> None:
    """Download an X/Twitter GIF and send it as a native Telegram animation."""
    await _safe_edit(status_msg, get_text(lang, "downloading_gif"))

    req_dir: Path | None = None
    try:
        file_path, req_dir = await download_media(
            url=media.source_url,
            temp_root=settings.temp_dir,
            format_selector="best[ext=mp4]/best",
            playlist_index=media.playlist_index,
            cookies_file=settings.instagram_cookies_file,
        )

        size_bytes = file_path.stat().st_size
        if size_bytes > TELEGRAM_MAX_FILE_SIZE_BYTES:
            await _safe_edit(
                status_msg,
                get_text(lang, "file_too_large", size_mb=size_bytes / (1024 * 1024)),
            )
            return

        await _safe_edit(status_msg, get_text(lang, "uploading_gif"))
        me = await bot.get_me()
        caption = get_text(lang, "done_caption", bot_username=me.username or "bot")

        await origin_message.answer_animation(
            animation=FSInputFile(file_path),
            caption=caption,
        )
        await status_msg.delete()
    except DownloaderError as exc:
        await _safe_edit(status_msg, get_text(lang, exc.error_key))
    except Exception:
        logger.exception("Failed to send GIF")
        await _safe_edit(status_msg, get_text(lang, "err_upload_failed"))
    finally:
        if req_dir is not None:
            shutil.rmtree(req_dir, ignore_errors=True)


@router.message(F.text)
async def handle_text_message(
    message: Message,
    db: Database,
    settings: Settings,
    pending_store: PendingDownloadStore,
    bot: Bot,
) -> None:
    """Detect X/Twitter & Instagram URLs, inspect metadata, and handle photos, GIFs, or videos."""
    if message.from_user is None or not message.text:
        return

    lang = await db.get_user_language(message.from_user.id)
    url = extract_x_url(message.text)
    if not url:
        await message.reply(get_text(lang, "invalid_link"))
        return

    status_msg = await message.reply(get_text(lang, "inspecting"))

    try:
        media_items = await inspect_url(url, cookies_file=settings.instagram_cookies_file)
    except DownloaderError as exc:
        await _safe_edit(status_msg, get_text(lang, exc.error_key))
        return
    except Exception:
        logger.exception("Unexpected inspection failure for %s", url)
        await _safe_edit(status_msg, get_text(lang, "err_generic"))
        return

    if len(media_items) > 1:
        await _safe_edit(
            status_msg,
            get_text(lang, "multi_media_notice", count=len(media_items)),
        )

    for media in media_items:
        item_status = (
            status_msg
            if len(media_items) == 1
            else await message.answer(get_text(lang, "inspecting"))
        )

        if media.media_type == "photo":
            await _process_photo(message, item_status, media, lang, settings, bot)
        elif media.media_type == "gif":
            await _process_gif(message, item_status, media, lang, settings, bot)
        else:
            token = pending_store.put(message.from_user.id, media)
            keyboard, has_over_limit = _build_quality_keyboard(token, media, lang)
            prompt = get_text(
                lang,
                "select_quality",
                title=html.escape(media.title),
            )
            if has_over_limit:
                prompt += get_text(lang, "select_quality_limit_note")
            await _safe_edit(item_status, prompt, reply_markup=keyboard)


@router.callback_query(F.data.startswith("gif:"))
async def cb_convert_video_to_gif(
    callback: CallbackQuery,
    db: Database,
    settings: Settings,
    pending_store: PendingDownloadStore,
    bot: Bot,
) -> None:
    """Download the selected X video and convert it into a Telegram GIF animation."""
    if callback.data is None or callback.message is None:
        return

    lang = await db.get_user_language(callback.from_user.id)
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer(get_text(lang, "err_generic"), show_alert=True)
        return

    _, token = parts
    pending = pending_store.get(token)
    if pending is None or pending.user_id != callback.from_user.id:
        await callback.answer(get_text(lang, "session_expired"), show_alert=True)
        return

    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    status_msg = callback.message
    await _safe_edit(status_msg, get_text(lang, "converting_to_gif"))

    req_dir: Path | None = None
    try:
        preferred_q = next(
            (q for q in pending.media.qualities if q.height <= 720),
            pending.media.qualities[-1] if pending.media.qualities else None,
        )
        selector = preferred_q.format_selector if preferred_q else "best[ext=mp4]/best"

        raw_video_path, req_dir = await download_media(
            url=pending.media.source_url,
            temp_root=settings.temp_dir,
            format_selector=selector,
            playlist_index=pending.media.playlist_index,
            cookies_file=settings.instagram_cookies_file,
        )

        gif_path = await convert_video_to_gif_mp4(raw_video_path, req_dir)
        size_bytes = gif_path.stat().st_size
        if size_bytes > TELEGRAM_MAX_FILE_SIZE_BYTES:
            await _safe_edit(
                status_msg,
                get_text(lang, "file_too_large", size_mb=size_bytes / (1024 * 1024)),
            )
            return

        await _safe_edit(status_msg, get_text(lang, "uploading_gif"))
        me = await bot.get_me()
        caption = get_text(lang, "done_caption", bot_username=me.username or "bot")

        await status_msg.answer_animation(
            animation=FSInputFile(gif_path),
            caption=caption,
        )
        pending_store.remove(token)
        await status_msg.delete()
    except DownloaderError as exc:
        await _safe_edit(status_msg, get_text(lang, exc.error_key))
    except Exception:
        logger.exception("Failed to convert/send video as GIF")
        await _safe_edit(status_msg, get_text(lang, "err_gif_convert_failed"))
    finally:
        if req_dir is not None:
            shutil.rmtree(req_dir, ignore_errors=True)


@router.callback_query(F.data.startswith("dl:"))
async def cb_download_video(
    callback: CallbackQuery,
    db: Database,
    settings: Settings,
    pending_store: PendingDownloadStore,
    bot: Bot,
) -> None:
    """Handle user video quality selection and upload the requested stream."""
    if callback.data is None or callback.message is None:
        return

    lang = await db.get_user_language(callback.from_user.id)
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer(get_text(lang, "err_generic"), show_alert=True)
        return

    _, token, height_str = parts
    pending = pending_store.get(token)
    if pending is None or pending.user_id != callback.from_user.id:
        await callback.answer(get_text(lang, "session_expired"), show_alert=True)
        return

    try:
        target_height = int(height_str)
    except ValueError:
        await callback.answer(get_text(lang, "err_generic"), show_alert=True)
        return

    quality = next(
        (q for q in pending.media.qualities if q.height == target_height),
        None,
    )
    if quality is None:
        await callback.answer(get_text(lang, "err_generic"), show_alert=True)
        return

    if quality.exceeds_limit and quality.filesize_bytes is not None:
        await callback.answer(
            get_text(
                lang,
                "file_too_large",
                size_mb=quality.filesize_bytes / (1024 * 1024),
            ),
            show_alert=True,
        )
        return

    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    status_msg = callback.message
    await _safe_edit(
        status_msg,
        get_text(lang, "downloading_video", quality=quality.label),
    )

    req_dir: Path | None = None
    try:
        file_path, req_dir = await download_media(
            url=pending.media.source_url,
            temp_root=settings.temp_dir,
            format_selector=quality.format_selector,
            playlist_index=pending.media.playlist_index,
            cookies_file=settings.instagram_cookies_file,
        )

        size_bytes = file_path.stat().st_size
        if size_bytes > TELEGRAM_MAX_FILE_SIZE_BYTES:
            await _safe_edit(
                status_msg,
                get_text(lang, "file_too_large", size_mb=size_bytes / (1024 * 1024)),
            )
            return

        await _safe_edit(status_msg, get_text(lang, "uploading_video"))
        me = await bot.get_me()
        caption = get_text(lang, "done_caption", bot_username=me.username or "bot")

        await status_msg.answer_video(
            video=FSInputFile(file_path),
            caption=caption,
            supports_streaming=True,
        )
        pending_store.remove(token)
        await status_msg.delete()
    except DownloaderError as exc:
        await _safe_edit(status_msg, get_text(lang, exc.error_key))
    except Exception:
        logger.exception("Failed to download/upload video")
        await _safe_edit(status_msg, get_text(lang, "err_upload_failed"))
    finally:
        if req_dir is not None:
            shutil.rmtree(req_dir, ignore_errors=True)