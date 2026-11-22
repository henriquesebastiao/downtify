"""Formats a user doesn't want in their library: find them, convert them.

Two settings-level ideas share the list of formats here:

* **Formats to avoid** (``avoid_formats``): a download never brings a
  file in one of them into the library. slskd skips such files when it
  picks one, and a source that hands one over anyway (Deemix, a file
  slskd left behind) counts as having found nothing, so the next source
  is tried. YouTube and SoundCloud downloads are always converted to the
  Downloads format, so they never produce one.
* **Convert to MP3** (the Doctor): files already in the library in
  chosen formats - a FLAC from before the format rules were set, say -
  are converted to MP3 at the Downloads quality. See
  :func:`convert_to_mp3` for what is kept; the Doctor then moves every
  reference from the old file to the new one and sends the old one to
  the music trash (``doctor_routes``), as a duplicate merge does.

Converting a lossless file to MP3 320 is how good MP3s are made in the
first place, so nothing audible is lost; a lossy file converted again
loses a little, which is why only the formats the user picks are touched.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable, Optional

from loguru import logger
from mutagen import File as MutagenFile

from . import isrc as isrc_mod
from . import lyrics as lyrics_mod
from .audio_formats import (  # noqa: F401  # re-exported
    FORMATS,
    avoided,
    extensions_of,
    format_of_extension,
    normalize_formats,
)
from .downloader import embed_metadata
from .library_catalog import UPGRADE_STAGING_MARKER
from .library_metadata import read_audio_metadata

#: The MP3 bitrates (kbps) a conversion may use: the Downloads quality.
BITRATES = (128, 192, 256, 320)
DEFAULT_BITRATE = 320
#: How far the new file's length may be from the old one's.
LENGTH_TOLERANCE_SECONDS = 1.0
#: Longest a single conversion may take.
CONVERT_TIMEOUT = 900


class ConvertError(ValueError):
    """A file that could not be converted; ``code`` says why."""

    def __init__(self, code: str, detail: str = '') -> None:
        super().__init__(detail or code)
        self.code = code


def target_bitrate(settings: dict[str, Any]) -> int:
    """The MP3 bitrate a conversion writes: the Downloads quality when
    it is one of :data:`BITRATES`, else 320."""

    try:
        value = int(str(settings.get('bitrate') or '').rstrip('kK'))
    except ValueError:
        return DEFAULT_BITRATE
    return value if value in BITRATES else DEFAULT_BITRATE


def estimated_size(duration: float, bitrate: int) -> int:
    """Bytes an MP3 of *duration* seconds takes at *bitrate* kbps."""

    return int(max(0.0, float(duration or 0)) * bitrate * 1000 / 8)


def files_in_formats(
    rows: Iterable[dict[str, Any]], formats: Iterable[str], bitrate: int
) -> list[dict[str, Any]]:
    """The library rows (``file``, ``size``, ``duration``, …) whose file
    is in one of *formats*, biggest first, each with its ``format`` and
    the ``estimated`` size of its MP3."""

    extensions = extensions_of(formats)
    found = []
    for row in rows:
        name = str(row.get('file') or '')
        ext = Path(name).suffix.lower().lstrip('.')
        if not ext or ext not in extensions:
            continue
        duration = float(row.get('duration') or 0)
        found.append({
            'file': name,
            'format': format_of_extension(ext),
            'size': int(row.get('size') or 0),
            'duration': duration,
            'title': str(row.get('title') or ''),
            'artist': str(row.get('artist') or ''),
            'estimated': estimated_size(duration, bitrate),
        })
    found.sort(key=lambda r: (-r['size'], r['file']))
    return found


def ffmpeg() -> Optional[str]:
    return shutil.which('ffmpeg')


def _length(path: Path) -> float:
    try:
        audio = MutagenFile(str(path))
    except Exception:
        return 0.0
    info = getattr(audio, 'info', None)
    return float(getattr(info, 'length', 0.0) or 0.0)


def _cover_bytes(path: Path) -> Optional[bytes]:
    """The front cover (or first picture) embedded in *path*."""

    try:
        audio = MutagenFile(str(path))
    except Exception:
        return None
    if audio is None:
        return None
    pictures = list(getattr(audio, 'pictures', None) or [])
    if pictures:
        front = [p for p in pictures if getattr(p, 'type', 0) == 3]
        return bytes((front or pictures)[0].data)
    tags = getattr(audio, 'tags', None)
    if tags is None:
        return None
    for key in ('covr',):  # MP4
        values = tags.get(key) if hasattr(tags, 'get') else None
        if values:
            return bytes(values[0])
    for frame in getattr(tags, 'getall', lambda _k: [])('APIC'):
        return bytes(frame.data)
    return None


def _song_from_tags(path: Path) -> dict[str, Any]:
    """The song a file's tags describe, as :func:`embed_metadata` takes
    it, so the MP3 gets the tags a download writes."""

    tags = read_audio_metadata(path)
    artists = list(tags.get('artists') or [])
    if not artists and tags.get('artist'):
        artists = [str(tags['artist'])]
    return {
        'name': tags.get('title') or path.stem,
        'artists': artists,
        'album_artist': tags.get('album_artist') or '',
        'album_name': tags.get('album') or '',
        'track_number': int(tags.get('track_number') or 0) or None,
        'year': tags.get('year') or '',
        'release_date': tags.get('release_date') or '',
        'genre': tags.get('genre') or '',
        'explicit': bool(tags.get('explicit')),
        'compilation': bool(tags.get('compilation')),
        'isrc': tags.get('isrc') or '',
    }


def mp3_path_for(source: Path) -> Path:
    """Where *source*'s MP3 goes: beside it, same name."""

    return source.with_suffix('.mp3')


