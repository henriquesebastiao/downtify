"""Replace a library track's audio with a version the user picks.

Automatic matching sometimes lands on the wrong song or the wrong version
(a live cut, a remix, a lyric video with an intro). From a track's menu,
an admin searches YouTube Music and YouTube (or pastes a link), picks the
right upload, and the file's audio is swapped for it:

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
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger
from mutagen import File as MutagenFile
from mutagen.id3 import ID3, ID3NoHeaderError

from . import providers
from .library_catalog import UPGRADE_STAGING_MARKER

#: File types whose audio can be replaced: the formats Downtify writes.
REPLACEABLE_FORMATS = ('mp3', 'flac', 'm4a', 'ogg', 'opus')

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


def _from_link(query: str) -> Optional[list[dict[str, Any]]]:
    """The one video a pasted YouTube / YouTube Music link names, or
    ``None`` when *query* isn't such a link."""

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
    """Replace *target*'s audio with YouTube video *video_id*, keeping its
    path, format, tags and modification time. ``{duration_before,
    duration_after}``. Raises :class:`ReplaceError` (nothing changed) or
    the download's own error."""

    fmt = replacement_format(target)
    if not target.is_file():
        raise ReplaceError('The file is no longer in the library')
    before = _length(target)
    stat = target.stat()
    basename = staging_basename(target)
    staged: Optional[Path] = None
    try:
        staged = downloader.fetch_audio(
            video_id,
            target.parent,
            basename,
            song=song,
            progress_cb=progress_cb,
            provider='youtube',
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
            progress_cb(98.0, 'Copying tags', 'youtube')
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
