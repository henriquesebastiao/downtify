"""What an admin hides from the other users' view of the library.

The library is shared: every account sees every song anyone downloaded.
An admin can take songs, albums or artists *out of the view of users who
aren't admins* - and put them back. Nothing is deleted, and admins keep
seeing everything (with a mark on what's hidden). With nothing hidden,
which is how it starts, there is nothing to evaluate.

Three kinds of rule, each matching the way the Library groups things:

* **track** - one file. Remembered by its content key (name + size, which
  survives a folder move) *and* its library path (which survives the file
  being rewritten in place, e.g. by an upgrade), so neither a move nor a
  rewrite quietly shows a hidden song again. Flows that rewrite a file
  re-point the rule (:meth:`LibraryVisibility.rekey_track`).
* **album** - every track of an album, by album artist + title.
* **artist** - every track filed under an artist (their album artist, as
  the Library's Artists tab groups them).

Hiding controls what is *listed* to a user - the Library, search's "in
library" marks, the apps' sync - not who can fetch a file whose address
they know; it is not an access-control boundary.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .library_catalog import album_artist_of, entry_content_key
from .sqlite_utils import connect_sqlite

KIND_TRACK = 'track'
KIND_ALBUM = 'album'
KIND_ARTIST = 'artist'
KINDS = (KIND_TRACK, KIND_ALBUM, KIND_ARTIST)

# Joins an album's artist and title in one stored key.
_SEP = '\x1f'


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fold(value: Any) -> str:
    return str(value or '').strip().casefold()


def _norm_path(path: Any) -> str:
    return str(path or '').strip().replace('\\', '/')


def artist_key(name: Any) -> str:
    """The stored key of an artist: their name, case-insensitively."""

    return _fold(name)


def album_key(artist: Any, title: Any) -> str:
    """The stored key of an album: its artist and title, case-insensitively."""

    return f'{_fold(artist)}{_SEP}{_fold(title)}'


@dataclass(frozen=True)
class HiddenRules:
    """Everything currently hidden, ready to test library rows against."""

    track_keys: frozenset[str] = frozenset()
    track_paths: frozenset[str] = frozenset()
    albums: frozenset[str] = frozenset()
    artists: frozenset[str] = frozenset()

    def __bool__(self) -> bool:
        return bool(
            self.track_keys or self.track_paths or self.albums or self.artists
        )

    def reason(self, entry: dict[str, Any]) -> str:
        """Why *entry* is hidden - ``artist``, ``album`` or ``track`` (the
        widest rule first) - or ``''`` when it is shown."""

        if not self:
            return ''
        artist = album_artist_of(entry)
        if artist and artist_key(artist) in self.artists:
            return KIND_ARTIST
        album = str(entry.get('album') or '').strip()
        if album and album_key(artist, album) in self.albums:
            return KIND_ALBUM
        if (
            _norm_path(entry.get('file')) in self.track_paths
            or entry_content_key(entry) in self.track_keys
        ):
            return KIND_TRACK
        return ''

    def hides(self, entry: dict[str, Any]) -> bool:
        return bool(self.reason(entry))

    def album_reason(self, artist: Any, title: Any) -> str:
        """``artist`` or ``album`` when that whole album is hidden by a
        rule on it (or its artist), else ``''``."""

        if artist_key(artist) in self.artists:
            return KIND_ARTIST
        if album_key(artist, title) in self.albums:
            return KIND_ALBUM
        return ''

    def artist_hidden(self, name: Any) -> bool:
        return artist_key(name) in self.artists


class LibraryVisibility:
    """The hidden items, in ``downtify_library.db``."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._lock = threading.Lock()
        self._rules: HiddenRules | None = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hidden_library_items (
                    kind TEXT NOT NULL,
                    item_key TEXT NOT NULL,
                    item_path TEXT NOT NULL DEFAULT '',
                    label TEXT NOT NULL DEFAULT '',
                    detail TEXT NOT NULL DEFAULT '',
                    hidden_at TEXT NOT NULL,
                    PRIMARY KEY (kind, item_key)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_hidden_library_path
                ON hidden_library_items (item_path)
            """)

    def rules(self) -> HiddenRules:
        """The current rules (kept in memory until something changes)."""

        with self._lock:
            if self._rules is None:
                self._rules = self._load()
            return self._rules

    def _load(self) -> HiddenRules:
        keys: set[str] = set()
        paths: set[str] = set()
        albums: set[str] = set()
        artists: set[str] = set()
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT kind, item_key, item_path FROM hidden_library_items'
            ).fetchall()
        for row in rows:
            kind = row['kind']
            if kind == KIND_TRACK:
                keys.add(row['item_key'])
                if row['item_path']:
                    paths.add(row['item_path'])
            elif kind == KIND_ALBUM:
                albums.add(row['item_key'])
            elif kind == KIND_ARTIST:
                artists.add(row['item_key'])
        return HiddenRules(
            frozenset(keys),
            frozenset(paths),
            frozenset(albums),
            frozenset(artists),
        )

    def _changed(self) -> None:
        self._rules = None

    def invalidate(self) -> None:
        """Reload rules after an atomic audio-reference transaction."""
        with self._lock:
            self._changed()

    def hide(
        self,
        kind: str,
        key: str,
        *,
        label: str = '',
        detail: str = '',
        path: str = '',
    ) -> bool:
        """Hide one item. ``True`` when it wasn't hidden already."""

        if kind not in KINDS or not key:
            return False
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO hidden_library_items
                   (kind, item_key, item_path, label, detail, hidden_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(kind, item_key) DO NOTHING""",
                (kind, key, _norm_path(path), label, detail, _now_iso()),
            )
            added = cur.rowcount > 0
            if added:
                self._changed()
            return added

    def show(self, kind: str, key: str) -> bool:
        """Show one item again. ``True`` when it was hidden."""

        with self._lock, self._connect() as conn:
            cur = conn.execute(
                'DELETE FROM hidden_library_items '
                'WHERE kind = ? AND item_key = ?',
                (kind, key),
            )
            removed = cur.rowcount > 0
            if removed:
                self._changed()
            return removed

    def show_track_by_path(self, path: str) -> int:
        """Show the hidden track(s) stored at *path* (a file whose
        content key changed since it was hidden). How many."""

        normal = _norm_path(path)
        if not normal:
            return 0
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                'DELETE FROM hidden_library_items '
                'WHERE kind = ? AND item_path = ?',
                (KIND_TRACK, normal),
            )
            if cur.rowcount:
                self._changed()
            return cur.rowcount

    def rekey_track(
        self, old_key: str, new_key: str, stored_path: str = ''
    ) -> int:
        """Point a hidden track at its rewritten file (upgrade, replace)."""

        old = str(old_key or '').strip()
        new = str(new_key or '').strip()
        if not old or not new or old == new:
            return 0
        path = _norm_path(stored_path)
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                'UPDATE OR IGNORE hidden_library_items SET item_key = ?, '
                "item_path = COALESCE(NULLIF(?, ''), item_path) "
                'WHERE kind = ? AND item_key = ?',
                (new, path, KIND_TRACK, old),
            )
            moved = cur.rowcount
            conn.execute(
                'DELETE FROM hidden_library_items '
                'WHERE kind = ? AND item_key = ?',
                (KIND_TRACK, old),
            )
            if moved:
                self._changed()
            return moved

    def drop_track(self, content_key: str) -> None:
        """Forget a hidden track whose file is gone."""

        key = str(content_key or '').strip()
        if not key:
            return
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                'DELETE FROM hidden_library_items '
                'WHERE kind = ? AND item_key = ?',
                (KIND_TRACK, key),
            )
            if cur.rowcount:
                self._changed()

    def items(self) -> dict[str, list[dict[str, Any]]]:
        """Every hidden item for the admin's list, newest first:
        ``{tracks, albums, artists}``."""

        with self._connect() as conn:
            rows = conn.execute(
                'SELECT kind, item_key, item_path, label, detail, hidden_at '
                'FROM hidden_library_items ORDER BY hidden_at DESC, rowid DESC'
            ).fetchall()
        out: dict[str, list[dict[str, Any]]] = {
            'tracks': [],
            'albums': [],
            'artists': [],
        }
        for row in rows:
            item = {
                'label': row['label'],
                'detail': row['detail'],
                'hidden_at': row['hidden_at'],
            }
            if row['kind'] == KIND_TRACK:
                out['tracks'].append({
                    **item,
                    'file': row['item_path'],
                    'key': row['item_key'],
                })
            elif row['kind'] == KIND_ALBUM:
                artist, _, title = row['item_key'].partition(_SEP)
                out['albums'].append({
                    **item,
                    'title': row['label'],
                    'artist': row['detail'],
                    'key': row['item_key'],
                    'folded': [artist, title],
                })
            elif row['kind'] == KIND_ARTIST:
                out['artists'].append({
                    **item,
                    'name': row['label'],
                    'key': row['item_key'],
                })
        return out
