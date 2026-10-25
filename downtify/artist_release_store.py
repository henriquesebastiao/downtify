"""Release-specific progress; a recording may occur on several releases."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Callable


class ArtistReleaseStore:
    def __init__(self, connect: Callable[[], sqlite3.Connection]) -> None:
        self._connect = connect
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS artist_release_tracks (
                playlist_id INTEGER NOT NULL,
                album_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                track_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                PRIMARY KEY (playlist_id, album_id, position),
                FOREIGN KEY (playlist_id) REFERENCES monitored_playlists(id)
                    ON DELETE CASCADE
            )""")
            columns = {
                r['name']
                for r in conn.execute('PRAGMA table_info(seen_albums)')
            }
            if 'last_attempt' not in columns:
                conn.execute(
                    'ALTER TABLE seen_albums ADD COLUMN last_attempt TEXT'
                )

    def tracks(
        self, playlist_id: int, album_id: str
    ) -> dict[tuple[int, str], str]:
        with self._connect() as conn:
            return {
                (r['position'], r['track_id']): r['filename']
                for r in conn.execute(
                    'SELECT position,track_id,filename FROM artist_release_tracks WHERE playlist_id=? AND album_id=?',
                    (playlist_id, album_id),
                )
            }

    def record(
        self,
        playlist_id: int,
        album_id: str,
        position: int,
        track_id: str,
        filename: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO artist_release_tracks VALUES (?,?,?,?,?)
                ON CONFLICT(playlist_id,album_id,position) DO UPDATE SET
                track_id=excluded.track_id,filename=excluded.filename""",
                (playlist_id, album_id, position, track_id, filename),
            )

    def next_release(self, playlist_id: int) -> str | None:
        """One historical release per pass; skipped baselines stay skipped.

        NULL attempts (legacy rows) come first. Attempts advance before
        contacting a provider, so unavailable releases cannot starve others.
        """
        with self._connect() as conn:
            row = conn.execute(
                """SELECT album_id FROM seen_albums
                WHERE playlist_id=? AND skipped=0
                ORDER BY last_attempt, id LIMIT 1""",
                (playlist_id,),
            ).fetchone()
            return row['album_id'] if row else None

    def attempt(self, playlist_id: int, album_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                'UPDATE seen_albums SET last_attempt=? WHERE playlist_id=? AND album_id=?',
                (
                    datetime.now(timezone.utc).isoformat(),
                    playlist_id,
                    album_id,
                ),
            )
