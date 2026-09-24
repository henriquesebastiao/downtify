"""DISPLAY-ONLY proxy for photos of artists that are not in the library.

This module exists so the artist page can show a face next to a related
artist the user does not own (Deezer's API sends no CORS headers, so the
browser cannot ask for it directly). It is a pass-through, nothing more:

* The image bytes are returned to the caller and forgotten. Nothing is
  written to disk, ever - not here, not via
  :func:`downtify.artist_profile.save_image` or
  :func:`downtify.artist_profile.fetch_and_save_image` (do not import
  them). Only a name -> Deezer CDN URL mapping is kept, in memory, for
  three hours.
* It is NOT a photo/banner source. A photo picked for an artist in the
  library goes through the artist-art picker and is saved as a sidecar
  file, as before. Do not call :func:`fetch_proxied_photo` from the
  download pipeline, ``ensure_profile`` or anything else that persists.
* The browser is told to cache the response for three hours
  (:data:`BROWSER_CACHE_SECONDS`), which is the only cache that holds
  the pixels.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

import httpx
from loguru import logger

from . import deezer

BROWSER_CACHE_SECONDS = 3 * 3600
_URL_TTL = 3 * 3600.0
_MAX_ENTRIES = 1000
_MAX_CONCURRENT = 4
_MAX_BYTES = 2 * 1024 * 1024
_TIMEOUT = 10
_CDN_SUFFIX = 'dzcdn.net'

# name (lower-cased) -> (cdn url or None for "no match", monotonic stamp)
_url_cache: dict[str, tuple[Optional[str], float]] = {}
_cache_lock = threading.Lock()
_slots = threading.BoundedSemaphore(_MAX_CONCURRENT)
_inflight: dict[str, threading.Lock] = {}


def _is_cdn_url(url: str) -> bool:
    try:
        parsed = httpx.URL(url)
    except Exception:
        return False
    host = parsed.host or ''
    return parsed.scheme == 'https' and (
        host == _CDN_SUFFIX or host.endswith(f'.{_CDN_SUFFIX}')
    )


def _cached_url(key: str) -> tuple[bool, Optional[str]]:
    with _cache_lock:
        entry = _url_cache.get(key)
        if entry is None:
            return False, None
        url, stamp = entry
        if time.monotonic() - stamp > _URL_TTL:
            del _url_cache[key]
            return False, None
        return True, url


def _remember_url(key: str, url: Optional[str]) -> None:
    with _cache_lock:
        if len(_url_cache) >= _MAX_ENTRIES and key not in _url_cache:
            # Oldest first; dicts keep insertion order.
            del _url_cache[next(iter(_url_cache))]
        _url_cache[key] = (url, time.monotonic())


def _lookup_url(name: str) -> Optional[str]:
    """The Deezer CDN URL for *name*, cached (misses too) and deduped so
    a burst of identical requests makes one search call."""

    key = name.strip().lower()
    hit, url = _cached_url(key)
    if hit:
        return url
    with _cache_lock:
        gate = _inflight.setdefault(key, threading.Lock())
    with gate:
        hit, url = _cached_url(key)
        if hit:
            return url
        with _slots:
            url = deezer.exact_artist_picture(name)
        if url is not None and not _is_cdn_url(url):
            url = None
        _remember_url(key, url)
    with _cache_lock:
        _inflight.pop(key, None)
    return url


def fetch_proxied_photo(name: str) -> Optional[tuple[bytes, str]]:
    """``(image bytes, content type)`` for *name*'s Deezer photo, or
    ``None`` when Deezer has no exact match / the download fails.

    Display only - see the module docstring. The bytes are not kept.
    """

    if not name.strip():
        return None
    url = _lookup_url(name)
    if url is None:
        return None
    try:
        with _slots:
            resp = httpx.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
    except Exception:
        logger.opt(exception=True).debug('Artist photo proxy fetch failed')
        return None
    data = resp.content
    if not data or len(data) > _MAX_BYTES:
        return None
    content_type = resp.headers.get('content-type', 'image/jpeg')
    if not content_type.startswith('image/'):
        return None
    return data, content_type.split(';')[0].strip()
