"""Periodic playlist monitoring and automatic downloading."""

from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger

from .cover_cache import CoverArtCache
from .downloader import Downloader
from .library_metadata_cache import LibraryMetadataCache
from .navidrome_index import NavidromeIndex
from .playlist_catalog import PlaylistCatalog
from .playlist_spotify_cache import PlaylistSpotifyCache
from .sqlite_utils import connect_sqlite
from .track_index import TrackIndex

MONITOR_LOOP_INTERVAL = 60  # seconds between loop sweeps


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_due(last_checked: Optional[str], interval_minutes: int) -> bool:
    if last_checked is None:
        return True
    try:
        last = datetime.fromisoformat(last_checked)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= last + timedelta(
            minutes=interval_minutes
        )
    except ValueError:
        return True


@dataclass
class MonitoredPlaylist:
    id: int
    spotify_id: str
    name: str
    url: str
    interval_minutes: int
    enabled: bool
    last_checked: Optional[str]
    last_track_count: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PlaylistMonitorDB:
    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._lock = asyncio.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = connect_sqlite(self._path, row_factory=True)
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS monitored_playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spotify_id TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    interval_minutes INTEGER NOT NULL DEFAULT 60,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    last_checked TEXT,
                    last_track_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS downloaded_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER NOT NULL,
                    track_spotify_id TEXT NOT NULL,
                    downloaded_at TEXT NOT NULL,
                    FOREIGN KEY (playlist_id) REFERENCES monitored_playlists(id)
                        ON DELETE CASCADE,
                    UNIQUE(playlist_id, track_spotify_id)
                );
            """)
            # Migration: add filename column if it doesn't exist yet
            try:
                conn.execute(
                    'ALTER TABLE downloaded_tracks ADD COLUMN filename TEXT'
                )
            except Exception:
                pass

    def add_playlist(
        self,
        spotify_id: str,
        name: str,
        url: str,
        interval_minutes: int = 60,
    ) -> MonitoredPlaylist:
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO monitored_playlists
                   (spotify_id, name, url, interval_minutes, enabled, created_at)
                   VALUES (?, ?, ?, ?, 1, ?)""",
                (spotify_id, name, url, interval_minutes, _now_iso()),
            )
            row = conn.execute(
                'SELECT * FROM monitored_playlists WHERE id = ?',
                (cur.lastrowid,),
            ).fetchone()
            return _row_to_playlist(row)

    def list_playlists(self) -> list[MonitoredPlaylist]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT * FROM monitored_playlists ORDER BY created_at DESC'
            ).fetchall()
            return [_row_to_playlist(r) for r in rows]

    def get_playlist(self, playlist_id: int) -> Optional[MonitoredPlaylist]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM monitored_playlists WHERE id = ?',
                (playlist_id,),
            ).fetchone()
            return _row_to_playlist(row) if row else None

    def get_by_spotify_id(
        self, spotify_id: str
    ) -> Optional[MonitoredPlaylist]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM monitored_playlists WHERE spotify_id = ?',
                (spotify_id,),
            ).fetchone()
            return _row_to_playlist(row) if row else None

    def delete_playlist(self, playlist_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                'DELETE FROM monitored_playlists WHERE id = ?',
                (playlist_id,),
            )
            return cur.rowcount > 0

    def update_playlist(
        self, playlist_id: int, **kwargs: Any
    ) -> Optional[MonitoredPlaylist]:
        allowed = {
            'interval_minutes',
            'enabled',
            'last_checked',
            'last_track_count',
            'name',
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return self.get_playlist(playlist_id)
        set_clause = ', '.join(f'{k} = ?' for k in updates)
        values = list(updates.values()) + [playlist_id]
        with self._connect() as conn:
            conn.execute(
                f'UPDATE monitored_playlists SET {set_clause} WHERE id = ?',
                values,
            )
            row = conn.execute(
                'SELECT * FROM monitored_playlists WHERE id = ?',
                (playlist_id,),
            ).fetchone()
            return _row_to_playlist(row) if row else None

    def get_track_filenames(
        self, playlist_id: int
    ) -> dict[str, Optional[str]]:
        """Return ``{track_spotify_id: filename}`` for all known tracks."""
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT track_spotify_id, filename FROM downloaded_tracks WHERE playlist_id = ?',
                (playlist_id,),
            ).fetchall()
            return {r['track_spotify_id']: r['filename'] for r in rows}

    def playlists_for_track(self, track_spotify_id: str) -> set[str]:
        """Monitored playlist names that include this Spotify track."""

        tid = str(track_spotify_id or '').strip()
        if not tid:
            return set()
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT DISTINCT p.name FROM downloaded_tracks dt
                   JOIN monitored_playlists p ON p.id = dt.playlist_id
                   WHERE dt.track_spotify_id = ?""",
                (tid,),
            ).fetchall()
        return {str(row['name']) for row in rows}

    def update_filename_for_spotify(
        self, track_spotify_id: str, filename: str
    ) -> set[str]:
        """Update stored paths for *track_spotify_id* across all playlists."""

        tid = str(track_spotify_id or '').strip()
        name = str(filename or '').strip().replace('\\', '/')
        if not tid or not name:
            return set()
        with self._connect() as conn:
            conn.execute(
                """UPDATE downloaded_tracks SET filename = ?
                   WHERE track_spotify_id = ? AND
                   (filename IS NULL OR filename != ?)""",
                (name, tid, name),
            )
        return self.playlists_for_track(tid)

    def mark_track_downloaded(
        self,
        playlist_id: int,
        track_spotify_id: str,
        filename: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO downloaded_tracks
                   (playlist_id, track_spotify_id, downloaded_at, filename)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(playlist_id, track_spotify_id) DO UPDATE SET
                   downloaded_at=excluded.downloaded_at,
                   filename=excluded.filename""",
                (playlist_id, track_spotify_id, _now_iso(), filename),
            )


