"""Songs an owner took out of an imported playlist - and keeps out.

An imported playlist (downloaded from a Spotify, YouTube Music or Deezer
link, often kept up to date by a Playlist Monitor watch) follows its
source: a sweep rewrites its M3U from the source's track list and
*Download missing* offers whatever the library lacks, so a song taken
out of the M3U by hand would come straight back. Hiding remembers the
song for that playlist, so every one of those paths leaves it out:

* its line leaves the M3U at once - the audio file stays in the library
  (deleting it is the Library's own *Delete*);
* watch sweeps neither list it nor download it again, even once its file
  is deleted;
* it doesn't count as missing, so *Download missing* skips it;
* downloading the playlist again from its link keeps it out of the M3U.

The source playlist itself is never changed: Downtify reads Spotify and
YouTube Music anonymously and can't edit them.

A hidden song is remembered by its source track id (a Spotify track id
or a YouTube video id - what sweeps and the completeness reports compare)
when one is known, and always by its library path and content key, so
playlists with no source id (older downloads) work too. Rows are keyed by
the playlist's sanitized, casefolded name - the M3U's stem - so a watch's
raw name (``Top 50: USA``) and the listing's (``Top 50 USA``) find the
same rows. Library-created playlists don't need any of this: removing a
song from one is simply editing it.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Optional

from . import m3u
from .library_cache_keys import file_content_key
from .library_catalog import LibraryContext, resolve_library_file
from .library_paths_cache import invalidate_library_paths_cache
from .sqlite_utils import connect_sqlite
from .track_index import normalize_spotify_track_id

if TYPE_CHECKING:
    from .monitor import PlaylistMonitorDB
    from .playlist_catalog import PlaylistCatalog

#: Most songs one request may hide or show again.
MAX_SONGS_PER_EDIT = 500


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_path(path: Any) -> str:
    return str(path or '').strip().replace('\\', '/')


def hidden_key(name: Any) -> str:
    """The stored key of a playlist: its M3U stem, case-insensitively."""

    text = str(name or '').strip()
    return m3u.sanitize_playlist_name(text).casefold() if text else ''


def _item_key(track_id: str, content_key: str, path: str) -> str:
    if track_id:
        return track_id
    if content_key:
        return f'key:{content_key}'
    return f'file:{path}'


@dataclass(frozen=True)
class HiddenSongs:
    """One playlist's hidden songs, ready to test source rows and library
    files against."""

    track_ids: frozenset[str] = frozenset()
    files: frozenset[str] = frozenset()
    content_keys: frozenset[str] = frozenset()

    def __bool__(self) -> bool:
        return bool(self.track_ids or self.files or self.content_keys)

    def hides_song(self, song: dict[str, Any]) -> bool:
        """Whether a source row (``song_id``: Spotify id or video id) is
        hidden."""

        if not self.track_ids:
            return False
        raw = str(song.get('song_id') or '').strip()
        if raw and raw in self.track_ids:
            return True
        spotify_id = normalize_spotify_track_id(song)
        return bool(spotify_id) and spotify_id in self.track_ids

    def hides_file(self, path: Any, content_key: str = '') -> bool:
        """Whether a library file is hidden, by path or content key."""

        normal = _norm_path(path)
        if normal and normal in self.files:
            return True
        return bool(content_key) and content_key in self.content_keys


class PlaylistHiddenSongs:
    """The hidden songs of every playlist, in ``downtify_library.db``."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._lock = threading.Lock()
        self._loaded: Optional[dict[str, HiddenSongs]] = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playlist_hidden_songs (
                    name_key TEXT NOT NULL,
                    item_key TEXT NOT NULL,
                    track_id TEXT NOT NULL DEFAULT '',
                    content_key TEXT NOT NULL DEFAULT '',
                    file TEXT NOT NULL DEFAULT '',
                    label TEXT NOT NULL DEFAULT '',
                    extinf TEXT NOT NULL DEFAULT '',
                    position INTEGER NOT NULL DEFAULT -1,
                    hidden_at TEXT NOT NULL,
                    PRIMARY KEY (name_key, item_key)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_playlist_hidden_content_key
                ON playlist_hidden_songs (content_key)
            """)

    def _changed(self) -> None:
        self._loaded = None

    def _all(self) -> dict[str, HiddenSongs]:
        with self._lock:
            if self._loaded is None:
                self._loaded = self._load()
            return self._loaded

    def _load(self) -> dict[str, HiddenSongs]:
        grouped: dict[str, tuple[set[str], set[str], set[str]]] = {}
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT name_key, track_id, content_key, file '
                'FROM playlist_hidden_songs'
            ).fetchall()
        for row in rows:
            ids, files, keys = grouped.setdefault(
                row['name_key'], (set(), set(), set())
            )
            if row['track_id']:
                ids.add(row['track_id'])
            if row['file']:
                files.add(row['file'])
            if row['content_key']:
                keys.add(row['content_key'])
        return {
            name: HiddenSongs(
                frozenset(ids), frozenset(files), frozenset(keys)
            )
            for name, (ids, files, keys) in grouped.items()
        }

    def songs(self, name: Any) -> HiddenSongs:
        """What playlist *name* hides (empty when nothing)."""

        return self._all().get(hidden_key(name), HiddenSongs())

    def counts(self) -> dict[str, int]:
        """``{playlist key: number of hidden songs}``, for the listing."""

        with self._connect() as conn:
            rows = conn.execute(
                'SELECT name_key, COUNT(*) AS n FROM playlist_hidden_songs '
                'GROUP BY name_key'
            ).fetchall()
        return {str(row['name_key']): int(row['n']) for row in rows}

    def hide(
        self,
        name: Any,
        *,
        track_id: str = '',
        content_key: str = '',
        path: str = '',
        label: str = '',
        extinf: str = '',
        position: int = -1,
    ) -> bool:
        """Remember one hidden song. ``True`` when it wasn't hidden yet."""

        key = hidden_key(name)
        tid = str(track_id or '').strip()
        ck = str(content_key or '').strip()
        normal = _norm_path(path)
        if not key or not (tid or ck or normal):
            return False
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO playlist_hidden_songs
                   (name_key, item_key, track_id, content_key, file, label,
                    extinf, position, hidden_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(name_key, item_key) DO NOTHING""",
                (
                    key,
                    _item_key(tid, ck, normal),
                    tid,
                    ck,
                    normal,
                    str(label or ''),
                    str(extinf or ''),
                    int(position),
                    _now_iso(),
                ),
            )
            added = cur.rowcount > 0
            if added:
                self._changed()
            return added

    def show(self, name: Any, keys: Iterable[str]) -> list[dict[str, Any]]:
        """Forget the hidden songs *keys* of playlist *name*; the rows
        that were there."""

        key = hidden_key(name)
        wanted = list(dict.fromkeys(str(k) for k in keys if str(k or '')))
        if not key or not wanted:
            return []
        removed: list[dict[str, Any]] = []
        with self._lock, self._connect() as conn:
            for item in wanted:
                row = conn.execute(
                    'SELECT * FROM playlist_hidden_songs '
                    'WHERE name_key = ? AND item_key = ?',
                    (key, item),
                ).fetchone()
                if row is None:
                    continue
                conn.execute(
                    'DELETE FROM playlist_hidden_songs '
                    'WHERE name_key = ? AND item_key = ?',
                    (key, item),
                )
                removed.append(_public_row(row))
            if removed:
                self._changed()
        return removed

    def items(self, name: Any) -> list[dict[str, Any]]:
        """Playlist *name*'s hidden songs, most recently hidden first."""

        with self._connect() as conn:
            rows = conn.execute(
                'SELECT * FROM playlist_hidden_songs WHERE name_key = ? '
                'ORDER BY hidden_at DESC, rowid DESC',
                (hidden_key(name),),
            ).fetchall()
        return [_public_row(row) for row in rows]

    def forget(self, name: Any) -> int:
        """Drop every hidden song of a playlist that was deleted or
        detached from its source. How many."""

        with self._lock, self._connect() as conn:
            cur = conn.execute(
                'DELETE FROM playlist_hidden_songs WHERE name_key = ?',
                (hidden_key(name),),
            )
            if cur.rowcount:
                self._changed()
            return cur.rowcount

    def rekey(self, old_key: str, new_key: str, stored_path: str = '') -> int:
        """Follow a hidden song's file when it is rewritten (upgrade,
        replace) - a song's track id never changes, its file may."""

        old = str(old_key or '').strip()
        new = str(new_key or '').strip()
        if not old or not new or old == new:
            return 0
        normal = _norm_path(stored_path)
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                'UPDATE OR IGNORE playlist_hidden_songs SET content_key = ?, '
                "file = COALESCE(NULLIF(?, ''), file) WHERE content_key = ?",
                (new, normal, old),
            )
            if cur.rowcount:
                self._changed()
            return cur.rowcount


def _public_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        'key': row['item_key'],
        'track_id': row['track_id'],
        'content_key': row['content_key'],
        'file': row['file'],
        'label': row['label'],
        'extinf': row['extinf'],
        'position': int(row['position']),
        'hidden_at': row['hidden_at'],
    }


