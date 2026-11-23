"""Whether a song a client asks for is already in the library (issue #636).

Clients that add songs (the iOS app, direct API calls) can ask the server
to skip a song the library already has instead of downloading a second
copy (``skip_if_in_library``), and ask which of a list of songs it has
(``POST /api/library/lookup`` with ``detailed``). Both use one rule, so
what the lookup reports as owned is what a download skips:

1. **Catalog id** - the same Spotify track (the track index), the same
   YouTube video or SoundCloud track a file was downloaded from (recorded
   since 3.12, :mod:`downtify.download_sources`), or the same ISRC.
2. **Song key** - the same lead artist and title
   (:func:`downtify.library_catalog.song_key`): feat./with credits and
   remaster tags are folded, so a remaster or another release of a song
   counts; "Live", "Acoustic", "Remix" and the like stay in the title, so
   a live version of an owned song does not.

Only rows the caller may see count (``allowed_keys``), so a song an admin
hid from someone is not reported to them as owned.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable
from dataclasses import dataclass, field
from typing import Any, Optional

from .library_catalog import (
    LibraryContext,
    listing_for_request,
    song_key,
)
from .track_index import normalize_spotify_track_id

#: How a match was made, in the order the rules are tried.
CATALOG_ID = 'catalog_id'
SONG_KEY = 'song_key'

_YOUTUBE_ID = re.compile(
    r'(?:[?&]v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])'
)
_BARE_YOUTUBE_ID = re.compile(r'[A-Za-z0-9_-]{11}')


def youtube_id(song: dict[str, Any]) -> str:
    """The YouTube video a song names, ``''`` when none."""

    explicit = str(song.get('youtube_id') or '').strip()
    if explicit:
        return explicit
    song_id = str(song.get('song_id') or '').strip()
    if song.get('source') == 'youtube' and _BARE_YOUTUBE_ID.fullmatch(song_id):
        return song_id
    found = _YOUTUBE_ID.search(str(song.get('url') or ''))
    return found.group(1) if found else ''


def _song_artist(song: dict[str, Any]) -> str:
    artist = str(song.get('artist') or '').strip()
    artists = song.get('artists')
    if not artist and isinstance(artists, list) and artists:
        artist = str(artists[0] or '').strip()
    return artist


def song_key_of(song: dict[str, Any]) -> str:
    """The song key of a request row (``''`` without artist or title)."""

    title = str(song.get('title') or song.get('name') or '').strip()
    key = song_key(_song_artist(song), title)
    return '' if key == '|' else key


@dataclass
class LibraryMatcher:
    """The library, indexed for :meth:`match`. Build one per request with
    :func:`build_matcher`; it reads the library once."""

    rows: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_spotify: dict[str, str] = field(default_factory=dict)
    by_source: dict[str, str] = field(default_factory=dict)
    by_isrc: dict[str, str] = field(default_factory=dict)
    by_key: dict[str, str] = field(default_factory=dict)

    def match(
        self, song: dict[str, Any]
    ) -> Optional[tuple[dict[str, Any], str]]:
        """``(library row, how)`` for the copy of *song* the library has,
        ``how`` being :data:`CATALOG_ID` or :data:`SONG_KEY`; ``None``."""

        if not isinstance(song, dict):
            return None
        for file in self._catalog_files(song):
            row = self.rows.get(file)
            if row is not None:
                return row, CATALOG_ID
        key = song_key_of(song)
        file = self.by_key.get(key) if key else None
        if file is not None:
            return self.rows[file], SONG_KEY
        return None

    def _catalog_files(self, song: dict[str, Any]) -> Iterable[str]:
        spotify = normalize_spotify_track_id(song)
        if spotify and spotify in self.by_spotify:
            yield self.by_spotify[spotify]
        for source in (
            youtube_id(song),
            str(song.get('soundcloud_url') or ''),
        ):
            if source and source in self.by_source:
                yield self.by_source[source]
        isrc = str(song.get('isrc') or '').strip().upper()
        if isrc and isrc in self.by_isrc:
            yield self.by_isrc[isrc]


def build_matcher(
    ctx: LibraryContext,
    *,
    allowed_keys: Optional[Collection[str]] = None,
    track_index: Any = None,
    download_sources: Any = None,
    sources: Iterable[str] = (),
) -> LibraryMatcher:
    """Index the rows the caller may see. *sources* are the videos and
    SoundCloud tracks the request names, looked up in *download_sources*
    (the table is keyed by file, so it is asked only for those)."""

    matcher = LibraryMatcher()
    for entry in listing_for_request(ctx, allowed_keys=allowed_keys):
        file = str(entry.get('file') or '').replace('\\', '/')
        if not file:
            continue
        matcher.rows[file] = entry
        isrc = str(entry.get('isrc') or '').strip().upper()
        if isrc:
            matcher.by_isrc.setdefault(isrc, file)
        key = song_key(
            str(entry.get('artist') or ''), str(entry.get('title') or '')
        )
        if key != '|':
            matcher.by_key.setdefault(key, file)
    if track_index is not None:
        for spotify, file in track_index.filenames_by_spotify_id().items():
            if file in matcher.rows:
                matcher.by_spotify[spotify] = file
    wanted = sorted({s for s in sources if s})
    if download_sources is not None and wanted:
        for source, file in download_sources.files_for_sources(wanted).items():
            if file in matcher.rows:
                matcher.by_source[source] = file
    return matcher


def request_sources(songs: Iterable[Any]) -> list[str]:
    """The videos and SoundCloud tracks *songs* name, for
    :func:`build_matcher`."""

    found: list[str] = []
    for song in songs:
        if not isinstance(song, dict):
            continue
        found.extend(
            source
            for source in (
                youtube_id(song),
                str(song.get('soundcloud_url') or ''),
            )
            if source
        )
    return found