def _row_to_playlist(row: sqlite3.Row) -> MonitoredPlaylist:
    return MonitoredPlaylist(
        id=row['id'],
        spotify_id=row['spotify_id'],
        name=row['name'],
        url=row['url'],
        interval_minutes=row['interval_minutes'],
        enabled=bool(row['enabled']),
        last_checked=row['last_checked'],
        last_track_count=row['last_track_count'],
        created_at=row['created_at'],
    )


async def check_playlist(
    playlist: MonitoredPlaylist,
    db: PlaylistMonitorDB,
    downloader: Downloader,
    broadcast: Callable[[dict[str, Any]], Any],
    loop: asyncio.AbstractEventLoop,
    settings: Optional[dict[str, Any]] = None,
    track_index: Optional[TrackIndex] = None,
    navidrome_index: Optional[NavidromeIndex] = None,
    metadata_cache: Optional[LibraryMetadataCache] = None,
    cover_cache: Optional[CoverArtCache] = None,
    playlist_catalog: Optional[PlaylistCatalog] = None,
    playlist_spotify_cache: Optional[PlaylistSpotifyCache] = None,
) -> int:
    """Refresh playlist from Spotify and queue missing tracks. Returns queued count."""

    del (
        downloader,
        broadcast,
        loop,
        track_index,
        navidrome_index,
        metadata_cache,
        cover_cache,
        playlist_catalog,
        playlist_spotify_cache,
    )

    from . import api as api_mod  # noqa: PLC0415

    logger.info(
        'Checking monitored playlist "{}" ({})',
        playlist.name,
        playlist.spotify_id,
    )

    generate_m3u = settings is None or bool(settings.get('generate_m3u', True))
    try:
        result = await api_mod.queue_missing_playlist_tracks(
            playlist.spotify_id,
            playlist_url=playlist.url,
            generate_m3u=generate_m3u,
            refresh=True,
        )
    except Exception:
        logger.exception(
            'Failed monitor check for playlist {}', playlist.spotify_id
        )
        await asyncio.to_thread(
            db.update_playlist, playlist.id, last_checked=_now_iso()
        )
        return 0

    queued = int(
        result.get('queued_count')
        or result.get('missing_count')
        or result.get('count')
        or 0
    )
    expected = int(
        result.get('expected_count') or playlist.last_track_count or 0
    )
    await asyncio.to_thread(
        db.update_playlist,
        playlist.id,
        last_checked=_now_iso(),
        last_track_count=expected,
    )
    if queued > 0:
        logger.info(
            'Queued {} missing track(s) from monitored playlist "{}"',
            queued,
            playlist.name,
        )
    return queued


async def monitor_loop(
    db: PlaylistMonitorDB,
    get_downloader: Callable[[], Optional[Downloader]],
    get_track_index: Callable[[], Optional[TrackIndex]],
    get_navidrome_index: Callable[[], Optional[NavidromeIndex]],
    get_metadata_cache: Callable[[], Optional[LibraryMetadataCache]],
    get_cover_cache: Callable[[], Optional[CoverArtCache]],
    get_playlist_catalog: Callable[[], Optional[PlaylistCatalog]],
    get_playlist_spotify_cache: Callable[[], Optional[PlaylistSpotifyCache]],
    broadcast: Callable[[dict[str, Any]], Any],
    loop: asyncio.AbstractEventLoop,
    settings: Optional[dict[str, Any]] = None,
) -> None:
    """Background task: sweep all enabled playlists that are due for checking."""
    while True:
        try:
            playlists = await asyncio.to_thread(db.list_playlists)
            for pl in playlists:
                if not pl.enabled:
                    continue
                if not _is_due(pl.last_checked, pl.interval_minutes):
                    continue
                downloader = get_downloader()
                if downloader is None:
                    continue
                track_index = get_track_index()
                navidrome_index = get_navidrome_index()
                metadata_cache = get_metadata_cache()
                cover_cache = get_cover_cache()
                playlist_catalog = get_playlist_catalog()
                playlist_spotify_cache = get_playlist_spotify_cache()
                try:
                    count = await check_playlist(
                        pl,
                        db,
                        downloader,
                        broadcast,
                        loop,
                        settings,
                        track_index=track_index,
                        navidrome_index=navidrome_index,
                        metadata_cache=metadata_cache,
                        cover_cache=cover_cache,
                        playlist_catalog=playlist_catalog,
                        playlist_spotify_cache=playlist_spotify_cache,
                    )
                    if count > 0:
                        logger.info(
                            'Auto-queued {} missing track(s) from "{}"',
                            count,
                            pl.name,
                        )
                except Exception:
                    logger.exception(
                        'Error while checking playlist "{}"', pl.name
                    )
        except Exception:
            logger.exception('Unexpected error in monitor loop')
        await asyncio.sleep(MONITOR_LOOP_INTERVAL)
