"""Store and serve an artist's public profile - their photo and banner
today, with more (bio, social links, ...) planned later.

Photo/banner are saved as flat sidecar files under the download
directory's ``Metadata`` folder (``ArtistImage`` / ``ArtistBannerImage``),
named after the artist - the same idea as
:func:`downtify.downloader.save_playlist_cover` saving a playlist's cover
next to its M3U. There is no database row: whether the file exists on
disk is the source of truth. The download directory is already served at
``/downloads`` (see ``main.py``), so no dedicated read endpoint is needed
- only a small existence check and the write paths below.

Function names are prefixed ``image_``/``_image`` on purpose, even though
photo and banner are the only profile fields so far - a future
``fetch_bio``/``save_bio`` (or similar, for social links) belongs
alongside these without colliding in name or behaviour.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from .downloader import _sanitize
from .image_size import image_dimensions

KIND_PHOTO = 'photo'
KIND_BANNER = 'banner'

_DIRNAMES = {
    KIND_PHOTO: 'Metadata/ArtistImage',
    KIND_BANNER: 'Metadata/ArtistBannerImage',
}
_SUFFIXES = {
    KIND_PHOTO: '.jpg',
    KIND_BANNER: '.banner.jpg',
}

#: Refuse anything implausibly large for a profile photo or banner.
MAX_IMAGE_BYTES = 15 * 1024 * 1024

_IMAGE_FETCH_TIMEOUT = 20


def image_path_for(download_dir: Path, name: str, kind: str) -> Path:
    """Sidecar file for *name*'s photo/banner, whether or not it exists."""

    return (
        Path(download_dir)
        / _DIRNAMES[kind]
        / f'{_sanitize(name)}{_SUFFIXES[kind]}'
    )


def image_url_for(download_dir: Path, name: str, kind: str) -> Optional[str]:
    """The ``/downloads/...`` URL for *name*'s photo/banner, or ``None``."""

    path = image_path_for(download_dir, name, kind)
    if not path.is_file():
        return None
    rel = path.relative_to(Path(download_dir)).as_posix()
    return f'/downloads/{rel}'


def _write_image(download_dir: Path, name: str, kind: str, data: bytes) -> str:
    path = image_path_for(download_dir, name, kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    rel = path.relative_to(Path(download_dir)).as_posix()
    return f'/downloads/{rel}'


def save_image(download_dir: Path, name: str, kind: str, data: bytes) -> str:
    """Validate *data* is a real image and save it; returns its public URL."""

    if (
        not data
        or len(data) > MAX_IMAGE_BYTES
        or image_dimensions(data) is None
    ):
        raise ValueError('Not a valid image')
    return _write_image(download_dir, name, kind, data)


def fetch_and_save_image(
    download_dir: Path, name: str, kind: str, image_url: str
) -> str:
    """Download *image_url* and save it as *name*'s photo/banner."""

    url = (image_url or '').strip()
    if not url:
        raise ValueError('No image URL given')
    try:
        resp = httpx.get(
            url, timeout=_IMAGE_FETCH_TIMEOUT, follow_redirects=True
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.opt(exception=True).debug(
            'Artist art fetch failed for {}', url[:200]
        )
        raise ValueError('Could not fetch that image') from exc
    return save_image(download_dir, name, kind, resp.content)


def delete_image(download_dir: Path, name: str, kind: str) -> bool:
    """Remove *name*'s saved photo/banner. Returns whether a file was removed."""

    path = image_path_for(download_dir, name, kind)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
