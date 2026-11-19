"""Asynchronous yt-dlp + fallback wrapper for X (Twitter) and Instagram media extraction."""

from __future__ import annotations

import asyncio
import html as html_lib
import logging
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse, urlunparse

import aiohttp
import imageio_ffmpeg
import yt_dlp
from yt_dlp.utils import DownloadError

from config import TELEGRAM_MAX_FILE_SIZE_BYTES

logger = logging.getLogger(__name__)

MEDIA_URL_REGEX = re.compile(
    r"https?://(?:www\.|mobile\.|m\.|dd)?"
    r"(?:x\.com|twitter\.com|fxtwitter\.com|vxtwitter\.com|t\.co|instagram\.com|instagr\.am)"
    r"/[^\s<>\"']+",
    re.IGNORECASE,
)

STATUS_PATH_REGEX = re.compile(
    r"^/([^/]+/status/\d+)(?:/(?:photo|video)/\d+)?/?$",
    re.IGNORECASE,
)

IG_POST_REGEX = re.compile(
    r"^/(?:[^/]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)/?",
    re.IGNORECASE,
)

IG_RESERVED_PATHS = {
    "p",
    "reel",
    "reels",
    "tv",
    "stories",
    "explore",
    "accounts",
    "direct",
    "about",
    "legal",
    "developer",
    "api",
    "static",
}

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


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
    direct_url: str | None = None


@dataclass(frozen=True)
class MediaItem:
    """Inspected media item from an X/Twitter or Instagram post/profile."""

    media_type: Literal["gif", "video", "photo"]
    title: str
    source_url: str
    duration: float | None = None
    qualities: list[VideoQuality] = field(default_factory=list)
    playlist_index: int | None = None
    direct_url: str | None = None
    platform: Literal["x", "instagram"] = "x"


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
    """Return the first valid X/Twitter or Instagram URL found in text, or None."""
    if not text:
        return None
    match = MEDIA_URL_REGEX.search(text)
    if not match:
        return None
    return match.group(0).rstrip(".,);!?")


def _is_instagram_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(d in host for d in ("instagram.com", "instagr.am"))


