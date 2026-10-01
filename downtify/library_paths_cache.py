"""In-memory + sqlite cache for library path scans and ``GET /tracks`` rows.

A full file walk runs only when the directory-tree fingerprint changes
(or the snapshot is missing). ``invalidate_library_paths_cache`` still
drops both the RAM copy and the sqlite snapshot.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from loguru import logger

from .library_fingerprint import (
    library_tree_fingerprint,
    playlist_listing_fingerprint,
)
from .library_listing_store import LibraryListingStore

if TYPE_CHECKING:
    from .library_catalog import LibraryContext

_PATH_CACHE: dict[str, tuple[str, list[tuple[str, str]]]] = {}
_PLAYLIST_CACHE: dict[str, tuple[str, list[dict[str, Any]]]] = {}
_ENTRIES_CACHE: dict[str, tuple[str, list[dict[str, Any]]]] = {}
_LISTING_LOCK = threading.RLock()
_STORE: Optional[LibraryListingStore] = None


def listing_lock() -> threading.RLock:
    return _LISTING_LOCK


def bind_listing_store(db_path: Optional[Path]) -> None:
    """Persist listings in the same ``/data`` sqlite file as the catalog.

    Pass ``None`` to disable persistence (tests).
    """

    global _STORE
    _STORE = LibraryListingStore(db_path) if db_path is not None else None


def cache_key_for_dirs(
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
    extra_dirs: Sequence[Path] = (),
) -> str:
    parts = [str(download_dir.resolve())]
    if slskd_dir is not None:
        try:
            parts.append(str(slskd_dir.resolve()))
        except OSError:
            parts.append(str(slskd_dir))
    else:
        parts.append('')
    extra: list[str] = []
    for root in extra_dirs or ():
        try:
            extra.append(str(root.resolve()))
        except OSError:
            extra.append(str(root))
    extra.sort()
    parts.append(','.join(extra))
    return '|'.join(parts)


def _cache_key(ctx: LibraryContext) -> str:
    return cache_key_for_dirs(
        ctx.download_dir,
        ctx.slskd_dir,
        getattr(ctx, 'extra_dirs', ()) or (),
    )


def listing_fingerprint(
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
    extra_dirs: Sequence[Path] = (),
) -> str:
    """Directory-tree fingerprint (folder mtimes, not per-file stats)."""

    return library_tree_fingerprint(download_dir, slskd_dir, extra_dirs)


def _ctx_fingerprint(ctx: LibraryContext) -> str:
    return listing_fingerprint(
        ctx.download_dir,
        ctx.slskd_dir,
        getattr(ctx, 'extra_dirs', ()) or (),
    )


def drop_listing_memory_caches() -> None:
    """Drop RAM copies only (sqlite snapshot stays). Used to test restart."""

    _PATH_CACHE.clear()
    _PLAYLIST_CACHE.clear()
    _ENTRIES_CACHE.clear()


def _hydrate_snapshot(key: str, snap: dict[str, Any]) -> None:
    fingerprint = str(snap['fingerprint'])
    paths = list(snap['paths'])
    entries = list(snap['entries'])
    _PATH_CACHE[key] = (fingerprint, paths)
    _ENTRIES_CACHE[key] = (fingerprint, entries)


def _try_sqlite(key: str, fingerprint: str) -> Optional[dict[str, Any]]:
    if _STORE is None:
        return None
    snap = _STORE.load(key)
    if snap is None or str(snap.get('fingerprint') or '') != fingerprint:
        return None
    _hydrate_snapshot(key, snap)
    return snap


def get_cached_path_pairs(
    ctx: LibraryContext,
    scan_fn,
) -> list[tuple[str, str]]:
    """Cached ``(stored, resolved)`` pairs, or scan and store the result."""

    key = _cache_key(ctx)
    with _LISTING_LOCK:
        fingerprint = _ctx_fingerprint(ctx)
        hit = _PATH_CACHE.get(key)
        if hit is not None and hit[0] == fingerprint:
            return list(hit[1])
        snap = _try_sqlite(key, fingerprint)
        if snap is not None:
            return list(snap['paths'])
        pairs = scan_fn(ctx)
        _PATH_CACHE[key] = (fingerprint, pairs)
        return list(pairs)


def get_cached_playlists(
    download_dir: Path,
    slskd_dir: Optional[Path],
    extra_dirs: Sequence[Path],
    build_fn: Callable[[], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Cached ``GET /playlists`` rows while the tree fingerprint matches."""

    key = cache_key_for_dirs(download_dir, slskd_dir, extra_dirs)
    with _LISTING_LOCK:
        fingerprint = playlist_listing_fingerprint(download_dir)
        hit = _PLAYLIST_CACHE.get(key)
        if hit is not None and hit[0] == fingerprint:
            return list(hit[1])
        playlists = build_fn()
        _PLAYLIST_CACHE[key] = (fingerprint, playlists)
        return list(playlists)


def get_cached_track_entries(
    ctx: LibraryContext,
) -> Optional[list[dict[str, Any]]]:
    """Folded ``GET /tracks`` rows, or ``None`` when RAM and sqlite miss."""

    key = _cache_key(ctx)
    with _LISTING_LOCK:
        fingerprint = _ctx_fingerprint(ctx)
        hit = _ENTRIES_CACHE.get(key)
        if hit is not None and hit[0] == fingerprint:
            return list(hit[1])
        snap = _try_sqlite(key, fingerprint)
        if snap is not None:
            return list(snap['entries'])
        return None


def store_cached_track_entries(
    ctx: LibraryContext,
    entries: list[dict[str, Any]],
    playlists: Optional[list[dict[str, Any]]] = None,
    paths: Optional[list[tuple[str, str]]] = None,
) -> None:
    key = _cache_key(ctx)
    with _LISTING_LOCK:
        fingerprint = _ctx_fingerprint(ctx)
        copied = list(entries)
        _ENTRIES_CACHE[key] = (fingerprint, copied)
        if paths is not None:
            _PATH_CACHE[key] = (fingerprint, list(paths))
        if _STORE is None:
            return
        path_rows = (
            paths
            if paths is not None
            else list(_PATH_CACHE.get(key, (fingerprint, []))[1])
        )
        playlist_rows = (
            playlists
            if playlists is not None
            else list(_PLAYLIST_CACHE.get(key, (fingerprint, []))[1])
        )
        try:
            _STORE.save(key, fingerprint, path_rows, playlist_rows, copied)
        except Exception:
            logger.opt(exception=True).debug(
                'Could not persist library listing snapshot'
            )


#: Called on every invalidation - i.e. whenever the library changed - with
#: no arguments, from whichever thread invalidated. See
#: :func:`add_invalidation_listener`.
_LISTENERS: list[Callable[[], None]] = []


def add_invalidation_listener(fn: Callable[[], None]) -> None:
    """Call *fn* whenever the library changes (e.g. to tell connected
    apps to sync). It must be quick and thread-safe."""

    if fn not in _LISTENERS:
        _LISTENERS.append(fn)


def invalidate_library_paths_cache(*, notify: bool = True) -> None:
    """Drop cached path lists (call after downloads, deletes, or path reconcile).

    *notify* ``False`` is for a rescan that isn't a change in itself (a
    client asking for a fresh scan): the listeners aren't told.
    """

    drop_listing_memory_caches()
    if _STORE is not None:
        try:
            _STORE.clear()
        except Exception:
            logger.opt(exception=True).debug(
                'Could not clear library listing snapshot'
            )
    if not notify:
        return
    for fn in list(_LISTENERS):
        try:
            fn()
        except Exception:
            logger.opt(exception=True).debug('Library change listener failed')
