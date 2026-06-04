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


def read_audio_metadata(path: Path) -> dict[str, Any]:
    """Return ``title``, ``artist``, ``artists``, and ``album`` from file tags."""

    empty: dict[str, Any] = {
        'title': '',
        'artist': '',
        'artists': [],
        'album': '',
    }
    if not path.is_file():
        return dict(empty)

    title = ''
    artist = ''
    album = ''

    try:
        audio = MutagenFile(str(path), easy=True)
    except Exception:
        audio = None

    if audio is not None:
        title = _tag_text(audio.get('title'))
        artist = _tag_text(audio.get('artist'))
        album = _tag_text(audio.get('album'))

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

    artists = _split_artists(artist)
    return {
        'title': title,
        'artist': artist,
        'artists': artists,
        'album': album,
    }


def library_entry_for_file(
    stored_path: str, full_path: Path
) -> dict[str, str]:
    """Build one ``/list`` row using tags, then filename fallbacks."""

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
        'has_cover': file_has_cover_art(full_path),
    }


def _fallback_title_from_filename(path: Path) -> tuple[str, str]:
    """Parse ``Artist - Title`` from the basename when tags are missing."""

    stem = path.stem
    dash = stem.find(' - ')
    if dash > 0:
        return stem[dash + 3 :].strip(), stem[:dash].strip()
    return stem, ''
