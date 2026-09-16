"""Lyrics providers used to enrich downloaded audio files.

Currently only ``lrclib`` (https://lrclib.net) is implemented. The legacy
``genius``/``musixmatch``/``azlyrics`` identifiers from the spotdl-era UI
are accepted as no-ops so existing settings keep round-tripping cleanly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import httpx
from loguru import logger
from mutagen import File as MutagenFile
from mutagen.id3 import ID3

LRCLIB_BASE = 'https://lrclib.net/api'
_USER_AGENT = 'Downtify (https://github.com/henriquesebastiao/downtify)'

SUPPORTED_PROVIDERS = {'lrclib'}


@dataclass
class Lyrics:
    plain: Optional[str] = None
    synced: Optional[str] = None

    def has_any(self) -> bool:
        return bool(self.plain) or bool(self.synced)


def fetch(song: dict[str, Any], providers: list[str]) -> Optional[Lyrics]:
    """Try each provider in order; return the first successful match."""

    for name in providers:
        if name not in SUPPORTED_PROVIDERS:
            continue
        try:
            result = _PROVIDER_FNS[name](song)
        except Exception:
            logger.exception('Lyrics provider {!r} failed', name)
            continue
        if result and result.has_any():
            return result
    return None


def _fetch_lrclib(song: dict[str, Any]) -> Optional[Lyrics]:
    artists = song.get('artists') or []
    title = (song.get('name') or '').strip()
    if not title or not artists:
        return None

    params = {
        'track_name': title,
        'artist_name': artists[0],
    }
    album = (song.get('album_name') or '').strip()
    if album:
        params['album_name'] = album
    duration = song.get('duration') or 0
    if duration:
        params['duration'] = int(duration)

    try:
        response = httpx.get(
            f'{LRCLIB_BASE}/get',
            params=params,
            headers={'User-Agent': _USER_AGENT},
            timeout=10,
        )
    except httpx.RequestError:
        logger.opt(exception=True).warning('lrclib request failed')
        return None

    if response.status_code == 404:
        return None
    if response.status_code != 200:
        logger.warning(
            'lrclib returned HTTP {} for {!r}', response.status_code, title
        )
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    plain = (data.get('plainLyrics') or '').strip() or None
    synced = (data.get('syncedLyrics') or '').strip() or None
    if not plain and not synced:
        return None
    return Lyrics(plain=plain, synced=synced)


_PROVIDER_FNS = {
    'lrclib': _fetch_lrclib,
}


#: Tag keys the downloader embeds plain lyrics under, per container:
#: ID3 ``USLT`` frames (MP3), MP4 ``©lyr`` and Vorbis-comment ``lyrics``
#: (FLAC, Ogg Vorbis, Opus). See ``downloader.embed_lyrics``.
_MP4_LYRICS_KEY = '\xa9lyr'
_VORBIS_LYRICS_KEY = 'lyrics'


def _file_tags(path: Path) -> Any:
    try:
        audio = MutagenFile(str(path))
    except Exception:
        audio = None
    tags = getattr(audio, 'tags', None)
    if tags or path.suffix.lower() != '.mp3':
        return tags
    # MP3s mutagen can't identify as audio still carry an ID3 header.
    try:
        return ID3(str(path))
    except Exception:
        return None


def _embedded_lyrics(path: Path) -> str:
    tags = _file_tags(path)
    if not tags:
        return ''
    if hasattr(tags, 'getall'):
        frames = tags.getall('USLT')
        return str(frames[0].text).strip() if frames else ''
    for key in (_MP4_LYRICS_KEY, _VORBIS_LYRICS_KEY):
        value = tags.get(key)
        if value:
            first = value[0] if isinstance(value, list) else value
            return str(first).strip()
    return ''


def read_track_lyrics(path: Path) -> dict[str, str]:
    """Lyrics saved with a downloaded track.

    ``synced`` is the LRC text of the ``.lrc`` sidecar (empty when there
    is none); ``plain`` is the text embedded in the file's tags. Either
    can be empty. Unreadable files count as having no lyrics.
    """

    synced = ''
    sidecar = path.with_suffix('.lrc')
    if sidecar.is_file():
        try:
            synced = sidecar.read_text(encoding='utf-8').strip()
        except (OSError, UnicodeDecodeError):
            logger.opt(exception=True).warning(
                'Could not read LRC sidecar {}', sidecar
            )
    return {'synced': synced, 'plain': _embedded_lyrics(path)}
