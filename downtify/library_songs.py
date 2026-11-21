"""The library's files by song, so an artist watch never downloads a
song the library already holds under another name.

An artist watch lists its releases on YouTube Music, while a playlist
download is named from Spotify's metadata - and the two spell the same
song differently: ``Way 2 Sexy (with Future & Young Thug)`` on Spotify
is ``Way 2 Sexy (feat. Future & Young Thug)`` on YouTube Music, with
``Future & Young Thug`` instead of ``Future, Young Thug`` in the
artists. The file name the output template renders differs, so the
name-based "already downloaded" check misses it and the song is fetched
a second time. The same happens inside one artist's catalogue: a single
that is also on the album, an album and its deluxe edition.

A song here is :func:`downtify.library_catalog.song_key` - the first
artist and the title, with ``(feat. …)`` / ``(with …)`` / remaster tags
folded away - plus its length: two files of one key whose lengths
differ by more than :data:`SAME_SONG_SECONDS` are different recordings
(a live version, an extended mix) and are never taken for each other.
A file or a track whose length is unknown never matches.

Deezer adds a few more spellings of the very same recording: ``(Album
Version)``, ``(Explicit Version)``, ``(Explicit)``, ``- Original Mix``
and the like are folded away too (:data:`_SAME_RECORDING_TAG`). So is
the film a soundtrack song comes from, which Indian labels add on one
catalogue and not another: ``Tum Hi Ho (From "Aashiqui 2")`` is the
``Tum Hi Ho`` MusicBrainz and Spotify list. Words that name another
recording - ``Clean``, ``Radio Edit``, ``Live``, ``Remix`` - are kept,
and the length must agree as well.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Optional

from .isrc import normalize as normalize_isrc
from .library_catalog import song_key
from .library_metadata import read_audio_metadata
from .library_paths import SLSKD_LIBRARY_PREFIX

#: Lengths (seconds) of one song in two sources differ by a second or
#: two (encoder padding, rounding); a different recording by far more.
SAME_SONG_SECONDS = 3.0

#: Two files with one ISRC are the same recording; a length further off
#: than this is a mislabelled one (an extended mix tagged with the
#: single's code).
ISRC_SECONDS = 10.0

#: Title tags that name no other recording: the album's (explicit)
#: version, or the film a song is from, as one catalogue spells it and
#: another leaves out.
_SAME_RECORDING_TAG = re.compile(
    r'\s*(?:[([]\s*(?:album|explicit|original|lp)(?:\s+(?:version|mix))?\s*'
    r'[)\]]|\s-\s(?:album|explicit|original|lp)\s+(?:version|mix)\s*$'
    r'|[([]\s*from\s[^)\]]*[)\]])',
    re.IGNORECASE,
)


def _length(value: Any) -> float:
    try:
        return max(0.0, float(value or 0))
    except (TypeError, ValueError):
        return 0.0


def _key(artists: Any, title: Any) -> str:
    if isinstance(artists, (list, tuple)):
        first = str(artists[0]) if artists else ''
    else:
        first = str(artists or '')
    key = song_key(first, _SAME_RECORDING_TAG.sub('', str(title or '')))
    # Both halves are needed: a title alone matches too much.
    return '' if key.startswith('|') or key.endswith('|') else key


def same_recording(path: Path, song: dict[str, Any]) -> bool:
    """Whether the file at *path* holds *song*: the same ISRC (a length
    within :data:`ISRC_SECONDS`), else the same song key and a length
    within :data:`SAME_SONG_SECONDS`, from the file's own tags."""

    key = _key(song.get('artists'), song.get('name'))
    length = _length(song.get('duration'))
    code = normalize_isrc(song.get('isrc'))
    if not code and (not key or length <= 0):
        return False
    try:
        tags = read_audio_metadata(path)
    except Exception:
        return False
    found = _length(tags.get('duration'))
    if code and normalize_isrc(tags.get('isrc')) == code:
        return not (found and length) or abs(found - length) <= ISRC_SECONDS
    if not key or length <= 0:
        return False
    return (
        found > 0
        and abs(found - length) <= SAME_SONG_SECONDS
        and _key(tags.get('artists') or tags.get('artist'), tags.get('title'))
        == key
    )


class LibrarySongs:
    """Library files by song (see the module docstring).

    Built from library listing rows (``file``, ``artist``, ``title``,
    ``duration``). :meth:`add` records a file downloaded meanwhile, so a
    later release of the same sweep finds it too.
    """

    def __init__(self, rows: Iterable[dict[str, Any]] = ()) -> None:
        self._songs: dict[str, list[tuple[str, float]]] = defaultdict(list)
        self._isrcs: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for row in rows:
            self._put(
                str(row.get('file') or ''),
                _key(row.get('artist'), row.get('title')),
                _length(row.get('duration')),
                row.get('isrc'),
            )

    def _put(self, name: str, key: str, length: float, isrc: Any = '') -> None:
        name = name.strip().replace('\\', '/')
        if name and key and length > 0:
            self._songs[key].append((name, length))
        code = normalize_isrc(isrc)
        if name and code:
            self._isrcs[code].append((name, length))

    def add(self, filename: str, song: dict[str, Any]) -> None:
        """Remember *filename* as holding *song*."""

        self._put(
            filename,
            _key(song.get('artists'), song.get('name')),
            _length(song.get('duration')),
            song.get('isrc'),
        )

    def find(self, song: dict[str, Any]) -> Optional[str]:
        """The library file already holding *song*, else ``None``.

        The closest length wins; a file outside slskd's folder is
        preferred over one in it.
        """

        length = _length(song.get('duration'))
        # The recording's own code first: the same recording whatever the
        # titles say (a length far off is another edit sharing a code).
        by_code = [
            (name.startswith(SLSKD_LIBRARY_PREFIX), abs(other - length), name)
            for name, other in self._isrcs.get(
                normalize_isrc(song.get('isrc')), ()
            )
            if not (length and other) or abs(other - length) <= ISRC_SECONDS
        ]
        if by_code:
            return min(by_code)[2]
        key = _key(song.get('artists'), song.get('name'))
        if not key or length <= 0:
            return None
        close = [
            (name.startswith(SLSKD_LIBRARY_PREFIX), abs(other - length), name)
            for name, other in self._songs.get(key, ())
            if abs(other - length) <= SAME_SONG_SECONDS
        ]
        return min(close)[2] if close else None
