"""The library as a mobile app syncs it: stable track ids and a change feed.

A phone keeps its own copy of the library (to browse offline, and to
remember offline files, likes, play history and a queue), so it needs to
recognise a track across time. The file path isn't enough - files move
when *Organize by artist/album* changes or a playlist folder is renamed,
and get renamed when the output template changes - so each track gets a
**track id** of its own the first time it's seen, and keeps it:

1. same path as before -> same id (a re-tag in place keeps its id, even
   though the file's size changes);
2. a new path, when a track that was there before has vanished: the same
   id if exactly one vanished track has the same file name and size (a
   move), or else the same title/artist/album/length (a rename);
3. anything else is a new track with a new id. A file both moved *and*
   re-tagged in the same sweep comes back as a new track; the old id is
   reported deleted.

The feed: every change - a track added, changed (tags, cover, file) or
removed - bumps a single sequence number, and a client asks
``GET /api/v1/library?since=<cursor>`` for everything after the cursor
it last saw. Removed tracks are remembered (as ids) for
:data:`TOMBSTONE_DAYS` days; a client whose cursor is older than that
gets a full list back (``full: true``) and replaces what it has.

Albums and artists aren't stored: a row carries the keys the web app
groups by (``album_id``, ``artist_id``), so a client groups exactly the
same way without reimplementing the rules.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from . import library_metadata
from .library_cache_keys import file_content_key_from_name_and_size
from .sqlite_utils import connect_sqlite

#: How long a removed track's id is kept for clients to hear about it.
TOMBSTONE_DAYS = 90

#: The fields of a library row a client gets (besides ``id``).
ROW_FIELDS = (
    'file',
    'title',
    'artist',
    'artists',
    'album',
    'album_artist',
    'album_id',
    'artist_id',
    'track_number',
    'year',
    'duration',
    'codec',
    'bitrate',
    'sample_rate',
    'channels',
    'size',
    'added',
    'has_cover',
    'playlists',
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def split_artists(artist: str, album_artist: str = '') -> list[str]:
    """The artists in a tag's artist string - the web app's own rule
    (``frontend/src/lib/library.js``): split on the first of ``;``,
    `` / `` or ``, `` it contains, unless it is the album artist too (see
    :func:`downtify.library_metadata.split_artists`)."""

    return library_metadata.split_artists(artist, album_artist)


def row_artists(row: dict[str, Any]) -> list[str]:
    """Every credited artist of a ``/tracks`` row: its ``artists`` (read
    from the ARTISTS tag when the file has one), else its artist text
    split by :func:`split_artists`."""

    artists = row.get('artists')
    if isinstance(artists, list):
        names = [str(name).strip() for name in artists if str(name).strip()]
        if names:
            return names
    return split_artists(
        row.get('artist', ''), str(row.get('album_artist') or '')
    )


def _short_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def grouping_keys(row: dict[str, Any]) -> dict[str, str]:
    """``album_artist`` as the web app shows it (the tag, else the first
    artist), and the ids it groups albums and artists by: ``album_id``
    (album artist + album title, case-insensitive; ``''`` when the track
    has no album) and ``artist_id`` (the album artist)."""

    artists = row_artists(row)
    album_artist = str(row.get('album_artist') or '').strip() or (
        artists[0] if artists else ''
    )
    album = str(row.get('album') or '').strip()
    return {
        'album_artist': album_artist,
        'album_id': (
            _short_hash(json.dumps([album_artist.lower(), album.lower()]))
            if album
            else ''
        ),
        'artist_id': _short_hash(album_artist.lower()) if album_artist else '',
    }


def public_row(entry: dict[str, Any]) -> dict[str, Any]:
    """A ``/tracks`` entry as a sync row (without its id)."""

    row = {
        'file': str(entry.get('file') or ''),
        'title': str(entry.get('title') or ''),
        'artist': str(entry.get('artist') or ''),
        'artists': row_artists(entry),
        'album': str(entry.get('album') or ''),
        'track_number': int(entry.get('track_number') or 0),
        'year': str(entry.get('year') or ''),
        'duration': float(entry.get('duration') or 0.0),
        'codec': str(entry.get('codec') or ''),
        'bitrate': int(entry.get('bitrate') or 0),
        'sample_rate': int(entry.get('sample_rate') or 0),
        'channels': int(entry.get('channels') or 0),
        'size': int(entry.get('size') or 0),
        'added': int(entry.get('added') or 0),
        'has_cover': bool(entry.get('has_cover')),
        'playlists': sorted(entry.get('playlists') or []),
    }
    row.update(grouping_keys(entry))
    return {key: row[key] for key in ROW_FIELDS}


def _row_hash(row: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()


def _content_key(row: dict[str, Any]) -> str:
    return (
        file_content_key_from_name_and_size(row['file'], int(row['size']))
        or ''
    )


def _tag_key(row: dict[str, Any]) -> str:
    """Title, artist, album and length: what identifies a song whose file
    was renamed (and whose name and size no longer match)."""

    if not row['title']:
        return ''
    return '\n'.join([
        row['title'].casefold(),
        row['artist'].casefold(),
        row['album'].casefold(),
        str(round(float(row['duration']))),
    ])


def new_track_id() -> str:
    return 't' + secrets.token_hex(8)


class LibrarySync:
    """Track ids and the change feed, in ``downtify_library.db``."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self):
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_tracks (
                    track_id TEXT PRIMARY KEY,
                    path TEXT,
                    content_key TEXT NOT NULL DEFAULT '',
                    tag_key TEXT NOT NULL DEFAULT '',
                    row_json TEXT NOT NULL DEFAULT '{}',
                    row_hash TEXT NOT NULL DEFAULT '',
                    seq INTEGER NOT NULL,
                    deleted_at TEXT
                )
            """)
            conn.execute(
                'CREATE UNIQUE INDEX IF NOT EXISTS idx_sync_tracks_path '
                'ON sync_tracks (path) WHERE path IS NOT NULL'
            )
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_sync_tracks_seq '
                'ON sync_tracks (seq)'
            )
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_meta (
                    key TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                )
            """)

    @staticmethod
    def _meta(conn, key: str) -> int:
        row = conn.execute(
            'SELECT value FROM sync_meta WHERE key = ?', (key,)
        ).fetchone()
        return int(row['value']) if row else 0

    @staticmethod
    def _set_meta(conn, key: str, value: int) -> None:
        conn.execute(
            """INSERT INTO sync_meta (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, value),
        )

    # Reconciling with what's on disk

    def refresh(
        self, entries: Iterable[dict[str, Any]], now: Optional[datetime] = None
    ) -> int:
        """Bring the ids and the feed in line with *entries* (the rows of
        ``GET /tracks``, i.e. the whole library as it is now). Returns the
        current cursor."""

        now = now or _now()
        rows = {}
        for entry in entries:
            row = public_row(entry)
            if row['file']:
                rows[row['file']] = row
        with self._lock, self._connect() as conn:
            seq = self._meta(conn, 'seq')
            live = {
                r['path']: r
                for r in conn.execute(
                    'SELECT track_id, path, content_key, tag_key, row_hash '
                    'FROM sync_tracks WHERE deleted_at IS NULL'
                ).fetchall()
            }
            vanished = {
                path: r for path, r in live.items() if path not in rows
            }
            by_content: dict[str, list[str]] = {}
            by_tags: dict[str, list[str]] = {}
            for path, r in vanished.items():
                if r['content_key']:
                    by_content.setdefault(r['content_key'], []).append(path)
                if r['tag_key']:
                    by_tags.setdefault(r['tag_key'], []).append(path)

            def claim(index: dict[str, list[str]], key: str) -> str:
                paths = [p for p in index.get(key, []) if p in vanished]
                if key and len(paths) == 1:
                    return paths[0]
                return ''

            for path, row in rows.items():
                content_key = _content_key(row)
                tag_key = _tag_key(row)
                digest = _row_hash(row)
                known = live.get(path)
                if known is not None:
                    if known['row_hash'] == digest:
                        continue
                    seq += 1
                    conn.execute(
                        'UPDATE sync_tracks SET content_key = ?, tag_key = ?, '
                        'row_json = ?, row_hash = ?, seq = ? '
                        'WHERE track_id = ?',
                        (
                            content_key,
                            tag_key,
                            json.dumps(row),
                            digest,
                            seq,
                            known['track_id'],
                        ),
                    )
                    continue
                old_path = claim(by_content, content_key) or claim(
                    by_tags, tag_key
                )
                seq += 1
                if old_path:
                    moved = vanished.pop(old_path)
                    conn.execute(
                        'UPDATE sync_tracks SET path = ?, content_key = ?, '
                        'tag_key = ?, row_json = ?, row_hash = ?, seq = ? '
                        'WHERE track_id = ?',
                        (
                            path,
                            content_key,
                            tag_key,
                            json.dumps(row),
                            digest,
                            seq,
                            moved['track_id'],
                        ),
                    )
                    continue
                conn.execute(
                    'INSERT INTO sync_tracks (track_id, path, content_key, '
                    'tag_key, row_json, row_hash, seq) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (
                        new_track_id(),
                        path,
                        content_key,
                        tag_key,
                        json.dumps(row),
                        digest,
                        seq,
                    ),
                )

            for gone in vanished.values():
                seq += 1
                conn.execute(
                    'UPDATE sync_tracks SET path = NULL, deleted_at = ?, '
                    "seq = ?, row_json = '{}' WHERE track_id = ?",
                    (now.isoformat(), seq, gone['track_id']),
                )

            self._purge(conn, now)
            self._set_meta(conn, 'seq', seq)
        return seq

    def _purge(self, conn, now: datetime) -> None:
        """Forget removed tracks older than :data:`TOMBSTONE_DAYS`; a
        client whose cursor predates them then needs a full sync."""

        cutoff = (now - timedelta(days=TOMBSTONE_DAYS)).isoformat()
        rows = conn.execute(
            'SELECT MAX(seq) AS seq FROM sync_tracks '
            'WHERE deleted_at IS NOT NULL AND deleted_at < ?',
            (cutoff,),
        ).fetchone()
        if rows and rows['seq'] is not None:
            conn.execute(
                'DELETE FROM sync_tracks '
                'WHERE deleted_at IS NOT NULL AND deleted_at < ?',
                (cutoff,),
            )
            floor = max(self._meta(conn, 'floor'), int(rows['seq']))
            self._set_meta(conn, 'floor', floor)

    # Reading the feed

    def cursor(self) -> int:
        with self._connect() as conn:
            return self._meta(conn, 'seq')

    def changes(self, since: int = 0) -> dict[str, Any]:
        """``{cursor, full, tracks, deleted}`` after *since*.

        ``full`` is ``True`` for *since* ``0`` (or older than what's
        remembered): ``tracks`` is then the whole library and the client
        should drop anything it has that isn't in it.
        """

        with self._connect() as conn:
            cursor = self._meta(conn, 'seq')
            floor = self._meta(conn, 'floor')
            full = since <= 0 or since < floor or since > cursor
            if full:
                live = conn.execute(
                    'SELECT track_id, row_json FROM sync_tracks '
                    'WHERE deleted_at IS NULL ORDER BY path'
                ).fetchall()
                deleted: list[str] = []
            else:
                live = conn.execute(
                    'SELECT track_id, row_json FROM sync_tracks '
                    'WHERE deleted_at IS NULL AND seq > ? ORDER BY seq',
                    (since,),
                ).fetchall()
                deleted = [
                    r['track_id']
                    for r in conn.execute(
                        'SELECT track_id FROM sync_tracks '
                        'WHERE deleted_at IS NOT NULL AND seq > ? '
                        'ORDER BY seq',
                        (since,),
                    ).fetchall()
                ]
        tracks = [
            {'id': r['track_id'], **json.loads(r['row_json'])} for r in live
        ]
        return {
            'cursor': cursor,
            'full': full,
            'tracks': tracks,
            'deleted': deleted,
        }

    # Lookups

    def path_for(self, track_id: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT path FROM sync_tracks WHERE track_id = ? '
                'AND deleted_at IS NULL',
                (track_id,),
            ).fetchone()
        return row['path'] if row else None

    def row_for(self, track_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT track_id, row_json FROM sync_tracks '
                'WHERE track_id = ? AND deleted_at IS NULL',
                (track_id,),
            ).fetchone()
        if row is None:
            return None
        return {'id': row['track_id'], **json.loads(row['row_json'])}

    def ids_for_paths(self, paths: Iterable[str]) -> dict[str, str]:
        """``{path: track_id}`` for the paths that are known."""

        wanted = [p for p in paths if p]
        found: dict[str, str] = {}
        with self._connect() as conn:
            for start in range(0, len(wanted), 500):
                chunk = wanted[start : start + 500]
                marks = ','.join('?' * len(chunk))
                for row in conn.execute(
                    f'SELECT track_id, path FROM sync_tracks '
                    f'WHERE deleted_at IS NULL AND path IN ({marks})',
                    chunk,
                ).fetchall():
                    found[row['path']] = row['track_id']
        return found
