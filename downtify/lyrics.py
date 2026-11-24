"""Lyrics providers used to enrich downloaded audio files.

Three sources are implemented, all free and keyless: ``lrclib``
(https://lrclib.net), ``netease`` (NetEase Cloud Music) and ``kugou``
(Kugou Music's lyrics service). Users put them in the order they prefer;
:func:`fetch` walks that order and stops at the first provider that has
something - with ``synced_only``, at the first that has time-synced
lyrics.

The legacy ``genius``/``musixmatch``/``azlyrics`` identifiers from the
spotdl-era UI are accepted as no-ops so existing settings keep
round-tripping cleanly. They are not implemented: AZLyrics forbids
third-party use of its content, Musixmatch's desktop API hands out an
empty token without credentials, and Genius' robots.txt disallows the
search endpoint needed to find a song's page.
"""

from __future__ import annotations

import base64
import binascii
import os
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

import httpx
from loguru import logger
from mutagen import File as MutagenFile
from mutagen.flac import FLAC
from mutagen.id3 import ID3, SYLT, USLT
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Tags
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

from .library_paths import library_stored_path
from .lyrics_cache import song_key

LRCLIB_BASE = 'https://lrclib.net/api'
NETEASE_BASE = 'https://music.163.com/api'
KUGOU_BASE = 'https://lyrics.kugou.com'
_USER_AGENT = 'Downtify (https://github.com/henriquesebastiao/downtify)'
_TIMEOUT = 10

#: Implemented providers, in the order they are offered by default.
PROVIDER_ORDER = ['lrclib', 'netease', 'kugou']
SUPPORTED_PROVIDERS = set(PROVIDER_ORDER)
#: Accepted in saved settings, but nothing is fetched from them.
LEGACY_PROVIDERS = {'genius', 'musixmatch', 'azlyrics'}

DEFAULT_LYRICS_LRC_DIR = '/data/lyrics'
MAX_LYRICS_LRC_DIR_LEN = 1024

_LrcResolve = Callable[[Path], Path]
_LrcRoot = Callable[[], Optional[Path]]
_LrcSearch = Callable[[Path], Sequence[Path]]
_lrc_resolve: Optional[_LrcResolve] = None
_lrc_tree_root: Optional[_LrcRoot] = None
_lrc_search: Optional[_LrcSearch] = None


def set_lrc_resolver(
    resolve: Optional[_LrcResolve],
    *,
    tree_root: Optional[_LrcRoot] = None,
    search: Optional[_LrcSearch] = None,
) -> None:
    """Hook used by the API to place ``.lrc`` files from live settings."""

    global _lrc_resolve, _lrc_tree_root, _lrc_search
    _lrc_resolve = resolve
    _lrc_tree_root = tree_root
    _lrc_search = search


def lrc_tree_root() -> Optional[Path]:
    """Dedicated lyrics folder when sidecars are not kept beside audio."""

    if _lrc_tree_root is None:
        return None
    try:
        return _lrc_tree_root()
    except Exception:
        logger.opt(exception=True).debug('LRC tree root lookup failed')
        return None


def coerce_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {'1', 'true', 'yes', 'on'}:
            return True
        if lowered in {'0', 'false', 'no', 'off', ''}:
            return False
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _path_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def sanitize_lyrics_lrc_dir(
    raw: Any,
    *,
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
    extra_dirs: Optional[Sequence[Path]] = None,
) -> str:
    """Absolute lyrics tree that is not inside a music folder."""

    text = str(raw or '').strip()
    if not text or len(text) > MAX_LYRICS_LRC_DIR_LEN:
        return DEFAULT_LYRICS_LRC_DIR
    path = Path(text)
    if not path.is_absolute():
        return DEFAULT_LYRICS_LRC_DIR
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    if resolved == Path('/') or len(resolved.parts) < 2:
        return DEFAULT_LYRICS_LRC_DIR
    forbidden: list[Path] = [download_dir]
    if slskd_dir is not None:
        forbidden.append(slskd_dir)
    forbidden.extend(extra_dirs or ())
    for root in forbidden:
        try:
            root_resolved = root.resolve()
        except OSError:
            root_resolved = root
        if _path_inside(resolved, root_resolved):
            return DEFAULT_LYRICS_LRC_DIR
    return str(path)


