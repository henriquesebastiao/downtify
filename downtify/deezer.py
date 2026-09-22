"""Search the public Deezer API for artist photo candidates.

``api.deezer.com`` is unauthenticated and keyless, same shape of
integration as :mod:`downtify.itunes`. Deezer's artist search never
returns a banner-shaped image, only square profile photos.
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

_SEARCH_URL = 'https://api.deezer.com/search/artist'
_TIMEOUT = 10


def search_artist(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Artist photo candidates for *query*, largest Deezer offers each.

    Each result is ``{source: 'deezer', name, image_url, url}`` - same
    shape the artist-image picker expects from every source.
    """

    text = query.strip()
    if not text:
        return []
    try:
        resp = httpx.get(
            _SEARCH_URL,
            params={'q': text, 'limit': max(1, limit)},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.opt(exception=True).debug('Deezer artist search failed')
        return []

    results: list[dict[str, Any]] = []
    for row in data.get('data') or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get('name') or '').strip()
        image = (
            row.get('picture_xl')
            or row.get('picture_big')
            or row.get('picture_medium')
            or ''
        )
        if not name or not image:
            continue
        results.append({
            'source': 'deezer',
            'name': name,
            'image_url': image,
            'url': row.get('link') or '',
        })
    return results
