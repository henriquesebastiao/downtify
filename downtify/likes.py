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
from collections.abc import Collection, Sequence
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
    """The liked library files, newest like first, per user.

    Each row keeps the file's library path (what the player, the Library
    and M3U files use), a content key so a like can follow the file when
    it is moved (see :func:`remap_moved`), and a snapshot of its title,
    artist and length for the playlist's ``#EXTINF`` lines, so rewriting
    the playlist never has to read every liked file's tags again.

    ``user_id`` ``0`` rows predate per-user likes and belong to the
    admin, like every other ownerless thing. The on-disk liked playlist
    (``LIKED_PLAYLIST_NAME``) is that admin set too - other users' likes
    live in the database (web UI and apps) only, so one user's hearts
    never show up in another user's library folder.
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
            columns = {
                row[1]
                for row in conn.execute('PRAGMA table_info(liked_tracks)')
            }
            if 'user_id' not in columns:
                conn.execute('BEGIN IMMEDIATE')
                try:
                    conn.execute("""
                        CREATE TABLE liked_tracks_new (
                            stored_path TEXT NOT NULL,
                            user_id INTEGER NOT NULL DEFAULT 0,
                            content_key TEXT NOT NULL DEFAULT '',
                            title TEXT NOT NULL DEFAULT '',
                            artist TEXT NOT NULL DEFAULT '',
                            duration REAL NOT NULL DEFAULT 0,
                            liked_at TEXT NOT NULL,
                            PRIMARY KEY (user_id, stored_path)
                        )
                    """)
                    conn.execute("""
                        INSERT INTO liked_tracks_new
                        (stored_path, user_id, content_key, title, artist,
                         duration, liked_at)
                        SELECT stored_path, 0, content_key, title, artist,
                               duration, liked_at
                        FROM liked_tracks ORDER BY rowid
                    """)
                    conn.execute('DROP TABLE liked_tracks')
                    conn.execute(
                        'ALTER TABLE liked_tracks_new RENAME TO liked_tracks'
                    )
                    conn.execute('COMMIT')
                except Exception:
                    conn.execute('ROLLBACK')
                    raise

    def like(
        self,
        stored_path: str,
        *,
        content_key: str = '',
        title: str = '',
        artist: str = '',
        duration: float = 0.0,
        user_id: int = 0,
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
                   (stored_path, user_id, content_key, title, artist,
                    duration, liked_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, stored_path) DO NOTHING""",
                (
                    path,
                    int(user_id or 0),
                    content_key or '',
                    title or '',
                    artist or '',
                    float(duration or 0.0),
                    _now_iso(),
                ),
            )
            return cur.rowcount > 0

    def unlike(self, stored_path: str, user_id: Optional[int] = None) -> bool:
        """Remove a like. ``True`` when there was one.

        With *user_id* only that user's heart goes (a user unliking);
        without it every row for the path goes (the file itself is gone).
        """

        path = _norm(stored_path)
        if not path:
            return False
        with self._connect() as conn:
            if user_id is None:
                cur = conn.execute(
                    'DELETE FROM liked_tracks WHERE stored_path = ?',
                    (path,),
                )
            else:
                cur = conn.execute(
                    'DELETE FROM liked_tracks WHERE stored_path = ? '
                    'AND user_id = ?',
                    (path, int(user_id)),
                )
            return cur.rowcount > 0

    def clear(self, user_id: Optional[int] = None) -> int:
        """Unlike everything (*user_id*'s, or all when ``None``)."""

        with self._connect() as conn:
            if user_id is None:
                return conn.execute('DELETE FROM liked_tracks').rowcount
            cur = conn.execute(
                'DELETE FROM liked_tracks WHERE user_id = ?',
                (int(user_id),),
            )
            return cur.rowcount

    def count(self, user_id: Optional[int] = None) -> int:
        with self._connect() as conn:
            if user_id is None:
                row = conn.execute(
                    'SELECT COUNT(*) AS n FROM liked_tracks'
                ).fetchone()
            else:
                row = conn.execute(
                    'SELECT COUNT(*) AS n FROM liked_tracks WHERE user_id = ?',
                    (int(user_id),),
                ).fetchone()
        return int(row['n'])

    def count_by_user(self) -> dict[int, int]:
        """Likes per account (Settings → Users summary)."""

        with self._connect() as conn:
            rows = conn.execute(
                'SELECT user_id, COUNT(*) AS n FROM liked_tracks '
                'GROUP BY user_id'
            ).fetchall()
        return {int(row['user_id']): int(row['n']) for row in rows}

    def rows(self, user_id: Optional[int] = None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if user_id is None:
                found = conn.execute(
                    """SELECT stored_path, user_id, content_key, title,
                              artist, duration, liked_at
                       FROM liked_tracks
                       ORDER BY liked_at DESC, rowid DESC"""
                ).fetchall()
            else:
                found = conn.execute(
                    """SELECT stored_path, user_id, content_key, title,
                              artist, duration, liked_at
                       FROM liked_tracks
                       WHERE user_id = ?
                       ORDER BY liked_at DESC, rowid DESC""",
                    (int(user_id),),
                ).fetchall()
        return [
            {
                'stored_path': str(row['stored_path']),
                'user_id': int(row['user_id']),
                'content_key': str(row['content_key'] or ''),
                'title': str(row['title'] or ''),
                'artist': str(row['artist'] or ''),
                'duration': float(row['duration'] or 0.0),
                'liked_at': str(row['liked_at']),
            }
            for row in found
        ]

    def paths(self, user_id: Optional[int] = None) -> list[str]:
        return [row['stored_path'] for row in self.rows(user_id)]

    def remove_user(self, user_id: int) -> int:
        """Drop a deleted account's likes; how many went."""

        return self.clear(user_id)

    def reassign_legacy(self, user_id: int) -> int:
        """Give pre-feature rows (``user_id`` ``0``) to *user_id*.

        Runs once on the first start with ownership; later system rows
        keep ``0`` (admins-only), so this must not run again.
        """

        if not user_id:
            return 0
        with self._connect() as conn:
            cur = conn.execute(
                'UPDATE liked_tracks SET user_id = ? WHERE user_id = 0',
                (int(user_id),),
            )
            return cur.rowcount

    def update_path(
        self, old: str, new: str, user_id: Optional[int] = None
    ) -> bool:
        """Point a like at the file's new path, after it moved."""

        old_path, new_path = _norm(old), _norm(new)
        if not old_path or not new_path or old_path == new_path:
            return False
        scope = '' if user_id is None else 'AND user_id = ?'
        args: tuple[Any, ...] = (
            (new_path,) if user_id is None else (new_path, int(user_id))
        )
        with self._connect() as conn:
            if conn.execute(
                'SELECT 1 FROM liked_tracks WHERE stored_path = ? ' + scope,
                args,
            ).fetchone():
                # Already liked there: the old row is just a duplicate.
                conn.execute(
                    'DELETE FROM liked_tracks WHERE stored_path = ? ' + scope,
                    (
                        (old_path,)
                        if user_id is None
                        else (old_path, int(user_id))
                    ),
                )
                return True
            cur = conn.execute(
                'UPDATE liked_tracks SET stored_path = ? '
                'WHERE stored_path = ? ' + scope,
                (
                    (new_path, old_path)
                    if user_id is None
                    else (new_path, old_path, int(user_id))
                ),
            )
            return cur.rowcount > 0


def sync_liked_playlist(
    likes: LikedTracks,
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
    extra_dirs: Optional[Sequence[Path]] = None,
    user_ids: Optional[Collection[int]] = None,
) -> Optional[Path]:
    """Write the liked playlist, or take it away when there is nothing to list.

    The playlist exists exactly while at least one liked file is still on
    disk: with none, the M3U is removed rather than left stale (the
    writer refuses to write an empty one, and would leave the old file
    behind). Returns the M3U's path, or ``None`` when there isn't one.

    A liked file that has gone missing is skipped, not unliked — an
    unmounted drive shouldn't cost anyone their hearts. It comes back the
    next time the playlist is written after the file returns.

    Only *user_ids*' likes are written (``None``: everyone's). The
    on-disk playlist is the shared one, so callers pass the admin set -
    other users' likes never land in the library folder.
    """

    with _SYNC_LOCK:
        rows = likes.rows()
        if user_ids is not None:
            wanted = {int(uid) for uid in user_ids}
            rows = [row for row in rows if row['user_id'] in wanted]
        entries = [
            {
                'filename': row['stored_path'],
                'title': row['title'],
                'artist': row['artist'],
                'duration': row['duration'],
            }
            for row in rows
        ]
        if entries:
            path, _kept = m3u.write_m3u(
                download_dir,
                LIKED_PLAYLIST_NAME,
                entries,
                slskd_dir=slskd_dir,
                extra_dirs=extra_dirs,
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
        if locate_library_file(
            old, ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs
        ):
            continue  # Still where it was: the key just matches a twin.
        if likes.update_path(old, new):
            moved += 1
    if moved:
        logger.info('liked songs: followed {} moved file(s)', moved)
    return moved


def content_key_for(full_path: Path) -> str:
    return file_content_key(full_path) or ''
