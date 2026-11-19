"""Async SQLite storage for user language preferences and seen trending GIFs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import aiosqlite

logger = logging.getLogger(__name__)

LanguageCode = Literal["en", "fa"]
DEFAULT_LANGUAGE: LanguageCode = "en"


class Database:
    """Lightweight async SQLite wrapper managing user preferences and GIF history."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open the SQLite connection and ensure schema exists."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'en',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_trending_gifs (
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                gif_url TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, category, gif_url)
            )
            """
        )
        await self._conn.commit()
        logger.info("SQLite database initialized at %s", self._db_path)

    async def close(self) -> None:
        """Close the SQLite connection gracefully."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            logger.info("SQLite database connection closed.")

    async def get_user_language(self, user_id: int) -> LanguageCode:
        """Return the saved language ('en' or 'fa') for a user, defaulting to 'en'."""
        if self._conn is None:
            raise RuntimeError("Database is not connected.")

        async with self._conn.execute(
            "SELECT language FROM users WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row and row[0] in ("en", "fa"):
            return row[0]
        return DEFAULT_LANGUAGE

    async def set_user_language(self, user_id: int, language: LanguageCode) -> None:
        """Insert or update the user's preferred language."""
        if self._conn is None:
            raise RuntimeError("Database is not connected.")
        if language not in ("en", "fa"):
            raise ValueError(f"Unsupported language code: {language}")

        await self._conn.execute(
            """
            INSERT INTO users (user_id, language, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                language = excluded.language,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, language),
        )
        await self._conn.commit()

    async def get_seen_trending_urls(self, user_id: int, category: str) -> set[str]:
        """Return all GIF URLs already sent to a user in a given category."""
        if self._conn is None:
            raise RuntimeError("Database is not connected.")

        async with self._conn.execute(
            "SELECT gif_url FROM sent_trending_gifs WHERE user_id = ? AND category = ?",
            (user_id, category),
        ) as cursor:
            rows = await cursor.fetchall()
        return {row[0] for row in rows}

    async def mark_trending_gif_sent(
        self, user_id: int, category: str, gif_url: str
    ) -> None:
        """Record a trending GIF URL as seen by the user."""
        if self._conn is None:
            raise RuntimeError("Database is not connected.")

        await self._conn.execute(
            """
            INSERT OR IGNORE INTO sent_trending_gifs (user_id, category, gif_url)
            VALUES (?, ?, ?)
            """,
            (user_id, category, gif_url),
        )
        await self._conn.commit()

    async def reset_seen_trending_urls(self, user_id: int, category: str) -> None:
        """Clear seen GIF history for a user/category once the full pool has been viewed."""
        if self._conn is None:
            raise RuntimeError("Database is not connected.")

        await self._conn.execute(
            "DELETE FROM sent_trending_gifs WHERE user_id = ? AND category = ?",
            (user_id, category),
        )
        await self._conn.commit()