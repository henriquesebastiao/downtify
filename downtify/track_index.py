"""Global Spotify track id → library file mapping for cross-playlist deduplication."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .library_cache_keys import file_content_key
from .library_paths import (
    locate_library_file,
    slskd_dir_from_downloader,
)

_SPOTIFY_TRACK_ID = re.compile(r'^[a-zA-Z0-9]{22}$')
_SPOTIFY_TRACK_URL = re.compile(
    r'(?:open\.spotify\.com|spotify\.com)/track/([a-zA-Z0-9]{22})'
)


def normalize_spotify_track_id(song: dict[str, Any]) -> Optional[str]:
    """Return a 22-char Spotify track id when ``song`` has one, else ``None``."""

    raw = str(song.get('song_id') or '').strip()
    if not raw:
        url = str(song.get('url') or '').strip()
        if url:
            raw = url
        else:
            return None
    if raw.startswith('spotify:track:'):
        raw = raw.rsplit(':', 1)[-1]
    else:
        match = _SPOTIFY_TRACK_URL.search(raw)
        if match:
            raw = match.group(1)
    if _SPOTIFY_TRACK_ID.fullmatch(raw):
        return raw
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TrackIndex:
    """SQLite index: one canonical relative path per Spotify track id."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS library_tracks (
                    spotify_track_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content_key TEXT,
                    registered_at TEXT NOT NULL
                )
            """)
            try:
                conn.execute(
                    'ALTER TABLE library_tracks ADD COLUMN content_key TEXT'
                )
            except Exception:
                pass
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_library_tracks_content_key
                ON library_tracks (content_key)
                WHERE content_key IS NOT NULL
            """)

    def lookup(self, spotify_track_id: str) -> Optional[str]:
        tid = str(spotify_track_id or '').strip()
        if not _SPOTIFY_TRACK_ID.fullmatch(tid):
            return None
        with self._connect() as conn:
            row = conn.execute(
                'SELECT filename FROM library_tracks WHERE spotify_track_id = ?',
                (tid,),
            ).fetchone()
        if row is None:
            return None
        return str(row['filename'])

    def lookup_song(self, song: dict[str, Any]) -> Optional[str]:
        tid = normalize_spotify_track_id(song)
        if not tid:
            return None
        return self.lookup(tid)

    def register(
        self,
        spotify_track_id: str,
        filename: str,
        *,
        full_path: Optional[Path] = None,
    ) -> None:
        tid = str(spotify_track_id or '').strip()
        name = str(filename or '').strip().replace('\\', '/')
        if not _SPOTIFY_TRACK_ID.fullmatch(tid) or not name:
            return
        ck: Optional[str] = None
        if full_path is not None:
            ck = file_content_key(full_path)
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO library_tracks
                   (spotify_track_id, filename, content_key, registered_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(spotify_track_id) DO UPDATE SET
                   filename=excluded.filename,
                   content_key=COALESCE(excluded.content_key, library_tracks.content_key),
                   registered_at=excluded.registered_at""",
                (tid, name, ck, _now_iso()),
            )

    def register_song(
        self,
        song: dict[str, Any],
        filename: str,
        *,
        full_path: Optional[Path] = None,
    ) -> None:
        tid = normalize_spotify_track_id(song)
        if tid:
            self.register(tid, filename, full_path=full_path)

    def update_filename(
        self,
        spotify_track_id: str,
        filename: str,
        *,
        content_key: Optional[str] = None,
    ) -> bool:
        tid = str(spotify_track_id or '').strip()
        name = str(filename or '').strip().replace('\\', '/')
        if not _SPOTIFY_TRACK_ID.fullmatch(tid) or not name:
            return False
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE library_tracks SET filename = ?,
                   content_key = COALESCE(?, content_key)
                   WHERE spotify_track_id = ? AND filename != ?""",
                (name, content_key, tid, name),
            )
            return cur.rowcount > 0

    def all_rows(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT spotify_track_id, filename, content_key
                   FROM library_tracks"""
            ).fetchall()
        return [
            {
                'spotify_track_id': str(row['spotify_track_id']),
                'filename': str(row['filename']).replace('\\', '/'),
                'content_key': row['content_key'],
            }
            for row in rows
        ]

    def set_content_key(self, spotify_track_id: str, content_key: str) -> bool:
        tid = str(spotify_track_id or '').strip()
        ck = str(content_key or '').strip()
        if not _SPOTIFY_TRACK_ID.fullmatch(tid) or not ck:
            return False
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE library_tracks SET content_key = ?
                   WHERE spotify_track_id = ? AND COALESCE(content_key, '') = ''""",
                (ck, tid),
            )
            return cur.rowcount > 0

    def remove_by_filename(self, filename: str) -> bool:
        name = str(filename or '').strip().replace('\\', '/')
        if not name:
            return False
        with self._connect() as conn:
            cur = conn.execute(
                'DELETE FROM library_tracks WHERE filename = ?', (name,)
            )
            return cur.rowcount > 0

    def list_filenames(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT filename FROM library_tracks ORDER BY filename'
            ).fetchall()
        return [
            str(row['filename']).replace('\\', '/')
            for row in rows
            if row['filename']
        ]

    def forget(self, spotify_track_id: str) -> None:
        tid = str(spotify_track_id or '').strip()
        if not _SPOTIFY_TRACK_ID.fullmatch(tid):
            return
        with self._connect() as conn:
            conn.execute(
                'DELETE FROM library_tracks WHERE spotify_track_id = ?',
                (tid,),
            )

    def backfill_from_monitor_db(self, monitor_db_path: Path) -> int:
        """Import rows from monitored-playlist history (best-effort, idempotent)."""

        path = Path(monitor_db_path)
        if not path.is_file():
            return 0
        imported = 0
        with sqlite3.connect(str(path)) as src:
            try:
                rows = src.execute(
                    """SELECT track_spotify_id, filename
                       FROM downloaded_tracks
                       WHERE filename IS NOT NULL AND filename != ''"""
                ).fetchall()
            except sqlite3.Error:
                return 0
        for track_id, filename in rows:
            tid = str(track_id or '').strip()
            if not _SPOTIFY_TRACK_ID.fullmatch(tid):
                continue
            before = self.lookup(tid)
            self.register(tid, str(filename))
            if before != str(filename):
                imported += 1
        return imported


def resolve_existing_download(
    downloader: Any,
    song: dict[str, Any],
    *,
    subdir: Optional[str] = None,
    track_index: Optional[TrackIndex] = None,
) -> Optional[tuple[str, str]]:
    """Return ``(relative_filename, skip_message)`` when a file already exists."""

    download_dir = Path(downloader.download_dir)
    slskd_dir = slskd_dir_from_downloader(downloader)

    if track_index is not None:
        tid = normalize_spotify_track_id(song)
        if tid:
            canonical = track_index.lookup(tid)
            if canonical:
                if locate_library_file(canonical, download_dir, slskd_dir):
                    return canonical, 'Already in library'
                track_index.forget(tid)

    local = downloader.existing_filename_for(song, subdir=subdir)
    if local and locate_library_file(local, download_dir, slskd_dir):
        if track_index is not None:
            full = locate_library_file(local, download_dir, slskd_dir)
            track_index.register_song(
                song, local, full_path=full if full is not None else None
            )
        return local, 'Already on disk'

    return None
