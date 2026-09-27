"""In-memory cache for ``list_library_paths`` (avoids repeated full-tree scans)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from .library_catalog import LibraryContext

_PATH_CACHE: dict[str, tuple[float, list[str]]] = {}
_CACHE_TTL_SECONDS = 90.0


def _cache_key(ctx: LibraryContext) -> str:
    parts = [str(ctx.download_dir.resolve())]
    if ctx.slskd_dir is not None:
        try:
            parts.append(str(ctx.slskd_dir.resolve()))
        except OSError:
            parts.append(str(ctx.slskd_dir))
    else:
        parts.append('')
    return '|'.join(parts)


def get_cached_paths(
    ctx: LibraryContext,
    scan_fn,
) -> list[str]:
    """Return cached path list or run *scan_fn(ctx)* and store the result."""

    key = _cache_key(ctx)
    now = time.monotonic()
    hit = _PATH_CACHE.get(key)
    if hit is not None and now - hit[0] < _CACHE_TTL_SECONDS:
        return list(hit[1])
    paths = scan_fn(ctx)
    _PATH_CACHE[key] = (now, paths)
    return paths


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

    _PATH_CACHE.clear()
    if not notify:
        return
    for fn in list(_LISTENERS):
        try:
            fn()
        except Exception:
            logger.opt(exception=True).debug('Library change listener failed')