def lrc_sidecar_path(
    audio: Path,
    *,
    settings: dict[str, Any],
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
    extra_dirs: Optional[Sequence[Path]] = None,
) -> Path:
    """Where the ``.lrc`` for *audio* should live given *settings*."""

    if coerce_bool(settings.get('lyrics_lrc_beside'), True):
        return audio.with_suffix('.lrc')
    root = Path(str(settings.get('lyrics_lrc_dir') or DEFAULT_LYRICS_LRC_DIR))
    stored = library_stored_path(audio, download_dir, slskd_dir, extra_dirs)
    return (root / stored).with_suffix('.lrc')


def lrc_path_for(audio: Path, sidecar: Optional[Path] = None) -> Path:
    """Sidecar path for *audio*, honouring the live settings hook."""

    if sidecar is not None:
        return sidecar
    if _lrc_resolve is not None:
        try:
            return _lrc_resolve(audio)
        except Exception:
            logger.opt(exception=True).debug(
                'LRC path resolver failed for {}', audio
            )
    return audio.with_suffix('.lrc')


def lrc_candidates(audio: Path) -> list[Path]:
    """Possible sidecar locations (configured dest, beside, and extras)."""

    dest = lrc_path_for(audio)
    beside = audio.with_suffix('.lrc')
    extra: list[Path] = []
    if _lrc_search is not None:
        try:
            extra = [Path(item) for item in (_lrc_search(audio) or ())]
        except Exception:
            logger.opt(exception=True).debug(
                'LRC search paths failed for {}', audio
            )
    found: list[Path] = []
    for path in (dest, beside, *extra):
        if path not in found:
            found.append(path)
    return found


def can_mutate_audio(path: Path) -> bool:
    """False when *path* (or its folder) cannot be rewritten in place.

    Extra folders mounted read-only still yield tags and a dedicated
    ``.lrc``; they must not be tagged or have leftover sidecars deleted.
    """

    try:
        parent = path.parent
        if not os.access(parent, os.W_OK):
            return False
        if path.exists() and not os.access(path, os.W_OK):
            return False
    except OSError:
        return False
    return True


def relocate_lrc_sidecar(audio: Path) -> str:
    """Put the sidecar at the configured location.

    ``present`` — already there; ``copied`` — moved from the other place;
    ``missing`` — nothing to copy.
    """

    dest = lrc_path_for(audio)
    try:
        if dest.is_file() and dest.stat().st_size:
            _unlink_other_lrc(audio, dest)
            return 'present'
    except OSError:
        pass
    for candidate in lrc_candidates(audio):
        if candidate == dest:
            continue
        try:
            if not candidate.is_file():
                continue
            text = candidate.read_text(encoding='utf-8').strip()
        except (OSError, UnicodeDecodeError):
            continue
        if not text:
            continue
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding='utf-8')
        except OSError:
            logger.opt(exception=True).warning(
                'Could not write LRC sidecar {}', dest
            )
            continue
        _unlink_other_lrc(audio, dest)
        return 'copied'
    return 'missing'


def _unlink_other_lrc(audio: Path, dest: Path) -> None:
    for leftover in lrc_candidates(audio):
        if leftover == dest:
            continue
        if leftover.exists() and not can_mutate_audio(leftover):
            logger.debug('Leaving LRC on read-only tree {}', leftover)
            continue
        try:
            leftover.unlink(missing_ok=True)
        except OSError:
            logger.opt(exception=True).debug(
                'Could not remove old LRC sidecar {}', leftover
            )


