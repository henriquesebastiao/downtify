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

The rest of the profile (bio, origin, formation year, social links,
related artists, platform ids, and which source each saved photo/banner
came from) lives in one JSON sidecar per artist,
``Metadata/ArtistData/<name>.json`` - see :func:`load_profile`/
:func:`fetch_bio`. Apple Music (:mod:`downtify.apple_music`) is the
primary bio source - it also brings origin/formation year/genre/group flag/
hero colour, nothing else supplies those; Deezer (:mod:`downtify.deezer`)
is the secondary bio source (used only when Apple's bio is empty for
that artist/language) and the only source for social links and related
artists. Always fetched on demand (a button on the artist page) - except
for a brand-new artist's very first profile, seeded automatically by
:func:`ensure_profile` (photo/banner from Spotify/YouTube Music - only
the ones the user's settings allow - and bio/social/platform ids the same
way the button would).

The artist's Spotify top songs are kept here too, as a cache next to the
profile (``Metadata/ArtistTopSongs/<name>.topsongs.json``, see the last
section):
not part of the profile itself, so it has a file of its own.

Function names are prefixed ``image_``/``_image`` for the photo/banner
half and ``profile_top_songs_`` for the top-songs cache on purpose, to keep
them visually distinct from the profile-data half added later - and from
:func:`downtify.spotify.artist_top_songs_from_id`, which only fetches.
"""

from __future__ import annotations

import contextlib
import json
import os
import queue
import re
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlsplit

import httpx
from loguru import logger

from . import apple_music, deezer, providers, spotify
from .downloader import _sanitize
from .file_naming import file_name_key
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
_TOP_SONGS_DIRNAME = 'Metadata/ArtistTopSongs'
# ``<name>.topsongs.json``: the artist's profile is ``<name>.json`` in its own
# folder, and one JSON per artist in both is easy to mix up.
_TOP_SONGS_SUFFIX = '.topsongs.json'

#: How many of the artist's top songs are kept.
TOP_SONGS_LIMIT = 5
#: How long a saved top-songs file is trusted before it is fetched again.
TOP_SONGS_TTL = timedelta(days=7)
#: The top-songs file layout. A file of an older layout counts as stale, so
#: a new field (2: each song's ``preview_url``) shows up on the next visit
#: instead of when the week is out.
TOP_SONGS_SCHEMA = 2

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


def image_version_for(
    download_dir: Path, name: str, kind: str
) -> Optional[int]:
    """When *name*'s photo/banner file last changed (milliseconds since
    the epoch), or ``None`` if there is none.

    A saved image keeps the same ``/downloads/...`` URL however often it
    is replaced, so a browser holding the old one has no reason to ask
    again. Callers put this in the URL (``?v=<version>``): it changes
    exactly when the file does, so a replaced photo shows up at once and
    an untouched one stays cached.
    """

    try:
        return int(
            image_path_for(download_dir, name, kind).stat().st_mtime * 1000
        )
    except OSError:
        return None


def _write_image(download_dir: Path, name: str, kind: str, data: bytes) -> str:
    path = image_path_for(download_dir, name, kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    rel = path.relative_to(Path(download_dir)).as_posix()
    return f'/downloads/{rel}'


def _origin_path(url: str) -> str:
    """The part of an image URL that names the image rather than the CDN
    serving it: the path, without host, query or fragment
    (``https://image-cdn-ak.spotifycdn.com/image/ab67…?x=1`` ->
    ``/image/ab67…``). ``''`` when there is none."""

    path = urlsplit((url or '').strip()).path
    return path if path.strip('/') else ''


def save_image(
    download_dir: Path,
    name: str,
    kind: str,
    data: bytes,
    source: str = '',
    origin: str = '',
) -> str:
    """Validate *data* is a real image and save it; returns its public URL.

    What the image was made from is recorded as ``current_cover`` (photo) /
    ``current_cover_banner`` (banner) in the artist's profile JSON (see
    :func:`load_profile`), so the picker can highlight the candidate in
    use: *origin*, the path of the URL it was downloaded from (see
    :func:`_origin_path`), or - with none, an upload - *source*
    (``upload``). Saving with neither clears a value already there, since
    it described the previous image, not this one.
    """

    if (
        not data
        or len(data) > MAX_IMAGE_BYTES
        or image_dimensions(data) is None
    ):
        raise ValueError('Not a valid image')
    url = _write_image(download_dir, name, kind, data)
    recorded = origin or source
    # Nothing to record and no profile yet: don't create one just for this.
    if recorded or _profile_path_for(download_dir, name).is_file():
        _set_current_cover(download_dir, name, kind, recorded)
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
    return save_image(
        download_dir,
        name,
        kind,
        resp.content,
        source=source,
        origin=_origin_path(url),
    )


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
        # Apple Music only - not translated per-language, so these don't
        # change when the bio is re-fetched in a different language.
        'origin': '',
        'born_or_formed': '',
        'genre': '',
        'is_group': None,
        'banner_bg_color': '',
        # Resolved automatically by ensure_profile/fetch_bio (Spotify: from
        # one of the artist's own tracks, else an exact-name search); a
        # manually edited profile JSON renders its platform icons too.
        'platforms_id': {
            'spotify': '',
            'youtubemusic': '',
            'deezer': '',
            'applemusic': '',
        },
        'social': {
            'twitter': '',
            'facebook': '',
            'website': '',
            'instagram': '',
            'youtube': '',
        },
        'related_artists': [],
        # Which image the saved photo/banner is: the path of the URL it was
        # downloaded from, or 'upload' (see save_image). The picker marks the
        # candidate with the same image as the one in use.
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
    platforms = dict(data.get('platforms_id') or {})
    # Files saved before the key was renamed call Apple Music's id
    # 'itunes' - same id, same 'slug/numeric-id' shape. Read it under the
    # new name; the file itself is rewritten on its next save.
    legacy_apple_id = platforms.pop('itunes', '')
    if legacy_apple_id and not platforms.get('applemusic'):
        platforms['applemusic'] = legacy_apple_id
    merged['platforms_id'] = {**default['platforms_id'], **platforms}
    merged['social'] = {**default['social'], **(data.get('social') or {})}
    merged['bio'] = _normalize_stored_bio(str(merged.get('bio') or ''))
    return merged


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write *data* to *path* atomically (a temp file in the same folder,
    then a rename): a reader never sees a half-written file, even with a
    request racing a background write of the same artist."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            Path(tmp).unlink()
        raise


def _save_profile(
    download_dir: Path, name: str, profile: dict[str, Any]
) -> None:
    _atomic_write_json(_profile_path_for(download_dir, name), profile)


def _set_current_cover(
    download_dir: Path, name: str, kind: str, value: str
) -> None:
    profile = load_profile(download_dir, name)
    field = 'current_cover' if kind == KIND_PHOTO else 'current_cover_banner'
    profile[field] = value
    _save_profile(download_dir, name, profile)


def _cached_apple_music_id(profile: dict[str, Any]) -> str:
    # platforms_id['applemusic'] stores 'slug/numeric-id' (see fetch_artist_full
    # below), but the catalog API only takes the numeric id - pull it back
    # out of a cached value instead of re-searching by name every time.
    cached = profile['platforms_id'].get('applemusic') or ''
    match = re.search(r'(\d+)$', cached)
    return match.group(1) if match else ''


def _cached_or_resolved_apple_music_id(
    profile: dict[str, Any], name: str
) -> str:
    return _cached_apple_music_id(profile) or (
        apple_music.resolve_artist_id(name) or ''
    )


class ProfileUnavailable(Exception):
    """A service that had to answer (Apple Music, Deezer) failed - an error,
    not "this artist isn't there". Seeding a profile raises it *before*
    writing anything, so no half-made profile stands in for the real one: the
    artist is seeded the next time they are needed."""


_BULLET_RE = re.compile(r'^•\s*')


def _format_bio_text(raw: str) -> str:
    """*raw* (Deezer's own ``<p>`` HTML, Apple Music's text with a ``•``
    list, or a user's manually typed text) turned into plain text:
    paragraphs separated by one blank line, and no HTML left at all.

    Every ``•`` bullet is dropped and starts a paragraph of its own -
    Apple separates its bullets with a single line break, so without this
    they'd render as one long paragraph. A single line break anywhere
    else is kept as it is.

    Starts from :func:`downtify.podcasts.strip_html`, which already turns
    block tags (``<p>``, ``<br>``, ``<li>`` ...) into line breaks and
    drops every other tag, so Deezer's HTML comes out as paragraphs
    separated by blank lines. Idempotent - running its own output through
    again changes nothing.
    """

    text = strip_html(raw)
    if not text:
        return ''
    paragraphs: list[list[str]] = []
    for block in re.split(r'\n\s*\n', text):
        current: list[str] = []
        for raw_line in block.split('\n'):
            line = raw_line.strip()
            if not line:
                continue
            if _BULLET_RE.match(line):
                if current:
                    paragraphs.append(current)
                current = []
                line = _BULLET_RE.sub('', line)
            if line:
                current.append(line)
        if current:
            paragraphs.append(current)
    return '\n\n'.join('\n'.join(lines) for lines in paragraphs)


def _normalize_stored_bio(bio: str) -> str:
    """A bio saved by an earlier version (HTML, maybe with a ``<ul>``
    list, or plain text still carrying ``•`` bullets) brought up to
    today's plain-text shape on read - a no-op for one already in it.
    Nothing is rewritten on disk until the next save.
    """

    if not bio or not ('<' in bio or '•' in bio):
        return bio
    # A list item is a bullet like any other: it ends up a paragraph.
    bio = re.sub(r'<li[^>]*>', '\n• ', bio).replace('</li>', '\n')
    return _format_bio_text(bio)


def _merge_names(existing: list[str], new: list[str]) -> list[str]:
    """*existing* followed by whichever of *new* isn't already present,
    case-insensitively - combines two platforms' related-artist name
    lists without duplicating an artist both happen to agree on.
    """

    seen = {n.strip().lower() for n in existing if n}
    merged = list(existing)
    for name in new:
        key = name.strip().lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(name)
    return merged


#: Which service's biography :func:`fetch_bio` should use.
BIO_SOURCE_AUTO = 'auto'
BIO_SOURCE_APPLE_MUSIC = 'applemusic'
BIO_SOURCE_DEEZER = 'deezer'
_BIO_SOURCES = (BIO_SOURCE_AUTO, BIO_SOURCE_APPLE_MUSIC, BIO_SOURCE_DEEZER)


def _fill_empty_social(
    current: dict[str, str], fetched: dict[str, str]
) -> dict[str, str]:
    """*current* with each of its empty links filled from *fetched*.

    Deezer sends an empty string for every network it doesn't know, so a
    plain ``{**current, **fetched}`` would blank a link the user typed
    in to complete what Deezer lacks - and a link that is already there,
    typed or fetched earlier, is never replaced either: there's no way to
    tell a hand-corrected one from a fetched one, and losing someone's
    edit is worse than keeping a stale link (they can clear the field).
    """

    merged = dict(current)
    for key, url in fetched.items():
        if url and not str(merged.get(key) or '').strip():
            merged[key] = url
    return merged


def fetch_bio(
    download_dir: Path,
    name: str,
    lang: str,
    source: str = BIO_SOURCE_AUTO,
) -> dict[str, Any]:
    """Fetch and save *name*'s bio and related profile data.

    Apple Music is the primary bio source, and the only one for origin/
    formation year/genre/group flag/banner colour - its artist id is resolved
    once and cached (see :func:`downtify.apple_music.resolve_artist_id`).
    Deezer is the secondary bio source - only used to fill the bio in
    when Apple's own is empty for that artist/language (see
    :func:`downtify.apple_music.fetch_artist_full`'s docstring: Apple's
    editorial bios aren't written for every artist in every language) -
    and a source for social links and related-artist names, which it
    contributes regardless of whether Apple already supplied a bio.
    Spotify also contributes related-artist names, merged in alongside
    Deezer's (see :func:`_merge_names`), using the cached
    ``platforms_id.spotify`` - or, when there is none yet, an exact-name
    search (:func:`_spotify_id_from_name`), cached the same way. An id
    already there - e.g. resolved from one of the artist's own Spotify
    tracks by :func:`ensure_profile` - is never replaced.

    *source* only chooses whose biography *text* is saved - every other
    field is fetched the same way whatever it is. ``'auto'`` (what
    :func:`ensure_profile` uses) is the behaviour described above: Apple
    Music's bio, Deezer's only as a fallback. ``'applemusic'`` and
    ``'deezer'`` are the user picking one: that service's bio replaces
    the saved one, with no fallback to the other, and nothing at all is
    saved (the current bio stays) if it has none.

    Raises :class:`ValueError` when nothing at all was found - or, for an
    explicit *source*, when that service has no biography for the artist.
    """

    if source not in _BIO_SOURCES:
        raise ValueError(f'Unknown bio source: {source!r}')
    profile = load_profile(download_dir, name)
    _fill_profile(profile, name, lang, source)
    _save_profile(download_dir, name, profile)
    return profile


def _fill_profile(
    profile: dict[str, Any],
    name: str,
    lang: str,
    source: str,
    *,
    strict: bool = False,
) -> None:
    """The fetching half of :func:`fetch_bio`: fills *profile* in memory from
    Apple Music, Deezer and Spotify and saves nothing. Raises
    :class:`ValueError` exactly where :func:`fetch_bio` documents it.

    Not *strict*, a service that fails is skipped, as if it had nothing.
    *strict* is for a profile that is seeded on its own (see
    :func:`_seed_profile`): there a failure of Apple Music or Deezer -
    whose lookups then tell an error from "no such artist" - raises
    :class:`ProfileUnavailable` instead, because what is saved would
    otherwise pass for the artist's real profile. Spotify's part (related
    names) stays best effort either way: it depends on a hash that Spotify
    rolls now and then, and that must not stop a profile from being made.
    """

    got_anything = False
    apple_bio = ''
    deezer_bio = ''

    if strict:
        apple_id = _cached_apple_music_id(profile)
        if not apple_id:
            try:
                apple_id = apple_music.lookup_artist_id(name) or ''
            except ValueError as exc:
                raise ProfileUnavailable('Apple Music did not answer') from exc
    else:
        apple_id = _cached_or_resolved_apple_music_id(profile, name)
    if apple_id:
        try:
            apple_full = apple_music.fetch_artist_full(apple_id, lang)
        except ValueError as exc:
            if strict:
                raise ProfileUnavailable('Apple Music did not answer') from exc
            apple_full = None
        if apple_full is not None:
            got_anything = True
            profile['origin'] = apple_full['origin']
            profile['born_or_formed'] = apple_full['born_or_formed']
            profile['genre'] = apple_full['genre']
            profile['is_group'] = apple_full['is_group']
            profile['banner_bg_color'] = apple_full['banner_bg_color']
            if apple_full['applemusic_id']:
                profile['platforms_id']['applemusic'] = apple_full[
                    'applemusic_id'
                ]
            if apple_full['bio_html']:
                apple_bio = _format_bio_text(apple_full['bio_html'])
                if source == BIO_SOURCE_AUTO:
                    profile['bio'] = apple_bio

    deezer_id = profile['platforms_id'].get('deezer') or ''
    if not deezer_id:
        if strict:
            try:
                deezer_id = deezer.lookup_artist_id(name) or ''
            except ValueError as exc:
                raise ProfileUnavailable('Deezer did not answer') from exc
        else:
            deezer_id = deezer.resolve_artist_id(name) or ''
        if deezer_id:
            profile['platforms_id']['deezer'] = deezer_id

    if deezer_id:
        try:
            deezer_full = deezer.fetch_artist_full(deezer_id, lang)
        except ValueError as exc:
            if strict:
                raise ProfileUnavailable('Deezer did not answer') from exc
            deezer_full = None
        if deezer_full is not None:
            got_anything = True
            profile['social'] = _fill_empty_social(
                profile['social'], deezer_full['social']
            )
            profile['related_artists'] = deezer_full['related_artist_names']
            if deezer_full['bio_html']:
                deezer_bio = _format_bio_text(deezer_full['bio_html'])
                if source == BIO_SOURCE_AUTO and not profile['bio']:
                    profile['bio'] = deezer_bio

    spotify_id = profile['platforms_id'].get('spotify') or ''
    if not spotify_id:
        spotify_id = _spotify_id_from_name(name) or ''
        if spotify_id:
            profile['platforms_id']['spotify'] = spotify_id
    if spotify_id:
        try:
            spotify_related = spotify.related_artist_names_from_id(spotify_id)
        except Exception:
            logger.opt(exception=True).debug(
                'Spotify related-artist fetch failed for {}', spotify_id
            )
            spotify_related = []
        if spotify_related:
            got_anything = True
            profile['related_artists'] = _merge_names(
                profile['related_artists'], spotify_related
            )

    if source == BIO_SOURCE_APPLE_MUSIC:
        if not apple_bio:
            raise ValueError(
                'Apple Music has no biography for this artist in this language'
            )
        profile['bio'] = apple_bio
    elif source == BIO_SOURCE_DEEZER:
        if not deezer_bio:
            raise ValueError('Deezer has no biography for this artist')
        profile['bio'] = deezer_bio

    if not got_anything:
        raise ValueError('No matching artist found on Apple Music or Deezer')


def preview_bio(download_dir: Path, name: str, lang: str, source: str) -> str:
    """*name*'s biography text from one service, **without saving
    anything** - what the artist edit modal loads into its text box so the
    user decides whether to keep it (see :func:`save_bio`).

    *source* is ``'applemusic'`` or ``'deezer'``; there's no fallback to
    the other one. Read-only on the profile too: an artist id it has to
    look up is not cached, unlike in :func:`fetch_bio`. Raises
    :class:`ValueError` when that service has no biography.
    """

    if source not in {BIO_SOURCE_APPLE_MUSIC, BIO_SOURCE_DEEZER}:
        raise ValueError(f'Unknown bio source: {source!r}')
    profile = load_profile(download_dir, name)
    html = ''
    if source == BIO_SOURCE_APPLE_MUSIC:
        apple_id = _cached_or_resolved_apple_music_id(profile, name)
        if apple_id:
            try:
                html = apple_music.fetch_artist_full(apple_id, lang)[
                    'bio_html'
                ]
            except ValueError:
                html = ''
        missing = (
            'Apple Music has no biography for this artist in this language'
        )
    else:
        deezer_id = (
            profile['platforms_id'].get('deezer')
            or deezer.resolve_artist_id(name)
            or ''
        )
        if deezer_id:
            try:
                html = deezer.fetch_artist_full(deezer_id, lang)['bio_html']
            except ValueError:
                html = ''
        missing = 'Deezer has no biography for this artist'
    text = _format_bio_text(html) if html else ''
    if not text:
        raise ValueError(missing)
    return text


def _spotify_id_from_name(name: str) -> Optional[str]:
    """Spotify artist id by exact name (see
    :func:`downtify.spotify.search_artist_by_name`), or ``None`` - never
    raises, so a Spotify hiccup can't fail a profile fetch."""

    try:
        found = spotify.search_artist_by_name(name)
    except Exception:
        logger.opt(exception=True).debug(
            'Spotify artist search failed for {!r}', name
        )
        return None
    return found['id'] if found else None


def resolve_platform_ids(
    name: str, known: Optional[dict[str, str]] = None
) -> dict[str, str]:
    """*name* looked up across every stream platform with a name-search
    API, requiring an exact match on each (ignoring case and the
    characters a file name can't hold, see
    :func:`downtify.file_naming.file_name_key`) - same
    strictness as every platform's own ``resolve_artist_id``, so an
    unrelated top result never gets attached to the wrong artist. Only
    the platforms that actually matched are in the returned dict.

    Covers Spotify (:func:`_spotify_id_from_name`), Deezer, YouTube Music
    and Apple Music (via :func:`apple_music.resolve_artist_slug_id`,
    already in the ``slug/numeric-id`` shape ``platforms_id.applemusic``
    needs, resolved from the same search call as the plain id).

    *known* is a ``platforms_id`` mapping: any platform with a non-empty
    id there is skipped (no request, not in the result), so an id
    already saved - above all a Spotify one resolved from the artist's
    own track, which is more reliable than a name match - is never
    replaced by a search result.
    """

    known = known or {}
    ids: dict[str, str] = {}
    if not known.get('spotify'):
        spotify_id = _spotify_id_from_name(name)
        if spotify_id:
            ids['spotify'] = spotify_id
    if not known.get('deezer'):
        deezer_id = deezer.resolve_artist_id(name)
        if deezer_id:
            ids['deezer'] = deezer_id
    if not known.get('youtubemusic'):
        ytm_id = providers.resolve_artist_id(name)
        if ytm_id:
            ids['youtubemusic'] = ytm_id
    if not known.get('applemusic'):
        apple_id = apple_music.resolve_artist_slug_id(name)
        if apple_id:
            ids['applemusic'] = apple_id
    return ids


def resolve_spotify_artist_id(
    track_files: list[str], track_index: Any, name: str = ''
) -> Optional[str]:
    """Spotify artist id, or ``None``.

    First choice is the first of *track_files* that was itself
    downloaded from Spotify (*track_index* may be ``None`` to skip this):
    a track already known to be theirs can't resolve to a namesake. When
    none is, *name* - if given - is searched on Spotify by exact name
    (:func:`_spotify_id_from_name`). Not private: a caller with its own
    track/track_index (e.g. a download-pipeline hook - see
    :func:`ensure_profile`) can reuse this directly instead of
    re-implementing the same loop.
    """

    for file in track_files[:5] if track_index is not None else []:
        filename = str(file or '').strip().replace('\\', '/')
        if not filename:
            continue
        track_id = track_index.spotify_id_for_filename(filename)
        if not track_id:
            continue
        try:
            artist_id = spotify.primary_artist_id_from_track_id(track_id)
        except Exception:
            logger.opt(exception=True).debug(
                'Spotify artist id resolution failed for track {}', track_id
            )
            continue
        if artist_id:
            return artist_id
    return _spotify_id_from_name(name) if name.strip() else None


def _seed_image_from_streams(
    download_dir: Path,
    name: str,
    kind: str,
    spotify_artist_id: Optional[str],
) -> None:
    """Save *name*'s photo/banner from Spotify, given an already-
    resolved artist id (see :func:`resolve_spotify_artist_id`). Falls
    back to an exact YouTube Music name match when Spotify has nothing
    (no id at all, or the artist simply has no banner set there). No-op
    if this *kind* is already saved.
    """

    if image_path_for(download_dir, name, kind).is_file():
        return

    if spotify_artist_id:
        url = ''
        try:
            url = (
                spotify.artist_banner_url_from_id(spotify_artist_id)
                if kind == KIND_BANNER
                else spotify.artist_image_url_from_id(spotify_artist_id)
            )
        except Exception:
            logger.opt(exception=True).debug(
                'Spotify artist art seed failed for {} ({})',
                spotify_artist_id,
                kind,
            )
        if url:
            try:
                fetch_and_save_image(
                    download_dir, name, kind, url, source='spotify'
                )
            except ValueError:
                logger.debug(
                    'Could not save seeded Spotify {} for {}', kind, name
                )
            return

    wanted = file_name_key(name)
    if not wanted:
        return
    for artist in providers.search_artists(name, limit=25):
        if file_name_key(str(artist.get('name') or '')) != wanted:
            continue
        url = artist.get('cover_url') or ''
        if url:
            try:
                fetch_and_save_image(
                    download_dir, name, kind, url, source='youtube'
                )
            except ValueError:
                logger.debug(
                    'Could not save seeded YouTube Music {} for {}',
                    kind,
                    name,
                )
        return


def ensure_profile(
    download_dir: Path,
    name: str,
    track_files: list[str],
    lang: str,
    track_index: Optional[Any] = None,
    image_kinds: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Seed a brand-new artist's profile the first time it's needed
    (e.g. opening their Library page) and nothing has been saved for
    them yet: bio/social/origin/etc from Apple Music and Deezer (see
    :func:`_fill_profile`) and platform ids via :func:`resolve_platform_ids`
    - exactly as if the user had opened the picker and clicked the fetch
    button themselves - then photo/banner from Spotify/YouTube Music (see
    :func:`_seed_image_from_streams`), only the kinds in *image_kinds*,
    which callers derive from the user's ``download_cover_art_artist``/
    ``download_cover_art_artist_banner`` settings (none by default: an
    image is never saved unless the caller says the user wants it).

    A no-op past the first call for a given artist: once a profile file
    exists at all - even a mostly-empty one, if the services answered that
    nothing matches - every later call just returns :func:`load_profile`
    directly, so an obscure artist nothing matches doesn't re-run this
    full, several-requests-deep lookup on every single page visit.

    A service that *fails* (Apple Music, Deezer: unreachable, over its
    limit) is a different thing from one with nothing to say: nothing is
    saved then - no file, no photo - and the blank profile comes back, so
    the next visit tries again instead of keeping a hollow profile for
    good (see :class:`ProfileUnavailable`).

    *track_index* is optional: with it, Spotify's artist id comes from one
    of the artist's own Spotify tracks (the most reliable route); without
    it, or when no track has one, from an exact-name search (see
    :func:`resolve_spotify_artist_id`). The download pipeline seeds through
    :func:`profile_seed_enqueue` instead, with the id of the track it just
    downloaded. Both share :func:`_seed_profile` and the per-artist lock, so
    a visit and a download never seed the same artist twice.
    """

    if _profile_path_for(download_dir, name).is_file():
        return load_profile(download_dir, name)

    with _seed_lock_for(download_dir, name):
        # Whoever held the lock (a download, another visit) may just have
        # made it.
        if _profile_path_for(download_dir, name).is_file():
            return load_profile(download_dir, name)
        spotify_artist_id = resolve_spotify_artist_id(
            track_files, track_index, name
        )
        try:
            return _seed_profile(
                download_dir, name, spotify_artist_id, lang, image_kinds
            )
        except ProfileUnavailable:
            logger.debug('Profile of {!r} not seeded: a service failed', name)
            return load_profile(download_dir, name)


def _seed_profile(
    download_dir: Path,
    name: str,
    spotify_artist_id: Optional[str],
    lang: str,
    image_kinds: tuple[str, ...],
) -> dict[str, Any]:
    """Make *name*'s profile and save it; the caller holds the artist's lock
    (see :func:`_seed_lock_for`) and has seen there is no profile yet.

    Everything is fetched *before* anything is written, so
    :class:`ProfileUnavailable` (Apple Music or Deezer failed) leaves no file
    at all - not a profile holding just a bio, and no photo either. Neither
    service knowing the artist is an answer, not a failure: the profile is
    made with what is known, and the file's mere existence is what makes
    later visits skip this. Photo/banner come last and are best effort: an
    error there is logged and leaves the (already saved) text as it is.
    """

    profile = load_profile(download_dir, name)
    if spotify_artist_id:
        profile['platforms_id']['spotify'] = spotify_artist_id
    try:
        _fill_profile(profile, name, lang, BIO_SOURCE_AUTO, strict=True)
    except ValueError:
        pass  # neither Apple Music nor Deezer has this artist
    # Only what _fill_profile (and the Spotify id above) didn't already
    # resolve - and never over an id that's already there.
    platform_ids = resolve_platform_ids(name, known=profile['platforms_id'])
    if platform_ids:
        profile['platforms_id'] = {**profile['platforms_id'], **platform_ids}
    _save_profile(download_dir, name, profile)

    for kind in image_kinds:
        try:
            _seed_image_from_streams(
                download_dir, name, kind, spotify_artist_id
            )
        except Exception:
            logger.opt(exception=True).debug(
                'Artist {} seed failed for {!r}', kind, name
            )
    return load_profile(download_dir, name)


# ── Seeding from the download pipeline ──────────────────────────────
#
# A track that finishes downloading asks for its artist's profile (see
# ``api.enrich_artist_after_download``, hooked to ``Downloader.on_downloaded``).
# A playlist can finish hundreds of tracks by dozens of artists at once, so:
#
# 1. *distinct*: an artist already waiting or being seeded is not queued again
#    (:data:`_seed_pending`, checked and set under one lock);
# 2. a small pool of daemon threads does the work, so the download that asked
#    never waits and the services aren't hit by hundreds of lookups at once;
# 3. the worker takes the artist's lock (shared with :func:`ensure_profile`)
#    and looks again for the file, so a visit and a download - or two workers -
#    can't seed the same artist twice, whatever the timing.
#
# An artist whose services failed is simply not saved (see
# :class:`ProfileUnavailable`), and the next track of theirs - or a visit to
# their page - tries again; nothing remembers the failure.

#: Artists seeded at the same time.
SEED_WORKERS = 2

_seed_locks: dict[str, threading.Lock] = {}
_seed_locks_guard = threading.Lock()
_seed_pending: set[str] = set()
_seed_pending_guard = threading.Lock()
_seed_jobs: queue.SimpleQueue = queue.SimpleQueue()
_seed_workers: list[threading.Thread] = []
_seed_workers_guard = threading.Lock()


def _seed_key(download_dir: Path, name: str) -> str:
    return str(_profile_path_for(download_dir, name)).lower()


def _seed_lock_for(download_dir: Path, name: str) -> threading.Lock:
    """One lock per artist, shared by every way of seeding them."""

    with _seed_locks_guard:
        return _seed_locks.setdefault(
            _seed_key(download_dir, name), threading.Lock()
        )


def profile_seed_artist_of(song: dict[str, Any]) -> str:
    """The artist whose profile a downloaded *song* seeds: the one its file
    is filed under (the album artist, else the first credited artist - the
    rule ``Downloader._artist_subdir`` uses), or ``''`` when that is no one
    worth a profile (``Various Artists``)."""

    album_artist = str(song.get('album_artist') or '').strip()
    artists = song.get('artists') or []
    first = str(artists[0]).strip() if artists else ''
    name = album_artist or first
    return '' if name.casefold() in {'various artists', 'unknown'} else name


def _spotify_artist_id_for_song(
    song: dict[str, Any], name: str
) -> Optional[str]:
    """Spotify's id for *name*: from the song's own Spotify track when its
    first credited artist is *name* (it can't pick a namesake), else an
    exact-name search."""

    track_id = song.get('song_id')
    artists = song.get('artists') or []
    if (
        song.get('source') == 'spotify'
        and isinstance(track_id, str)
        and re.fullmatch(r'[A-Za-z0-9]{22}', track_id)
        and artists
        and file_name_key(str(artists[0])) == file_name_key(name)
    ):
        try:
            found = spotify.primary_artist_id_from_track_id(track_id)
        except Exception:
            logger.opt(exception=True).debug(
                'Spotify artist id from track {} failed', track_id
            )
            found = None
        if found:
            return found
    return _spotify_id_from_name(name)


def profile_seed_song(
    download_dir: Path,
    song: dict[str, Any],
    lang: str,
    image_kinds: tuple[str, ...] = (),
) -> bool:
    """Seed the profile of *song*'s artist, unless it already exists (or
    someone is making it). Blocking - what the pool's workers run. Returns
    whether a profile was made; a failure of Apple Music or Deezer makes
    none (see :class:`ProfileUnavailable`)."""

    name = profile_seed_artist_of(song)
    if not name or _profile_path_for(download_dir, name).is_file():
        return False
    with _seed_lock_for(download_dir, name):
        if _profile_path_for(download_dir, name).is_file():
            return False
        spotify_artist_id = _spotify_artist_id_for_song(song, name)
        try:
            _seed_profile(
                download_dir, name, spotify_artist_id, lang, image_kinds
            )
        except ProfileUnavailable:
            logger.debug('Profile of {!r} not seeded: a service failed', name)
            return False
    return True


def profile_seed_enqueue(
    download_dir: Path,
    song: dict[str, Any],
    lang: str,
    image_kinds: tuple[str, ...] = (),
) -> bool:
    """Queue seeding *song*'s artist and return at once (a download must not
    wait for this); ``False`` when there is nothing to do - no artist worth a
    profile, one that already has it, or one that is already queued."""

    name = profile_seed_artist_of(song)
    if not name or _profile_path_for(download_dir, name).is_file():
        return False
    key = _seed_key(download_dir, name)
    with _seed_pending_guard:
        if key in _seed_pending:
            return False
        _seed_pending.add(key)
    _seed_jobs.put((key, Path(download_dir), dict(song), lang, image_kinds))
    _start_seed_workers()
    return True


def _run_seed_job(job: tuple[Any, ...]) -> None:
    key, download_dir, song, lang, image_kinds = job
    try:
        profile_seed_song(download_dir, song, lang, image_kinds)
    except Exception:
        logger.opt(exception=True).debug('Profile seeding failed')
    finally:
        with _seed_pending_guard:
            _seed_pending.discard(key)


def _seed_worker() -> None:
    while True:
        _run_seed_job(_seed_jobs.get())


def _start_seed_workers() -> None:
    # Daemon threads on purpose: a pool that runs its queue dry at exit would
    # hold the app up for as long as a big playlist's artists take.
    with _seed_workers_guard:
        _seed_workers[:] = [t for t in _seed_workers if t.is_alive()]
        while len(_seed_workers) < SEED_WORKERS:
            worker = threading.Thread(
                target=_seed_worker, name='downtify-profile-seed', daemon=True
            )
            worker.start()
            _seed_workers.append(worker)


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


def save_bio(download_dir: Path, name: str, bio: str) -> dict[str, Any]:
    """Manually set *name*'s bio text, overwriting a fetched or prior one.

    Unlike :func:`fetch_bio`, this never touches Apple Music/Deezer -
    it's the user typing their own text into the artist page's editor
    (plain text, blank lines between paragraphs). Still run through
    :func:`_format_bio_text` so ``bio`` is always the same plain-text
    shape (no HTML, no bullets) regardless of where it came from.
    """

    profile = load_profile(download_dir, name)
    profile['bio'] = _format_bio_text(bio or '')
    _save_profile(download_dir, name, profile)
    return profile


def save_social(
    download_dir: Path, name: str, social: dict[str, Any]
) -> dict[str, Any]:
    """Manually set *name*'s social links, replacing all four fields.

    Like :func:`save_bio`, this is the user editing directly - it never
    fetches anything. Unknown/missing keys in *social* are saved as
    empty strings rather than left at whatever was there before, since
    the editor always submits its full form.
    """

    profile = load_profile(download_dir, name)
    default_social = _default_profile(name)['social']
    profile['social'] = {
        key: str(social.get(key) or '').strip() for key in default_social
    }
    _save_profile(download_dir, name, profile)
    return profile


# ── Top songs: the Spotify shelf, kept as a JSON cache ──────────────
#
# Fetching an artist's top songs is slow - the artist embed, one embed per
# song for its cover and album, and an overview request for the play counts
# (see :func:`downtify.spotify.artist_top_songs_from_id`) - so the first
# five are saved to ``Metadata/ArtistTopSongs/<name>.topsongs.json``, next
# to the artist's photo, banner and profile. It is a cache, not user data:
# machine-written, never edited by hand, and separate from
# ``ArtistData/<name>.json`` on purpose (a bio or social-link save rewrites
# that whole file, and deleting it to re-seed an artist shouldn't touch
# this one).
#
# Only links and text are stored - the covers and the 30 s preview clips
# stay remote URLs, nothing is downloaded - and nothing that changes per
# download: whether a song is in the library or the queue is worked out
# live by the UI.
#
# A file is *fresh* for :data:`TOP_SONGS_TTL` (7 days: play counts move
# daily, the ranking rarely), only while it belongs to the Spotify artist id
# asked about and only in the current :data:`TOP_SONGS_SCHEMA`.
# :func:`profile_top_songs_ensure` is the one entry point: it creates the
# file when it is missing or stale and otherwise just reads it, so the
# artist page, the profile seeding and - later - the download pipeline can
# all call it whenever they need the songs.

_top_songs_locks: dict[str, threading.Lock] = {}
_top_songs_locks_guard = threading.Lock()


def profile_top_songs_path_for(download_dir: Path, name: str) -> Path:
    """The file for *name*'s top songs, whether or not it exists."""

    return (
        Path(download_dir)
        / _TOP_SONGS_DIRNAME
        / f'{_sanitize(name)}{_TOP_SONGS_SUFFIX}'
    )


def _profile_top_songs_lock_for(
    download_dir: Path, name: str
) -> threading.Lock:
    """One lock per artist: a background refresh and a request for the
    same artist queue up behind each other instead of fetching twice."""

    key = str(profile_top_songs_path_for(download_dir, name)).lower()
    with _top_songs_locks_guard:
        return _top_songs_locks.setdefault(key, threading.Lock())


def profile_top_songs_load(
    download_dir: Path, name: str
) -> Optional[dict[str, Any]]:
    """The saved file, or ``None`` when missing, unreadable or malformed."""

    try:
        data = json.loads(
            profile_top_songs_path_for(download_dir, name).read_text(
                encoding='utf-8'
            )
        )
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get('songs'), list):
        return None
    return data


