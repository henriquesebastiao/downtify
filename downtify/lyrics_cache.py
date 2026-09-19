"""Which lyrics providers have already been asked about a track.

A provider that has no lyrics for a song today usually still has none
tomorrow, so every download and every library pass would otherwise repeat
the same misses. Hits are remembered too, but only so a re-download can
tell how the file got its lyrics; a miss expires after a while, since
catalogues do grow.
"""

from __future__ import annotations

import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from .sqlite_utils import connect_sqlite

#: How long a "this provider has nothing" answer is trusted.
DEFAULT_MISS_TTL_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(value: Optional[str]) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _clean(text: Any) -> str:
    return unicodedata.normalize('NFKC', str(text or '')).strip().casefold()


def song_key(song: dict[str, Any]) -> str:
    """Stable key for a song: its Spotify id, else artist and title.

    Falls back to the text so tracks from YouTube Music, a CSV import or a
    library pass are cached too.
    """

    track_id = str(song.get('song_id') or '').strip()
    if track_id:
        return f'id:{track_id}'
    artists = song.get('artists') or []
    artist = _clean(artists[0] if artists else song.get('artist'))
    title = _clean(song.get('name') or song.get('title'))
    if not title:
        return ''
    return f'text:{artist}|{title}'


class LyricsLookupCache:
    """Remembers, per song and provider, whether lyrics were found."""

    def __init__(
        self, db_path: Path, miss_ttl_days: int = DEFAULT_MISS_TTL_DAYS
    ) -> None:
        self._path = str(db_path)
        self.miss_ttl = timedelta(days=miss_ttl_days)
        self._init_db()

    def _connect(self):
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lyrics_lookups (
                    song_key TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    found INTEGER NOT NULL,
                    checked_at TEXT NOT NULL,
                    PRIMARY KEY (song_key, provider)
                )
            """)

    def should_skip(self, key: str, provider: str) -> bool:
        """True when this provider recently had nothing for this song."""

        if not key:
            return False
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """SELECT found, checked_at FROM lyrics_lookups
                       WHERE song_key = ? AND provider = ?""",
                    (key, provider),
                ).fetchone()
        except Exception:
            logger.opt(exception=True).warning('Lyrics cache read failed')
            return False
        if row is None or row['found']:
            return False
        checked = _parse(row['checked_at'])
        return bool(checked and _now() - checked < self.miss_ttl)

    def record(self, key: str, provider: str, found: bool) -> None:
        if not key:
            return
        try:
            with self._connect() as conn:
                conn.execute(
                    """INSERT INTO lyrics_lookups
                       (song_key, provider, found, checked_at)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(song_key, provider) DO UPDATE SET
                       found = excluded.found,
                       checked_at = excluded.checked_at""",
                    (key, provider, 1 if found else 0, _now().isoformat()),
                )
        except Exception:
            logger.opt(exception=True).warning('Lyrics cache write failed')

    def forget(self, key: str) -> int:
        """Drop what's known about a song, so every provider is tried again."""

        if not key:
            return 0
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    'DELETE FROM lyrics_lookups WHERE song_key = ?', (key,)
                )
                return cur.rowcount
        except Exception:
            logger.opt(exception=True).warning('Lyrics cache delete failed')
            return 0

    def clear(self) -> int:
        try:
            with self._connect() as conn:
                cur = conn.execute('DELETE FROM lyrics_lookups')
                return cur.rowcount
        except Exception:
            logger.opt(exception=True).warning('Lyrics cache clear failed')
            return 0
