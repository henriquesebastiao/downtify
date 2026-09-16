"""Read embedded audio tags for library / player display."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile
from mutagen.id3 import ID3

from .cover_art import file_has_cover_art


def _tag_text(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, list):
        parts = [_tag_text(item) for item in value]
        return '; '.join(part for part in parts if part)
    return str(value).strip()


def _split_artists(artist: str) -> list[str]:
    text = artist.strip()
    if not text:
        return []
    for sep in (';', '/', ',', '\\'):
        if sep in text:
            return [part.strip() for part in text.split(sep) if part.strip()]
    return [text]


def _track_number(value: Any) -> int:
    """``3``, ``'3'`` or ``'3/12'`` -> 3; anything unreadable -> 0."""

    text = _tag_text(value).split('/', 1)[0].strip()
    try:
        return max(0, int(text))
    except ValueError:
        return 0


def _year(value: Any) -> str:
    text = _tag_text(value)
    return text[:4] if len(text) >= 4 and text[:4].isdigit() else ''


def _duration(audio: Any) -> float:
    try:
        length = float(audio.info.length)
    except (AttributeError, TypeError, ValueError):
        return 0.0
    return round(length, 2) if length > 0 else 0.0


def read_audio_metadata(path: Path) -> dict[str, Any]:
    """Return display tags read from ``path``.

    ``title``, ``artist``, ``artists`` and ``album``, plus
    ``album_artist``, ``track_number`` (0 when unknown), ``year`` and
    ``duration`` in seconds (0 when unknown).
    """

    empty: dict[str, Any] = {
        'title': '',
        'artist': '',
        'artists': [],
        'album': '',
        'album_artist': '',
        'track_number': 0,
        'year': '',
        'duration': 0.0,
    }
    if not path.is_file():
        return dict(empty)

    title = ''
    artist = ''
    album = ''
    album_artist = ''
    track_number = 0
    year = ''
    duration = 0.0

    try:
        audio = MutagenFile(str(path), easy=True)
    except Exception:
        audio = None

    if audio is not None:
        title = _tag_text(audio.get('title'))
        artist = _tag_text(audio.get('artist'))
        album = _tag_text(audio.get('album'))
        album_artist = _tag_text(audio.get('albumartist'))
        track_number = _track_number(audio.get('tracknumber'))
        year = _year(audio.get('date'))
        duration = _duration(audio)

        if not title and audio.tags is not None:
            title = _tag_text(audio.tags.get('title'))
        if not artist and audio.tags is not None:
            artist = _tag_text(audio.tags.get('artist'))
        if not album and audio.tags is not None:
            album = _tag_text(audio.tags.get('album'))

    if not title and not artist and not album:
        try:
            id3 = ID3(str(path))
        except Exception:
            id3 = None
        if id3 is not None:
            title = _tag_text(id3.get('TIT2'))
            artist = _tag_text(id3.get('TPE1'))
            album = _tag_text(id3.get('TALB'))
            album_artist = _tag_text(id3.get('TPE2'))
            track_number = _track_number(id3.get('TRCK'))
            year = _year(id3.get('TDRC'))

    artists = _split_artists(artist)
    return {
        'title': title,
        'artist': artist,
        'artists': artists,
        'album': album,
        'album_artist': album_artist,
        'track_number': track_number,
        'year': year,
        'duration': duration,
    }


def file_stat_fields(full_path: Path) -> dict[str, int]:
    """``added`` (modification time, epoch seconds) and ``size`` in bytes."""

    try:
        st = full_path.stat()
    except OSError:
        return {'added': 0, 'size': 0}
    return {'added': int(st.st_mtime), 'size': int(st.st_size)}


def library_entry_for_file(
    stored_path: str, full_path: Path
) -> dict[str, Any]:
    """Build one ``/tracks`` row using tags, then filename fallbacks."""

    fb_title, fb_artist = _fallback_title_from_filename(full_path)
    meta = read_audio_metadata(full_path)
    title = str(meta.get('title') or '').strip() or fb_title
    artist = str(meta.get('artist') or '').strip() or fb_artist
    album = str(meta.get('album') or '').strip()
    return {
        'file': stored_path,
        'title': title,
        'artist': artist,
        'album': album,
        'album_artist': str(meta.get('album_artist') or '').strip(),
        'track_number': int(meta.get('track_number') or 0),
        'year': str(meta.get('year') or ''),
        'duration': float(meta.get('duration') or 0.0),
        'has_cover': file_has_cover_art(full_path),
        **file_stat_fields(full_path),
    }


def _fallback_title_from_filename(path: Path) -> tuple[str, str]:
    """Parse ``Artist - Title`` from the basename when tags are missing."""

    stem = path.stem
    dash = stem.find(' - ')
    if dash > 0:
        return stem[dash + 3 :].strip(), stem[:dash].strip()
    return stem, ''
