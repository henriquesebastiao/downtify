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

Function names are prefixed ``image_``/``_image`` for the photo/banner
half on purpose, to keep it visually distinct from the profile-data half
added later.
"""

from __future__ import annotations

import json
import re
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


def _save_profile(
    download_dir: Path, name: str, profile: dict[str, Any]
) -> None:
    path = _profile_path_for(download_dir, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8'
    )


def _set_current_cover(
    download_dir: Path, name: str, kind: str, value: str
) -> None:
    profile = load_profile(download_dir, name)
    field = 'current_cover' if kind == KIND_PHOTO else 'current_cover_banner'
    profile[field] = value
    _save_profile(download_dir, name, profile)


def _cached_or_resolved_apple_music_id(
    profile: dict[str, Any], name: str
) -> str:
    # platforms_id['applemusic'] stores 'slug/numeric-id' (see fetch_artist_full
    # below), but the catalog API only takes the numeric id - pull it back
    # out of a cached value instead of re-searching by name every time.
    cached = profile['platforms_id'].get('applemusic') or ''
    match = re.search(r'(\d+)$', cached)
    if match:
        return match.group(1)
    return apple_music.resolve_artist_id(name) or ''


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
    got_anything = False
    apple_bio = ''
    deezer_bio = ''

    apple_id = _cached_or_resolved_apple_music_id(profile, name)
    if apple_id:
        try:
            apple_full = apple_music.fetch_artist_full(apple_id, lang)
        except ValueError:
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
        deezer_id = deezer.resolve_artist_id(name) or ''
        if deezer_id:
            profile['platforms_id']['deezer'] = deezer_id

    if deezer_id:
        try:
            deezer_full = deezer.fetch_artist_full(deezer_id, lang)
        except ValueError:
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

    _save_profile(download_dir, name, profile)
    return profile


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
    them yet: photo/banner from Spotify/YouTube Music (see
    :func:`_seed_image_from_streams`) - only the kinds in *image_kinds*,
    which callers derive from the user's ``download_cover_art_artist``/
    ``download_cover_art_artist_banner`` settings (none by default: an
    image is never saved unless the caller says the user wants it) -
    plus bio/social/origin/etc via
    :func:`fetch_bio` and platform ids via :func:`resolve_platform_ids` -
    exactly as if the user had opened the picker and clicked the fetch
    button themselves.

    A no-op past the first call for a given artist: once a profile file
    exists at all - even a mostly-empty one, if nothing could be found -
    every later call just returns :func:`load_profile` directly, so an
    obscure artist nothing matches doesn't re-run this full, several-
    requests-deep lookup on every single page visit. *track_index* is
    optional: with it, Spotify's artist id comes from one of the artist's
    own Spotify tracks (the most reliable route); without it, or when no
    track has one, from an exact-name search (see
    :func:`resolve_spotify_artist_id`). Callers without an index handy -
    or a future one, like the download pipeline resolving this right
    after a new artist's first track finishes, not wired up yet - aren't
    forced to fake it.

    Spotify's artist id is cached into ``platforms_id.spotify`` *before*
    :func:`fetch_bio` runs, so its own related-artist merge (see that
    function's docstring) picks it up on this very first call, not just
    on some later re-fetch.
    """

    if _profile_path_for(download_dir, name).is_file():
        return load_profile(download_dir, name)

    spotify_artist_id = resolve_spotify_artist_id(
        track_files, track_index, name
    )
    if spotify_artist_id:
        profile = load_profile(download_dir, name)
        profile['platforms_id']['spotify'] = spotify_artist_id
        _save_profile(download_dir, name, profile)
    for kind in image_kinds:
        _seed_image_from_streams(download_dir, name, kind, spotify_artist_id)

    try:
        profile = fetch_bio(download_dir, name, lang)
    except ValueError:
        profile = load_profile(download_dir, name)

    # Only what fetch_bio (and the Spotify step above) didn't already
    # resolve - and never over an id that's already there.
    platform_ids = resolve_platform_ids(name, known=profile['platforms_id'])
    if platform_ids:
        profile['platforms_id'] = {**profile['platforms_id'], **platform_ids}

    # Always persist, even when nothing was found at all - the file's
    # mere existence is what makes the next call take the fast path
    # above instead of repeating this every visit.
    _save_profile(download_dir, name, profile)
    return profile


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