# ── Hiding and showing ──────────────────────────────────────────────────


class HiddenSongsError(ValueError):
    """User-facing failure (not found, not imported, nothing to hide)."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _imported_m3u(ctx: LibraryContext, name: str) -> Path:
    path = m3u.find_m3u_for_name(ctx.download_dir, name)
    if path is None:
        raise HiddenSongsError(
            f'Playlist {name!r} was not found', status_code=404
        )
    if m3u.is_manual_m3u(path):
        raise HiddenSongsError(
            'Songs are removed from a Library playlist, not hidden',
            status_code=409,
        )
    return path


def catalog_names_for(
    catalog: Optional[PlaylistCatalog], name: str
) -> list[str]:
    """The playlist catalog's names for playlist *name* (a watch stores
    the raw name, the listing the M3U stem)."""

    if catalog is None:
        return []
    key = hidden_key(name)
    return [n for n in catalog.list_playlist_names() if hidden_key(n) == key]


def source_track_ids(
    name: str,
    files: Iterable[str],
    *,
    catalog: Optional[PlaylistCatalog] = None,
    monitor_db: Optional[PlaylistMonitorDB] = None,
) -> dict[str, str]:
    """``{library path: source track id}`` for the *files* of playlist
    *name*, from the playlist catalog and its watch's history - the id a
    sweep or a completeness report compares."""

    wanted = {_norm_path(f) for f in files if _norm_path(f)}
    found: dict[str, str] = {}
    for exact in catalog_names_for(catalog, name):
        for row in catalog.list_tracks(exact):
            path = _norm_path(row.get('filename'))
            if path in wanted and row.get('track_spotify_id'):
                found.setdefault(path, str(row['track_spotify_id']))
    if monitor_db is not None and len(found) < len(wanted):
        key = hidden_key(name)
        for watch in monitor_db.list_playlists():
            if hidden_key(watch.name) != key:
                continue
            for tid, path in monitor_db.get_track_filenames(watch.id).items():
                normal = _norm_path(path)
                if normal in wanted and tid:
                    found.setdefault(normal, str(tid))
    return found


def hide_playlist_songs(
    ctx: LibraryContext,
    store: PlaylistHiddenSongs,
    name: str,
    files: Iterable[str],
    *,
    track_ids: Optional[dict[str, str]] = None,
    catalog: Optional[PlaylistCatalog] = None,
) -> dict[str, Any]:
    """Hide *files* from imported playlist *name*: remember them, take
    them out of its M3U and of its catalog rows. The audio stays.
    ``keys`` in the result are what :func:`show_playlist_songs` takes to
    undo it."""

    path = _imported_m3u(ctx, name)
    download_dir, slskd_dir = ctx.download_dir, ctx.slskd_dir
    extra_dirs = tuple(ctx.extra_dirs or ())
    entries = m3u.read_m3u_entries(path, download_dir, slskd_dir, extra_dirs)
    current = [stored for stored, _extinf in entries]
    wanted = {_norm_path(f) for f in files if _norm_path(f)}
    if len(wanted) > MAX_SONGS_PER_EDIT:
        raise HiddenSongsError(
            f'Hide at most {MAX_SONGS_PER_EDIT} songs at a time'
        )
    chosen = [stored for stored in dict.fromkeys(current) if stored in wanted]
    if not chosen:
        raise HiddenSongsError('Those songs are not in this playlist')
    if not [stored for stored in current if stored not in wanted]:
        raise HiddenSongsError(
            'A playlist must keep at least one song - delete it instead'
        )
    hidden, keys = _remember_hidden(
        ctx, store, path.stem, entries, chosen, track_ids or {}
    )
    m3u.remove_m3u_tracks(path, chosen, download_dir, slskd_dir, extra_dirs)
    if catalog is not None:
        for exact in catalog_names_for(catalog, path.stem):
            for stored in chosen:
                catalog.remove_tracks_for_filename(stored, exact)
    invalidate_library_paths_cache()
    kept = m3u.read_m3u_tracks(
        path, download_dir, slskd_dir, extra_dirs, keep_missing=True
    )
    return {
        'name': path.stem,
        'hidden': hidden,
        'keys': keys,
        'files': kept,
        'count': len(kept),
    }


def _remember_hidden(
    ctx: LibraryContext,
    store: PlaylistHiddenSongs,
    name: str,
    entries: list[tuple[str, str]],
    chosen: list[str],
    track_ids: dict[str, str],
) -> tuple[int, list[str]]:
    """Store *chosen* (of the M3U *entries*) as hidden from playlist
    *name*: ``(newly hidden, every chosen song's key)``."""

    current = [stored for stored, _extinf in entries]
    hidden = 0
    keys: list[str] = []
    for stored in chosen:
        position = current.index(stored)
        extinf = entries[position][1]
        full = resolve_library_file(stored, ctx)
        content_key = file_content_key(full) if full is not None else ''
        track_id = track_ids.get(stored, '')
        keys.append(_item_key(track_id, content_key, stored))
        if store.hide(
            name,
            track_id=track_id,
            content_key=content_key,
            path=stored,
            label=m3u.extinf_label(extinf) or Path(stored).stem,
            extinf=extinf,
            position=position,
        ):
            hidden += 1
    return hidden, keys


def show_playlist_songs(
    ctx: LibraryContext,
    store: PlaylistHiddenSongs,
    name: str,
    keys: Iterable[str],
    *,
    catalog: Optional[PlaylistCatalog] = None,
) -> dict[str, Any]:
    """Show hidden songs *keys* of playlist *name* again: forget them and
    put the ones still in the library back where they were. A song whose
    file is gone comes back the way any missing song does - the next
    watch sweep, or *Download missing*."""

    path = _imported_m3u(ctx, name)
    download_dir, slskd_dir = ctx.download_dir, ctx.slskd_dir
    extra_dirs = tuple(ctx.extra_dirs or ())
    wanted = list(keys)
    if len(wanted) > MAX_SONGS_PER_EDIT:
        raise HiddenSongsError(
            f'Show at most {MAX_SONGS_PER_EDIT} songs at a time'
        )
    rows = store.show(path.stem, wanted)
    current = m3u.read_m3u_tracks(
        path, download_dir, slskd_dir, extra_dirs, keep_missing=True
    )
    restored = 0
    for row in sorted(rows, key=lambda item: item['position']):
        stored = row['file']
        full = resolve_library_file(stored, ctx) if stored else None
        if full is None or stored in current:
            continue
        position = max(row['position'], 0)
        if not m3u.insert_m3u_track(
            path,
            stored,
            position,
            row['extinf'],
            download_dir,
            slskd_dir,
            extra_dirs,
        ):
            continue
        current.insert(min(position, len(current)), stored)
        restored += 1
        tid = row['track_id']
        if catalog is not None and normalize_spotify_track_id({
            'song_id': tid
        }):
            for exact in catalog_names_for(catalog, path.stem):
                catalog.upsert_track(
                    exact, {'song_id': tid}, stored, full, track_order=position
                )
    invalidate_library_paths_cache()
    return {
        'name': path.stem,
        'shown': len(rows),
        'restored': restored,
        'files': current,
        'count': len(current),
    }
