"""Extract embedded cover art from audio files."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from mutagen import File as MutagenFile
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis


def _embedded_cover_from_id3(path: Path) -> tuple[bytes | None, str | None]:
    try:
        tag = ID3(str(path))
        for frame in tag.getall('APIC'):
            if frame.data:
                return frame.data, frame.mime or 'image/jpeg'
    except Exception:
        pass
    return None, None


def _embedded_cover_from_flac(path: Path) -> tuple[bytes | None, str | None]:
    try:
        f = FLAC(str(path))
        if f.pictures:
            pic = f.pictures[0]
            return pic.data, pic.mime or 'image/jpeg'
    except Exception:
        pass
    return None, None


def _embedded_cover_from_mp4(path: Path) -> tuple[bytes | None, str | None]:
    try:
        m = MP4(str(path))
        covr = m.tags.get('covr') if m.tags else None
        if not covr:
            return None, None
        pic = covr[0]
        fmt = getattr(pic, 'imageformat', None)
        mime = 'image/png' if fmt == 14 else 'image/jpeg'
        return bytes(pic), mime
    except Exception:
        return None, None


def _embedded_cover_from_ogg(path: Path) -> tuple[bytes | None, str | None]:
    try:
        ogg = (
            OggOpus(str(path))
            if path.suffix.lower() == '.opus'
            else OggVorbis(str(path))
        )
        blocks = ogg.get('metadata_block_picture') or []
        for raw in blocks:
            try:
                pic = Picture(base64.b64decode(raw))
                if pic.data:
                    return pic.data, pic.mime or 'image/jpeg'
            except Exception:
                continue
    except Exception:
        pass
    return None, None


def _embedded_cover_from_mutagen(
    path: Path,
) -> tuple[bytes | None, str | None]:
    try:
        f = MutagenFile(str(path))
        if f is not None and getattr(f, 'pictures', None):
            pic = f.pictures[0]
            return pic.data, pic.mime or 'image/jpeg'
    except Exception:
        pass
    return None, None


def extract_embedded_cover(path: Path) -> tuple[bytes | None, str | None]:
    """Return ``(image_bytes, mime)`` for the embedded cover, or ``(None, None)``."""

    suffix = path.suffix.lower()
    data, mime = _embedded_cover_from_id3(path)
    if data:
        return data, mime
    if suffix == '.flac':
        data, mime = _embedded_cover_from_flac(path)
        if data:
            return data, mime
    if suffix in {'.m4a', '.mp4', '.aac'}:
        data, mime = _embedded_cover_from_mp4(path)
        if data:
            return data, mime
    if suffix in {'.ogg', '.opus'}:
        data, mime = _embedded_cover_from_ogg(path)
        if data:
            return data, mime
    return _embedded_cover_from_mutagen(path)


_FOLDER_COVER_STEMS = frozenset({
    'cover',
    'folder',
    'front',
    'album',
    'artwork',
    'albumart',
})


def _mime_for_image(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or 'image/jpeg'


def extract_folder_cover(path: Path) -> tuple[bytes | None, str | None]:
    """Return cover image bytes from common filenames next to *path*."""

    parent = path.parent
    if not parent.is_dir():
        return None, None

    try:
        entries = list(parent.iterdir())
    except OSError:
        return None, None

    for entry in sorted(entries, key=lambda p: p.name.casefold()):
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
            continue
        if entry.resolve() == path.resolve():
            continue
        if entry.stem.casefold() not in _FOLDER_COVER_STEMS:
            continue
        try:
            data = entry.read_bytes()
        except OSError:
            continue
        if data:
            return data, _mime_for_image(entry)
    return None, None


def extract_cover_art(path: Path) -> tuple[bytes | None, str | None]:
    """Embedded tags first, then ``cover.jpg`` / ``folder.jpg`` in the same folder."""

    data, mime = extract_embedded_cover(path)
    if data:
        return data, mime
    return extract_folder_cover(path)
