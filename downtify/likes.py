"""Songs the user has liked, and the playlist that lists them.

Liking is a heart on a track in the library. The likes live in
``downtify_library.db`` — on the server, so a heart tapped on a phone is
there on the desktop too — and, as long as there is at least one, they
are also written out as a regular M3U playlist, so the same songs show up
in Downtify's Library and in any media server pointed at the folder.

Two things are easy to get wrong here, and both are handled on purpose:

* The playlist is a plain file next to the ones downloaded playlists
  write, so its name can't be one a downloaded playlist could also have
  (a Spotify playlist called "Liked songs" is common): it would write the
  same file. It gets a reserved name, ``LIKED_PLAYLIST_NAME``.
* Deleting a playlist in Downtify deletes its tracks from disk. Deleting
  *this* one only ever means "unlike everything" — see the guard on
  ``DELETE /api/library/playlist``.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from . import m3u
from .library_cache_keys import file_content_key
from .library_catalog import LibraryContext
from .library_paths import locate_library_file
from .library_reconcile import build_disk_content_index
from .sqlite_utils import connect_sqlite

#: The M3U's name: reserved, so no downloaded playlist can write over it.
LIKED_PLAYLIST_NAME = 'Downtify Liked Songs'

_SYNC_LOCK = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(path: str) -> str:
    return str(path or '').strip().replace('\\', '/')


def is_liked_playlist(name: Any) -> bool:
    """True for the reserved name, however the caller cased or spaced it."""

    return str(name or '').strip().casefold() == LIKED_PLAYLIST_NAME.casefold()


class LikedTracks:
    """The liked library files, newest like first.

    Each row keeps the file's library path (what the player, the Library
    and M3U files use), a content key so a like can follow the file when
    it is moved (see :func:`remap_moved`), and a snapshot of its title,
    artist and length for the playlist's ``#EXTINF`` lines, so rewriting
    the playlist never has to read every liked file's tags again.
    """

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self):
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS liked_tracks (
                    stored_path TEXT PRIMARY KEY,
                    content_key TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    artist TEXT NOT NULL DEFAULT '',
                    duration REAL NOT NULL DEFAULT 0,
                    liked_at TEXT NOT NULL
                )
            """)

    def like(
        self,
        stored_path: str,
        *,
        content_key: str = '',
        title: str = '',
        artist: str = '',
        duration: float = 0.0,
    ) -> bool:
        """Like a file. ``True`` when it wasn't liked yet.

        Liking it again is a no-op that keeps its place in the order, so
        a double tap never moves a song to the top.
        """

        path = _norm(stored_path)
        if not path:
            return False
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO liked_tracks
                   (stored_path, content_key, title, artist, duration,
                    liked_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(stored_path) DO NOTHING""",
                (
                    path,
                    content_key or '',
                    title or '',
                    artist or '',
                    float(duration or 0.0),
                    _now_iso(),
                ),
            )
            return cur.rowcount > 0

    def unlike(self, stored_path: str) -> bool:
        """Remove a like. ``True`` when there was one."""

        with self._connect() as conn:
            cur = conn.execute(
                'DELETE FROM liked_tracks WHERE stored_path = ?',
                (_norm(stored_path),),
            )
            return cur.rowcount > 0

    def clear(self) -> int:
        with self._connect() as conn:
            return conn.execute('DELETE FROM liked_tracks').rowcount

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT COUNT(*) AS n FROM liked_tracks'
            ).fetchone()
        return int(row['n'])

    def rows(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            found = conn.execute(
                """SELECT stored_path, content_key, title, artist, duration,
                          liked_at
                   FROM liked_tracks
                   ORDER BY liked_at DESC, rowid DESC"""
            ).fetchall()
        return [
            {
                'stored_path': str(row['stored_path']),
                'content_key': str(row['content_key'] or ''),
                'title': str(row['title'] or ''),
                'artist': str(row['artist'] or ''),
                'duration': float(row['duration'] or 0.0),
                'liked_at': str(row['liked_at']),
            }
            for row in found
        ]

    def paths(self) -> list[str]:
        return [row['stored_path'] for row in self.rows()]

    def update_path(self, old: str, new: str) -> bool:
        """Point a like at the file's new path, after it moved."""

        old_path, new_path = _norm(old), _norm(new)
        if not old_path or not new_path or old_path == new_path:
            return False
        with self._connect() as conn:
            if conn.execute(
                'SELECT 1 FROM liked_tracks WHERE stored_path = ?',
                (new_path,),
            ).fetchone():
                # Already liked there: the old row is just a duplicate.
                conn.execute(
                    'DELETE FROM liked_tracks WHERE stored_path = ?',
                    (old_path,),
                )
                return True
            cur = conn.execute(
                'UPDATE liked_tracks SET stored_path = ? WHERE stored_path = ?',
                (new_path, old_path),
            )
            return cur.rowcount > 0


def sync_liked_playlist(
    likes: LikedTracks,
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Write the liked playlist, or take it away when there is nothing to list.

    The playlist exists exactly while at least one liked file is still on
    disk: with none, the M3U is removed rather than left stale (the
    writer refuses to write an empty one, and would leave the old file
    behind). Returns the M3U's path, or ``None`` when there isn't one.

    A liked file that has gone missing is skipped, not unliked — an
    unmounted drive shouldn't cost anyone their hearts. It comes back the
    next time the playlist is written after the file returns.
    """

    with _SYNC_LOCK:
        entries = [
            {
                'filename': row['stored_path'],
                'title': row['title'],
                'artist': row['artist'],
                'duration': row['duration'],
            }
            for row in likes.rows()
        ]
        if entries:
            path, _kept = m3u.write_m3u(
                download_dir,
                LIKED_PLAYLIST_NAME,
                entries,
                slskd_dir=slskd_dir,
            )
            if path is not None:
                return path
        stale = m3u.m3u_path_for(download_dir, LIKED_PLAYLIST_NAME)
        try:
            stale.unlink(missing_ok=True)
        except OSError:
            logger.opt(exception=True).warning(
                'Could not remove the liked songs playlist {}', stale
            )
        return None


def remap_moved(likes: LikedTracks, ctx: LibraryContext) -> int:
    """Follow liked files that were moved on disk.

    The same idea as "Fix library paths" for the track index and the
    playlist catalog: a like keeps the file's content key, and a file
    that is gone from its path but turns up elsewhere with the same key
    is the same file. Returns how many likes were repointed.
    """

    rows = [row for row in likes.rows() if row['content_key']]
    if not rows:
        return 0
    disk = build_disk_content_index(ctx)
    if not disk:
        return 0
    moved = 0
    for row in rows:
        old = row['stored_path']
        new = disk.get(row['content_key'])
        if not new or new == old:
            continue
        if locate_library_file(old, ctx.download_dir, ctx.slskd_dir):
            continue  # Still where it was: the key just matches a twin.
        if likes.update_path(old, new):
            moved += 1
    if moved:
        logger.info('liked songs: followed {} moved file(s)', moved)
    return moved


def content_key_for(full_path: Path) -> str:
    return file_content_key(full_path) or ''
