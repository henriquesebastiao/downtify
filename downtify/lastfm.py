"""Similar-track lookup via the Last.fm API (``track.getSimilar``).

The user brings their own API key (a free key from
``https://www.last.fm/api/account/create``), stored in settings as
``lastfm_api_key`` (Settings → Audio sources). This module only talks to
Last.fm and shapes its answer; the HTTP endpoint lives in
``downtify.api`` (``GET /api/similar/tracks``).

Failures surface as :class:`ValueError` (same convention as
:mod:`downtify.deezer`), so the endpoint maps them to ``502``.
"""

from __future__ import annotations

from typing import Any

import httpx

_LASTFM_URL = 'https://ws.audioscrobbler.com/2.0/'
_TIMEOUT = 10
_MAX_LIMIT = 50


def _image_url(images: Any) -> str:
    """The largest ``extralarge``/``large`` image of a Last.fm track."""

    if not isinstance(images, list):
        return ''
    by_size = {
        str(img.get('size') or ''): str(img.get('#text') or '')
        for img in images
        if isinstance(img, dict)
    }
    for size in ('extralarge', 'large', 'medium', 'small'):
        if by_size.get(size):
            return by_size[size]
    return ''


def _similar_track(entry: Any) -> dict[str, Any] | None:
    """One ``track.getSimilar`` entry shaped for the Similar page."""

    if not isinstance(entry, dict):
        return None
    title = str(entry.get('name') or '').strip()
    artist = ''
    raw_artist = entry.get('artist')
    if isinstance(raw_artist, dict):
        artist = str(raw_artist.get('name') or '').strip()
    else:
        artist = str(raw_artist or '').strip()
    if not title or not artist:
        return None
    try:
        match = float(entry.get('match') or 0)
    except (TypeError, ValueError):
        match = 0.0
    return {
        'title': title,
        'artist': artist,
        'match': round(max(0.0, min(1.0, match)), 4),
        'url': str(entry.get('url') or '').strip(),
        'image_url': _image_url(entry.get('image')),
    }


def get_similar_tracks(
    artist: str,
    track: str,
    api_key: str,
    *,
    limit: int = 20,
) -> dict[str, Any]:
    """Tracks similar to *track* by *artist* (Last.fm ``track.getSimilar``).

    Returns ``{'artist', 'track', 'tracks': [...]}`` where each track is
    ``{title, artist, match, url, image_url}``. Raises :class:`ValueError`
    when the key is missing, Last.fm reports an error, or it can't be
    reached.
    """

    artist = str(artist or '').strip()
    track = str(track or '').strip()
    api_key = str(api_key or '').strip()
    if not artist or not track:
        raise ValueError('artist and track are required')
    if not api_key:
        raise ValueError(
            'No Last.fm API key: set one in Settings → Audio sources'
        )
    limit = max(1, min(_MAX_LIMIT, int(limit or 20)))
    try:
        resp = httpx.get(
            _LASTFM_URL,
            params={
                'method': 'track.getsimilar',
                'artist': artist,
                'track': track,
                'api_key': api_key,
                'format': 'json',
                'autocorrect': '1',
                'limit': str(limit),
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f'Last.fm did not answer: {exc}') from exc
    if not isinstance(payload, dict):
        raise ValueError('Last.fm answered with an unreadable reply')
    if 'error' in payload:
        raise ValueError(
            str(payload.get('message') or 'Last.fm reported an error')
        )
    raw = (payload.get('similartracks') or {}).get('track') or []
    if isinstance(raw, dict):
        raw = [raw]
    tracks = []
    for entry in raw:
        shaped = _similar_track(entry)
        if shaped is not None:
            tracks.append(shaped)
    return {'artist': artist, 'track': track, 'tracks': tracks[:limit]}
