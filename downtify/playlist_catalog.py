"""Playlist membership catalog (tracks per playlist, survives path moves)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .library_cache_keys import file_content_key
from .library_paths import locate_library_file
from .track_index import normalize_spotify_track_id


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_path(filename: str) -> str:
    return str(filename or '').strip().replace('\\', '/')


def _chunked(values: list[str], size: int):
    for index in range(0, len(values), size):
        chunk = values[index : index + size]
        if chunk:
            yield chunk


class PlaylistCatalog:
    """Maps playlist names to ordered Spotify tracks and library paths."""

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
                CREATE TABLE IF NOT EXISTS playlists (
                    name TEXT PRIMARY KEY,
                    spotify_id TEXT,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playlist_tracks (
                    playlist_name TEXT NOT NULL,
                    track_spotify_id TEXT NOT NULL,
                    content_key TEXT,
                    filename TEXT NOT NULL,
                    track_order INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (playlist_name, track_spotify_id),
                    FOREIGN KEY (playlist_name) REFERENCES playlists(name)
                        ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_playlist_tracks_content_key
                ON playlist_tracks (content_key)
                WHERE content_key IS NOT NULL
            """)

    def ensure_playlist(
        self, name: str, *, spotify_id: Optional[str] = None
    ) -> None:
        pl_name = str(name or '').strip()
        if not pl_name:
            return
        sid = str(spotify_id or '').strip() or None
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO playlists (name, spotify_id, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                   spotify_id=COALESCE(excluded.spotify_id, playlists.spotify_id),
                   updated_at=excluded.updated_at""",
                (pl_name, sid, _now_iso()),
            )

    def upsert_track(
        self,
        playlist_name: str,
        song: dict[str, Any],
        filename: str,
        full_path: Path,
        *,
        track_order: int = 0,
    ) -> None:
        pl_name = str(playlist_name or '').strip()
        tid = normalize_spotify_track_id(song)
        name = _norm_path(filename)
        if not pl_name or not tid or not name:
            return
        ck = file_content_key(full_path)
        self.ensure_playlist(pl_name, spotify_id=None)
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO playlist_tracks
                   (playlist_name, track_spotify_id, content_key, filename, track_order)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(playlist_name, track_spotify_id) DO UPDATE SET
                   content_key=excluded.content_key,
                   filename=excluded.filename,
                   track_order=excluded.track_order""",
                (pl_name, tid, ck, name, int(track_order)),
            )

    def replace_playlist_tracks(
        self,
        playlist_name: str,
        rows: list[tuple[dict[str, Any], str, Path]],
        *,
        spotify_id: Optional[str] = None,
    ) -> None:
        """Replace all tracks for a playlist (batch download)."""

        pl_name = str(playlist_name or '').strip()
        if not pl_name:
            return
        self.ensure_playlist(pl_name, spotify_id=spotify_id)
        with self._connect() as conn:
            conn.execute(
                'DELETE FROM playlist_tracks WHERE playlist_name = ?',
                (pl_name,),
            )
        for index, (song, filename, full_path) in enumerate(rows):
            self.upsert_track(
                pl_name, song, filename, full_path, track_order=index
            )

    def backfill_from_monitor_db(
        self,
        monitor_db_path: Path,
        *,
        download_dir: Path,
        slskd_dir: Optional[Path] = None,
    ) -> int:
        """Import playlist membership from monitor history (older downloads)."""

        path = Path(monitor_db_path)
        if not path.is_file():
            return 0
        try:
            with sqlite3.connect(str(path)) as src:
                rows = src.execute(
                    """SELECT p.name, p.spotify_id, dt.track_spotify_id, dt.filename
                       FROM downloaded_tracks dt
                       JOIN monitored_playlists p ON p.id = dt.playlist_id
                       WHERE dt.filename IS NOT NULL AND dt.filename != ''"""
                ).fetchall()
        except sqlite3.Error:
            return 0

        linked = 0
        for row in rows:
            pl_name = str(row[0] or '').strip()
            spotify_id = str(row[1] or '').strip() or None
            tid = str(row[2] or '').strip()
            filename = _norm_path(str(row[3] or ''))
            if not pl_name or not tid or not filename:
                continue
            full = locate_library_file(filename, download_dir, slskd_dir)
            if full is None:
                continue
            self.ensure_playlist(pl_name, spotify_id=spotify_id)
            self.upsert_track(pl_name, {'song_id': tid}, filename, full)
            linked += 1
        return linked

    def list_playlist_names(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT name FROM playlists ORDER BY name'
            ).fetchall()
        return [str(row['name']) for row in rows]

    def list_tracks(self, playlist_name: str) -> list[dict[str, Any]]:
        pl_name = str(playlist_name or '').strip()
        if not pl_name:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT track_spotify_id, content_key, filename, track_order
                   FROM playlist_tracks
                   WHERE playlist_name = ?
                   ORDER BY track_order ASC, track_spotify_id ASC""",
                (pl_name,),
            ).fetchall()
        return [
            {
                'track_spotify_id': str(row['track_spotify_id']),
                'content_key': row['content_key'],
                'filename': _norm_path(str(row['filename'])),
                'track_order': int(row['track_order']),
            }
            for row in rows
        ]

    def spotify_id_for_playlist(self, playlist_name: str) -> Optional[str]:
        pl_name = str(playlist_name or '').strip()
        if not pl_name:
            return None
        with self._connect() as conn:
            row = conn.execute(
                'SELECT spotify_id FROM playlists WHERE name = ?',
                (pl_name,),
            ).fetchone()
        if row is None or not row['spotify_id']:
            return None
        return str(row['spotify_id'])

    def update_filename_by_content_key(
        self, content_key: str, filename: str
    ) -> list[str]:
        """Update rows for *content_key*; return affected playlist names."""

        ck = str(content_key or '').strip()
        name = _norm_path(filename)
        if not ck or not name:
            return []
        with self._connect() as conn:
            conn.execute(
                """UPDATE playlist_tracks SET filename = ?
                   WHERE content_key = ? AND filename != ?""",
                (name, ck, name),
            )
            rows = conn.execute(
                """SELECT DISTINCT playlist_name FROM playlist_tracks
                   WHERE content_key = ?""",
                (ck,),
            ).fetchall()
        return [str(row['playlist_name']) for row in rows]

    def playlists_by_content_keys(
        self, content_keys: list[str]
    ) -> dict[str, list[str]]:
        keys = [str(k).strip() for k in content_keys if str(k).strip()]
        if not keys:
            return {}
        result: dict[str, list[str]] = {k: [] for k in keys}
        with self._connect() as conn:
            for chunk in _chunked(keys, 400):
                placeholders = ','.join('?' * len(chunk))
                rows = conn.execute(
                    f"""SELECT content_key, playlist_name FROM playlist_tracks
                        WHERE content_key IN ({placeholders})
                        ORDER BY playlist_name""",
                    chunk,
                ).fetchall()
                for row in rows:
                    ck = str(row['content_key'])
                    pl = str(row['playlist_name'])
                    if pl not in result[ck]:
                        result[ck].append(pl)
        return result

    def playlists_by_filenames(
        self, filenames: list[str]
    ) -> dict[str, list[str]]:
        names = [_norm_path(n) for n in filenames if _norm_path(n)]
        if not names:
            return {}
        result: dict[str, list[str]] = {n: [] for n in names}
        with self._connect() as conn:
            for chunk in _chunked(names, 400):
                placeholders = ','.join('?' * len(chunk))
                rows = conn.execute(
                    f"""SELECT filename, playlist_name FROM playlist_tracks
                        WHERE filename IN ({placeholders})
                        ORDER BY playlist_name""",
                    chunk,
                ).fetchall()
                for row in rows:
                    fn = _norm_path(str(row['filename']))
                    pl = str(row['playlist_name'])
                    if pl not in result[fn]:
                        result[fn].append(pl)
        return result

    def set_content_key(
        self,
        playlist_name: str,
        track_spotify_id: str,
        content_key: str,
    ) -> None:
        pl_name = str(playlist_name or '').strip()
        tid = str(track_spotify_id or '').strip()
        ck = str(content_key or '').strip()
        if not pl_name or not tid or not ck:
            return
        with self._connect() as conn:
            conn.execute(
                """UPDATE playlist_tracks SET content_key = ?
                   WHERE playlist_name = ? AND track_spotify_id = ?""",
                (ck, pl_name, tid),
            )

    def remove_track(self, playlist_name: str, track_spotify_id: str) -> bool:
        pl_name = str(playlist_name or '').strip()
        tid = str(track_spotify_id or '').strip()
        if not pl_name or not tid:
            return False
        with self._connect() as conn:
            cur = conn.execute(
                """DELETE FROM playlist_tracks
                   WHERE playlist_name = ? AND track_spotify_id = ?""",
                (pl_name, tid),
            )
            return cur.rowcount > 0

    def remove_tracks_for_filename(self, filename: str) -> list[str]:
        """Delete rows pointing at *filename*; return affected playlist names."""

        name = _norm_path(filename)
        if not name:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT DISTINCT playlist_name FROM playlist_tracks
                   WHERE filename = ?""",
                (name,),
            ).fetchall()
            conn.execute(
                'DELETE FROM playlist_tracks WHERE filename = ?', (name,)
            )
        return [str(row['playlist_name']) for row in rows]

    def all_track_rows(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT playlist_name, track_spotify_id, content_key, filename
                   FROM playlist_tracks"""
            ).fetchall()
        return [
            {
                'playlist_name': str(row['playlist_name']),
                'track_spotify_id': str(row['track_spotify_id']),
                'content_key': row['content_key'],
                'filename': _norm_path(str(row['filename'])),
            }
            for row in rows
        ]
