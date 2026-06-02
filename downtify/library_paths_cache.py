"""In-memory cache for ``list_library_paths`` (avoids repeated full-tree scans)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

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


def invalidate_library_paths_cache() -> None:
    """Drop cached path lists (call after downloads, deletes, or path reconcile)."""

    _PATH_CACHE.clear()