_LRC_STAMP = re.compile(r'\[\d{1,2}:\d{2}')


def looks_like_lrc(text: str) -> bool:
    """True when *text* already carries LRC timestamps."""

    return bool(text and _LRC_STAMP.search(text))


@dataclass
class Lyrics:
    plain: Optional[str] = None
    synced: Optional[str] = None

    def has_any(self) -> bool:
        return bool(self.plain) or bool(self.synced)

    def usable(self, synced_only: bool = False) -> bool:
        """Whether this is worth keeping: anything at all, or only
        time-synced lyrics when *synced_only*."""

        return bool(self.synced) if synced_only else self.has_any()


def providers_from_settings(settings: dict[str, Any]) -> list[str]:
    """Providers a download (and library sync) will try, in order.

    Unknown names are dropped; a list left with nothing but the spotdl-era
    placeholders (genius/musixmatch/azlyrics) falls back to the defaults,
    since those settings were never asking for "no lyrics". An explicitly
    empty list, and lyrics being off, both mean none.
    """

    if not settings.get('download_lyrics', True):
        return []
    raw = [
        part.strip()
        for part in (settings.get('lyrics_providers') or [])
        if isinstance(part, str) and part.strip()
    ]
    if not raw:
        return []
    providers: list[str] = []
    for name in raw:
        if name in SUPPORTED_PROVIDERS and name not in providers:
            providers.append(name)
    return providers or list(PROVIDER_ORDER)


