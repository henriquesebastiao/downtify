"""Lyrics providers used to enrich downloaded audio files.

Two sources are implemented, both free and keyless: ``lrclib``
(https://lrclib.net) and ``netease`` (NetEase Cloud Music). Users put
them in the order they prefer; :func:`fetch` walks that order and stops
at the first provider that has something.

The legacy ``genius``/``musixmatch``/``azlyrics`` identifiers from the
spotdl-era UI are accepted as no-ops so existing settings keep
round-tripping cleanly. They are not implemented: AZLyrics forbids
third-party use of its content, Musixmatch's desktop API hands out an
empty token without credentials, and Genius' robots.txt disallows the
search endpoint needed to find a song's page.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

import httpx
from loguru import logger
from mutagen import File as MutagenFile
from mutagen.id3 import ID3

from .lyrics_cache import song_key

LRCLIB_BASE = 'https://lrclib.net/api'
NETEASE_BASE = 'https://music.163.com/api'
_USER_AGENT = 'Downtify (https://github.com/henriquesebastiao/downtify)'
_TIMEOUT = 10

#: Implemented providers, in the order they are offered by default.
PROVIDER_ORDER = ['lrclib', 'netease']
SUPPORTED_PROVIDERS = set(PROVIDER_ORDER)
#: Accepted in saved settings, but nothing is fetched from them.
LEGACY_PROVIDERS = {'genius', 'musixmatch', 'azlyrics'}


@dataclass
class Lyrics:
    plain: Optional[str] = None
    synced: Optional[str] = None

    def has_any(self) -> bool:
        return bool(self.plain) or bool(self.synced)


def fetch(
    song: dict[str, Any],
    providers: list[str],
    cache: Optional[Any] = None,
) -> Optional[Lyrics]:
    """Try each provider in order; return the first successful match.

    ``cache`` is an optional :class:`~downtify.lyrics_cache.LyricsLookupCache`:
    providers that recently came back empty for this song are skipped, and
    every answer is recorded.
    """

    key = song_key(song) if cache is not None else ''
    for name in providers:
        if name not in SUPPORTED_PROVIDERS:
            continue
        if cache is not None and cache.should_skip(key, name):
            logger.debug('Lyrics: skipping {} (nothing last time)', name)
            continue
        try:
            result = _PROVIDER_FNS[name](song)
        except Exception:
            logger.exception('Lyrics provider {!r} failed', name)
            continue
        found = bool(result and result.has_any())
        if cache is not None:
            cache.record(key, name, found)
        if found:
            if name != providers[0]:
                logger.info(
                    'Lyrics for {!r} came from {}', song.get('name'), name
                )
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


# ── NetEase Cloud Music ──────────────────────────────────────────────
# Its public search and lyric endpoints need no key. Lyrics come as LRC,
# so synced and plain text both fall out of one request.

#: Credits NetEase puts inside the lyric body ("作词 : ..."), dropped so
#: they don't end up in the tag or the .lrc file.
_NETEASE_CREDIT = re.compile(
    r'^(作词|作曲|编曲|制作人|录音|混音|母带|监制|出品|发行|'
    r'lyricist|composer|arranger|producer|mixing|mastering)\s*[:：]',
    re.IGNORECASE,
)
#: NetEase marks instrumentals with this instead of leaving lyrics empty.
_NETEASE_INSTRUMENTAL = '纯音乐'
_LRC_LINE = re.compile(r'^((?:\[\d{1,3}:\d{2}(?:[.:]\d{1,3})?\])+)(.*)$')


def _normalize(text: Any) -> str:
    text = unicodedata.normalize('NFKC', str(text or '')).casefold()
    return re.sub(r'[^\w\s]', ' ', text).strip()


def _netease_get(path: str, params: dict[str, Any]) -> Optional[dict]:
    try:
        response = httpx.get(
            f'{NETEASE_BASE}{path}',
            params=params,
            headers={
                'User-Agent': _USER_AGENT,
                'Referer': 'https://music.163.com/',
            },
            timeout=_TIMEOUT,
        )
    except httpx.RequestError:
        logger.opt(exception=True).warning('NetEase request failed')
        return None
    if response.status_code != 200:
        logger.warning('NetEase returned HTTP {}', response.status_code)
        return None
    try:
        return response.json()
    except ValueError:
        return None


def _core_title(text: Any) -> str:
    """Title without the bracketed extras services add or drop.

    YouTube Music may call a song "起风了（The Wind）" where NetEase has
    just "起风了"; comparing the part before the brackets matches them.
    """

    stripped = re.sub(r'[(\[][^)\]]*[)\]]', ' ', _normalize(text))
    return re.sub(r'\s+', ' ', stripped).strip()


def _netease_score(
    candidate: dict[str, Any], title: str, artist: str, duration: float
) -> float:
    """How well a search hit matches the song (higher is better, <0 rejects)."""

    name = _core_title(candidate.get('name'))
    wanted_title = _core_title(title)
    if not name or not wanted_title:
        return -1
    if name == wanted_title:
        score = 2.0
    elif wanted_title in name or name in wanted_title:
        score = 1.0
    else:
        return -1

    artists = [
        _normalize(a.get('name'))
        for a in (candidate.get('artists') or [])
        if isinstance(a, dict)
    ]
    wanted_artist = _normalize(artist)
    artist_matched = bool(wanted_artist) and any(
        wanted_artist == a or wanted_artist in a or a in wanted_artist
        for a in artists
    )
    if artist_matched:
        score += 2 if wanted_artist in artists else 1

    delta = None
    if duration:
        # NetEase reports milliseconds.
        delta = abs(float(candidate.get('duration') or 0) / 1000 - duration)
        if delta > 15:
            return -1
        score += max(0.0, 1 - delta / 15)

    # Services write artists differently ("馮沁苑LaJiao" vs
    # "冯沁苑(买辣椒也用券)"), so a name that doesn't line up is only
    # accepted when the title and the length both do.
    if not artist_matched and (delta is None or delta > 3):
        return -1
    return score


def _parse_lrc(text: str) -> Lyrics:
    """LRC text → timed lines (synced) and their words (plain)."""

    synced: list[str] = []
    plain: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = _LRC_LINE.match(line)
        words = (match.group(2) if match else line).strip()
        if _NETEASE_CREDIT.match(words):
            continue
        if match:
            synced.append(f'{match.group(1)}{words}')
        if words:
            plain.append(words)
    return Lyrics(
        plain='\n'.join(plain).strip() or None,
        synced='\n'.join(synced).strip() or None,
    )


def _fetch_netease(song: dict[str, Any]) -> Optional[Lyrics]:
    artists = song.get('artists') or []
    title = (song.get('name') or '').strip()
    artist = str(artists[0] if artists else '').strip()
    if not title:
        return None

    data = _netease_get(
        '/search/get',
        {
            's': f'{artist} {title}'.strip(),
            'type': 1,
            'limit': 8,
            'offset': 0,
        },
    )
    songs = ((data or {}).get('result') or {}).get('songs') or []
    duration = float(song.get('duration') or 0)
    best = None
    best_score = 0.0
    for candidate in songs:
        if not isinstance(candidate, dict):
            continue
        score = _netease_score(candidate, title, artist, duration)
        if score > best_score:
            best, best_score = candidate, score
    if best is None:
        return None

    lyric = _netease_get(
        '/song/lyric', {'id': best.get('id'), 'lv': 1, 'kv': 1, 'tv': -1}
    )
    if not lyric or lyric.get('nolyric') or lyric.get('uncollected'):
        return None
    text = ((lyric.get('lrc') or {}).get('lyric') or '').strip()
    if not text or _NETEASE_INSTRUMENTAL in text:
        return None
    result = _parse_lrc(text)
    return result if result.has_any() else None


_PROVIDER_FNS: dict[str, Callable[[dict[str, Any]], Optional[Lyrics]]] = {
    'lrclib': _fetch_lrclib,
    'netease': _fetch_netease,
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
