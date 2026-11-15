"""Replace a library track's audio with a version the user picks.

Automatic matching sometimes lands on the wrong song or the wrong version
(a live cut, a remix, a lyric video with an intro). From a track's menu,
an admin searches YouTube Music and YouTube (or pastes a YouTube or
SoundCloud track link), picks the right upload, and the file's audio is
swapped for it:

* **Same file.** The new audio is written to the same path, in the same
  format (an ``.flac`` stays FLAC, an ``.mp3`` MP3 at the chosen bitrate),
  so every M3U, playlist, like, Navidrome entry and app track id that
  points at the file keeps pointing at it.
* **Same tags.** Every tag of the old file - title, artists, album,
  numbers, cover, lyrics, whatever else - is copied onto the new audio as
  it is; the ``.lrc`` sidecar is left alone. The file's modification time
  is kept, so it doesn't jump to the top of "recently added".
* **Safe.** The new audio is downloaded beside the file under a staging
  name the library scan skips (``<name>.downtify-upgrade.<ext>``), checked
  to be readable audio, and only then moved over the old file. A failed
  download or check leaves the old file untouched.

Candidates come from :func:`candidates`; the swap is :func:`replace_audio`.

**From a file.** The admin can also upload the right audio from their
own computer (a CD rip, a Soulseek download, a file a friend sent):
:func:`replace_from_file`. A file in the same format as the library file
is used as it is, bit for bit; another format is converted to the file's
own (an ``.mp3`` at the chosen bitrate), so the path still doesn't
change. Same tags, same date, same staging and checks as above.

Either way the file is then remembered as replaced by hand
(:mod:`downtify.hand_replaced`), so a later download of the same song
doesn't write over it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger
from mutagen import File as MutagenFile
from mutagen.id3 import ID3, ID3NoHeaderError

from . import providers
from .library_catalog import UPGRADE_STAGING_MARKER

#: File types whose audio can be replaced: the formats Downtify writes.
REPLACEABLE_FORMATS = ('mp3', 'flac', 'm4a', 'ogg', 'opus')

#: What an uploaded replacement may be: the formats above, plus the
#: usual lossless and lossy files people have (converted on the way in).
UPLOAD_FORMATS = (*REPLACEABLE_FORMATS, 'wav', 'aiff', 'aif', 'aac', 'webm')

#: The biggest file accepted for upload (a 20-minute WAV is ~210 MB).
MAX_UPLOAD_BYTES = 400 * 1024 * 1024

#: ffmpeg's encoder for each format Downtify writes.
_ENCODERS = {
    'mp3': 'libmp3lame',
    'm4a': 'aac',
    'ogg': 'libvorbis',
    'opus': 'libopus',
    'flac': 'flac',
}

#: Candidates asked of each source.
CANDIDATE_LIMIT = 10

ProgressCallback = Callable[[float, str, Optional[str]], None]


class ReplaceError(ValueError):
    """The audio can't be replaced; the message says why."""


def replacement_format(path: Path) -> str:
    """The format new audio for *path* is written in: its own."""

    fmt = path.suffix.lower().lstrip('.')
    if fmt not in REPLACEABLE_FORMATS:
        raise ReplaceError(
            f'Only {", ".join(REPLACEABLE_FORMATS)} files can be replaced'
        )
    return fmt


def search_query(entry: dict[str, Any]) -> str:
    """What to search for a track: ``Artist - Title``."""

    title = str(entry.get('title') or '').strip()
    artist = ', '.join(
        part.strip()
        for part in str(entry.get('artist') or '').split(';')
        if part.strip()
    )
    return f'{artist} - {title}' if artist and title else title or artist


# ── Candidates ──────────────────────────────────────────────────────────


def _thumbnail(video_id: str) -> str:
    return f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg'


