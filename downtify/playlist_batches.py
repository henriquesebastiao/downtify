"""Persistent playlist batch jobs and completeness vs the library."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .library_paths import locate_library_file, slskd_dir_from_downloader
from .sqlite_utils import connect_sqlite
from .track_index import normalize_spotify_track_id, resolve_existing_download

_BATCH_STATUSES = frozenset({'in_progress', 'incomplete', 'complete'})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PlaylistBatchStore:
    """SQLite store for playlist download batches under ``/data``."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playlist_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spotify_playlist_id TEXT NOT NULL,
                    playlist_name TEXT NOT NULL,
                    playlist_url TEXT NOT NULL,
                    expected_count INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL DEFAULT 'in_progress',
                    succeeded_count INTEGER NOT NULL DEFAULT 0,
                    failed_count INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_playlist_batches_spotify
                ON playlist_batches (spotify_playlist_id, id DESC)
            """)

    def start_batch(
        self,
        spotify_playlist_id: str,
        playlist_name: str,
        playlist_url: str,
        expected_count: int,
    ) -> int:
        sid = str(spotify_playlist_id or '').strip()
        name = str(playlist_name or '').strip() or sid
        url = str(playlist_url or '').strip()
        expected = max(int(expected_count), 0)
        if not sid or not url:
            raise ValueError(
                'spotify_playlist_id and playlist_url are required'
            )
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO playlist_batches
                   (spotify_playlist_id, playlist_name, playlist_url,
                    expected_count, started_at, status)
                   VALUES (?, ?, ?, ?, ?, 'in_progress')""",
                (sid, name, url, expected, _now_iso()),
            )
            return int(cur.lastrowid)

    def update_batch_name(self, batch_id: int, playlist_name: str) -> None:
        name = str(playlist_name or '').strip()
        if not name:
            return
        with self._connect() as conn:
            conn.execute(
                """UPDATE playlist_batches SET playlist_name = ?
                   WHERE id = ?""",
                (name, int(batch_id)),
            )

    def finish_batch(
        self,
        batch_id: int,
        succeeded_count: int,
        failed_count: int,
        *,
        status: str,
    ) -> None:
        st = str(status or '').strip().lower()
        if st not in _BATCH_STATUSES:
            raise ValueError(f'invalid batch status: {status!r}')
        with self._connect() as conn:
            conn.execute(
                """UPDATE playlist_batches SET
                   succeeded_count = ?,
                   failed_count = ?,
                   status = ?,
                   finished_at = ?
                   WHERE id = ?""",
                (
                    max(int(succeeded_count), 0),
                    max(int(failed_count), 0),
                    st,
                    _now_iso(),
                    int(batch_id),
                ),
            )

    def mark_complete(self, batch_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """UPDATE playlist_batches SET
                   status = 'complete',
                   finished_at = COALESCE(finished_at, ?)
                   WHERE id = ?""",
                (_now_iso(), int(batch_id)),
            )

    def list_open_batches(self) -> list[dict[str, Any]]:
        """Latest open batch row per Spotify playlist id."""

        with self._connect() as conn:
            rows = conn.execute(
                """SELECT b.*
                   FROM playlist_batches b
                   INNER JOIN (
                       SELECT spotify_playlist_id, MAX(id) AS max_id
                       FROM playlist_batches
                       WHERE status IN ('in_progress', 'incomplete')
                       GROUP BY spotify_playlist_id
                   ) latest ON b.id = latest.max_id
                   ORDER BY b.started_at DESC"""
            ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def list_latest_batches(self) -> list[dict[str, Any]]:
        """Latest batch row per Spotify playlist id (any status)."""

        with self._connect() as conn:
            rows = conn.execute(
                """SELECT b.*
                   FROM playlist_batches b
                   INNER JOIN (
                       SELECT spotify_playlist_id, MAX(id) AS max_id
                       FROM playlist_batches
                       GROUP BY spotify_playlist_id
                   ) latest ON b.id = latest.max_id
                   ORDER BY b.started_at DESC"""
            ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def get_batch(self, batch_id: int) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM playlist_batches WHERE id = ?',
                (int(batch_id),),
            ).fetchone()
        if row is None:
            return None
        return _row_to_dict(row)

    def delete_for_spotify_playlist(self, spotify_playlist_id: str) -> int:
        sid = str(spotify_playlist_id or '').strip()
        if not sid:
            return 0
        with self._connect() as conn:
            cur = conn.execute(
                'DELETE FROM playlist_batches WHERE spotify_playlist_id = ?',
                (sid,),
            )
        return int(cur.rowcount or 0)


def ensure_batch_records(
    store: PlaylistBatchStore,
    playlists: list[dict[str, Any]],
) -> int:
    """Register batch rows for known Spotify playlists not yet tracked."""

    existing = {b['spotify_playlist_id'] for b in store.list_latest_batches()}
    created = 0
    for row in playlists:
        sid = str(row.get('spotify_id') or '').strip()
        if not sid or sid in existing:
            continue
        name = str(row.get('name') or sid).strip() or sid
        url = str(row.get('url') or f'https://open.spotify.com/playlist/{sid}')
        expected = int(row.get('track_count') or row.get('expected') or 0)
        if expected <= 0:
            expected = 1
        batch_id = store.start_batch(sid, name, url, expected)
        store.finish_batch(batch_id, 0, 0, status='incomplete')
        existing.add(sid)
        created += 1
    return created


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        'id': int(row['id']),
        'spotify_playlist_id': str(row['spotify_playlist_id']),
        'playlist_name': str(row['playlist_name']),
        'playlist_url': str(row['playlist_url']),
        'expected_count': int(row['expected_count']),
        'started_at': str(row['started_at']),
        'finished_at': row['finished_at'],
        'status': str(row['status']),
        'succeeded_count': int(row['succeeded_count']),
        'failed_count': int(row['failed_count']),
    }


def split_tracks_by_library(
    tracks: list[dict[str, Any]],
    *,
    downloader: Any,
    track_index: Any,
    subdir: Optional[str] = None,
    catalog_filenames: Optional[dict[str, str]] = None,
) -> tuple[int, list[dict[str, Any]]]:
    """Return ``(downloaded_count, missing_tracks)`` for *tracks*."""

    download_dir = Path(downloader.download_dir)
    slskd_dir = slskd_dir_from_downloader(downloader)
    downloaded = 0
    missing: list[dict[str, Any]] = []
    for track in tracks:
        if not track.get('song_id') and not normalize_spotify_track_id(track):
            continue
        hit = resolve_existing_download(
            downloader,
            track,
            subdir=subdir,
            track_index=track_index,
        )
        if hit:
            downloaded += 1
            continue
        tid = normalize_spotify_track_id(track)
        if tid and catalog_filenames:
            filename = str(catalog_filenames.get(tid) or '').strip()
            if filename and locate_library_file(
                filename, download_dir, slskd_dir
            ):
                downloaded += 1
                continue
        missing.append(track)
    return downloaded, missing


def active_queue_count_for_playlist(
    spotify_playlist_id: str,
    download_jobs: dict[str, dict[str, Any]],
) -> int:
    """Count in-flight queue jobs tied to a Spotify playlist id."""

    sid = str(spotify_playlist_id or '').strip()
    if not sid:
        return 0
    needle = f'/playlist/{sid}'
    count = 0
    for job in download_jobs.values():
        status = str(job.get('status') or '')
        if status in {'done', 'error'}:
            continue
        song = job.get('song') or {}
        pl_url = str(song.get('downtify_playlist_url') or '')
        if needle in pl_url:
            count += 1
    return count