def normalize_media_url(url: str) -> str:
    """Normalize X or Instagram domain and strip unnecessary suffixes/tracking params."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if _is_instagram_url(url):
        parsed = parsed._replace(netloc="www.instagram.com", query="", fragment="")
        return urlunparse(parsed)

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

    path_match = STATUS_PATH_REGEX.match(parsed.path)
    if path_match:
        clean_path = f"/{path_match.group(1)}"
        parsed = parsed._replace(path=clean_path, query="", fragment="")

    return urlunparse(parsed)


def _load_ig_cookies(cookies_file: Path | None) -> dict[str, str]:
    """Parse Netscape-formatted cookies.txt into a dict for aiohttp sessions."""
    cookies: dict[str, str] = {}
    if not cookies_file or not cookies_file.exists():
        return cookies

    try:
        for line in cookies_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7 and "instagram.com" in parts[0].lower():
                cookies[parts[5]] = parts[6]
    except Exception:
        logger.warning("Failed to parse Instagram cookies file")
    return cookies


def _classify_yt_dlp_error(exc: Exception) -> DownloaderError:
    """Map raw yt-dlp error strings to localized error keys."""
    msg = str(exc).lower()
    if any(
        kw in msg
        for kw in (
            "no video could be found",
            "no video formats found",
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


def _is_twitter_gif(formats: list[dict[str, Any]]) -> bool:
    """Detect whether an X/Twitter media entry is an animated GIF (muted looping MP4)."""
    for fmt in formats:
        url = (fmt.get("url") or "").lower()
        if "/tweet_video/" in url:
            return True

    video_formats = [f for f in formats if f.get("vcodec") not in (None, "none")]
    if not video_formats:
        return False

    has_any_audio = any(f.get("acodec") not in (None, "none") for f in formats)
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
        exceeds = size_bytes is not None and size_bytes > TELEGRAM_MAX_FILE_SIZE_BYTES
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
    is_instagram: bool = False,
) -> MediaItem | None:
    """Convert a single yt-dlp info dict into a MediaItem."""
    formats: list[dict[str, Any]] = entry.get("formats") or []
    if not formats:
        return None

    platform: Literal["x", "instagram"] = "instagram" if is_instagram else "x"
    default_title = "Instagram Video" if is_instagram else "X Video"
    raw_title = (entry.get("title") or entry.get("description") or default_title).strip()
    title = (raw_title[:80] + "…") if len(raw_title) > 80 else raw_title
    duration = entry.get("duration")

    if not is_instagram and _is_twitter_gif(formats):
        return MediaItem(
            media_type="gif",
            title=title,
            source_url=source_url,
            duration=duration,
            qualities=[],
            playlist_index=playlist_index,
            platform=platform,
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
        platform=platform,
    )


# ---------------------------------------------------------------------------
# X (Twitter) Fallback via FxTwitter
# ---------------------------------------------------------------------------


async def _inspect_via_fxtwitter(url: str) -> list[MediaItem]:
    """Fallback inspector using api.fxtwitter.com to bypass age-restriction/NSFW blocks."""
    parsed = urlparse(url)
    api_url = f"https://api.fxtwitter.com{parsed.path}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TelegramBot/1.0)"}

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                raise DownloaderError("err_no_media", f"FxTwitter status {resp.status}")
            data = await resp.json()

    tweet = data.get("tweet") or {}
    media_block = tweet.get("media") or {}
    videos = media_block.get("videos") or []
    if not videos:
        all_media = media_block.get("all") or []
        videos = [m for m in all_media if m.get("type") in ("video", "gif")]

    if not videos:
        raise DownloaderError("err_no_media", "No video/gif found in FxTwitter response")

    raw_title = (tweet.get("text") or "X Media").strip()
    title = (raw_title[:80] + "…") if len(raw_title) > 80 else raw_title
    items: list[MediaItem] = []

    for idx, vid in enumerate(videos, start=1):
        vid_type = vid.get("type", "video")
        vid_url = vid.get("url")
        duration = vid.get("duration")
        if not vid_url:
            continue

        if vid_type == "gif" or "/tweet_video/" in vid_url.lower():
            items.append(
                MediaItem(
                    media_type="gif",
                    title=title,
                    source_url=url,
                    duration=duration,
                    qualities=[],
                    playlist_index=idx if len(videos) > 1 else None,
                    direct_url=vid_url,
                    platform="x",
                )
            )
        else:
            variants = vid.get("variants") or []
            mp4_variants = [
                v for v in variants
                if v.get("content_type") == "video/mp4" and v.get("url")
            ]
            qualities: list[VideoQuality] = []
            seen_heights: set[int] = set()

            if mp4_variants:
                mp4_variants.sort(key=lambda x: x.get("bitrate", 0), reverse=True)
                for v in mp4_variants:
                    m = re.search(r"/(\d+)x(\d+)/", v["url"])
                    h = int(m.group(2)) if m else 720
                    if h in seen_heights:
                        continue
                    seen_heights.add(h)
                    qualities.append(
                        VideoQuality(
                            height=h,
                            label=f"{h}p",
                            format_selector=f"direct:{v['url']}",
                            filesize_bytes=None,
                            exceeds_limit=False,
                            direct_url=v["url"],
                        )
                    )

            if not qualities:
                qualities.append(
                    VideoQuality(
                        height=720,
                        label="HD",
                        format_selector=f"direct:{vid_url}",
                        filesize_bytes=None,
                        exceeds_limit=False,
                        direct_url=vid_url,
                    )
                )

            items.append(
                MediaItem(
                    media_type="video",
                    title=title,
                    source_url=url,
                    duration=duration,
                    qualities=qualities,
                    playlist_index=idx if len(videos) > 1 else None,
                    direct_url=vid_url,
                    platform="x",
                )
            )

    if not items:
        raise DownloaderError("err_no_media")
    return items


# ---------------------------------------------------------------------------
# Instagram Profile & Post/Carousel Extraction
# ---------------------------------------------------------------------------


def _extract_ig_profile_username(url: str) -> str | None:
    """Return username if URL is an Instagram profile link, else None."""
    path = urlparse(url).path.strip("/")
    if not path:
        return None
    segments = [s for s in path.split("/") if s]
    if len(segments) == 1 and segments[0].lower() not in IG_RESERVED_PATHS:
        return segments[0]
    return None


def _clean_escaped_url(raw: str) -> str:
    return (
        raw.replace("\\u0026", "&")
        .replace("\\/", "/")
        .replace("&amp;", "&")
        .strip()
    )


async def _inspect_ig_profile(
    username: str,
    source_url: str,
    cookies_file: Path | None = None,
) -> list[MediaItem]:
    """Fetch HD profile picture (avatar) for public or private Instagram accounts."""
    cookies = _load_ig_cookies(cookies_file)
    api_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "X-IG-App-ID": "936619743392459",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://www.instagram.com/{username}/",
        "Accept": "*/*",
    }
    if "csrftoken" in cookies:
        api_headers["X-CSRFToken"] = cookies["csrftoken"]

    async with aiohttp.ClientSession(cookies=cookies) as session:
        api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
        try:
            async with session.get(
                api_url, headers=api_headers, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 404:
                    raise DownloaderError("err_private_or_deleted")
                if resp.status == 200 and "application/json" in resp.headers.get("Content-Type", ""):
                    payload = await resp.json()
                    user = (payload.get("data") or {}).get("user") or {}
                    pic_url = user.get("profile_pic_url_hd") or user.get("profile_pic_url")
                    if pic_url:
                        return [
                            MediaItem(
                                media_type="photo",
                                title=f"@{username}",
                                source_url=source_url,
                                direct_url=pic_url,
                                platform="instagram",
                            )
                        ]
        except DownloaderError:
            raise
        except Exception:
            logger.debug("IG web_profile_info failed for %s, trying search endpoint", username)

        search_url = f"https://www.instagram.com/web/search/topsearch/?context=blended&query={username}"
        try:
            async with session.get(
                search_url, headers=api_headers, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200 and "application/json" in resp.headers.get("Content-Type", ""):
                    payload = await resp.json()
                    for entry in payload.get("users") or []:
                        user_obj = entry.get("user") or {}
                        if user_obj.get("username", "").lower() == username.lower():
                            pic_url = user_obj.get("profile_pic_url")
                            if pic_url:
                                return [
                                    MediaItem(
                                        media_type="photo",
                                        title=f"@{username}",
                                        source_url=source_url,
                                        direct_url=pic_url,
                                        platform="instagram",
                                    )
                                ]
        except Exception:
            logger.debug("IG topsearch failed for %s, trying HTML fallback", username)

        profile_page = f"https://www.instagram.com/{username}/"
        async with session.get(
            profile_page, headers=BROWSER_HEADERS, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status == 404:
                raise DownloaderError("err_private_or_deleted")
            html_text = await resp.text()

    hd_match = re.search(r'"profile_pic_url_hd"\s*:\s*"([^"]+)"', html_text)
    if hd_match:
        pic_url = _clean_escaped_url(hd_match.group(1))
        return [
            MediaItem(
                media_type="photo",
                title=f"@{username}",
                source_url=source_url,
                direct_url=pic_url,
                platform="instagram",
            )
        ]

    og_match = re.search(
        r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
        html_text,
        re.IGNORECASE,
    )
    if og_match:
        pic_url = html_lib.unescape(og_match.group(1))
        return [
            MediaItem(
                media_type="photo",
                title=f"@{username}",
                source_url=source_url,
                direct_url=pic_url,
                platform="instagram",
            )
        ]

    if not cookies and ("accounts/login" in html_text.lower() or "loginform" in html_text.lower()):
        raise DownloaderError("err_age_restricted")

    raise DownloaderError("err_private_or_deleted")


async def _inspect_ig_embed_fallback(url: str) -> list[MediaItem]:
    """Extract photos, videos, and carousels from Instagram's public embed endpoint."""
    match = IG_POST_REGEX.match(urlparse(url).path)
    if not match:
        raise DownloaderError("err_no_media")

    shortcode = match.group(1)
    embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"

    async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as session:
        async with session.get(embed_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 404:
                raise DownloaderError("err_private_or_deleted")
            if resp.status != 200:
                raise DownloaderError("err_age_restricted")
            page = await resp.text()

    if "login" in page.lower() and "embeddedmedia" not in page.lower() and "display_url" not in page.lower():
        raise DownloaderError("err_age_restricted")

    items: list[MediaItem] = []
    seen_urls: set[str] = set()

    for vid_match in re.finditer(r'"video_url"\s*:\s*"([^"]+)"', page):
        v_url = _clean_escaped_url(vid_match.group(1))
        if v_url and v_url not in seen_urls:
            seen_urls.add(v_url)
            items.append(
                MediaItem(
                    media_type="video",
                    title="Instagram Video",
                    source_url=url,
                    qualities=[
                        VideoQuality(
                            height=720,
                            label="HD",
                            format_selector=f"direct:{v_url}",
                            filesize_bytes=None,
                            exceeds_limit=False,
                            direct_url=v_url,
                        )
                    ],
                    direct_url=v_url,
                    platform="instagram",
                )
            )

    for img_match in re.finditer(r'"display_url"\s*:\s*"([^"]+)"', page):
        i_url = _clean_escaped_url(img_match.group(1))
        if i_url and i_url not in seen_urls:
            seen_urls.add(i_url)
            items.append(
                MediaItem(
                    media_type="photo",
                    title="Instagram Photo",
                    source_url=url,
                    direct_url=i_url,
                    platform="instagram",
                )
            )

    if not items:
        tag_match = re.search(
            r'<img[^>]+class=["\'][^"\']*EmbeddedMediaImage[^"\']*["\'][^>]+src=["\']([^"\']+)["\']',
            page,
            re.IGNORECASE,
        )
        if tag_match:
            i_url = _clean_escaped_url(tag_match.group(1))
            items.append(
                MediaItem(
                    media_type="photo",
                    title="Instagram Photo",
                    source_url=url,
                    direct_url=i_url,
                    platform="instagram",
                )
            )

    if not items:
        raise DownloaderError("err_no_media")
    return items


# ---------------------------------------------------------------------------
# Core Inspection, Download & GIF Conversion Entrypoints
# ---------------------------------------------------------------------------


def _inspect_url_sync(
    normalized: str,
    is_instagram: bool = False,
    cookies_file: Path | None = None,
) -> list[MediaItem]:
    """Blocking yt-dlp metadata inspection (run inside asyncio.to_thread)."""
    ydl_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "socket_timeout": 20,
        "ffmpeg_location": FFMPEG_PATH,
    }
    if is_instagram and cookies_file and cookies_file.exists():
        ydl_opts["cookiefile"] = str(cookies_file)

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
            parsed = _parse_entry(
                entry, normalized, playlist_index=idx, is_instagram=is_instagram
            )
            if parsed:
                items.append(parsed)
    else:
        parsed = _parse_entry(
            info, normalized, playlist_index=None, is_instagram=is_instagram
        )
        if parsed:
            items.append(parsed)

    if not items:
        raise DownloaderError("err_no_media")
    return items