def _from_youtube_music(song: dict[str, Any]) -> dict[str, Any]:
    video_id = str(song.get('song_id') or '')
    return {
        'video_id': video_id,
        'title': str(song.get('name') or ''),
        'artist': ', '.join(song.get('artists') or []),
        'album': str(song.get('album_name') or ''),
        'duration': int(song.get('duration') or 0),
        'thumbnail': str(song.get('cover_url') or '') or _thumbnail(video_id),
        'source': 'youtube-music',
        'url': f'https://music.youtube.com/watch?v={video_id}',
    }


def _from_youtube(entry: dict[str, Any]) -> Optional[dict[str, Any]]:
    video_id = entry.get('id')
    if not isinstance(video_id, str) or not video_id:
        return None
    if entry.get('live_status') in {'is_live', 'is_upcoming', 'post_live'}:
        return None
    try:
        duration = int(entry.get('duration') or 0)
    except (TypeError, ValueError):
        duration = 0
    return {
        'video_id': video_id,
        'title': str(entry.get('title') or ''),
        'artist': str(entry.get('channel') or entry.get('uploader') or ''),
        'album': '',
        'duration': duration,
        'thumbnail': _thumbnail(video_id),
        'source': 'youtube',
        'url': f'https://www.youtube.com/watch?v={video_id}',
    }


def _from_soundcloud_link(url: str) -> list[dict[str, Any]]:
    """The one track a pasted SoundCloud link names; its ``video_id`` is
    the track URL (what :func:`replace_audio` fetches)."""

    try:
        song = providers.soundcloud_track_from_url(url)
    except Exception as exc:
        logger.opt(exception=True).debug('SoundCloud lookup failed')
        raise ReplaceError('Could not read that SoundCloud track') from exc
    return [
        {
            'video_id': song['url'],
            'title': song['name'],
            'artist': song['artist'],
            'album': '',
            'duration': int(song.get('duration') or 0),
            'thumbnail': song['cover_url'],
            'source': 'link',
            'url': song['url'],
        }
    ]


def _from_link(query: str) -> Optional[list[dict[str, Any]]]:
    """The one video (or SoundCloud track) a pasted link names, or
    ``None`` when *query* isn't such a link."""

    soundcloud = providers.parse_soundcloud_url(query.strip())
    if soundcloud is not None:
        return _from_soundcloud_link(soundcloud[1])
    parsed = providers.parse_youtube_url(query.strip())
    if parsed is None:
        return None
    kind, video_id = parsed
    if kind != 'track':
        raise ReplaceError('Paste a link to one video or song')
    try:
        song = providers.song_from_video_id(video_id)
    except Exception:
        logger.opt(exception=True).debug('Video lookup failed')
        song = {}
    found = _from_youtube_music({**song, 'song_id': video_id})
    found['source'] = 'link'
    return [found]


def candidates(
    query: str, limit: int = CANDIDATE_LIMIT
) -> list[dict[str, Any]]:
    """Versions of a song to pick from: YouTube Music songs first, then
    standard YouTube uploads (covers, live cuts, fan uploads), without
    repeats. A pasted link is that one video."""

    text = str(query or '').strip()
    if not text:
        return []
    linked = _from_link(text)
    if linked is not None:
        return linked
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    # ytmusicapi can hand back more than it was asked for.
    for song in providers.search_songs(text, limit=limit)[:limit]:
        row = _from_youtube_music(song)
        if row['video_id'] and row['video_id'] not in seen:
            seen.add(row['video_id'])
            found.append(row)
    try:
        uploads = providers.youtube_search(text, limit)
    except Exception:
        logger.opt(exception=True).warning('YouTube search failed')
        uploads = []
    for entry in uploads:
        row = _from_youtube(entry)
        if row and row['video_id'] not in seen:
            seen.add(row['video_id'])
            found.append(row)
    return found


# ── Tags ────────────────────────────────────────────────────────────────


