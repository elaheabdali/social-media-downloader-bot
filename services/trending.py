"""Live trending GIF fetcher for Persian X, English X, Romantic, and Meme categories."""

from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from typing import Literal
from urllib.parse import quote_plus

import aiohttp

from database import Database

logger = logging.getLogger(__name__)

TrendingCategory = Literal["fa_twitter", "en_twitter", "romantic", "memes"]

VALID_CATEGORIES: set[str] = {"fa_twitter", "en_twitter", "romantic", "memes"}

CATEGORY_LABEL_KEYS: dict[str, str] = {
    "fa_twitter": "cat_fa_twitter",
    "en_twitter": "cat_en_twitter",
    "romantic": "cat_romantic",
    "memes": "cat_memes",
}

# Search queries tailored for each requested timeline/category
CATEGORY_CONFIG: dict[str, dict[str, list[str]]] = {
    "fa_twitter": {
        "x_queries": [
            'site:x.com "توییترفارسی" OR "توییتر_فارسی"',
            'site:x.com "ری اکشن" OR "ری‌اکشن" gif',
            'site:x.com "پایتخت" OR "برره" OR "قهوه تلخ" gif',
        ],
        "tenor_slugs": [
            "iranian-reaction",
            "persian-meme",
            "iran-funny-reaction",
            "persian-cat-reaction",
        ],
    },
    "en_twitter": {
        "x_queries": [
            "site:x.com/GIF__",
            'site:x.com "reaction gif" OR "viral gif"',
        ],
        "tenor_slugs": [
            "twitter-reaction",
            "viral-reaction-gif",
            "shocked-reaction",
            "trending-reaction",
        ],
    },
    "romantic": {
        "x_queries": [
            'site:x.com "romantic gif" OR "love gif" OR "cute couple gif"',
            'site:x.com "عاشقانه" gif',
        ],
        "tenor_slugs": [
            "romantic-love",
            "cute-couple-hug",
            "romantic-kiss-love",
            "love-heart-couple",
        ],
    },
    "memes": {
        "x_queries": [
            'site:x.com "meme gif" OR "funny gif"',
            'site:x.com "میم" OR "طنز" gif',
        ],
        "tenor_slugs": [
            "funny-meme",
            "hilarious-meme-reaction",
            "dank-memes",
            "funny-cat-meme",
        ],
    },
}

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
}

X_STATUS_LINK_RE = re.compile(
    r"https?://(?:www\.)?(?:x\.com|twitter\.com)/([A-Za-z0-9_]+)/status/(\d+)",
    re.IGNORECASE,
)

TENOR_MP4_RE = re.compile(
    r"https://(?:media|c)\.tenor\.com/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+\.mp4",
    re.IGNORECASE,
)

# In-memory pool cache: category -> (timestamp, list_of_mp4_urls)
_POOL_CACHE: dict[str, tuple[float, list[str]]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour


async def _discover_x_gif_urls(
    session: aiohttp.ClientSession, queries: list[str]
) -> list[str]:
    """Discover real X/Twitter status links via RSS search and resolve their tweet_video MP4s."""
    status_paths: list[str] = []
    seen_ids: set[str] = set()

    for q in random.sample(queries, k=min(2, len(queries))):
        rss_url = f"https://www.bing.com/search?format=rss&q={quote_plus(q)}"
        try:
            async with session.get(
                rss_url, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    continue
                xml_text = await resp.text()
                for m in X_STATUS_LINK_RE.finditer(xml_text):
                    user, status_id = m.group(1), m.group(2)
                    if status_id not in seen_ids:
                        seen_ids.add(status_id)
                        status_paths.append(f"/{user}/status/{status_id}")
        except Exception:
            logger.debug("Bing RSS discovery failed for query: %s", q)

    if not status_paths:
        return []

    async def _resolve_single(path: str) -> str | None:
        api_url = f"https://api.fxtwitter.com{path}"
        try:
            async with session.get(
                api_url, timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
            tweet = data.get("tweet") or {}
            media = tweet.get("media") or {}
            videos = media.get("videos") or media.get("all") or []
            for item in videos:
                v_url = item.get("url") or ""
                if "/tweet_video/" in v_url.lower() or item.get("type") == "gif":
                    return v_url
        except Exception:
            return None
        return None

    candidates = random.sample(status_paths, k=min(10, len(status_paths)))
    resolved = await asyncio.gather(*[_resolve_single(p) for p in candidates])
    return [u for u in resolved if u]


async def _fetch_tenor_mp4_urls(
    session: aiohttp.ClientSession, slugs: list[str]
) -> list[str]:
    """Extract lightweight MP4 animation URLs from public Tenor search pages."""
    urls: list[str] = []
    seen: set[str] = set()

    for slug in random.sample(slugs, k=min(2, len(slugs))):
        search_url = f"https://tenor.com/search/{slug}-gifs"
        try:
            async with session.get(
                search_url, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    continue
                html_text = await resp.text()
                for match in TENOR_MP4_RE.finditer(html_text):
                    mp4_url = match.group(0)
                    # Prefer standard feed/preview MP4s (fast & compact for Telegram)
                    if mp4_url not in seen:
                        seen.add(mp4_url)
                        urls.append(mp4_url)
        except Exception:
            logger.debug("Tenor fetch failed for slug: %s", slug)

    return urls[:25]


async def _refresh_category_pool(category: str) -> list[str]:
    """Fetch a fresh batch of GIF MP4 URLs from X/Twitter and Tenor for a category."""
    cfg = CATEGORY_CONFIG.get(category)
    if not cfg:
        return []

    async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as session:
        x_task = _discover_x_gif_urls(session, cfg["x_queries"])
        tenor_task = _fetch_tenor_mp4_urls(session, cfg["tenor_slugs"])
        x_urls, tenor_urls = await asyncio.gather(x_task, tenor_task)

    combined: list[str] = []
    seen: set[str] = set()
    for u in x_urls + tenor_urls:
        if u not in seen:
            seen.add(u)
            combined.append(u)

    if combined:
        random.shuffle(combined)
        _POOL_CACHE[category] = (time.monotonic(), combined)

    return combined


async def get_next_trending_gif(db: Database, user_id: int, category: str) -> str | None:
    """Return an unseen trending GIF URL for the user in the chosen category."""
    if category not in VALID_CATEGORIES:
        return None

    now = time.monotonic()
    cached = _POOL_CACHE.get(category)
    if cached and (now - cached[0]) < _CACHE_TTL_SECONDS and cached[1]:
        pool = cached[1]
    else:
        pool = await _refresh_category_pool(category)

    if not pool:
        return None

    seen_urls = await db.get_seen_trending_urls(user_id, category)
    unseen = [u for u in pool if u not in seen_urls]

    if not unseen:
        # Refresh pool once before resetting user's history
        pool = await _refresh_category_pool(category)
        unseen = [u for u in pool if u not in seen_urls]

    if not unseen:
        await db.reset_seen_trending_urls(user_id, category)
        unseen = list(pool)

    if not unseen:
        return None

    chosen = random.choice(unseen)
    await db.mark_trending_gif_sent(user_id, category, chosen)
    return chosen