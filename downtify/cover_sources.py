"""Find the best cover art available for a track.

A track's own source often offers a small cover - Spotify's largest is
640px, and a library downloaded by an older Downtify often carries 300px
- while the same release is published at 1400px or more elsewhere. This
module asks the known sources (Spotify, iTunes, YouTube Music, Deezer)
for the release's cover at the configured size, all at once, measures
what comes back, and hands back the one the user's preference asks for.

iTunes and YouTube Music resize their master image to the size asked
for, and send the master itself when it is smaller - never an enlarged
copy (measured: asking for 3000px gives 1400-3000px masters) - so a
cover's measured size is its real detail.

Nothing here writes to a file; downloads (:mod:`downtify.downloader`)
and :mod:`downtify.library_upgrade` decide whether a candidate is worth
embedding.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import httpx
from loguru import logger

from . import deezer, itunes, providers, spotify
from .cover_art import extract_cover_art
from .file_naming import file_name_key, title_key
from .image_size import image_short_side

_TIMEOUT = 20

SOURCE_FILE = 'file'
SOURCE_SPOTIFY = 'spotify'
SOURCE_ITUNES = 'itunes'
SOURCE_YOUTUBE = 'youtube-music'
SOURCE_DEEZER = 'deezer'

#: Settings values for "where should artwork come from".
PREFERENCE_HIGHEST = 'highest'
ARTWORK_SOURCES = (
    PREFERENCE_HIGHEST,
    SOURCE_SPOTIFY,
    SOURCE_ITUNES,
    SOURCE_YOUTUBE,
)


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
    """Point a small Spotify image URL at the largest published size (on
    either of Spotify's image hosts, see :func:`spotify.largest_cover_url`).
    A library tagged from the 300px variant gets the 640px one without
    another API call."""

    return spotify.largest_cover_url(url)


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


def _artist_and_title(song: dict[str, Any]) -> tuple[str, str]:
    artists = song.get('artists') or []
    artist = artists[0] if artists else (song.get('artist') or '')
    title = song.get('name') or song.get('title') or ''
    return str(artist), str(title)


def same_song(song: dict[str, Any], artists: list[str], title: str) -> bool:
    """Whether a search result by *artists* called *title* is *song*:
    the titles match (ignoring ``(Deluxe)``/`` - Live`` style suffixes,
    see :func:`title_key`) and *song*'s first artist is among *artists* -
    so another song's or another artist's cover is never taken."""

    artist, wanted = _artist_and_title(song)
    wanted_title = title_key(wanted)
    wanted_artist = file_name_key(artist)
    if not wanted_title or not wanted_artist:
        return False
    if title_key(title) != wanted_title:
        return False
    return any(file_name_key(a) == wanted_artist for a in artists)


def _youtube_cover_url(song: dict[str, Any], px: int) -> str:
    """The cover of *song*'s YouTube Music release, *px* wide."""

    artist, title = _artist_and_title(song)
    if not title:
        return ''
    try:
        results = providers.search_songs(f'{artist} {title}'.strip(), limit=5)
    except Exception:
        logger.debug('Cover lookup: YouTube Music search failed')
        return ''
    for result in results:
        url = str(result.get('cover_url') or '')
        names = [str(a) for a in result.get('artists') or []]
        if url and same_song(song, names, str(result.get('name') or '')):
            return providers.resize_thumbnail(url, px)
    return ''


def _deezer_cover_url(song: dict[str, Any], px: int) -> str:
    artist, title = _artist_and_title(song)
    if not title:
        return ''
    try:
        return deezer.find_track_cover(artist, title, px)
    except Exception:
        logger.debug('Cover lookup: Deezer search failed')
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


def _source_url(source: str, song: dict[str, Any], px: int) -> str:
    if source == SOURCE_SPOTIFY:
        return _spotify_cover_url(song)
    if source == SOURCE_ITUNES:
        return itunes.fetch_artwork_url(song, size=px)
    if source == SOURCE_YOUTUBE:
        return _youtube_cover_url(song, px)
    if source == SOURCE_DEEZER:
        return _deezer_cover_url(song, px)
    return ''


def _candidate_from(
    source: str, song: dict[str, Any], px: int
) -> Optional[CoverCandidate]:
    try:
        return _candidate(source, _source_url(source, song, px))
    except Exception:
        logger.opt(exception=True).debug('Cover lookup: {} failed', source)
        return None


def collect_candidates(
    song: dict[str, Any],
    *,
    sources: tuple[str, ...],
    px: Optional[int] = None,
) -> list[CoverCandidate]:
    """Fetch and measure one cover per requested source, all at once,
    each asked for *px* pixels (the configured cover size by default,
    see :func:`providers.cover_resolution`); returned in *sources*'
    order."""

    size = px or providers.cover_resolution()
    if not sources:
        return []
    with ThreadPoolExecutor(
        max_workers=len(sources), thread_name_prefix='downtify-cover'
    ) as pool:
        futures = [
            pool.submit(_candidate_from, source, song, size)
            for source in sources
        ]
        results = [future.result() for future in futures]
    return [c for c in results if c is not None]


def _preferred_order(preference: str) -> tuple[str, ...]:
    remote = (SOURCE_SPOTIFY, SOURCE_ITUNES, SOURCE_YOUTUBE, SOURCE_DEEZER)
    if preference in remote:
        return (preference,) + tuple(s for s in remote if s != preference)
    return remote


def best_cover(
    song: dict[str, Any],
    *,
    current: Optional[CoverCandidate],
    preference: str = PREFERENCE_HIGHEST,
    px: Optional[int] = None,
) -> Optional[CoverCandidate]:
    """The cover worth embedding, or ``None`` to leave the file alone.

    With a named preference, that source wins as long as it beats what
    the file already has; the others are only tried when it has nothing.
    With ``highest`` every source is asked and the largest image wins.
    A candidate has to be strictly larger than the current cover, so a
    re-run never rewrites a file for nothing. Each source is asked for
    *px* pixels (the configured cover size by default).
    """

    have = current.width if current else 0
    order = _preferred_order(preference)

    if preference == PREFERENCE_HIGHEST:
        candidates = collect_candidates(song, sources=order, px=px)
    else:
        candidates = []
        for source in order:
            candidates = collect_candidates(song, sources=(source,), px=px)
            if candidates:
                # The preferred source answered; the rest are a fallback
                # for when it has nothing at all, not a size contest.
                break

    if not candidates:
        return None
    best = max(candidates, key=lambda c: c.width)
    return best if best.width > have else None