def copy_tags(source: Path, target: Path) -> None:
    """Put every tag of *source* (cover and lyrics included) on *target*,
    replacing whatever *target* had. Both are the same format."""

    if source.suffix.lower() == '.mp3':
        try:
            tags = ID3(str(source))
        except ID3NoHeaderError:
            return
        try:
            ID3(str(target)).delete(str(target))
        except ID3NoHeaderError:
            pass
        # Written in the ID3 version the file had (2.3 or 2.4).
        version = tags.version[1] if tags.version[1] in {3, 4} else 4
        if version == 3:
            tags.update_to_v23()
        tags.save(str(target), v2_version=version)
        return

    old = MutagenFile(str(source))
    new = MutagenFile(str(target))
    if old is None or new is None:
        raise ReplaceError('Could not read the tags')
    new.delete()
    if new.tags is None:
        new.add_tags()
    if old.tags is not None:
        for key in list(old.tags.keys()):
            new.tags[key] = old.tags[key]
    # FLAC keeps pictures outside the Vorbis comments.
    for picture in getattr(old, 'pictures', None) or []:
        new.add_picture(picture)
    new.save()


def _length(path: Path) -> float:
    try:
        audio = MutagenFile(str(path))
    except Exception:
        return 0.0
    info = getattr(audio, 'info', None)
    return float(getattr(info, 'length', 0.0) or 0.0)


# ── The swap ────────────────────────────────────────────────────────────


def staging_basename(path: Path) -> str:
    """The name new audio is downloaded under, beside *path* (the library
    scan skips it)."""

    return f'{path.stem}{UPGRADE_STAGING_MARKER}'


def replace_audio(
    downloader: Any,
    target: Path,
    video_id: str,
    *,
    song: dict[str, Any],
    progress_cb: Optional[ProgressCallback] = None,
) -> dict[str, Any]:
    """Replace *target*'s audio with YouTube video *video_id* (or the
    SoundCloud track it is the URL of), keeping its path, format, tags and
    modification time. ``{duration_before,
    duration_after}``. Raises :class:`ReplaceError` (nothing changed) or
    the download's own error."""

    fmt = replacement_format(target)
    if not target.is_file():
        raise ReplaceError('The file is no longer in the library')
    before = _length(target)
    stat = target.stat()
    basename = staging_basename(target)
    provider = (
        'soundcloud'
        if providers.parse_soundcloud_url(video_id) is not None
        else 'youtube'
    )
    staged: Optional[Path] = None
    try:
        staged = downloader.fetch_audio(
            video_id,
            target.parent,
            basename,
            song=song,
            progress_cb=progress_cb,
            provider=provider,
            audio_format=fmt,
        )
        if staged.suffix.lower() != target.suffix.lower():
            raise ReplaceError(
                f'The download came out as {staged.suffix}, not {target.suffix}'
            )
        after = _length(staged)
        if after <= 0:
            raise ReplaceError('The downloaded audio could not be read')
        if progress_cb is not None:
            progress_cb(98.0, 'Copying tags', provider)
        copy_tags(target, staged)
        os.replace(str(staged), str(target))
        staged = None
    finally:
        # Whatever is left of the staging download (a failed conversion
        # leaves the upstream file) goes.
        for leftover in target.parent.glob(f'{basename}.*'):
            if leftover.is_file():
                leftover.unlink(missing_ok=True)
    try:
        os.utime(str(target), ns=(stat.st_atime_ns, stat.st_mtime_ns))
    except OSError:
        pass
    logger.info(
        'Replaced the audio of {} with video {} ({:.0f}s -> {:.0f}s)',
        target.name,
        video_id,
        before,
        after,
    )
    return {
        'duration_before': round(before, 1),
        'duration_after': round(after, 1),
    }


# ── From a file ─────────────────────────────────────────────────────────


def upload_format(name: str) -> str:
    """The format of an uploaded file, from its name (``ReplaceError``
    for anything that isn't an audio file Downtify takes)."""

    fmt = Path(str(name or '')).suffix.lower().lstrip('.')
    if fmt not in UPLOAD_FORMATS:
        raise ReplaceError(
            f'Upload an audio file: {", ".join(UPLOAD_FORMATS)}'
        )
    return fmt


