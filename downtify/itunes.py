"""Fetch genre metadata from the iTunes Search API.

The public ``itunes.apple.com/search`` endpoint returns
``primaryGenreName`` for every song result — no API key or
authentication required.  This module provides a single entry-point,
:func:`fetch_genre`, that looks up a track and returns the genre
string (or ``""`` when nothing matches).
"""

from __future__ import annotations

import re
import time
import unicodedata
from threading import Lock
from typing import Any, Optional
from urllib.parse import quote_plus

import requests
from loguru import logger

_ITUNES_SEARCH_URL = 'https://itunes.apple.com/search'
_TIMEOUT = 10  # seconds
_MIN_INTERVAL = 0.35  # seconds between API calls (rate-limit courtesy)

# ── In-memory cache ────────────────────────────────────────────────
# key = "normalized_artist|normalized_album" → genre string.
# Avoids repeated API calls when downloading a full album (all tracks
# share the same album and therefore the same genre).
_genre_cache: dict[str, str] = {}
_cache_lock = Lock()

# Timestamp of the last outgoing request – used for rate pacing.
_last_request_time: float = 0.0
_rate_lock = Lock()


# ── Text normalisation ────────────────────────────────────────────
def _normalise(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    if not text:
        return ''
    # Decompose → strip combining marks → recompose
    nfkd = unicodedata.normalize('NFKD', text)
    stripped = ''.join(
        ch for ch in nfkd if unicodedata.category(ch) != 'Mn'
    )
    folded = stripped.casefold()
    # Remove common noise: feat., ft., parenthetical extras
    folded = re.sub(r'\s*\(.*?\)', '', folded)
    folded = re.sub(r'\s*\[.*?\]', '', folded)
    folded = re.sub(r'\b(feat\.?|ft\.?)\b.*', '', folded)
    return re.sub(r'\s+', ' ', folded).strip()


def _names_match(a: str, b: str) -> bool:
    """Fuzzy comparison after normalisation."""
    na, nb = _normalise(a), _normalise(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    # One contains the other (handles "Arctic Monkeys" vs
    # "Arctic Monkeys & …" or "Do I Wanna Know?" vs
    # "Do I Wanna Know? - Single Version").
    return na in nb or nb in na


# ── iTunes API call ───────────────────────────────────────────────
def _rate_wait() -> None:
    """Block until at least ``_MIN_INTERVAL`` seconds have elapsed
    since the last request."""
    global _last_request_time
    with _rate_lock:
        now = time.monotonic()
        wait = _MIN_INTERVAL - (now - _last_request_time)
        if wait > 0:
            time.sleep(wait)
        _last_request_time = time.monotonic()


def _search_itunes(
    query: str, limit: int = 5
) -> list[dict[str, Any]]:
    """Call the iTunes Search API and return the ``results`` list."""
    _rate_wait()
    params = f'term={quote_plus(query)}&entity=song&limit={limit}'
    url = f'{_ITUNES_SEARCH_URL}?{params}'
    logger.debug('iTunes genre lookup: {}', url)
    try:
        resp = requests.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.opt(exception=True).debug('iTunes Search API failed')
        return []
    results = data.get('results') or []
    logger.debug(
        'iTunes Search returned {} result(s) for q={!r}',
        len(results),
        query[:100],
    )
    return results


# ── Best-match selection ──────────────────────────────────────────
def _pick_best(
    results: list[dict[str, Any]],
    artist: str,
    title: str,
) -> Optional[dict[str, Any]]:
    """Return the result whose artist + track name best match."""
    for r in results:
        if r.get('wrapperType') != 'track':
            continue
        if r.get('kind') != 'song':
            continue
        r_artist = r.get('artistName', '')
        r_title = r.get('trackName', '')
        if _names_match(r_artist, artist) and _names_match(r_title, title):
            return r
    # Fallback: accept any result whose title matches (artist may
    # differ due to "feat." / collaboration discrepancies).
    for r in results:
        if r.get('wrapperType') != 'track' or r.get('kind') != 'song':
            continue
        if _names_match(r.get('trackName', ''), title):
            return r
    return None


# ── Public API ────────────────────────────────────────────────────
def fetch_genre(song: dict[str, Any]) -> str:
    """Return the genre string for *song*, or ``""`` if unavailable.

    ``song`` is the standard Downtify track dict with at least
    ``name``, ``artists`` (list[str]) and optionally ``album_name``.
    """

    artists = song.get('artists') or []
    artist = artists[0] if artists else (song.get('artist') or '')
    title = song.get('name', '')
    album = song.get('album_name', '')

    if not artist and not title:
        return ''

    # ── Check album-level cache first ─────────────────────────────
    cache_key = f'{_normalise(artist)}|{_normalise(album)}' if album else ''
    if cache_key:
        with _cache_lock:
            cached = _genre_cache.get(cache_key)
        if cached is not None:
            logger.debug(
                'iTunes genre cache hit: {} → {!r}', cache_key, cached
            )
            return cached

    # ── Search iTunes ─────────────────────────────────────────────
    query = f'{artist} {title}'.strip()
    results = _search_itunes(query, limit=5)
    match = _pick_best(results, artist, title)

    if match is None and album:
        # Retry with album name in query for disambiguation.
        query_alt = f'{artist} {title} {album}'.strip()
        results_alt = _search_itunes(query_alt, limit=5)
        match = _pick_best(results_alt, artist, title)

    genre = ''
    if match:
        genre = (match.get('primaryGenreName') or '').strip()
        logger.info(
            'iTunes genre resolved: {!r} by {!r} → {!r}',
            title,
            artist,
            genre,
        )
    else:
        logger.info(
            'iTunes genre: no match for {!r} by {!r}', title, artist
        )

    # ── Populate album cache ──────────────────────────────────────
    if cache_key and genre:
        with _cache_lock:
            _genre_cache[cache_key] = genre
    elif cache_key:
        # Negative cache: avoid retrying the same album repeatedly.
        with _cache_lock:
            _genre_cache.setdefault(cache_key, '')

    return genre
