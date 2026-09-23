"""Store and serve an artist's public profile: photo, banner, bio, social
links, related artists and platform ids.

Photo/banner are saved as flat sidecar files under the download
directory's ``Metadata`` folder (``ArtistImage`` / ``ArtistBannerImage``),
named after the artist - the same idea as
:func:`downtify.downloader.save_playlist_cover` saving a playlist's cover
next to its M3U. There is no database row: whether the file exists on
disk is the source of truth. The download directory is already served at
``/downloads`` (see ``main.py``), so no dedicated read endpoint is needed
- only a small existence check and the write paths below.

The rest of the profile (bio, social links, related artists, platform
ids, and which source each saved photo/banner came from) lives in one
JSON sidecar per artist, ``Metadata/ArtistData/<name>.json`` - see
:func:`load_profile`/:func:`fetch_bio`. Bio, social links and related
artists all come from Deezer (:mod:`downtify.deezer`) when it has an
exact name match; YouTube Music (:mod:`downtify.providers`) is a
bio-only fallback for when Deezer doesn't. Always fetched on demand (a
button on the artist page), never automatically.

Function names are prefixed ``image_``/``_image`` for the photo/banner
half on purpose, to keep it visually distinct from the profile-data half
added later.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import httpx
from loguru import logger

from . import deezer, providers
from .downloader import _sanitize
from .image_size import image_dimensions
from .podcasts import strip_html

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
_PROFILE_DIRNAME = 'Metadata/ArtistData'

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


def save_image(
    download_dir: Path,
    name: str,
    kind: str,
    data: bytes,
    source: str = '',
) -> str:
    """Validate *data* is a real image and save it; returns its public URL.

    *source* (``spotify``/``youtube``/``deezer``/``link``/``upload``), if
    given, is recorded as ``current_cover``/``current_cover_banner`` in
    the artist's profile JSON (see :func:`load_profile`).
    """

    if (
        not data
        or len(data) > MAX_IMAGE_BYTES
        or image_dimensions(data) is None
    ):
        raise ValueError('Not a valid image')
    url = _write_image(download_dir, name, kind, data)
    if source:
        _set_current_cover(download_dir, name, kind, source)
    return url


def fetch_and_save_image(
    download_dir: Path,
    name: str,
    kind: str,
    image_url: str,
    source: str = '',
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
    return save_image(download_dir, name, kind, resp.content, source=source)


def delete_image(download_dir: Path, name: str, kind: str) -> bool:
    """Remove *name*'s saved photo/banner. Returns whether a file was removed."""

    path = image_path_for(download_dir, name, kind)
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    _set_current_cover(download_dir, name, kind, '')
    return True


# ── Profile data: bio, social links, related artists, platform ids ──


def _profile_path_for(download_dir: Path, name: str) -> Path:
    return Path(download_dir) / _PROFILE_DIRNAME / f'{_sanitize(name)}.json'


def _default_profile(name: str) -> dict[str, Any]:
    return {
        'name': name,
        'bio': '',
        'platforms_id': {'deezer': ''},
        'social': {
            'twitter': '',
            'facebook': '',
            'website': '',
            'instagram': '',
        },
        'related_artists': [],
        'current_cover': '',
        'current_cover_banner': '',
    }


def load_profile(download_dir: Path, name: str) -> dict[str, Any]:
    """*name*'s profile JSON, or a blank skeleton if none was saved yet."""

    default = _default_profile(name)
    path = _profile_path_for(download_dir, name)
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default
    if not isinstance(data, dict):
        return default
    merged = {**default, **data}
    merged['platforms_id'] = {
        **default['platforms_id'],
        **(data.get('platforms_id') or {}),
    }
    merged['social'] = {**default['social'], **(data.get('social') or {})}
    return merged


def _save_profile(
    download_dir: Path, name: str, profile: dict[str, Any]
) -> None:
    path = _profile_path_for(download_dir, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8'
    )


def _set_current_cover(
    download_dir: Path, name: str, kind: str, source: str
) -> None:
    profile = load_profile(download_dir, name)
    field = 'current_cover' if kind == KIND_PHOTO else 'current_cover_banner'
    profile[field] = source
    _save_profile(download_dir, name, profile)


def fetch_bio(download_dir: Path, name: str, lang: str) -> dict[str, Any]:
    """Fetch and save *name*'s bio, trying Deezer first, then YouTube Music.

    Deezer also brings social links and related-artist names, so it's
    tried first; its artist id is resolved once and cached (see
    :func:`downtify.deezer.resolve_artist_id`). If Deezer has no exact
    name match, or matches but has no bio text, YouTube Music's own
    artist "About" description (:func:`downtify.providers.
    artist_bio_from_channel_id`) is tried as a bio-only fallback - it
    doesn't have social links or related artists. Raises
    :class:`ValueError` only when neither source has anything at all.
    """

    profile = load_profile(download_dir, name)
    deezer_id = profile['platforms_id'].get('deezer') or ''
    if not deezer_id:
        deezer_id = deezer.resolve_artist_id(name) or ''
        if deezer_id:
            profile['platforms_id']['deezer'] = deezer_id

    if deezer_id:
        try:
            full = deezer.fetch_artist_full(deezer_id, lang)
        except ValueError:
            full = None
        if full is not None:
            profile['social'] = full['social']
            profile['related_artists'] = full['related_artist_names']
            if full['bio_html']:
                profile['bio'] = strip_html(full['bio_html'])
                _save_profile(download_dir, name, profile)
                return profile

    channel_id = providers.resolve_artist_id_by_name(name)
    bio_text = (
        providers.artist_bio_from_channel_id(channel_id, lang)
        if channel_id
        else ''
    )
    if bio_text:
        profile['bio'] = strip_html(bio_text)
        _save_profile(download_dir, name, profile)
        return profile

    if deezer_id:
        # Deezer matched (social/related may already be updated above)
        # but neither source had bio text - still worth persisting.
        _save_profile(download_dir, name, profile)
        return profile

    raise ValueError('No matching artist found on Deezer or YouTube Music')


def remove_bio(download_dir: Path, name: str) -> dict[str, Any]:
    """Clear only the saved bio text.

    ``social``, ``related_artists`` and ``platforms_id`` are left as-is -
    a re-fetch afterwards still reuses the cached Deezer id instead of
    searching by name again.
    """

    profile = load_profile(download_dir, name)
    profile['bio'] = ''
    _save_profile(download_dir, name, profile)
    return profile