def upload_staging_path(target: Path, fmt: str) -> Path:
    """Where an upload for *target* is written while it arrives: beside
    it, under a name the library scan skips."""

    return target.with_name(f'{staging_basename(target)}.upload.{fmt}')


def _ffmpeg() -> Optional[str]:
    return shutil.which('ffmpeg')


def _decodes(path: Path, ffmpeg: str) -> bool:
    """Whether ffmpeg reads *path* through to the end without an error
    (a truncated or renamed non-audio file doesn't)."""

    try:
        subprocess.run(
            [ffmpeg, '-nostdin', '-v', 'error', '-xerror', '-i', str(path)]
            + ['-map', '0:a:0', '-f', 'null', '-'],
            check=True,
            capture_output=True,
            timeout=300,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return True


def _convert(
    source: Path, output: Path, fmt: str, bitrate: str, ffmpeg: str
) -> None:
    """Re-encode *source*'s audio as *fmt* into *output* (no tags, no
    cover: those come from the library file)."""

    args = [ffmpeg, '-nostdin', '-v', 'error', '-y', '-i', str(source)]
    args += ['-map', '0:a:0', '-map_metadata', '-1', '-vn']
    args += ['-c:a', _ENCODERS[fmt]]
    if fmt != 'flac' and str(bitrate).isdigit():
        args += ['-b:a', f'{bitrate}k']
    if fmt == 'm4a':
        args += ['-f', 'mp4']
    args.append(str(output))
    try:
        subprocess.run(args, check=True, capture_output=True, timeout=900)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or b'').decode('utf-8', 'replace').strip()
        logger.warning('Converting {} failed: {}', source.name, detail)
        raise ReplaceError('Could not convert the uploaded file') from exc
    except (subprocess.SubprocessError, OSError) as exc:
        raise ReplaceError('Could not convert the uploaded file') from exc


def replace_from_file(
    target: Path, upload: Path, *, bitrate: str = '320'
) -> dict[str, Any]:
    """Replace *target*'s audio with the uploaded file *upload* (already
    on disk, beside it - :func:`upload_staging_path`), keeping its path,
    format, tags and modification time. The upload is used as it is when
    it is already in *target*'s format, converted otherwise.

    ``{duration_before, duration_after, converted}``. Raises
    :class:`ReplaceError` with nothing changed. *upload* is gone
    afterwards either way."""

    converted: Optional[Path] = None
    try:
        fmt = replacement_format(target)
        if not target.is_file():
            raise ReplaceError('The file is no longer in the library')
        upload_fmt = upload_format(upload.name)
        ffmpeg = _ffmpeg()
        if _length(upload) <= 0 or (ffmpeg and not _decodes(upload, ffmpeg)):
            raise ReplaceError('The uploaded file is not readable audio')
        before = _length(target)
        stat = target.stat()
        if upload_fmt == fmt:
            staged = upload
        else:
            if not ffmpeg:
                raise ReplaceError(
                    f'Converting to .{fmt} needs ffmpeg: upload a .{fmt} file'
                )
            converted = target.with_name(f'{staging_basename(target)}.{fmt}')
            _convert(upload, converted, fmt, bitrate, ffmpeg)
            staged = converted
        after = _length(staged)
        if after <= 0:
            raise ReplaceError('The new audio could not be read')
        copy_tags(target, staged)
        os.replace(str(staged), str(target))
        converted = None
    finally:
        upload.unlink(missing_ok=True)
        if converted is not None:
            converted.unlink(missing_ok=True)
    try:
        os.utime(str(target), ns=(stat.st_atime_ns, stat.st_mtime_ns))
    except OSError:
        pass
    logger.info(
        'Replaced the audio of {} with an uploaded .{} file '
        '({:.0f}s -> {:.0f}s{})',
        target.name,
        upload_fmt,
        before,
        after,
        ', converted' if upload_fmt != fmt else '',
    )
    return {
        'duration_before': round(before, 1),
        'duration_after': round(after, 1),
        'converted': upload_fmt != fmt,
    }