def _parse_fetched_at(value: Any) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def profile_top_songs_is_fresh(
    data: Optional[dict[str, Any]],
    spotify_artist_id: str,
    now: Optional[datetime] = None,
) -> bool:
    """Whether *data* can be served as is: it belongs to
    *spotify_artist_id* (a corrected id must not keep serving the old
    artist's songs), is of the current :data:`TOP_SONGS_SCHEMA` and was
    fetched less than :data:`TOP_SONGS_TTL` ago."""

    if not data or str(data.get('artist_id') or '') != spotify_artist_id:
        return False
    if data.get('schema') != TOP_SONGS_SCHEMA:
        return False
    fetched = _parse_fetched_at(data.get('fetched_at'))
    if fetched is None:
        return False
    return (now or datetime.now(timezone.utc)) - fetched < TOP_SONGS_TTL


def profile_top_songs_cached(
    download_dir: Path, name: str, spotify_artist_id: str
) -> tuple[Optional[dict[str, Any]], bool]:
    """``(saved file or None, is it fresh)`` - no network."""

    data = profile_top_songs_load(download_dir, name)
    return data, profile_top_songs_is_fresh(data, spotify_artist_id)


def _profile_top_songs_write(
    download_dir: Path, name: str, data: dict[str, Any]
) -> None:
    """Write atomically (temp file, then rename): a reader never sees a
    half-written file, even with a request racing a background refresh."""

    _atomic_write_json(profile_top_songs_path_for(download_dir, name), data)