def convert_to_mp3(
    source: Path, bitrate: int = DEFAULT_BITRATE, *, ffmpeg_path: str = ''
) -> Path:
    """Write *source* as an MP3 beside it and return the MP3's path.

    The audio is encoded at *bitrate* kbps; the title, artists, album,
    album artist, numbers, date, genre, ISRC, explicit and compilation
    flags and the cover are written the way a download writes them, and
    the embedded lyrics are copied (an ``.lrc`` sidecar has the same name
    and keeps working). Other tags come across as ffmpeg maps them.

    The MP3 is written under a staging name the library scan skips,
    checked to decode and to be as long as the original, and only then
    given its name; *source* itself is never changed. Raises
    :class:`ConvertError` (``no_ffmpeg``, ``missing``, ``exists``,
    ``failed``, ``length``) and leaves nothing behind when it does.
    """

    tool = ffmpeg_path or ffmpeg()
    if not tool:
        raise ConvertError('no_ffmpeg')
    if not source.is_file():
        raise ConvertError('missing')
    target = mp3_path_for(source)
    if target.exists():
        # Another file already has the name: never written over.
        raise ConvertError('exists', str(target.name))
    bitrate = bitrate if bitrate in BITRATES else DEFAULT_BITRATE
    staging = source.with_name(f'{source.stem}{UPGRADE_STAGING_MARKER}.mp3')
    args = [tool, '-nostdin', '-v', 'error', '-y', '-i', str(source)]
    args += ['-map', '0:a:0', '-map_metadata', '0', '-vn']
    args += ['-c:a', 'libmp3lame', '-b:a', f'{bitrate}k']
    args += ['-id3v2_version', '3', str(staging)]
    try:
        try:
            subprocess.run(
                args, check=True, capture_output=True, timeout=CONVERT_TIMEOUT
            )
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or b'').decode('utf-8', 'replace').strip()
            logger.warning('Converting {} failed: {}', source.name, detail)
            raise ConvertError('failed', detail[-300:]) from None
        except (subprocess.SubprocessError, OSError) as exc:
            raise ConvertError('failed', str(exc)) from None
        before, after = _length(source), _length(staging)
        if after <= 0 or (
            before > 0 and abs(after - before) > LENGTH_TOLERANCE_SECONDS
        ):
            raise ConvertError('length', f'{before:.1f}s -> {after:.1f}s')
        _copy_tags(source, staging)
        if target.exists():
            raise ConvertError('exists', str(target.name))
        os.replace(staging, target)
    finally:
        if staging.exists():
            try:
                staging.unlink()
            except OSError:
                logger.warning('Could not remove {}', staging)
    _keep_dates(source, target)
    return target


def _copy_tags(source: Path, target: Path) -> None:
    song = _song_from_tags(source)
    embed_metadata(
        target, song, download_cover=True, cover_bytes=_cover_bytes(source)
    )
    if song['isrc']:
        isrc_mod.write(target, song['isrc'])
    text = _embedded_lyrics(source)
    if text:
        lyrics_mod.write_to_file(target, lyrics_mod.Lyrics(plain=text))


def _embedded_lyrics(path: Path) -> str:
    """The lyrics text in *path*'s own tags (not its ``.lrc``), as it is."""

    try:
        audio = MutagenFile(str(path))
    except Exception:
        return ''
    tags = getattr(audio, 'tags', None)
    if tags is None:
        return ''
    for frame in getattr(tags, 'getall', lambda _k: [])('USLT'):
        return str(frame.text or '')
    for key in ('lyrics', 'LYRICS', 'unsyncedlyrics', 'UNSYNCEDLYRICS'):
        try:
            values = tags.get(key)
        except Exception:
            values = None
        if values:
            return str(values[0])
    values = tags.get('\xa9lyr') if hasattr(tags, 'get') else None
    return str(values[0]) if values else ''


def _keep_dates(source: Path, target: Path) -> None:
    """The MP3 keeps the original's modification time, so it doesn't jump
    to the top of "recently added"."""

    try:
        stat = source.stat()
        os.utime(target, (stat.st_atime, stat.st_mtime))
    except OSError:
        pass
