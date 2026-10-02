"""In-memory + sqlite cache for library path scans and ``GET /tracks`` rows.

UI reads return the last snapshot without walking the disk. A background
refresh (or a caller that needs a live scan) still fingerprints the
tree and rebuilds when files change. ``invalidate_library_paths_cache``
drops the cheap playlist list (M3U) but keeps the track snapshot so a
download does not freeze Home / Library.
"""

from __future__ import annotations

import threading
import time
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
_DATA_LOCK = threading.RLock()
_LISTING_LOCK = threading.RLock()
_PLAYLIST_LOCK = threading.RLock()
_STORE: Optional[LibraryListingStore] = None
_REFRESH_LOCK = threading.Lock()
_REFRESH_THREAD: Optional[threading.Thread] = None
_REFRESH_AGAIN = False
_REFRESH_FN: Optional[Callable[[], None]] = None
_REFRESH_GATE: Optional[Callable[[], bool]] = None
# Seconds to wait after the last invalidation before walking the tree,
# so a playlist queue does not rescan extra folders after every track.
_REFRESH_DEBOUNCE_S = 5.0


def set_listing_refresh_fn(fn: Callable[[], None]) -> None:
    """Remember how to rebuild listings after an invalidation."""

    global _REFRESH_FN
    _REFRESH_FN = fn


def set_listing_refresh_gate(fn: Optional[Callable[[], bool]]) -> None:
    """*fn* True means a download is using the disk; delay the tree walk."""

    global _REFRESH_GATE
    _REFRESH_GATE = fn


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

    with _DATA_LOCK:
        _PATH_CACHE.clear()
        _PLAYLIST_CACHE.clear()
        _ENTRIES_CACHE.clear()


def _hydrate_snapshot(key: str, snap: dict[str, Any]) -> None:
    fingerprint = str(snap['fingerprint'])
    paths = list(snap['paths'])
    entries = list(snap['entries'])
    _PATH_CACHE[key] = (fingerprint, paths)
    _ENTRIES_CACHE[key] = (fingerprint, entries)
    playlists = list(snap.get('playlists') or [])
    if playlists:
        _PLAYLIST_CACHE[key] = (fingerprint, playlists)


def _load_sqlite(key: str) -> Optional[dict[str, Any]]:
    if _STORE is None:
        return None
    try:
        return _STORE.load(key)
    except Exception:
        logger.opt(exception=True).debug('Could not load listing snapshot')
        return None


def _try_sqlite(key: str, fingerprint: str) -> Optional[dict[str, Any]]:
    snap = _load_sqlite(key)
    if snap is None or str(snap.get('fingerprint') or '') != fingerprint:
        return None
    with _DATA_LOCK:
        _hydrate_snapshot(key, snap)
    return snap


def peek_cached_path_pairs(
    ctx: LibraryContext,
) -> Optional[list[tuple[str, str]]]:
    """Last known path pairs, with no directory walk."""

    key = _cache_key(ctx)
    with _DATA_LOCK:
        hit = _PATH_CACHE.get(key)
        if hit is not None:
            return list(hit[1])
    snap = _load_sqlite(key)
    if snap is None:
        return None
    with _DATA_LOCK:
        _hydrate_snapshot(key, snap)
        hit = _PATH_CACHE.get(key)
        return list(hit[1]) if hit is not None else None


def peek_cached_track_entries(
    ctx: LibraryContext,
) -> Optional[list[dict[str, Any]]]:
    """Last folded ``GET /tracks`` rows, with no directory walk."""

    key = _cache_key(ctx)
    with _DATA_LOCK:
        hit = _ENTRIES_CACHE.get(key)
        if hit is not None:
            return list(hit[1])
    snap = _load_sqlite(key)
    if snap is None:
        return None
    with _DATA_LOCK:
        _hydrate_snapshot(key, snap)
        hit = _ENTRIES_CACHE.get(key)
        return list(hit[1]) if hit is not None else None


def start_background_listing_refresh(fn: Callable[[], None]) -> None:
    """Run *fn* on a daemon thread; coalesce overlapping requests."""

    global _REFRESH_THREAD, _REFRESH_AGAIN, _REFRESH_FN
    _REFRESH_FN = fn

    def worker() -> None:
        global _REFRESH_AGAIN, _REFRESH_THREAD
        while True:
            time.sleep(_REFRESH_DEBOUNCE_S)
            with _REFRESH_LOCK:
                again = _REFRESH_AGAIN
                _REFRESH_AGAIN = False
            if again:
                continue
            gate = _REFRESH_GATE
            if gate is not None:
                try:
                    if gate():
                        with _REFRESH_LOCK:
                            _REFRESH_AGAIN = True
                        continue
                except Exception:
                    pass
            task = _REFRESH_FN
            try:
                if task is not None:
                    task()
            except Exception:
                logger.opt(exception=True).debug(
                    'Background library listing refresh failed'
                )
            with _REFRESH_LOCK:
                if _REFRESH_AGAIN:
                    _REFRESH_AGAIN = False
                    continue
                _REFRESH_THREAD = None
                return

    with _REFRESH_LOCK:
        if _REFRESH_THREAD is not None and _REFRESH_THREAD.is_alive():
            _REFRESH_AGAIN = True
            return
        _REFRESH_THREAD = threading.Thread(
            target=worker,
            name='downtify-listing-refresh',
            daemon=True,
        )
        _REFRESH_THREAD.start()