def _profile_top_songs_fetch(spotify_artist_id: str) -> dict[str, Any]:
    artist_name, cover_url, songs = spotify.artist_top_songs_from_id(
        spotify_artist_id, limit=TOP_SONGS_LIMIT
    )
    return {
        'schema': TOP_SONGS_SCHEMA,
        'source': 'spotify',
        'artist_id': spotify_artist_id,
        'name': artist_name,
        'cover_url': cover_url,
        'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'songs': songs,
    }


def profile_top_songs_ensure(
    download_dir: Path, name: str, spotify_artist_id: str
) -> dict[str, Any]:
    """*name*'s top songs: the saved file while it is fresh, otherwise
    fetched from Spotify and saved.

    The single entry point - the artist page, the profile seeding and the
    download pipeline all go through it, so a missing or stale file gets
    (re)created by whoever needs it first. Blocking (seconds when it has
    to fetch): run it off the event loop.

    A failed refresh falls back to the stale file when there is one; with
    nothing saved the error propagates. An empty shelf is returned but not
    saved, so a transient failure isn't trusted for a week.
    """

    if not spotify_artist_id:
        raise ValueError('No Spotify artist id')
    with _profile_top_songs_lock_for(download_dir, name):
        # Re-read under the lock: whoever held it may just have written it.
        saved = profile_top_songs_load(download_dir, name)
        if profile_top_songs_is_fresh(saved, spotify_artist_id):
            return saved  # type: ignore[return-value]
        try:
            data = _profile_top_songs_fetch(spotify_artist_id)
        except Exception:
            if saved is not None and saved.get('artist_id') == (
                spotify_artist_id
            ):
                logger.opt(exception=True).warning(
                    'Top songs refresh failed for {}; serving the saved file',
                    name,
                )
                return saved
            raise
        if data['songs']:
            _profile_top_songs_write(download_dir, name, data)
        return data


def profile_top_songs_refresh_in_background(
    download_dir: Path, name: str, spotify_artist_id: str
) -> bool:
    """Start :func:`profile_top_songs_ensure` on a daemon thread when the
    file is missing or stale and nobody is already fetching it; returns
    whether a thread was started. Never raises and never blocks - for
    callers (the profile seeding) that want the file made without waiting
    for it."""

    if not spotify_artist_id:
        return False
    _, fresh = profile_top_songs_cached(download_dir, name, spotify_artist_id)
    if fresh or _profile_top_songs_lock_for(download_dir, name).locked():
        return False

    def run() -> None:
        try:
            profile_top_songs_ensure(download_dir, name, spotify_artist_id)
        except Exception:
            logger.opt(exception=True).debug(
                'Background top songs fetch failed for {}', name
            )

    threading.Thread(
        target=run, name='downtify-top-songs', daemon=True
    ).start()
    return True