async def inspect_url(
    url: str,
    cookies_file: Path | None = None,
) -> list[MediaItem]:
    """Inspect X/Twitter or Instagram URL with automatic fallbacks."""
    normalized = normalize_media_url(url)
    is_ig = _is_instagram_url(normalized)

    if is_ig:
        username = _extract_ig_profile_username(normalized)
        if username:
            return await _inspect_ig_profile(username, normalized, cookies_file=cookies_file)

        try:
            return await asyncio.to_thread(
                _inspect_url_sync, normalized, True, cookies_file
            )
        except DownloaderError as primary_err:
            logger.info(
                "Primary yt-dlp IG inspection failed (%s), trying embed fallback for %s",
                primary_err.error_key,
                normalized,
            )
            try:
                return await _inspect_ig_embed_fallback(normalized)
            except DownloaderError:
                raise primary_err

    try:
        return await asyncio.to_thread(_inspect_url_sync, normalized, False, None)
    except DownloaderError as primary_err:
        logger.info(
            "Primary yt-dlp X inspection failed (%s), trying FxTwitter fallback for %s",
            primary_err.error_key,
            normalized,
        )
        try:
            return await _inspect_via_fxtwitter(normalized)
        except Exception:
            raise primary_err


async def download_direct_file(
    direct_url: str,
    temp_root: Path,
    default_ext: str = ".mp4",
) -> tuple[Path, Path]:
    """Download a direct CDN media file (photo, GIF, or MP4) into a temp directory."""
    temp_root.mkdir(parents=True, exist_ok=True)
    req_dir = Path(tempfile.mkdtemp(prefix="xbot_", dir=temp_root))
    out_path = req_dir / f"{uuid.uuid4().hex[:12]}{default_ext}"
    try:
        async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as session:
            async with session.get(
                direct_url, timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    raise DownloaderError(
                        "err_generic", f"Direct download failed: HTTP {resp.status}"
                    )
                with out_path.open("wb") as f:
                    async for chunk in resp.content.iter_chunked(65536):
                        f.write(chunk)
        return out_path, req_dir
    except Exception:
        shutil.rmtree(req_dir, ignore_errors=True)
        raise


def _download_media_sync(
    url: str,
    req_dir: Path,
    format_selector: str | None,
    playlist_index: int | None,
    cookies_file: Path | None = None,
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
        "ffmpeg_location": FFMPEG_PATH,
    }
    if _is_instagram_url(url) and cookies_file and cookies_file.exists():
        ydl_opts["cookiefile"] = str(cookies_file)

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
    cookies_file: Path | None = None,
) -> tuple[Path, Path]:
    """Download video/GIF into a unique temp directory."""
    if format_selector and format_selector.startswith("direct:"):
        direct_url = format_selector.split("direct:", 1)[1]
        return await download_direct_file(direct_url, temp_root, default_ext=".mp4")

    temp_root.mkdir(parents=True, exist_ok=True)
    req_dir = Path(tempfile.mkdtemp(prefix="xbot_", dir=temp_root))
    try:
        try:
            file_path = await asyncio.to_thread(
                _download_media_sync,
                url,
                req_dir,
                format_selector,
                playlist_index,
                cookies_file,
            )
            return file_path, req_dir
        except DownloaderError:
            if _is_instagram_url(url):
                items = await _inspect_ig_embed_fallback(url)
            else:
                items = await _inspect_via_fxtwitter(url)

            target_idx = (playlist_index - 1) if playlist_index and playlist_index > 0 else 0
            target_item = items[min(target_idx, len(items) - 1)]
            fallback_url = (
                target_item.qualities[0].direct_url
                if target_item.qualities and target_item.qualities[0].direct_url
                else target_item.direct_url
            )
            if not fallback_url:
                raise
            shutil.rmtree(req_dir, ignore_errors=True)
            return await download_direct_file(fallback_url, temp_root, default_ext=".mp4")
    except Exception:
        shutil.rmtree(req_dir, ignore_errors=True)
        raise


def _convert_to_gif_mp4_sync(input_path: Path, req_dir: Path) -> Path:
    """Convert any video file into a muted, Telegram-compatible looping MP4 GIF."""
    output_path = req_dir / f"gif_{uuid.uuid4().hex[:10]}.mp4"
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i",
        str(input_path),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "26",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        "scale='min(720,iw)':-2,fps=24",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
    except Exception as exc:
        logger.exception("FFmpeg subprocess error during GIF conversion")
        raise DownloaderError("err_gif_convert_failed", str(exc)) from exc

    if result.returncode != 0 or not output_path.exists():
        stderr_tail = result.stderr.decode("utf-8", errors="ignore")[-400:]
        logger.error("FFmpeg GIF conversion failed: %s", stderr_tail)
        raise DownloaderError("err_gif_convert_failed", stderr_tail)

    return output_path


async def convert_video_to_gif_mp4(input_path: Path, req_dir: Path) -> Path:
    """Asynchronously convert a downloaded video into a muted Telegram GIF animation."""
    return await asyncio.to_thread(_convert_to_gif_mp4_sync, input_path, req_dir)