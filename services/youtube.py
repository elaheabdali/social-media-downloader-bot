"""YouTube channel search and latest videos fetcher (no API key required)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus, urlparse

import aiohttp
import yt_dlp

logger = logging.getLogger(__name__)

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

YT_CHANNEL_URL_RE = re.compile(
    r"^https?://(?:www\.|m\.)?youtube\.com/"
    r"(?:@[\w.-]+|channel/UC[\w-]+|c/[\w.-]+|user/[\w.-]+)(?:/(?:videos|featured|shorts|streams)?)?/?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class YouTubeChannelResult:
    """Represents a YouTube channel matched during search."""

    channel_id: str
    title: str
    subscribers: str = ""


@dataclass(frozen=True)
class YouTubeVideoEntry:
    """Represents a recent video published on a YouTube channel."""

    video_id: str
    title: str
    url: str
    published: str = ""


def is_youtube_url(url: str) -> bool:
    """Return True if URL belongs to YouTube or youtu.be."""
    host = urlparse(url).netloc.lower()
    return any(d in host for d in ("youtube.com", "youtu.be"))


def is_youtube_channel_url(url: str) -> bool:
    """Return True if URL points to a YouTube channel page rather than a single video."""
    clean = url.split("?")[0].split("#")[0]
    return bool(YT_CHANNEL_URL_RE.match(clean))


def _walk_channel_renderers(obj: Any, results: list[YouTubeChannelResult], seen: set[str]) -> None:
    """Recursively extract channelRenderer objects from ytInitialData."""
    if isinstance(obj, dict):
        if "channelRenderer" in obj:
            cr = obj["channelRenderer"]
            cid = cr.get("channelId")
            title_obj = cr.get("title") or {}
            title = title_obj.get("simpleText") or ""
            if not title and "runs" in title_obj:
                title = "".join(r.get("text", "") for r in title_obj["runs"])

            sub_obj = cr.get("subscriberCountText") or cr.get("videoCountText") or {}
            subs = sub_obj.get("simpleText") or ""
            if not subs and "runs" in sub_obj:
                subs = "".join(r.get("text", "") for r in sub_obj["runs"])

            if cid and title and cid not in seen:
                seen.add(cid)
                results.append(
                    YouTubeChannelResult(
                        channel_id=cid,
                        title=title.strip(),
                        subscribers=subs.strip(),
                    )
                )
            return

        for val in obj.values():
            if len(results) >= 6:
                return
            _walk_channel_renderers(val, results, seen)
    elif isinstance(obj, list):
        for item in obj:
            if len(results) >= 6:
                return
            _walk_channel_renderers(item, results, seen)


async def search_youtube_channels(query: str) -> list[YouTubeChannelResult]:
    """Search YouTube channels by name or @handle using YouTube's channel search filter."""
    clean_query = query.strip()
    if not clean_query:
        return []

    # sp=EgIQAg%3D%3D filters YouTube search results strictly to Channels
    search_url = f"https://www.youtube.com/results?search_query={quote_plus(clean_query)}&sp=EgIQAg%3D%3D"

    try:
        async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as session:
            async with session.get(
                search_url, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    return []
                html_text = await resp.text()
    except Exception:
        logger.exception("YouTube channel search HTTP request failed")
        return []

    results: list[YouTubeChannelResult] = []
    seen: set[str] = set()

    json_match = re.search(r"var ytInitialData\s*=\s*(\{.+?\});\s*</script>", html_text)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            _walk_channel_renderers(data, results, seen)
        except Exception:
            logger.debug("Failed to parse ytInitialData JSON, falling back to regex")

    if not results:
        for m in re.finditer(
            r'"channelRenderer"\s*:\s*\{"channelId"\s*:\s*"(UC[\w-]+)"\s*,\s*"title"\s*:\s*\{"simpleText"\s*:\s*"([^"]+)"',
            html_text,
        ):
            cid, title = m.group(1), m.group(2)
            if cid not in seen:
                seen.add(cid)
                results.append(YouTubeChannelResult(channel_id=cid, title=title))
            if len(results) >= 6:
                break

    return results[:6]


async def resolve_channel_id_from_url(url: str) -> str | None:
    """Resolve any YouTube channel URL (@handle, /c/name, /channel/UC...) into a UC... channel_id."""
    direct_match = re.search(r"/channel/(UC[\w-]+)", url)
    if direct_match:
        return direct_match.group(1)

    try:
        async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return None
                html_text = await resp.text()
    except Exception:
        return None

    for pattern in (
        r'"externalId"\s*:\s*"(UC[\w-]+)"',
        r'"channelId"\s*:\s*"(UC[\w-]+)"',
        r'<meta\s+itemprop=["\']identifier["\']\s+content=["\'](UC[\w-]+)["\']',
    ):
        m = re.search(pattern, html_text)
        if m:
            return m.group(1)

    return None


def _fetch_channel_videos_ytdlp_sync(channel_id: str, limit: int) -> tuple[str, list[YouTubeVideoEntry]]:
    """Fallback flat playlist extraction via yt-dlp."""
    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": limit,
        "socket_timeout": 15,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False) or {}

    channel_title = (info.get("channel") or info.get("title") or "YouTube Channel").strip()
    entries = info.get("entries") or []
    videos: list[YouTubeVideoEntry] = []

    for e in entries[:limit]:
        if not e:
            continue
        vid_id = e.get("id")
        title = (e.get("title") or "YouTube Video").strip()
        if vid_id:
            videos.append(
                YouTubeVideoEntry(
                    video_id=vid_id,
                    title=title,
                    url=f"https://www.youtube.com/watch?v={vid_id}",
                )
            )
    return channel_title, videos


async def fetch_channel_latest_videos(
    channel_id: str, limit: int = 8
) -> tuple[str, list[YouTubeVideoEntry]]:
    """Fetch the latest videos of a YouTube channel via its official public XML feed."""
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    try:
        async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as session:
            async with session.get(
                feed_url, timeout=aiohttp.ClientTimeout(total=12)
            ) as resp:
                if resp.status == 200:
                    xml_text = await resp.text()
                    root = ET.fromstring(xml_text)
                    ns = {
                        "atom": "http://www.w3.org/2005/Atom",
                        "yt": "http://www.youtube.com/xml/schemas/2015",
                    }
                    title_el = root.find("atom:title", ns)
                    channel_title = (
                        title_el.text.strip()
                        if title_el is not None and title_el.text
                        else "YouTube Channel"
                    )

                    videos: list[YouTubeVideoEntry] = []
                    for entry in root.findall("atom:entry", ns)[:limit]:
                        vid_el = entry.find("yt:videoId", ns)
                        vtitle_el = entry.find("atom:title", ns)
                        pub_el = entry.find("atom:published", ns)

                        if vid_el is not None and vid_el.text:
                            vid_id = vid_el.text.strip()
                            vtitle = (
                                vtitle_el.text.strip()
                                if vtitle_el is not None and vtitle_el.text
                                else "YouTube Video"
                            )
                            pub_date = (
                                pub_el.text[:10]
                                if pub_el is not None and pub_el.text
                                else ""
                            )
                            videos.append(
                                YouTubeVideoEntry(
                                    video_id=vid_id,
                                    title=vtitle,
                                    url=f"https://www.youtube.com/watch?v={vid_id}",
                                    published=pub_date,
                                )
                            )
                    if videos:
                        return channel_title, videos
    except Exception:
        logger.debug("YouTube RSS feed failed for %s, falling back to yt-dlp", channel_id)

    return await asyncio.to_thread(_fetch_channel_videos_ytdlp_sync, channel_id, limit)