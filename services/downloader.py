"""Asynchronous yt-dlp wrapper for X (Twitter) GIF and video extraction."""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse, urlunparse

import yt_dlp
from yt_dlp.utils import DownloadError

from config import TELEGRAM_MAX_FILE_SIZE_BYTES

logger = logging.getLogger(__name__)

X_URL_REGEX = re.compile(
    r"https?://(?:www\.|mobile\.)?"
    r"(?:x\.com|twitter\.com|fxtwitter\.com|vxtwitter\.com|t\.co)/[^\s<>\"']+",
    re.IGNORECASE,
)


class DownloaderError(Exception):
    """Domain-specific error mapped to a localization key."""

    def __init__(self, error_key: str, detail: str = "") -> None:
        self.error_key = error_key
        self.detail = detail
        super().__init__(detail or error_key)


@dataclass(frozen=True)
class VideoQuality:
    """Represents a selectable video resolution."""

    height: int
    label: str
    format_selector: str
    filesize_bytes: int | None
    exceeds_limit: bool


@dataclass(frozen=True)
class MediaItem:
    """Inspected media item from an X/Twitter post."""

    media_type: Literal["gif", "video"]
    title: str
    source_url: str
    duration: float | None
    qualities: list[VideoQuality] = field(default_factory=list)
    playlist_index: int | None = None


@dataclass
class PendingDownload:
    """Cached metadata for an inline quality-selection menu."""

    user_id: int
    media: MediaItem
    created_at: float = field(default_factory=time.monotonic)


class PendingDownloadStore:
    """In-memory TTL store mapping short tokens to inspected video metadata."""

    def __init__(self, ttl_seconds: int = 1800) -> None:
        self._ttl = ttl_seconds
        self._items: dict[str, PendingDownload] = {}

    def put(self, user_id: int, media: MediaItem) -> str:
        self._purge_expired()
        token = uuid.uuid4().hex[:10]
        self._items[token] = PendingDownload(user_id=user_id, media=media)
        return token

    def get(self, token: str) -> PendingDownload | None:
        self._purge_expired()
        return self._items.get(token)

    def remove(self, token: str) -> None:
        self._items.pop(token, None)

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired = [k for k, v in self._items.items() if now - v.created_at > self._ttl]
        for key in expired:
            self._items.pop(key, None)


def extract_x_url(text: str) -> str | None:
    """Return the first valid X/Twitter URL found in text, or None."""
    if not text:
        return None
    match = X_URL_REGEX.search(text)
    if not match:
        return None
    return match.group(0).rstrip(".,);!?")


