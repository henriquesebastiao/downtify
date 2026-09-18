"""Find the best cover art available for a track already on disk.

A library downloaded by an older Downtify often carries the smallest
image its source offered — 300x300 is common — while the same release is
published at 1200px or more elsewhere. This module gathers the covers
the known sources can offer for one track, measures them, and hands back
the one the user's preference asks for.

Nothing here writes to the file; :mod:`downtify.library_upgrade` decides
whether a candidate is worth embedding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import httpx
from loguru import logger

from . import itunes, providers, spotify
from .cover_art import extract_cover_art
from .image_size import image_short_side

_TIMEOUT = 20

#: What to ask iTunes for. Their CDN happily resizes past the master, so
#: a larger request is measured like any other candidate rather than
#: trusted.
ITUNES_REQUEST_PX = 1200

SOURCE_FILE = 'file'
SOURCE_SPOTIFY = 'spotify'
SOURCE_ITUNES = 'itunes'
SOURCE_YOUTUBE = 'youtube-music'

#: Settings values for "where should artwork come from".
PREFERENCE_HIGHEST = 'highest'
ARTWORK_SOURCES = (
    PREFERENCE_HIGHEST,
    SOURCE_SPOTIFY,
    SOURCE_ITUNES,
    SOURCE_YOUTUBE,
)

#: Spotify serves one image per size under a fixed id prefix. A library
#: tagged from the 300px variant can be pointed at the 640px one without
#: another API call.
_SPOTIFY_SIZE_PREFIXES = ('ab67616d00001e02', 'ab67616d00004851')
_SPOTIFY_LARGEST_PREFIX = 'ab67616d0000b273'
_SPOTIFY_IMAGE_HOST = 'i.scdn.co/image/'


@dataclass(frozen=True)
class CoverCandidate:
    """One cover image, already fetched and measured."""

    source: str
    data: bytes
    width: int
    url: str = ''

    @property
    def size_label(self) -> str:
        return f'{self.width}x{self.width}' if self.width else 'unknown'


def spotify_upgrade_url(url: str) -> str:
    """Point a small Spotify image URL at the largest published size."""

    if not url or _SPOTIFY_IMAGE_HOST not in url:
        return url
    for prefix in _SPOTIFY_SIZE_PREFIXES:
        if prefix in url:
            return url.replace(prefix, _SPOTIFY_LARGEST_PREFIX)
    return url


def _fetch(url: str) -> Optional[bytes]:
    if not url:
        return None
    try:
        resp = httpx.get(url, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        logger.debug('Cover fetch failed: {}', url[:120])
        return None
    data = resp.content
    return data if data else None


def _candidate(source: str, url: str) -> Optional[CoverCandidate]:
    data = _fetch(url)
    if data is None:
        return None
    width = image_short_side(data)
    if not width:
        return None
    return CoverCandidate(source=source, data=data, width=width, url=url)


def _youtube_cover_url(song: dict[str, Any]) -> str:
    """A YouTube Music thumbnail for *song*, at the configured size."""

    artists = song.get('artists') or []
    artist = artists[0] if artists else (song.get('artist') or '')
    title = song.get('name') or song.get('title') or ''
    query = f'{artist} {title}'.strip()
    if not title:
        return ''
    try:
        results = providers.search_songs(query, limit=3)
    except Exception:
        logger.debug('Cover lookup: YouTube Music search failed')
        return ''
    for result in results:
        url = str(result.get('cover_url') or '')
        if url:
            return url
    return ''


def _spotify_cover_url(song: dict[str, Any]) -> str:
    url = spotify_upgrade_url(str(song.get('cover_url') or ''))
    if url:
        return url
    track_id = str(song.get('song_id') or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9]{22}', track_id):
        return ''
    try:
        fetched = spotify.track_from_id(track_id)
    except Exception:
        logger.debug('Cover lookup: Spotify track {} failed', track_id)
        return ''
    return spotify_upgrade_url(str((fetched or {}).get('cover_url') or ''))


def current_cover(path: Path) -> Optional[CoverCandidate]:
    """The cover already embedded in (or sitting next to) *path*."""

    data, _mime = extract_cover_art(path)
    if not data:
        return None
    return CoverCandidate(
        source=SOURCE_FILE, data=data, width=image_short_side(data)
    )


def collect_candidates(
    song: dict[str, Any], *, sources: tuple[str, ...]
) -> list[CoverCandidate]:
    """Fetch and measure one cover per requested source, in order."""

    found: list[CoverCandidate] = []
    for source in sources:
        if source == SOURCE_SPOTIFY:
            url = _spotify_cover_url(song)
        elif source == SOURCE_ITUNES:
            url = itunes.fetch_artwork_url(song, size=ITUNES_REQUEST_PX)
        elif source == SOURCE_YOUTUBE:
            url = _youtube_cover_url(song)
        else:
            continue
        candidate = _candidate(source, url)
        if candidate is not None:
            found.append(candidate)
    return found


def _preferred_order(preference: str) -> tuple[str, ...]:
    remote = (SOURCE_SPOTIFY, SOURCE_ITUNES, SOURCE_YOUTUBE)
    if preference in remote:
        return (preference,) + tuple(s for s in remote if s != preference)
    return remote


def best_cover(
    song: dict[str, Any],
    *,
    current: Optional[CoverCandidate],
    preference: str = PREFERENCE_HIGHEST,
) -> Optional[CoverCandidate]:
    """The cover worth embedding, or ``None`` to leave the file alone.

    With a named preference, that source wins as long as it beats what
    the file already has; the others are only tried when it has nothing.
    With ``highest`` every source is asked and the largest image wins.
    A candidate has to be strictly larger than the current cover, so a
    re-run never rewrites a file for nothing.
    """

    have = current.width if current else 0
    order = _preferred_order(preference)

    if preference == PREFERENCE_HIGHEST:
        candidates = collect_candidates(song, sources=order)
    else:
        candidates = []
        for source in order:
            candidates = collect_candidates(song, sources=(source,))
            if candidates:
                # The preferred source answered; the rest are a fallback
                # for when it has nothing at all, not a size contest.
                break

    if not candidates:
        return None
    best = max(candidates, key=lambda c: c.width)
    return best if best.width > have else None
