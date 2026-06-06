"""Persist Spotify playlist and track metadata in SQLite."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger

from . import spotify
from .sqlite_utils import connect_sqlite
from .track_index import normalize_spotify_track_id

_TRACK_KEYS = (
    'song_id',
    'name',
    'artists',
    'artist',
    'album_name',
    'cover_url',
    'url',
    'duration',
    'year',
    'track_number',
    'album_track_total',
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compact_track(song: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key in _TRACK_KEYS:
        value = song.get(key)
        if value is None or value is False:
            continue
        if isinstance(value, str) and not value:
            continue
        if isinstance(value, list) and not value:
            continue
        row[key] = value
    tid = normalize_spotify_track_id(row)
    if tid:
        row['song_id'] = tid
    return row


class PlaylistSpotifyCache:
    """SQLite store for Spotify playlist membership and track metadata."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spotify_playlist_cache (
                    spotify_playlist_id TEXT PRIMARY KEY,
                    playlist_name TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    tracks_json TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spotify_playlist_tracks (
                    spotify_playlist_id TEXT NOT NULL,
                    track_spotify_id TEXT NOT NULL,
                    track_order INTEGER NOT NULL DEFAULT 0,
                    track_json TEXT NOT NULL,
                    PRIMARY KEY (spotify_playlist_id, track_order)
                )
            """)
            self._migrate_playlist_tracks_table(conn)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_spotify_pl_tracks_track
                ON spotify_playlist_tracks (track_spotify_id)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spotify_track_cache (
                    track_spotify_id TEXT PRIMARY KEY,
                    track_json TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                )
            """)

    @staticmethod
    def _migrate_playlist_tracks_table(conn: sqlite3.Connection) -> None:
        row = conn.execute(
            """SELECT sql FROM sqlite_master
               WHERE type = 'table' AND name = 'spotify_playlist_tracks'"""
        ).fetchone()
        if row is None:
            return
        ddl = str(row['sql'] or '')
        if 'PRIMARY KEY (spotify_playlist_id, track_order)' in ddl:
            return
        conn.executescript("""
            CREATE TABLE spotify_playlist_tracks_new (
                spotify_playlist_id TEXT NOT NULL,
                track_spotify_id TEXT NOT NULL,
                track_order INTEGER NOT NULL DEFAULT 0,
                track_json TEXT NOT NULL,
                PRIMARY KEY (spotify_playlist_id, track_order)
            );
            INSERT OR IGNORE INTO spotify_playlist_tracks_new
                (spotify_playlist_id, track_spotify_id, track_order, track_json)
            SELECT spotify_playlist_id, track_spotify_id, track_order, track_json
            FROM spotify_playlist_tracks;
            DROP TABLE spotify_playlist_tracks;
            ALTER TABLE spotify_playlist_tracks_new
                RENAME TO spotify_playlist_tracks;
        """)

    @staticmethod
    def _track_from_json(raw: Any) -> Optional[dict[str, Any]]:
        if isinstance(raw, dict):
            return dict(raw)
        if not raw:
            return None
        try:
            parsed = json.loads(str(raw))
        except (TypeError, json.JSONDecodeError):
            return None
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _sync_playlist_track_rows(
        conn: sqlite3.Connection,
        spotify_playlist_id: str,
        tracks: list[dict[str, Any]],
    ) -> None:
        sid = str(spotify_playlist_id or '').strip()
        conn.execute(
            'DELETE FROM spotify_playlist_tracks WHERE spotify_playlist_id = ?',
            (sid,),
        )
        for index, track in enumerate(tracks):
            compact = _compact_track(track)
            tid = normalize_spotify_track_id(compact)
            if not tid:
                continue
            conn.execute(
                """INSERT INTO spotify_playlist_tracks
                   (spotify_playlist_id, track_spotify_id, track_order, track_json)
                   VALUES (?, ?, ?, ?)""",
                (
                    sid,
                    tid,
                    int(index),
                    json.dumps(compact, separators=(',', ':')),
                ),
            )

    def get(
        self, spotify_playlist_id: str
    ) -> Optional[tuple[str, list[dict[str, Any]]]]:
        sid = str(spotify_playlist_id or '').strip()
        if not sid:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """SELECT playlist_name, tracks_json
                   FROM spotify_playlist_cache
                   WHERE spotify_playlist_id = ?""",
                (sid,),
            ).fetchone()
        if row is None:
            return None
        try:
            tracks = json.loads(str(row['tracks_json']))
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(tracks, list):
            return None
        return str(row['playlist_name']), tracks

    def list_playlists(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT spotify_playlist_id, playlist_name, fetched_at,
                          (SELECT COUNT(*) FROM spotify_playlist_tracks pt
                           WHERE pt.spotify_playlist_id = c.spotify_playlist_id)
                           AS track_count
                   FROM spotify_playlist_cache c
                   ORDER BY playlist_name"""
            ).fetchall()
        return [
            {
                'spotify_playlist_id': str(row['spotify_playlist_id']),
                'playlist_name': str(row['playlist_name']),
                'fetched_at': str(row['fetched_at']),
                'track_count': int(row['track_count'] or 0),
            }
            for row in rows
        ]

    def get_playlist_track(
        self,
        spotify_playlist_id: str,
        track_spotify_id: str,
    ) -> Optional[dict[str, Any]]:
        sid = str(spotify_playlist_id or '').strip()
        tid = str(track_spotify_id or '').strip()
        if not sid or not tid:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """SELECT track_json FROM spotify_playlist_tracks
                   WHERE spotify_playlist_id = ? AND track_spotify_id = ?""",
                (sid, tid),
            ).fetchone()
        if row is None:
            return None
        return self._track_from_json(row['track_json'])

    def find_track_in_playlists(
        self, track_spotify_id: str
    ) -> Optional[dict[str, Any]]:
        tid = str(track_spotify_id or '').strip()
        if not tid:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """SELECT track_json FROM spotify_playlist_tracks
                   WHERE track_spotify_id = ?
                   ORDER BY track_order ASC LIMIT 1""",
                (tid,),
            ).fetchone()
        if row is None:
            return None
        return self._track_from_json(row['track_json'])

    def playlists_for_track(self, track_spotify_id: str) -> list[str]:
        tid = str(track_spotify_id or '').strip()
        if not tid:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT DISTINCT spotify_playlist_id
                   FROM spotify_playlist_tracks
                   WHERE track_spotify_id = ?
                   ORDER BY spotify_playlist_id""",
                (tid,),
            ).fetchall()
        return [str(row['spotify_playlist_id']) for row in rows]

    def get_cached_track(
        self, track_spotify_id: str
    ) -> Optional[dict[str, Any]]:
        tid = str(track_spotify_id or '').strip()
        if not tid:
            return None
        with self._connect() as conn:
            row = conn.execute(
                'SELECT track_json FROM spotify_track_cache WHERE track_spotify_id = ?',
                (tid,),
            ).fetchone()
        if row is None:
            return None
        return self._track_from_json(row['track_json'])

    @staticmethod
    def _store_track_row(
        conn: sqlite3.Connection,
        track_spotify_id: str,
        track: dict[str, Any],
    ) -> None:
        tid = (
            normalize_spotify_track_id(track)
            or str(track_spotify_id or '').strip()
        )
        if not tid:
            return
        payload = json.dumps(_compact_track(track), separators=(',', ':'))
        conn.execute(
            """INSERT INTO spotify_track_cache
               (track_spotify_id, track_json, fetched_at)
               VALUES (?, ?, ?)
               ON CONFLICT(track_spotify_id) DO UPDATE SET
               track_json=excluded.track_json,
               fetched_at=excluded.fetched_at""",
            (tid, payload, _now_iso()),
        )

    def store_track(
        self, track_spotify_id: str, track: dict[str, Any]
    ) -> None:
        with self._connect() as conn:
            self._store_track_row(conn, track_spotify_id, track)

    def store(
        self,
        spotify_playlist_id: str,
        playlist_name: str,
        tracks: list[dict[str, Any]],
    ) -> None:
        sid = str(spotify_playlist_id or '').strip()
        name = str(playlist_name or '').strip() or sid
        if not sid:
            return
        compact_rows = [_compact_track(track) for track in tracks]
        payload = json.dumps(compact_rows, separators=(',', ':'))
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO spotify_playlist_cache
                   (spotify_playlist_id, playlist_name, fetched_at, tracks_json)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(spotify_playlist_id) DO UPDATE SET
                   playlist_name=excluded.playlist_name,
                   fetched_at=excluded.fetched_at,
                   tracks_json=excluded.tracks_json""",
                (sid, name, _now_iso(), payload),
            )
            self._sync_playlist_track_rows(conn, sid, tracks)
            for track in compact_rows:
                tid = normalize_spotify_track_id(track)
                if tid:
                    self._store_track_row(conn, tid, track)

    def track_count(self, spotify_playlist_id: str) -> int:
        sid = str(spotify_playlist_id or '').strip()
        if not sid:
            return 0
        with self._connect() as conn:
            row = conn.execute(
                """SELECT COUNT(*) AS n FROM spotify_playlist_tracks
                   WHERE spotify_playlist_id = ?""",
                (sid,),
            ).fetchone()
        return int(row['n'] or 0) if row is not None else 0

    def delete_playlist(self, spotify_playlist_id: str) -> None:
        sid = str(spotify_playlist_id or '').strip()
        if not sid:
            return
        with self._connect() as conn:
            conn.execute(
                'DELETE FROM spotify_playlist_tracks WHERE spotify_playlist_id = ?',
                (sid,),
            )
            conn.execute(
                'DELETE FROM spotify_playlist_cache WHERE spotify_playlist_id = ?',
                (sid,),
            )


def fetch_playlist_tracks(
    spotify_playlist_id: str,
    *,
    cache: Optional[PlaylistSpotifyCache] = None,
    refresh: bool = False,
) -> tuple[str, list[dict[str, Any]]]:
    """Return ``(playlist_name, tracks)``, using DB unless *refresh*."""

    sid = str(spotify_playlist_id or '').strip()
    if not sid:
        return '', []
    if cache is not None and not refresh:
        hit = cache.get(sid)
        if hit is not None:
            return hit
    name, tracks = spotify.playlist_info_and_tracks(sid)
    if cache is not None:
        cache.store(sid, name, tracks)
    return name, tracks


def fetch_track_metadata(
    track_spotify_id: str,
    *,
    cache: Optional[PlaylistSpotifyCache] = None,
    playlist_id: Optional[str] = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """Return track metadata from DB when available, else Spotify embed."""

    tid = str(track_spotify_id or '').strip()
    if not tid:
        raise ValueError('track_spotify_id required')

    if cache is not None and not refresh:
        if playlist_id:
            hit = cache.get_playlist_track(playlist_id, tid)
            if hit is not None:
                return hit
        hit = cache.get_cached_track(tid)
        if hit is not None:
            return hit
        hit = cache.find_track_in_playlists(tid)
        if hit is not None:
            return hit

    track = spotify.track_from_id(tid)
    if cache is not None:
        cache.store_track(tid, track)
    return track


async def warm_uncached_playlists(
    cache: PlaylistSpotifyCache,
    spotify_ids: list[str],
    *,
    delay_seconds: float = 1.0,
) -> int:
    """Fetch Spotify playlists missing from *cache* and persist them."""

    warmed = 0
    for raw_id in spotify_ids:
        sid = str(raw_id or '').strip()
        if not sid or cache.get(sid) is not None:
            continue
        try:
            await asyncio.to_thread(
                fetch_playlist_tracks,
                sid,
                cache=cache,
                refresh=True,
            )
            warmed += 1
        except Exception:
            logger.opt(exception=True).warning(
                'Spotify cache warm failed for {}',
                sid,
            )
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
    return warmed


async def playlist_spotify_cache_loop(
    cache: PlaylistSpotifyCache,
    list_spotify_ids: Callable[[], list[str]],
    *,
    delay_seconds: float = 1.0,
    idle_seconds: float = 300.0,
) -> None:
    """Background task: keep known playlists cached from Spotify."""

    while True:
        try:
            ids = list_spotify_ids()
            warmed = await warm_uncached_playlists(
                cache,
                ids,
                delay_seconds=delay_seconds,
            )
            if warmed:
                logger.info('Spotify cache: stored {} playlist(s)', warmed)
        except Exception:
            logger.exception('Spotify playlist cache loop failed')
        await asyncio.sleep(idle_seconds)
