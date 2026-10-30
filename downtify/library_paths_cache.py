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
#: Seconds a checked ``GET /playlists`` listing is served without walking
#: the downloads folder for M3U files again (slow on a NAS). Downtify's
#: own M3U writes drop it at once (:func:`forget_cached_playlists`); this
#: bounds how late an M3U changed by hand shows up.
PLAYLIST_RECHECK_SECONDS = 60.0
#: When each playlist listing was last checked against the disk.
_PLAYLIST_CHECKED: dict[str, float] = {}
#: Listings being checked in the background: a burst of page loads starts
#: one walk of the downloads folder, not one each.
_PLAYLIST_RECHECKING: set[str] = set()
#: Bumped when a listing is dropped, so a walk that began before an M3U was
#: written can't store what it read over the drop.
_PLAYLIST_GENERATION = 0


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
    key = cache_key_for_dirs(
        ctx.download_dir,
        ctx.slskd_dir,
        getattr(ctx, 'extra_dirs', ()) or (),
    )
    primary = getattr(ctx, 'primary_extra_id', '')
    return f'{key}|primary={primary}' if primary else key


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
        _drop_playlist_listings()
        _ENTRIES_CACHE.clear()


def _drop_playlist_listings() -> None:
    """Forget every playlist listing. Call with ``_DATA_LOCK`` held."""

    global _PLAYLIST_GENERATION
    _PLAYLIST_CACHE.clear()
    _PLAYLIST_CHECKED.clear()
    _PLAYLIST_GENERATION += 1


def forget_cached_playlists() -> None:
    """Drop the playlist listing (an M3U was just written); the next
    ``GET /playlists`` reads the M3U files again."""

    with _DATA_LOCK:
        _drop_playlist_listings()


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

    *stale_ok* (UI reads) always serves the RAM listing when there is one,
    so no page waits on a walk of the downloads folder; once it is older
    than :data:`PLAYLIST_RECHECK_SECONDS` a background check brings it up
    to date for the next read. Without it, every call checks the M3U
    files, so tests and writes see a new M3U on the next listing.
    """

    key = cache_key_for_dirs(download_dir, slskd_dir, extra_dirs)
    with _DATA_LOCK:
        hit = _PLAYLIST_CACHE.get(key)
        cached = list(hit[1]) if hit is not None else None
        fresh = _playlists_checked_recently(key)
    if cached is not None and stale_ok:
        if not fresh:
            _recheck_playlists_in_background(key, download_dir, build_fn)
        return cached
    return _check_playlists(key, download_dir, build_fn, stale_ok=stale_ok)


def _playlists_checked_recently(key: str) -> bool:
    """Call with ``_DATA_LOCK`` held."""

    checked = _PLAYLIST_CHECKED.get(key)
    return (
        checked is not None
        and time.monotonic() - checked < PLAYLIST_RECHECK_SECONDS
    )


def _check_playlists(
    key: str,
    download_dir: Path,
    build_fn: Callable[[], list[dict[str, Any]]],
    *,
    stale_ok: bool = False,
) -> list[dict[str, Any]]:
    """The listing, rebuilt when the M3U files on disk have changed."""

    with _PLAYLIST_LOCK:
        with _DATA_LOCK:
            generation = _PLAYLIST_GENERATION
            hit = _PLAYLIST_CACHE.get(key)
            # Whoever held the lock just walked: don't walk again after it.
            if (
                stale_ok
                and hit is not None
                and _playlists_checked_recently(key)
            ):
                return list(hit[1])
        fingerprint = playlist_listing_fingerprint(download_dir)
        with _DATA_LOCK:
            hit = _PLAYLIST_CACHE.get(key)
            if hit is not None and hit[0] == fingerprint:
                _PLAYLIST_CHECKED[key] = time.monotonic()
                return list(hit[1])
        playlists = build_fn()
        with _DATA_LOCK:
            if generation == _PLAYLIST_GENERATION:
                _PLAYLIST_CACHE[key] = (fingerprint, playlists)
                _PLAYLIST_CHECKED[key] = time.monotonic()
        return list(playlists)


def _recheck_playlists_in_background(
    key: str,
    download_dir: Path,
    build_fn: Callable[[], list[dict[str, Any]]],
) -> None:
    """Run :func:`_check_playlists` on a daemon thread, one per listing."""

    with _DATA_LOCK:
        if key in _PLAYLIST_RECHECKING:
            return
        _PLAYLIST_RECHECKING.add(key)

    def worker() -> None:
        try:
            _check_playlists(key, download_dir, build_fn)
        except Exception:
            logger.opt(exception=True).debug(
                'Background playlist listing check failed'
            )
        finally:
            with _DATA_LOCK:
                _PLAYLIST_RECHECKING.discard(key)

    threading.Thread(
        target=worker, name='downtify-playlist-recheck', daemon=True
    ).start()


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


#: Fingerprint of a RAM listing patched in place (one file added or
#: removed): never equal to a real one, so the next live read rebuilds.
PROVISIONAL_FINGERPRINT = ''


def store_cached_track_entries(
    ctx: LibraryContext,
    entries: list[dict[str, Any]],
    playlists: Optional[list[dict[str, Any]]] = None,
    paths: Optional[list[tuple[str, str]]] = None,
    *,
    provisional: bool = False,
) -> None:
    """Remember a folded listing in RAM and in sqlite.

    *provisional* (a download or delete patching the listing) keeps it in
    RAM only, without fingerprinting the tree: walking every library
    folder and rewriting the whole snapshot for each downloaded track
    was slow on a NAS. The refresh that follows the change (see
    :func:`invalidate_library_paths_cache`) stores the real one.
    """

    key = _cache_key(ctx)
    fingerprint = (
        PROVISIONAL_FINGERPRINT if provisional else _ctx_fingerprint(ctx)
    )
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
    if _STORE is None or provisional:
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
        _drop_playlist_listings()
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