def fetch(
    song: dict[str, Any],
    providers: list[str],
    cache: Optional[Any] = None,
    *,
    synced_only: bool = False,
) -> Optional[Lyrics]:
    """Try each provider in order; return the first successful match.

    ``cache`` is an optional :class:`~downtify.lyrics_cache.LyricsLookupCache`:
    providers that recently came back empty for this song are skipped, and
    every answer is recorded. With *synced_only*, lyrics without
    timestamps count as nothing: the next provider is asked.
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
        found = bool(result and result.usable(synced_only))
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

    found = _lrclib_lyrics(data)
    if found is not None and found.synced:
        return found
    # No exact match, or one without timestamps: LRCLIB's search finds
    # the same song filed under a slightly different album or length.
    searched = _search_lrclib(song)
    return searched or found


def _lrclib_lyrics(data: Any) -> Optional[Lyrics]:
    if not isinstance(data, dict):
        return None
    plain = (data.get('plainLyrics') or '').strip() or None
    synced = (data.get('syncedLyrics') or '').strip() or None
    if not plain and not synced:
        return None
    return Lyrics(plain=plain, synced=synced)


def _search_lrclib(song: dict[str, Any]) -> Optional[Lyrics]:
    """The best time-synced hit of LRCLIB's search for the song, matched
    on title, artist and length the way NetEase hits are."""

    artists = song.get('artists') or []
    title = (song.get('name') or '').strip()
    artist = str(artists[0] if artists else '').strip()
    if not title or not artist:
        return None
    try:
        response = httpx.get(
            f'{LRCLIB_BASE}/search',
            params={'track_name': title, 'artist_name': artist},
            headers={'User-Agent': _USER_AGENT},
            timeout=_TIMEOUT,
        )
    except httpx.RequestError:
        logger.opt(exception=True).warning('lrclib search failed')
        return None
    if response.status_code != 200:
        return None
    try:
        hits = response.json()
    except ValueError:
        return None
    duration = float(song.get('duration') or 0)
    best = None
    best_score = 0.0
    for hit in hits if isinstance(hits, list) else []:
        if not isinstance(hit, dict) or not hit.get('syncedLyrics'):
            continue
        candidate = {
            'name': hit.get('trackName') or hit.get('name'),
            'artists': [{'name': hit.get('artistName')}],
            'duration': float(hit.get('duration') or 0) * 1000,
        }
        score = _netease_score(candidate, title, artist, duration)
        if score > best_score:
            best, best_score = hit, score
    return _lrclib_lyrics(best) if best is not None else None


# ── NetEase Cloud Music ──────────────────────────────────────────────
# Its public search and lyric endpoints need no key. Lyrics come as LRC,
# so synced and plain text both fall out of one request.

#: Credits NetEase puts inside the lyric body ("作词 : ..."), dropped so
#: they don't end up in the tag or the .lrc file.
_NETEASE_CREDIT = re.compile(
    r'^(作词|作曲|编曲|制作人|录音|混音|母带|监制|出品|发行|词|曲|'
    r'lyricist|composer|arranger|producer|mixing|mastering|'
    r'written by|lyrics by|music by|composed by|produced by)\s*[:：]',
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


# ── Kugou ────────────────────────────────────────────────────────────
# Kugou Music's lyrics service: a keyless search that lists candidate
# lyrics with their song's length, then the chosen one as base64 LRC.

#: LRC header tags (``[ar:Artist]``, ``[offset:0]``): not lyrics.
_LRC_TAG = re.compile(r'^\[[a-z#]+:[^\]]*\]$', re.IGNORECASE)


def _kugou_get(path: str, params: dict[str, Any]) -> Optional[dict]:
    try:
        response = httpx.get(
            f'{KUGOU_BASE}{path}',
            params=params,
            headers={'User-Agent': _USER_AGENT},
            timeout=_TIMEOUT,
        )
    except httpx.RequestError:
        logger.opt(exception=True).warning('Kugou request failed')
        return None
    if response.status_code != 200:
        logger.warning('Kugou returned HTTP {}', response.status_code)
        return None
    try:
        data = response.json()
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _fetch_kugou(song: dict[str, Any]) -> Optional[Lyrics]:
    artists = song.get('artists') or []
    title = (song.get('name') or '').strip()
    artist = str(artists[0] if artists else '').strip()
    if not title:
        return None
    duration = float(song.get('duration') or 0)
    data = _kugou_get(
        '/search',
        {
            'ver': 1,
            'man': 'yes',
            'client': 'pc',
            'keyword': f'{artist} - {title}' if artist else title,
            'duration': int(duration * 1000) if duration else '',
            'hash': '',
        },
    )
    best = None
    best_score = 0.0
    for hit in (data or {}).get('candidates') or []:
        if not isinstance(hit, dict) or not hit.get('id'):
            continue
        candidate = {
            'name': hit.get('song'),
            'artists': [
                {'name': part}
                for part in re.split(r'[、,&/]', str(hit.get('singer') or ''))
                if part.strip()
            ],
            'duration': hit.get('duration'),
        }
        score = _netease_score(candidate, title, artist, duration)
        if score > best_score:
            best, best_score = hit, score
    if best is None:
        return None
    payload = _kugou_get(
        '/download',
        {
            'ver': 1,
            'client': 'pc',
            'id': best['id'],
            'accesskey': best.get('accesskey') or '',
            'fmt': 'lrc',
            'charset': 'utf8',
        },
    )
    try:
        text = base64.b64decode(str((payload or {}).get('content') or ''))
        lrc = text.decode('utf-8', errors='replace')
    except (binascii.Error, ValueError):
        return None
    # Kugou opens with the song's own "Title - Artist" line.
    heading = {
        _normalize(f'{best.get("song")} - {best.get("singer")}'),
        _normalize(f'{best.get("singer")} - {best.get("song")}'),
    }
    lines = [
        line
        for line in lrc.splitlines()
        if not _LRC_TAG.match(line.strip())
        and _normalize(_LRC_LINE.sub(r'\2', line.strip())) not in heading
    ]
    result = _parse_lrc('\n'.join(lines))
    return result if result.has_any() else None


_PROVIDER_FNS: dict[str, Callable[[dict[str, Any]], Optional[Lyrics]]] = {
    'lrclib': _fetch_lrclib,
    'netease': _fetch_netease,
    'kugou': _fetch_kugou,
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
    try:
        tags = _file_tags(path)
        if not tags:
            return ''
        if hasattr(tags, 'getall'):
            frames = tags.getall('USLT')
            return str(frames[0].text).strip() if frames else ''
        # Vorbis comments reject MP4's non-ASCII key with ValueError.
        # Use the tag container, not the filename, to choose a valid key.
        key = (
            _MP4_LYRICS_KEY
            if isinstance(tags, MP4Tags)
            else _VORBIS_LYRICS_KEY
        )
        value = tags.get(key)
        if value:
            first = value[0] if isinstance(value, list) else value
            return str(first).strip()
    except Exception:
        # Damaged/unsupported tags must not fail the API or upgrade scan,
        # or prevent read_track_lyrics from returning a valid sidecar.
        logger.opt(exception=True).debug(
            'Could not read embedded lyrics from {}', path
        )
    return ''


def _sylt_lrc(frame: Any) -> str:
    """An ID3 ``SYLT`` frame as LRC text; empty when its times aren't in
    milliseconds (format 2) or it holds no lines."""

    if not isinstance(frame, SYLT) or frame.format != 2:
        return ''
    entries = [(str(text).strip(), int(time)) for text, time in frame.text]
    if not any(text for text, _time in entries):
        return ''
    lines = []
    for text, time in entries:
        ms = max(0, time)
        minutes, seconds = ms // 60000, ms // 1000 % 60
        lines.append(
            f'[{minutes:02d}:{seconds:02d}.{ms % 1000 // 10:02d}]{text}'
        )
    return '\n'.join(lines)


def embedded_synced_text(path: Path, embedded: Optional[str] = None) -> str:
    """Time-synced lyrics in the file's own tags, as LRC text: lyrics
    text with LRC timestamps (as files shared over Soulseek or tagged by
    other apps often carry), or an ID3 ``SYLT`` frame. Empty when the
    tags have none, or only plain lyrics. *embedded* is the tag's lyrics
    text when already read."""

    if embedded is None:
        embedded = _embedded_lyrics(path)
    if looks_like_lrc(embedded):
        return embedded
    try:
        tags = _file_tags(path)
        if tags and hasattr(tags, 'getall'):
            for frame in tags.getall('SYLT'):
                text = _sylt_lrc(frame)
                if text:
                    return text
    except Exception:
        logger.opt(exception=True).debug(
            'Could not read synced lyrics from {}', path
        )
    return ''


def has_synced_lyrics(path: Path) -> bool:
    """Whether a track already has time-synced lyrics: a ``.lrc`` sidecar
    (beside it or in the lyrics folder) or synced lyrics in its tags."""

    if any(_read_lrc_text(sidecar) for sidecar in lrc_candidates(path)):
        return True
    return bool(embedded_synced_text(path))


def read_track_lyrics(path: Path, *, raw: bool = False) -> dict[str, str]:
    """Lyrics saved with a downloaded track.

    ``synced`` is the LRC text of the ``.lrc`` sidecar or, without one,
    the time-synced lyrics in the file's tags; ``plain`` is the text
    embedded in the file's tags, timestamps removed. Either can be empty.
    Unreadable files count as having no lyrics.

    With *raw*, ``synced`` is the sidecar only and ``plain`` the tag's
    text exactly as stored.
    """

    synced = ''
    for sidecar in lrc_candidates(path):
        synced = _read_lrc_text(sidecar)
        if synced:
            break
    plain = _embedded_lyrics(path)
    if raw:
        return {'synced': synced, 'plain': plain}
    if not synced:
        synced = embedded_synced_text(path, plain)
    if looks_like_lrc(plain):
        plain = _strip_lrc_timestamps(plain) or plain
    return {'synced': synced, 'plain': plain}


def _read_lrc_text(sidecar: Path) -> str:
    if not sidecar.is_file():
        return ''
    try:
        return sidecar.read_text(encoding='utf-8').strip()
    except (OSError, UnicodeDecodeError):
        logger.opt(exception=True).warning(
            'Could not read LRC sidecar {}', sidecar
        )
        return ''


def _strip_lrc_timestamps(synced: str) -> str:
    cleaned = re.sub(r'\[\d{1,2}:\d{2}(?:\.\d{1,3})?\]', '', synced)
    # Header tags (``[ti:Title]``, ``[offset:0]``) aren't lyrics either.
    return '\n'.join(
        line.strip()
        for line in cleaned.splitlines()
        if line.strip() and not _LRC_TAG.match(line.strip())
    )


def write_to_file(
    path: Path,
    lyrics: Lyrics,
    *,
    sidecar: Optional[Path] = None,
    embed_synced: bool = False,
) -> None:
    """Embed plain lyrics and write a ``.lrc`` sidecar when they are synced.

    With *embed_synced* (the ``lyrics_synced_only`` setting), the tag gets
    the time-synced LRC text instead, so players that only read the
    file's own tags show synced lyrics too.

    Same write a download uses (see ``downloader.embed_lyrics``).
    """

    if not path.exists() or not lyrics.has_any():
        return

    if lyrics.synced:
        dest = lrc_path_for(path, sidecar)
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(lyrics.synced, encoding='utf-8')
        except OSError:
            logger.opt(exception=True).warning(
                'Could not write LRC sidecar {}', dest
            )
        else:
            _unlink_other_lrc(path, dest)

    if embed_synced and lyrics.synced:
        text = lyrics.synced
    else:
        text = lyrics.plain or _strip_lrc_timestamps(lyrics.synced or '')
    if not text:
        return
    if not can_mutate_audio(path):
        logger.debug('Skipping lyrics embed in read-only file {}', path)
        return
    _embed_lyrics_text(path, text)


def _embed_lyrics_text(path: Path, text: str) -> None:
    """Write *text* as the file's lyrics tag (USLT, ``©lyr`` or the
    Vorbis ``lyrics`` comment, by container)."""

    suffix = path.suffix.lower().lstrip('.')
    if suffix == 'mp3':
        audio = None
        try:
            audio = MP3(str(path), ID3=ID3)
        except Exception:
            audio = None
        if audio is not None:
            if audio.tags is None:
                audio.add_tags()
            tags = audio.tags
        else:
            tags = ID3(str(path))
        tags.delall('USLT')
        tags.add(USLT(encoding=3, lang='eng', desc='', text=text))
        if audio is not None:
            audio.save(v2_version=4)
        else:
            tags.save(v2_version=4)
    elif suffix in {'m4a', 'mp4', 'aac'}:
        audio = MP4(str(path))
        audio['\xa9lyr'] = text
        audio.save()
    elif suffix == 'flac':
        audio = FLAC(str(path))
        audio['lyrics'] = text
        audio.save()
    elif suffix in {'ogg', 'oga'}:
        audio = OggVorbis(str(path))
        audio['lyrics'] = text
        audio.save()
    elif suffix == 'opus':
        audio = OggOpus(str(path))
        audio['lyrics'] = text
        audio.save()


# ── Timing adjustment ────────────────────────────────────────────────
# Lyrics found online are sometimes a little early or late for the audio
# actually downloaded (another edit, a longer intro). Shifting rewrites
# the saved timestamps themselves, so every player that reads the
# ``.lrc`` or the tags agrees, not only Downtify's (issue #663).

#: Largest shift accepted in one go, in milliseconds.
MAX_LYRICS_SHIFT_MS = 60_000

#: The time tags opening an LRC line (``[01:02.34][01:40.00]Words``).
_LRC_LEADING_TAGS = re.compile(
    r'^\s*((?:\[\d{1,3}:\d{1,2}(?:[.:]\d{1,3})?\])+)'
)
_LRC_TIME = re.compile(r'\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]')
#: Digits of a fraction in milliseconds (``.345``), not centiseconds.
_MILLIS_DIGITS = 3
#: ``SYLT`` time-stamp format: absolute milliseconds (ID3v2.4, 4.9).
_SYLT_MILLISECONDS = 2
#: ``[offset:+500]``: show the lyrics that many milliseconds sooner.
_LRC_OFFSET = re.compile(r'^\s*\[offset:\s*([+-]?\d+)\s*\]\s*$', re.I)


def _lrc_time(ms: int, millis: bool) -> str:
    minutes, rest = divmod(max(0, ms), 60_000)
    seconds, fraction = divmod(rest, 1000)
    if millis:
        return f'[{minutes:02d}:{seconds:02d}.{fraction:03d}]'
    return f'[{minutes:02d}:{seconds:02d}.{fraction // 10:02d}]'


def _shift_time_tag(match: re.Match[str], shift_ms: int) -> str:
    minutes, seconds, fraction = match.groups()
    fraction = fraction or ''
    ms = (int(minutes) * 60 + int(seconds)) * 1000
    if fraction:
        ms += int(fraction.ljust(_MILLIS_DIGITS, '0'))
    return _lrc_time(ms + shift_ms, len(fraction) == _MILLIS_DIGITS)


def shift_lrc(text: str, offset_ms: int) -> str:
    """*text* (LRC) with every line's time moved *offset_ms* later
    (earlier when negative), stopping at ``00:00.00``.

    An ``[offset:N]`` header is folded into the times and dropped: many
    players ignore it, so lyrics that rely on it are out of sync there.
    """

    header = 0
    kept: list[str] = []
    for line in text.splitlines():
        found = _LRC_OFFSET.match(line)
        if found:
            header += int(found.group(1))
        else:
            kept.append(line)
    shift = offset_ms - header

    def move(line: str) -> str:
        found = _LRC_LEADING_TAGS.match(line)
        if not found or not shift:
            return line
        tags = _LRC_TIME.sub(
            lambda tag: _shift_time_tag(tag, shift), found.group(1)
        )
        return line[: found.start(1)] + tags + line[found.end(1) :]

    return '\n'.join(move(line) for line in kept)


def _shift_sylt(path: Path, offset_ms: int) -> bool:
    """Move the times of an MP3's millisecond ``SYLT`` frames."""

    try:
        tags = ID3(str(path))
    except Exception:
        return False
    frames = [
        frame
        for frame in tags.getall('SYLT')
        if frame.format == _SYLT_MILLISECONDS
    ]
    if not frames:
        return False
    for frame in frames:
        frame.text = [
            (text, max(0, int(time) + offset_ms)) for text, time in frame.text
        ]
    tags.save(str(path), v2_version=4)
    return True


def shift_track_lyrics(path: Path, offset_ms: int) -> list[str]:
    """Move the time-synced lyrics saved with *path* by *offset_ms*.

    Rewrites the ``.lrc`` sidecar the player reads and, when the file's
    tags hold time-synced lyrics too (LRC text or an ID3 ``SYLT`` frame),
    those - unless the audio is read-only. Returns what changed
    (``sidecar``, ``tags``); empty when the track has no time-synced
    lyrics. A sidecar that can't be written raises ``OSError``.
    """

    changed: list[str] = []
    for sidecar in lrc_candidates(path):
        text = _read_lrc_text(sidecar)
        if not text:
            continue
        sidecar.write_text(shift_lrc(text, offset_ms), encoding='utf-8')
        changed.append('sidecar')
        break

    if not can_mutate_audio(path):
        return changed
    embedded = _embedded_lyrics(path)
    if looks_like_lrc(embedded):
        _embed_lyrics_text(path, shift_lrc(embedded, offset_ms))
        changed.append('tags')
    elif path.suffix.lower() == '.mp3' and _shift_sylt(path, offset_ms):
        changed.append('tags')
    return changed