def get_cached_path_pairs(
    ctx: LibraryContext,
    scan_fn,
) -> list[tuple[str, str]]:
    """Cached ``(stored, resolved)`` pairs, or scan and store the result."""

    key = _cache_key(ctx)
    fingerprint = _ctx_fingerprint(ctx)
    with _DATA_LOCK:
        hit = _PATH_CACHE.get(key)
        if hit is not None and hit[0] == fingerprint:
            return list(hit[1])
    snap = _try_sqlite(key, fingerprint)
    if snap is not None:
        return list(snap['paths'])
    pairs = scan_fn(ctx)
    with _DATA_LOCK:
        _PATH_CACHE[key] = (fingerprint, pairs)
    return list(pairs)


def get_cached_playlists(
    download_dir: Path,
    slskd_dir: Optional[Path],
    extra_dirs: Sequence[Path],
    build_fn: Callable[[], list[dict[str, Any]]],
    *,
    stale_ok: bool = False,
) -> list[dict[str, Any]]:
    """``GET /playlists`` rows.

    *stale_ok* returns the RAM snapshot immediately (no M3U walk) and
    rebuilds in the background. Live callers omit it so tests and writes
    see a new M3U on the next listing.
    """

    key = cache_key_for_dirs(download_dir, slskd_dir, extra_dirs)
    with _DATA_LOCK:
        hit = _PLAYLIST_CACHE.get(key)
        cached = list(hit[1]) if hit is not None else None
    if cached is not None and stale_ok:
        return cached
    if cached is not None:
        fingerprint = playlist_listing_fingerprint(download_dir)
        with _DATA_LOCK:
            hit = _PLAYLIST_CACHE.get(key)
            if hit is not None and hit[0] == fingerprint:
                return list(hit[1])
    with _PLAYLIST_LOCK:
        fingerprint = playlist_listing_fingerprint(download_dir)
        with _DATA_LOCK:
            hit = _PLAYLIST_CACHE.get(key)
            if hit is not None and hit[0] == fingerprint:
                return list(hit[1])
        playlists = build_fn()
        with _DATA_LOCK:
            _PLAYLIST_CACHE[key] = (fingerprint, playlists)
        return list(playlists)


def get_cached_track_entries(
    ctx: LibraryContext,
) -> Optional[list[dict[str, Any]]]:
    """Folded ``GET /tracks`` rows when the tree fingerprint still matches."""

    key = _cache_key(ctx)
    fingerprint = _ctx_fingerprint(ctx)
    with _DATA_LOCK:
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
    fingerprint = _ctx_fingerprint(ctx)
    copied = list(entries)
    with _DATA_LOCK:
        _ENTRIES_CACHE[key] = (fingerprint, copied)
        if paths is not None:
            _PATH_CACHE[key] = (fingerprint, list(paths))
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
    if _STORE is None:
        return
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


def invalidate_library_paths_cache(
    *, notify: bool = True, drop_entries: bool = False
) -> None:
    """Mark listings stale after downloads, deletes, or path reconcile.

    Playlist RAM is always dropped (an M3U scan is cheap). The folded
    track snapshot stays unless *drop_entries* is set, so UI routes can
    keep serving it while a background refresh catches up.

    *notify* ``False`` is for a rescan that isn't a change in itself (a
    client asking for a fresh scan): the listeners aren't told.
    """

    with _DATA_LOCK:
        _PLAYLIST_CACHE.clear()
        if drop_entries:
            _PATH_CACHE.clear()
            _ENTRIES_CACHE.clear()
    if drop_entries and _STORE is not None:
        try:
            _STORE.clear()
        except Exception:
            logger.opt(exception=True).debug(
                'Could not clear library listing snapshot'
            )
    refresh = _REFRESH_FN
    if refresh is not None:
        start_background_listing_refresh(refresh)
    if not notify:
        return
    for listener in list(_LISTENERS):
        try:
            listener()
        except Exception:
            logger.opt(exception=True).debug('Library change listener failed')
