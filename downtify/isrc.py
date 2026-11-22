"""ISRC codes: the recording's own ID, written into every download.

An ISRC (International Standard Recording Code) is the code a label gives
a recording - ``USCM51600061`` is Drake's *Keep The Family Close* - and
every streaming catalogue carries it. Two files with the same ISRC hold
the same recording whatever their titles say (*Tum Hi Ho* and *Tum Hi Ho
(From "Aashiqui 2")*, a ``feat.`` one catalogue adds and another leaves
out), so Downtify matches a song the library already has by it first
(:mod:`downtify.library_songs`), and its name and length only after.

Unlike MusicBrainz IDs, an ISRC is not part of how Navidrome tells songs
and albums apart (its persistent IDs), so writing one into a file it
already knows changes nothing there.

Where a download's ISRC comes from (:func:`for_song`):

* the song itself, when its catalogue gave one (MusicBrainz);
* Deezer's track, for a song from Deezer (its album and playlist rows
  leave the code out; the track itself has it);
* otherwise a Deezer search: only a result with the same first artist and
  title (as :mod:`downtify.library_songs` compares them) and a length
  within :data:`LENGTH_SECONDS`, and only when every such result agrees
  on the code. Anything less certain writes nothing.

Tags: ``TSRC`` in MP3s, ``ISRC`` in FLAC, Ogg and Opus, and the iTunes
``ISRC`` atom in M4A - what MusicBrainz Picard and players read.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from mutagen import File as MutagenFile
from mutagen.id3 import ID3, TSRC, ID3NoHeaderError
from mutagen.mp4 import MP4, MP4FreeForm

#: Two catalogues' lengths of one recording differ by a few seconds
#: (Spotify has Drake's *Keep The Family Close* at 328 s, Deezer at 331 s):
#: the library's own same-song tolerance
#: (:data:`downtify.library_songs.SAME_SONG_SECONDS`).
LENGTH_SECONDS = 3.0

_SEARCH_URL = 'https://api.deezer.com/search'
_TRACK_URL = 'https://api.deezer.com/track/'
_MP4_KEY = '----:com.apple.iTunes:ISRC'
_FORM = re.compile(r'^[A-Z]{2}[A-Z0-9]{3}\d{7}$')


def normalize(value: Any) -> str:
    """*value* as a 12-character ISRC (``US-CM5-16-00061`` and
    ``uscm51600061`` both read ``USCM51600061``), ``''`` when it isn't
    one."""

    code = re.sub(r'[\s-]', '', str(value or '')).upper()
    return code if _FORM.match(code) else ''


# ── Tags ────────────────────────────────────────────────────────────────


def read(path: Path) -> str:
    """The ISRC tag of an audio file, ``''`` without one."""

    suffix = path.suffix.lower()
    try:
        if suffix == '.mp3':
            frames = ID3(str(path)).getall('TSRC')
            return normalize(frames[0].text[0]) if frames else ''
        audio = MutagenFile(str(path))
    except (ID3NoHeaderError, Exception):  # noqa: BLE001  # unreadable: none
        return ''
    if audio is None or audio.tags is None:
        return ''
    if isinstance(audio, MP4):
        values = audio.tags.get(_MP4_KEY) or []
        return (
            normalize(bytes(values[0]).decode('utf-8', 'replace'))
            if values
            else ''
        )
    values = audio.tags.get('isrc') or audio.tags.get('ISRC') or []
    return normalize(values[0]) if values else ''


def write(path: Path, code: str) -> bool:
    """Write *code* as *path*'s ISRC tag (replacing one there). Whether
    it was written."""

    code = normalize(code)
    if not code or not path.is_file():
        return False
    suffix = path.suffix.lower()
    try:
        if suffix == '.mp3':
            try:
                tags = ID3(str(path))
            except ID3NoHeaderError:
                tags = ID3()
            version = tags.version[1] if tags.version[1] in {3, 4} else 4
            tags.setall('TSRC', [TSRC(encoding=3, text=[code])])
            tags.save(str(path), v2_version=version)
            return True
        audio = MutagenFile(str(path))
        if audio is None:
            return False
        if audio.tags is None:
            audio.add_tags()
        if isinstance(audio, MP4):
            audio.tags[_MP4_KEY] = [MP4FreeForm(code.encode('utf-8'))]
        else:
            audio.tags['ISRC'] = [code]
        audio.save()
        return True
    except Exception:
        logger.opt(exception=True).warning(
            'Could not write the ISRC of {}', path.name
        )
        return False


# ── Finding a song's ISRC ───────────────────────────────────────────────


def _same_song(song: dict[str, Any], row: dict[str, Any]) -> bool:
    # Imported here: the library reads tags through this module.
    from .library_songs import _key  # noqa: PLC0415

    artist = row.get('artist') if isinstance(row.get('artist'), dict) else {}
    wanted = _key(
        song.get('artists') or [song.get('artist')], song.get('name')
    )
    found = _key([artist.get('name')], row.get('title'))
    if not wanted or wanted != found:
        return False
    length = float(song.get('duration') or 0)
    other = float(row.get('duration') or 0)
    return bool(length and other) and abs(length - other) <= LENGTH_SECONDS


def _track_isrc(track_id: Any) -> str:
    from . import deezer  # noqa: PLC0415  # see _same_song

    try:
        return normalize(
            deezer._get_json(f'{_TRACK_URL}{track_id}').get('isrc')
        )  # noqa: SLF001
    except ValueError:
        return ''


def find_on_deezer(song: dict[str, Any]) -> str:
    """The ISRC of *song* on Deezer, when the search finds it beyond doubt
    (see the module notes); ``''`` otherwise, including when Deezer
    doesn't answer."""

    artists = song.get('artists') or []
    first = str(artists[0] if artists else song.get('artist') or '').strip()
    title = str(song.get('name') or '').strip()
    if not first or not title or not song.get('duration'):
        return ''
    from . import deezer  # noqa: PLC0415  # see _same_song

    try:
        rows = (
            deezer._get_json(  # noqa: SLF001
                _SEARCH_URL, q=f'{first} {title}', limit=10
            ).get('data')
            or []
        )
    except ValueError:
        return ''
    matches = [r for r in rows if isinstance(r, dict) and _same_song(song, r)]
    codes = {_track_isrc(r.get('id')) for r in matches[:3]}
    codes.discard('')
    return codes.pop() if len(codes) == 1 else ''


def for_song(song: dict[str, Any]) -> str:
    """The ISRC to write into *song*'s file (see the module notes), or
    ``''``."""

    known = normalize(song.get('isrc'))
    if known:
        return known
    song_id = str(song.get('song_id') or '')
    if song_id.startswith('deezer-') and song_id[len('deezer-') :].isdigit():
        found = _track_isrc(song_id[len('deezer-') :])
        if found:
            return found
    return find_on_deezer(song)


def lookup(song: dict[str, Any]) -> Optional[str]:
    """:func:`for_song` that never raises (a download's side lookup)."""

    try:
        return for_song(song) or None
    except Exception:
        logger.opt(exception=True).debug(
            'ISRC lookup failed for {}', song.get('name')
        )
        return None
