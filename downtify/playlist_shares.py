"""Who besides its owner may see a playlist (view-only).

Every playlist is private to its owner (and admins) until the owner
shares it: with named users (``shared``) or with everyone on the server
(``public``). A viewer can play it, follow a public one so it stays in
their sidebar, and save a copy - never edit it. The owner is whoever the
playlist catalog or the Library-playlist owners table says (see
``downtify.playlist_catalog``); this module only records the sharing, by
casefolded playlist name like those tables.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .sqlite_utils import connect_sqlite

PRIVATE = 'private'
SHARED = 'shared'
PUBLIC = 'public'
VISIBILITIES = (PRIVATE, SHARED, PUBLIC)


def share_key(name: str) -> str:
    return str(name or '').strip().casefold()


@dataclass(frozen=True)
class ShareView:
    """What one user is shown of other people's playlists."""

    #: Casefolded names of every public playlist.
    public: frozenset[str] = frozenset()
    #: ``{name: seen}`` for playlists shared with this user by name.
    to_me: dict[str, bool] = field(default_factory=dict)
    #: Public playlists this user follows.
    followed: frozenset[str] = frozenset()


class PlaylistShares:
    """Visibility, the share list and follows, in the library database."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playlist_shares (
                    name_key TEXT PRIMARY KEY,
                    visibility TEXT NOT NULL DEFAULT 'private'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playlist_share_users (
                    name_key TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    seen INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (name_key, user_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playlist_follows (
                    user_id INTEGER NOT NULL,
                    name_key TEXT NOT NULL,
                    PRIMARY KEY (user_id, name_key)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playlist_display_names (
                    identity TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL
                )
            """)

    def display_names(self) -> dict[str, str]:
        with self._connect() as conn:
            return {
                str(row['identity']): str(row['display_name'])
                for row in conn.execute('SELECT * FROM playlist_display_names')
            }

    def set_display_name(self, identity: str, display_name: str) -> None:
        with self._connect() as conn:
            if display_name:
                conn.execute(
                    'INSERT INTO playlist_display_names (identity, display_name) '
                    'VALUES (?, ?) ON CONFLICT(identity) DO UPDATE SET '
                    'display_name = excluded.display_name',
                    (identity, display_name),
                )
            else:
                conn.execute(
                    'DELETE FROM playlist_display_names WHERE identity = ?',
                    (identity,),
                )

    # Reading

    def visibility(self, name: str) -> str:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT visibility FROM playlist_shares WHERE name_key = ?',
                (share_key(name),),
            ).fetchone()
        return row['visibility'] if row else PRIVATE

    def visibility_map(self) -> dict[str, str]:
        """``{name key: visibility}`` for playlists that aren't private."""

        with self._connect() as conn:
            rows = conn.execute(
                'SELECT name_key, visibility FROM playlist_shares '
                'WHERE visibility != ?',
                (PRIVATE,),
            ).fetchall()
        return {str(row['name_key']): str(row['visibility']) for row in rows}

    def shared_users(self) -> dict[str, list[int]]:
        """``{name key: [user ids]}`` for playlists shared by name."""

        with self._connect() as conn:
            rows = conn.execute(
                'SELECT name_key, user_id FROM playlist_share_users '
                'ORDER BY user_id'
            ).fetchall()
        shared: dict[str, list[int]] = {}
        for row in rows:
            shared.setdefault(str(row['name_key']), []).append(
                int(row['user_id'])
            )
        return shared

    def view_for(self, user_id: int) -> ShareView:
        """Public playlists, those shared with *user_id*, and the public
        ones they follow (a playlist that stopped being public is no
        longer followed)."""

        with self._connect() as conn:
            public = {
                str(row['name_key'])
                for row in conn.execute(
                    'SELECT name_key FROM playlist_shares '
                    'WHERE visibility = ?',
                    (PUBLIC,),
                )
            }
            shared = {
                str(row['name_key']): bool(row['seen'])
                for row in conn.execute(
                    'SELECT u.name_key, u.seen FROM playlist_share_users u '
                    'JOIN playlist_shares s ON s.name_key = u.name_key '
                    'WHERE u.user_id = ? AND s.visibility = ?',
                    (int(user_id), SHARED),
                )
            }
            followed = {
                str(row['name_key'])
                for row in conn.execute(
                    'SELECT name_key FROM playlist_follows WHERE user_id = ?',
                    (int(user_id),),
                )
            }
        return ShareView(
            frozenset(public), shared, frozenset(followed & public)
        )

    # Changing

    def set_visibility(
        self, name: str, visibility: str, user_ids: Iterable[int] = ()
    ) -> None:
        """Make *name* ``private``, ``public`` or ``shared`` with exactly
        *user_ids*. Users already on the list keep whether they opened it;
        anyone new has not. Following only makes sense while public."""

        key = share_key(name)
        if not key or visibility not in VISIBILITIES:
            raise ValueError('Unknown visibility')
        wanted = (
            {int(uid) for uid in user_ids if int(uid) > 0}
            if visibility == SHARED
            else set()
        )
        with self._connect() as conn:
            if visibility == PRIVATE:
                conn.execute(
                    'DELETE FROM playlist_shares WHERE name_key = ?', (key,)
                )
            else:
                conn.execute(
                    'INSERT INTO playlist_shares (name_key, visibility) '
                    'VALUES (?, ?) ON CONFLICT(name_key) DO UPDATE SET '
                    'visibility = excluded.visibility',
                    (key, visibility),
                )
            have = {
                int(row['user_id'])
                for row in conn.execute(
                    'SELECT user_id FROM playlist_share_users '
                    'WHERE name_key = ?',
                    (key,),
                )
            }
            for uid in have - wanted:
                conn.execute(
                    'DELETE FROM playlist_share_users '
                    'WHERE name_key = ? AND user_id = ?',
                    (key, uid),
                )
            for uid in wanted - have:
                conn.execute(
                    'INSERT INTO playlist_share_users '
                    '(name_key, user_id, seen) VALUES (?, ?, 0)',
                    (key, uid),
                )
            if visibility != PUBLIC:
                conn.execute(
                    'DELETE FROM playlist_follows WHERE name_key = ?', (key,)
                )

    def follow(self, user_id: int, name: str, followed: bool = True) -> None:
        key = share_key(name)
        if not key or not user_id:
            return
        with self._connect() as conn:
            if followed:
                conn.execute(
                    'INSERT OR IGNORE INTO playlist_follows '
                    '(user_id, name_key) VALUES (?, ?)',
                    (int(user_id), key),
                )
            else:
                conn.execute(
                    'DELETE FROM playlist_follows '
                    'WHERE user_id = ? AND name_key = ?',
                    (int(user_id), key),
                )

    def mark_seen(self, name: str, user_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                'UPDATE playlist_share_users SET seen = 1 '
                'WHERE name_key = ? AND user_id = ?',
                (share_key(name), int(user_id)),
            )

    def rename(self, name: str, new_name: str) -> None:
        """Carry the sharing over when its playlist is renamed."""

        old, new = share_key(name), share_key(new_name)
        if not old or not new or old == new:
            return
        with self._connect() as conn:
            for table in (
                'playlist_shares',
                'playlist_share_users',
                'playlist_follows',
            ):
                conn.execute(
                    f'UPDATE OR REPLACE {table} SET name_key = ? '
                    'WHERE name_key = ?',
                    (new, old),
                )

    def forget(self, name: str) -> None:
        """Drop all sharing of a playlist that is gone or detached from
        its owner."""

        key = share_key(name)
        with self._connect() as conn:
            for table in (
                'playlist_shares',
                'playlist_share_users',
                'playlist_follows',
            ):
                conn.execute(f'DELETE FROM {table} WHERE name_key = ?', (key,))

    def remove_user(self, user_id: int) -> None:
        """A deleted account's follows, and being on anyone's list."""

        with self._connect() as conn:
            conn.execute(
                'DELETE FROM playlist_follows WHERE user_id = ?',
                (int(user_id),),
            )
            conn.execute(
                'DELETE FROM playlist_share_users WHERE user_id = ?',
                (int(user_id),),
            )