def normalize_x_url(url: str) -> str:
    """Normalize fxtwitter/vxtwitter/mobile links to x.com for yt-dlp."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host in {
        "fxtwitter.com",
        "www.fxtwitter.com",
        "vxtwitter.com",
        "www.vxtwitter.com",
        "mobile.twitter.com",
        "mobile.x.com",
        "twitter.com",
        "www.twitter.com",
    }:
        parsed = parsed._replace(netloc="x.com")
        return urlunparse(parsed)
    return url


def _classify_yt_dlp_error(exc: Exception) -> DownloaderError:
    """Map raw yt-dlp error strings to localized error keys."""
    msg = str(exc).lower()
    if any(
        kw in msg
        for kw in (
            "no video could be found",
            "there's no video",
            "no media",
            "unsupported url",
            "requested format is not available",
        )
    ):
        return DownloaderError("err_no_media", str(exc))
    if any(
        kw in msg
        for kw in (
            "nsfw",
            "age-restricted",
            "age restricted",
            "login",
            "sign in",
            "authenticate",
            "cookies",
        )
    ):
        return DownloaderError("err_age_restricted", str(exc))
    if any(
        kw in msg
        for kw in (
            "private",
            "protected",
            "deleted",
            "not found",
            "404",
            "suspended",
            "unavailable",
            "403",
        )
    ):
        return DownloaderError("err_private_or_deleted", str(exc))
    if any(kw in msg for kw in ("429", "rate limit", "too many requests")):
        return DownloaderError("err_rate_limit", str(exc))
    return DownloaderError("err_generic", str(exc))


def _estimate_filesize(fmt: dict[str, Any], duration: float | None) -> int | None:
    """Return exact or approximate byte size for a format."""
    size = fmt.get("filesize") or fmt.get("filesize_approx")
    if isinstance(size, (int, float)) and size > 0:
        return int(size)
    tbr = fmt.get("tbr") or fmt.get("vbr")
    if isinstance(tbr, (int, float)) and tbr > 0 and duration and duration > 0:
        return int((tbr * 1000 / 8) * duration)
    return None


def _is_twitter_gif(info: dict[str, Any], formats: list[dict[str, Any]]) -> bool:
    """Detect whether an X/Twitter media entry is an animated GIF (muted looping MP4)."""
    for fmt in formats:
        url = (fmt.get("url") or "").lower()
        if "/tweet_video/" in url:
            return True

    video_formats = [
        f for f in formats if f.get("vcodec") not in (None, "none")
    ]
    if not video_formats:
        return False

    has_any_audio = any(
        f.get("acodec") not in (None, "none") for f in formats
    )
    # Single silent MP4 stream is typically a Twitter GIF
    if not has_any_audio and len(video_formats) == 1:
        return True
    return False


def _build_video_qualities(
    formats: list[dict[str, Any]],
    duration: float | None,
) -> list[VideoQuality]:
    """Extract deduplicated, sorted video resolutions with size & 50MB limit checks."""
    by_height: dict[int, dict[str, Any]] = {}

    for fmt in formats:
        vcodec = fmt.get("vcodec")
        height = fmt.get("height")
        if vcodec in (None, "none") or not isinstance(height, int) or height <= 0:
            continue

        # Prefer MP4 / formats that already include audio, then higher bitrate
        ext_score = 1 if fmt.get("ext") == "mp4" else 0
        audio_score = 1 if fmt.get("acodec") not in (None, "none") else 0
        tbr_score = float(fmt.get("tbr") or 0.0)
        score = (ext_score, audio_score, tbr_score)

        existing = by_height.get(height)
        if existing is None or score > existing["_score"]:
            fmt_copy = dict(fmt)
            fmt_copy["_score"] = score
            by_height[height] = fmt_copy

    qualities: list[VideoQuality] = []
    for height in sorted(by_height.keys(), reverse=True):
        fmt = by_height[height]
        fmt_id = str(fmt.get("format_id"))
        has_audio = fmt.get("acodec") not in (None, "none")
        if has_audio:
            selector = fmt_id
        else:
            selector = (
                f"{fmt_id}+bestaudio[ext=m4a]/{fmt_id}+bestaudio/"
                f"best[height<={height}][ext=mp4]/best[height<={height}]"
            )

        size_bytes = _estimate_filesize(fmt, duration)
        exceeds = (
            size_bytes is not None and size_bytes > TELEGRAM_MAX_FILE_SIZE_BYTES
        )
        qualities.append(
            VideoQuality(
                height=height,
                label=f"{height}p",
                format_selector=selector,
                filesize_bytes=size_bytes,
                exceeds_limit=exceeds,
            )
        )
    return qualities


def _parse_entry(
    entry: dict[str, Any],
    source_url: str,
    playlist_index: int | None = None,
) -> MediaItem | None:
    """Convert a single yt-dlp info dict into a MediaItem."""
    formats: list[dict[str, Any]] = entry.get("formats") or []
    if not formats:
        return None

    raw_title = (entry.get("title") or entry.get("description") or "X Video").strip()
    title = (raw_title[:80] + "…") if len(raw_title) > 80 else raw_title
    duration = entry.get("duration")

    if _is_twitter_gif(entry, formats):
        return MediaItem(
            media_type="gif",
            title=title,
            source_url=source_url,
            duration=duration,
            qualities=[],
            playlist_index=playlist_index,
        )

    qualities = _build_video_qualities(formats, duration)
    if not qualities:
        return None

    return MediaItem(
        media_type="video",
        title=title,
        source_url=source_url,
        duration=duration,
        qualities=qualities,
        playlist_index=playlist_index,
    )


def _inspect_url_sync(url: str) -> list[MediaItem]:
    """Blocking yt-dlp metadata inspection (run inside asyncio.to_thread)."""
    normalized = normalize_x_url(url)
    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "socket_timeout": 20,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(normalized, download=False)
    except DownloadError as exc:
        raise _classify_yt_dlp_error(exc) from exc
    except Exception as exc:
        logger.exception("Unexpected error during yt-dlp inspection")
        raise DownloaderError("err_generic", str(exc)) from exc

    if not info:
        raise DownloaderError("err_no_media")

    items: list[MediaItem] = []
    if info.get("_type") == "playlist" or "entries" in info:
        entries = [e for e in (info.get("entries") or []) if e]
        for idx, entry in enumerate(entries, start=1):
            parsed = _parse_entry(entry, normalized, playlist_index=idx)
            if parsed:
                items.append(parsed)
    else:
        parsed = _parse_entry(info, normalized, playlist_index=None)
        if parsed:
            items.append(parsed)

    if not items:
        raise DownloaderError("err_no_media")
    return items


async def inspect_url(url: str) -> list[MediaItem]:
    """Asynchronously inspect an X/Twitter URL without blocking the event loop."""
    return await asyncio.to_thread(_inspect_url_sync, url)


def _download_media_sync(
    url: str,
    req_dir: Path,
    format_selector: str | None,
    playlist_index: int | None,
) -> Path:
    """Blocking yt-dlp download into an isolated temp directory."""
    output_template = str(req_dir / "%(id)s.%(ext)s")
    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "socket_timeout": 30,
        "retries": 2,
        "noplaylist": playlist_index is None,
    }
    if format_selector:
        ydl_opts["format"] = format_selector
    else:
        ydl_opts["format"] = "best[ext=mp4]/best"

    if playlist_index is not None:
        ydl_opts["playlist_items"] = str(playlist_index)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise DownloaderError("err_no_media")

            if "entries" in info:
                entries = [e for e in (info.get("entries") or []) if e]
                if not entries:
                    raise DownloaderError("err_no_media")
                target_info = entries[0]
            else:
                target_info = info

            prepared = Path(ydl.prepare_filename(target_info))
            if prepared.exists():
                return prepared

            # Fallback: if ffmpeg remuxed to .mp4, find the resulting file in req_dir
            mp4_candidate = prepared.with_suffix(".mp4")
            if mp4_candidate.exists():
                return mp4_candidate

            files = [p for p in req_dir.iterdir() if p.is_file()]
            if files:
                return files[0]

            raise DownloaderError("err_generic", "Downloaded file not found on disk.")
    except DownloaderError:
        raise
    except DownloadError as exc:
        raise _classify_yt_dlp_error(exc) from exc
    except Exception as exc:
        logger.exception("Unexpected error during yt-dlp download")
        raise DownloaderError("err_generic", str(exc)) from exc


async def download_media(
    url: str,
    temp_root: Path,
    format_selector: str | None = None,
    playlist_index: int | None = None,
) -> tuple[Path, Path]:
    """Download media into a unique temp directory.

    Returns (file_path, req_dir). Caller MUST remove req_dir in a try...finally block.
    """
    temp_root.mkdir(parents=True, exist_ok=True)
    req_dir = Path(tempfile.mkdtemp(prefix="xbot_", dir=temp_root))
    try:
        file_path = await asyncio.to_thread(
            _download_media_sync,
            url,
            req_dir,
            format_selector,
            playlist_index,
        )
        return file_path, req_dir
    except Exception:
        shutil.rmtree(req_dir, ignore_errors=True)
        raise
