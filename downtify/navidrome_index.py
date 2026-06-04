"""SQLite cache of Navidrome song IDs (resolve once, reuse on playlist sync)."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .library_cache_keys import file_content_key
from .track_index import normalize_spotify_track_id
from .sqlite_utils import connect_sqlite


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_filename(filename: str) -> str:
    return str(filename or '').strip().replace('\\', '/')


class NavidromeIndex:
    """Maps library files (basename+size) and Spotify ids to Navidrome song ids."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name='navidrome_tracks'"
            ).fetchone()
            if row is None:
                conn.execute("""
                    CREATE TABLE navidrome_tracks (
                        content_key TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        navidrome_song_id TEXT NOT NULL,
                        spotify_track_id TEXT,
                        resolved_at TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_navidrome_filename
                    ON navidrome_tracks (filename)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_navidrome_spotify
                    ON navidrome_tracks (spotify_track_id)
                    WHERE spotify_track_id IS NOT NULL
                """)
                return
            if row[0] and 'content_key' in str(row[0]):
                return
            self._migrate_legacy_table(conn)

    @staticmethod
    def _migrate_legacy_table(conn: sqlite3.Connection) -> None:
        conn.execute("""
            CREATE TABLE navidrome_tracks_new (
                content_key TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                navidrome_song_id TEXT NOT NULL,
                spotify_track_id TEXT,
                resolved_at TEXT NOT NULL
            )
        """)
        rows = conn.execute('SELECT * FROM navidrome_tracks').fetchall()
        for row in rows:
            filename = str(row['filename'])
            ck = hashlib.sha256(_norm_filename(filename).encode()).hexdigest()
            conn.execute(
                """INSERT OR REPLACE INTO navidrome_tracks_new
                   (content_key, filename, navidrome_song_id,
                    spotify_track_id, resolved_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    ck,
                    filename,
                    str(row['navidrome_song_id']),
                    row['spotify_track_id'],
                    str(row['resolved_at']),
                ),
            )
        conn.execute('DROP TABLE navidrome_tracks')
        conn.execute(
            'ALTER TABLE navidrome_tracks_new RENAME TO navidrome_tracks'
        )
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_navidrome_filename
            ON navidrome_tracks (filename)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_navidrome_spotify
            ON navidrome_tracks (spotify_track_id)
            WHERE spotify_track_id IS NOT NULL
        """)

    def lookup_filename(self, filename: str) -> Optional[str]:
        name = _norm_filename(filename)
        if not name:
            return None
        with self._connect() as conn:
            row = conn.execute(
                'SELECT navidrome_song_id FROM navidrome_tracks WHERE filename = ?',
                (name,),
            ).fetchone()
        if row is None:
            return None
        return str(row['navidrome_song_id'] or '').strip() or None

    def lookup_file(self, full_path: Path) -> Optional[str]:
        ck = file_content_key(full_path)
        if not ck:
            return None
        with self._connect() as conn:
            row = conn.execute(
                'SELECT navidrome_song_id FROM navidrome_tracks WHERE content_key = ?',
                (ck,),
            ).fetchone()
        if row is None:
            return None
        return str(row['navidrome_song_id'] or '').strip() or None

    def lookup_spotify(self, spotify_track_id: str) -> Optional[str]:
        tid = normalize_spotify_track_id({'song_id': spotify_track_id})
        if not tid:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """SELECT navidrome_song_id FROM navidrome_tracks
                   WHERE spotify_track_id = ?
                   ORDER BY resolved_at DESC LIMIT 1""",
                (tid,),
            ).fetchone()
        if row is None:
            return None
        return str(row['navidrome_song_id'] or '').strip() or None

    def lookup_song(
        self,
        song: dict[str, Any],
        *,
        full_path: Optional[Path] = None,
    ) -> Optional[str]:
        if full_path is not None:
            hit = self.lookup_file(full_path)
            if hit:
                filename = str(song.get('filename') or '').strip()
                if filename:
                    self._touch_filename(full_path, filename)
                return hit
        filename = str(song.get('filename') or '')
        hit = self.lookup_filename(filename)
        if hit:
            return hit
        tid = normalize_spotify_track_id(song)
        if tid:
            return self.lookup_spotify(tid)
        return None

    def store(
        self,
        filename: str,
        navidrome_song_id: str,
        *,
        spotify_track_id: Optional[str] = None,
        full_path: Optional[Path] = None,
    ) -> None:
        name = _norm_filename(filename)
        sid = str(navidrome_song_id or '').strip()
        if not name or not sid:
            return
        ck = file_content_key(full_path) if full_path is not None else None
        if not ck:
            return
        tid = normalize_spotify_track_id(
            {'song_id': spotify_track_id} if spotify_track_id else {}
        )
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO navidrome_tracks
                   (content_key, filename, navidrome_song_id,
                    spotify_track_id, resolved_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(content_key) DO UPDATE SET
                   filename=excluded.filename,
                   navidrome_song_id=excluded.navidrome_song_id,
                   spotify_track_id=excluded.spotify_track_id,
                   resolved_at=excluded.resolved_at""",
                (ck, name, sid, tid, _now_iso()),
            )

    def _touch_filename(self, full_path: Path, filename: str) -> None:
        ck = file_content_key(full_path)
        name = _norm_filename(filename)
        if not ck or not name:
            return
        with self._connect() as conn:
            conn.execute(
                'UPDATE navidrome_tracks SET filename = ? WHERE content_key = ?',
                (name, ck),
            )

    def forget_filename(
        self,
        filename: str,
        *,
        full_path: Optional[Path] = None,
    ) -> None:
        name = _norm_filename(filename)
        if not name:
            return
        with self._connect() as conn:
            conn.execute(
                'DELETE FROM navidrome_tracks WHERE filename = ?', (name,)
            )
            if full_path is not None:
                ck = file_content_key(full_path)
                if ck:
                    conn.execute(
                        'DELETE FROM navidrome_tracks WHERE content_key = ?',
                        (ck,),
                    )
