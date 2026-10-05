"""Read embedded audio tags for library / player display."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile
from mutagen.id3 import ID3
from mutagen.mp4 import MP4

from .album_artist import is_act_of
from .cover_art import extract_cover_art
from .image_size import image_short_side


def _tag_text(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, list):
        parts = [_tag_text(item) for item in value]
        return '; '.join(part for part in parts if part)
    return str(value).strip()


def split_artists(artist: str, album_artist: str = '') -> list[str]:
    """The artists in an artist tag's text, for a file with no ``ARTISTS``
    tag: split on the first of ``;`` (how Downtify joins them in MP3 and
    how a multi-value tag reads back), `` / `` or ``, `` it contains - the
    web app's own rule (``frontend/src/lib/library.js``). ``AC/DC`` stays
    whole, and so does a text that is the file's *album_artist* too
    (``Earth, Wind & Fire`` on its own album): that is one name.

    So is a split whose names make up the album artist: an act YouTube
    Music credited as its members, which older Downtify versions wrote as
    ``Henrique; Juliano`` on an album by ``Henrique, Juliano`` - one act,
    named as its album is."""

    text = str(artist or '').strip()
    if not text:
        return []
    album_artist = str(album_artist or '').strip()
    if text.casefold() == album_artist.casefold():
        return [text]
    for sep in (';', ' / ', ', '):
        if sep in text:
            parts = [part.strip() for part in text.split(sep) if part.strip()]
            if is_act_of(parts, album_artist):
                return [album_artist]
            return parts
    return [text]


def _multi_value_artists(path: Path, audio: Any) -> list[str]:
    """The ``ARTISTS`` tag - one artist per value, as Downtify and
    MusicBrainz Picard write it - or ``[]`` when the file has none."""

    suffix = path.suffix.lower()
    try:
        if suffix == '.mp3':
            frame = ID3(str(path)).get('TXXX:ARTISTS')
            values = list(frame.text) if frame is not None else []
        elif suffix in {'.m4a', '.mp4', '.aac'}:
            tags = MP4(str(path)).tags or {}
            values = [
                bytes(value).decode('utf-8', 'replace')
                for value in tags.get('----:com.apple.iTunes:ARTISTS', [])
            ]
        else:
            tags = getattr(audio, 'tags', None)
            values = list(tags.get('artists') or []) if tags else []
    except Exception:
        return []
    return [str(value).strip() for value in values if str(value).strip()]


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


def _codec(audio: Any) -> str:
    """The audio codec, in the names a client knows: ``mp3``, ``flac``,
    ``aac``, ``alac``, ``opus``, ``vorbis`` - ``''`` when unknown."""

    kind = type(audio).__name__.lower()
    if kind in {'mp3', 'easymp3'}:
        return 'mp3'
    if kind == 'flac':
        return 'flac'
    if kind in {'oggopus'}:
        return 'opus'
    if kind in {'oggvorbis'}:
        return 'vorbis'
    if kind in {'mp4', 'easymp4'}:
        codec = str(getattr(audio.info, 'codec', '') or '').lower()
        if codec.startswith('mp4a'):
            return 'aac'
        return codec or 'aac'
    return ''


def audio_format(audio: Any) -> dict[str, Any]:
    """``codec``, ``bitrate`` (bits/s), ``sample_rate`` (Hz) and
    ``channels`` of a mutagen file; zeros and ``''`` when unknown."""

    info = getattr(audio, 'info', None)

    def number(name: str) -> int:
        try:
            return max(0, int(getattr(info, name, 0) or 0))
        except (TypeError, ValueError):
            return 0

    return {
        'codec': _codec(audio) if audio is not None else '',
        'bitrate': number('bitrate'),
        'sample_rate': number('sample_rate'),
        'channels': number('channels'),
    }


def read_audio_metadata(path: Path) -> dict[str, Any]:
    """Return display tags read from ``path``.

    ``title``, ``artist``, ``artists`` and ``album``, plus
    ``album_artist``, ``track_number`` (0 when unknown), ``year`` and
    ``duration`` in seconds (0 when unknown), plus the audio format:
    ``codec``, ``bitrate``, ``sample_rate`` and ``channels`` (see
    :func:`audio_format`).
    """

    empty: dict[str, Any] = {
        'title': '',
        'artist': '',
        'artists': [],
        'album': '',
        'album_artist': '',
        'track_number': 0,
        'year': '',
        'genre': '',
        'duration': 0.0,
        **audio_format(None),
    }
    if not path.is_file():
        return dict(empty)

    title = ''
    artist = ''
    album = ''
    album_artist = ''
    track_number = 0
    year = ''
    genre = ''
    duration = 0.0

    try:
        audio = MutagenFile(str(path), easy=True)
    except Exception:
        audio = None
    fmt = audio_format(audio)

    if audio is not None:
        title = _tag_text(audio.get('title'))
        artist = _tag_text(audio.get('artist'))
        album = _tag_text(audio.get('album'))
        album_artist = _tag_text(audio.get('albumartist'))
        track_number = _track_number(audio.get('tracknumber'))
        year = _year(audio.get('date'))
        genre = _tag_text(audio.get('genre'))
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
            genre = _tag_text(id3.get('TCON'))

    artists = _multi_value_artists(path, audio) or split_artists(
        artist, album_artist
    )
    return {
        'title': title,
        'artist': artist,
        'artists': artists,
        'album': album,
        'album_artist': album_artist,
        'track_number': track_number,
        'year': year,
        'genre': genre,
        'duration': duration,
        **fmt,
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
    artists = [
        str(name).strip()
        for name in meta.get('artists') or []
        if str(name).strip()
    ] or split_artists(artist, str(meta.get('album_artist') or ''))
    album = str(meta.get('album') or '').strip()
    # The cover is read once and both answered from it: whether there is
    # one, and how big it is (which the library upgrade scan needs for
    # every track, and would otherwise pay a second full read for).
    cover_data, _cover_mime = (
        extract_cover_art(full_path) if full_path.is_file() else (None, None)
    )
    return {
        'file': stored_path,
        'title': title,
        'artist': artist,
        # Every credited artist, one per entry (see read_audio_metadata).
        'artists': artists,
        'album': album,
        'album_artist': str(meta.get('album_artist') or '').strip(),
        'track_number': int(meta.get('track_number') or 0),
        'year': str(meta.get('year') or ''),
        'genre': str(meta.get('genre') or ''),
        'duration': float(meta.get('duration') or 0.0),
        'codec': str(meta.get('codec') or ''),
        'bitrate': int(meta.get('bitrate') or 0),
        'sample_rate': int(meta.get('sample_rate') or 0),
        'channels': int(meta.get('channels') or 0),
        'has_cover': bool(cover_data),
        'cover_px': image_short_side(cover_data),
        **file_stat_fields(full_path),
    }


def _fallback_title_from_filename(path: Path) -> tuple[str, str]:
    """Parse ``Artist - Title`` from the basename when tags are missing."""

    stem = path.stem
    dash = stem.find(' - ')
    if dash > 0:
        return stem[dash + 3 :].strip(), stem[:dash].strip()
    return stem, ''
