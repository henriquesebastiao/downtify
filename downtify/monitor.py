"""Periodic playlist monitoring and automatic downloading."""

from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger

from . import m3u, spotify
from .downloader import Downloader

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
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.row_factory = sqlite3.Row
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

    def get_downloaded_track_ids(self, playlist_id: int) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT track_spotify_id FROM downloaded_tracks WHERE playlist_id = ?',
                (playlist_id,),
            ).fetchall()
            return {r['track_spotify_id'] for r in rows}

    def mark_track_downloaded(
        self, playlist_id: int, track_spotify_id: str
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO downloaded_tracks
                   (playlist_id, track_spotify_id, downloaded_at)
                   VALUES (?, ?, ?)""",
                (playlist_id, track_spotify_id, _now_iso()),
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
) -> int:
    """Fetch playlist, detect new tracks, download them. Returns count downloaded."""
    logger.info(
        'Checking monitored playlist "{}" ({})',
        playlist.name,
        playlist.spotify_id,
    )

    try:
        tracks = await asyncio.to_thread(
            spotify.playlist_tracks_from_id, playlist.spotify_id
        )
    except Exception:
        logger.exception('Failed to fetch playlist {}', playlist.spotify_id)
        await asyncio.to_thread(
            db.update_playlist, playlist.id, last_checked=_now_iso()
        )
        return 0

    known_ids = await asyncio.to_thread(
        db.get_downloaded_track_ids, playlist.id
    )
    new_tracks = [
        t for t in tracks if t.get('song_id') and t['song_id'] not in known_ids
    ]

    if new_tracks:
        logger.info(
            'Found {} new track(s) in playlist "{}"',
            len(new_tracks),
            playlist.name,
        )

    pl_subdir = m3u.sanitize_playlist_name(playlist.name)

    downloaded = 0
    for song in new_tracks:
        track_id = song['song_id']
        pl_name = playlist.name

        # Playlist embed entries are missing release year and use the
        # playlist cover instead of the album cover. Re-fetching the track
        # embed gives us both per-track. We still keep the playlist values
        # as a fallback if the per-track fetch fails for any reason.
        try:
            full = await asyncio.to_thread(spotify.track_from_id, track_id)
            for key in ('cover_url', 'year', 'album_name', 'artists'):
                value = full.get(key)
                if value:
                    song[key] = value
        except Exception:
            logger.opt(exception=True).warning(
                'Per-track Spotify fetch failed for {}; '
                'falling back to playlist data',
                track_id,
            )

        def _make_cb(s: dict, name: str) -> Callable[[float, str], None]:
            def _cb(pct: float, message: str) -> None:
                asyncio.run_coroutine_threadsafe(
                    broadcast({
                        'song': s,
                        'progress': pct,
                        'message': message,
                        'playlist_name': name,
                    }),
                    loop,
                )

            return _cb

        try:
            await loop.run_in_executor(
                None,
                lambda s=song: downloader.download(
                    s, _make_cb(s, pl_name), subdir=pl_subdir
                ),
            )
            await asyncio.to_thread(
                db.mark_track_downloaded, playlist.id, track_id
            )
            downloaded += 1
        except Exception:
            logger.exception('Failed to auto-download track {}', track_id)

    await asyncio.to_thread(
        db.update_playlist,
        playlist.id,
        last_checked=_now_iso(),
        last_track_count=len(tracks),
    )

    if downloaded > 0 and (
        settings is None or settings.get('generate_m3u', True)
    ):
        await asyncio.to_thread(_regenerate_m3u, playlist, tracks, downloader)
    return downloaded


def _regenerate_m3u(
    playlist: MonitoredPlaylist,
    tracks: list[dict[str, Any]],
    downloader: Downloader,
) -> None:
    """Rewrite the playlist's M3U from on-disk state after a sweep.

    Walks the full ordered track list (not just the freshly downloaded
    ones), resolves each to an existing file via the downloader, and
    hands the entries to :func:`m3u.write_m3u`. Tracks without a
    matching file on disk are dropped.
    """

    pl_subdir = m3u.sanitize_playlist_name(playlist.name)
    entries: list[dict[str, Any]] = []
    for song in tracks:
        filename = downloader.existing_filename_for(song, subdir=pl_subdir)
        if not filename:
            continue
        entries.append({
            'filename': filename,
            'title': song.get('name', ''),
            'artist': ', '.join(song.get('artists') or []),
            'duration': song.get('duration', 0),
        })
    if not entries:
        logger.warning(
            'M3U skip for monitored playlist "{}": no tracks on disk',
            playlist.name,
        )
        return
    m3u.write_m3u(
        downloader.download_dir,
        playlist.name,
        entries,
        playlist_subdir=pl_subdir,
    )


async def monitor_loop(
    db: PlaylistMonitorDB,
    get_downloader: Callable[[], Optional[Downloader]],
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
                try:
                    count = await check_playlist(
                        pl, db, downloader, broadcast, loop, settings
                    )
                    if count > 0:
                        logger.info(
                            'Auto-downloaded {} new track(s) from "{}"',
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
