"""MusicBrainz: a watched artist's whole catalogue (issue #581, phase 2).

MusicBrainz is the open music encyclopedia Lidarr is built on; its core
data is CC0. Downtify reads its public web service directly, as its rules
ask: at most one request a second (:data:`_INTERVAL`, shared by every
caller in the process) and a User-Agent naming Downtify. A ``503`` means
"slow down" and is retried after a pause.

How a watch uses it (``monitor._musicbrainz_releases``):

* :func:`artist_id_for` maps the watched artist to a MusicBrainz artist,
  once: through the artist's Deezer or YouTube Music page (MusicBrainz
  keeps links to both), else by name - only when exactly one artist of
  exactly that name scores 100, so a common name never picks a stranger.
* :func:`release_groups` lists the artist's release groups. A group is
  one album, single or EP with all of its editions (*Views* has nine:
  CD, digital, clean, explicit, hi-res...), typed like Lidarr's metadata
  profiles: a primary type (Album, Single, EP...) and secondary types
  (Mixtape/Street, Live, Compilation, Remix...).
* :func:`wanted` keeps the artist's own groups (not the ones they are a
  guest on) of the asked types; :data:`KINDS` are the secondary types a
  user can let in.
* :func:`release_group_tracks` picks one edition of a group
  (:func:`_edition_rank`: official, explicit, the most tracks) and turns
  its tracks into Downtify songs, with their ISRCs and a Cover Art
  Archive cover when there is one.
"""

from __future__ import annotations

import re
import threading
import time
from typing import Any, Iterable, Optional

import httpx
from loguru import logger

from . import __version__
from .album_artist import album_artist_fields
from .file_naming import file_name_key

BASE = 'https://musicbrainz.org/ws/2/'
COVER_ART = 'https://coverartarchive.org/'

#: Seconds between two requests (MusicBrainz allows one a second).
_INTERVAL = 1.1
#: Tries of a request MusicBrainz answers with "slow down".
_RETRIES = 4
_TIMEOUT = 20

_lock = threading.Lock()
_last_request = 0.0

#: Primary types Artist Watch downloads (the watch's ``release_types``).
PRIMARY_TYPES = ('album', 'single', 'ep')

#: Secondary types a user can let in, by setting name -> MusicBrainz's.
KINDS = {
    'mixtape': 'mixtape/street',
    'soundtrack': 'soundtrack',
    'live': 'live',
    'compilation': 'compilation',
    'remix': 'remix',
    'dj-mix': 'dj-mix',
    'demo': 'demo',
}
#: Let in by default: a mixtape or a soundtrack is the artist's own music;
#: live albums, compilations, remixes, DJ mixes and demos repeat it.
DEFAULT_KINDS = ('mixtape', 'soundtrack')

# A joinphrase that makes the artists after it guests ("A feat. B").
_GUEST = re.compile(r'\b(?:feat|ft|featuring|with)\b', re.IGNORECASE)


class MusicBrainzError(RuntimeError):
    """MusicBrainz couldn't answer (unreachable, busy, refused)."""


class NotFound(MusicBrainzError):
    """MusicBrainz has no such entity (a ``404``)."""


def _user_agent() -> str:
    return (
        f'Downtify/{__version__} '
        '( https://github.com/henriquesebastiao/downtify )'
    )


def _get(path: str, **params: Any) -> dict[str, Any]:
    """A web service GET as JSON, at most one a second process-wide."""

    global _last_request  # noqa: PLW0603  # the shared request clock
    params['fmt'] = 'json'
    for attempt in range(_RETRIES):
        with _lock:
            wait = _INTERVAL - (time.monotonic() - _last_request)
            if wait > 0:
                time.sleep(wait)
            try:
                resp = httpx.get(
                    BASE + path,
                    params=params,
                    headers={
                        'User-Agent': _user_agent(),
                        'Accept': 'application/json',
                    },
                    timeout=_TIMEOUT,
                )
            except httpx.HTTPError as exc:
                raise MusicBrainzError('Could not reach MusicBrainz') from exc
            finally:
                _last_request = time.monotonic()
        if resp.status_code in {429, 503}:
            logger.debug('MusicBrainz asked to slow down ({})', path)
            time.sleep(_INTERVAL * 2 * (attempt + 1))
            continue
        if resp.status_code == 404:
            raise NotFound(f'MusicBrainz has no {path}')
        if resp.status_code >= 400:
            raise MusicBrainzError(
                f'MusicBrainz refused the request ({resp.status_code})'
            )
        try:
            data = resp.json()
        except ValueError as exc:
            raise MusicBrainzError(
                'MusicBrainz sent an unreadable answer'
            ) from exc
        if not isinstance(data, dict):
            raise MusicBrainzError('MusicBrainz sent an unexpected answer')
        return data
    raise MusicBrainzError('MusicBrainz is busy; try again later')


# ── The artist ──────────────────────────────────────────────────────────


def _artist_by_url(resource: str) -> str:
    """The one artist a page (``https://www.deezer.com/artist/…``) is
    linked to in MusicBrainz, else ``''``."""

    try:
        data = _get('url', resource=resource, inc='artist-rels')
    except NotFound:
        return ''
    found = {
        str(rel['artist'].get('id') or '')
        for rel in data.get('relations') or []
        if isinstance(rel, dict) and isinstance(rel.get('artist'), dict)
    }
    found.discard('')
    return found.pop() if len(found) == 1 else ''


def _artist_by_name(name: str) -> str:
    """The artist named exactly *name*, when only one such artist
    matches fully; ``''`` otherwise (none, or an ambiguous name)."""

    wanted = file_name_key(name)
    if not wanted:
        return ''
    quoted = name.replace('\\', '\\\\').replace('"', '\\"')
    data = _get('artist', query=f'artist:"{quoted}"', limit=10)
    exact = [
        str(artist.get('id') or '')
        for artist in data.get('artists') or []
        if isinstance(artist, dict)
        and int(artist.get('score') or 0) == 100
        and file_name_key(str(artist.get('name') or '')) == wanted
    ]
    return exact[0] if len(exact) == 1 and exact[0] else ''


def artist_id_for(
    name: str, *, deezer_id: str = '', channel_id: str = ''
) -> str:
    """The MusicBrainz artist of a watched artist: through their Deezer
    page, then their YouTube Music channel, then by name. ``''`` when
    none of these settles it."""

    pages = []
    if deezer_id:
        pages.append(f'https://www.deezer.com/artist/{deezer_id}')
    if channel_id:
        pages.append(f'https://music.youtube.com/channel/{channel_id}')
    for page in pages:
        found = _artist_by_url(page)
        if found:
            return found
    return _artist_by_name(name)


# ── Release groups ──────────────────────────────────────────────────────


def _credit(rows: Any) -> list[tuple[str, str, str]]:
    """An artist credit as ``(artist id, name, joinphrase)`` rows."""

    credit = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        artist = (
            row.get('artist') if isinstance(row.get('artist'), dict) else {}
        )
        credit.append((
            str(artist.get('id') or ''),
            str(row.get('name') or artist.get('name') or '').strip(),
            str(row.get('joinphrase') or ''),
        ))
    return credit


def credit_text(credit: list[tuple[str, str, str]]) -> str:
    """The credit as it is printed: "PARTYNEXTDOOR & Drake"."""

    return ''.join(name + join for _id, name, join in credit).strip()


def _group(row: Any) -> Optional[dict[str, Any]]:
    if not isinstance(row, dict) or not row.get('id') or not row.get('title'):
        return None
    return {
        'id': str(row['id']),
        'title': str(row['title']).strip(),
        'primary': str(row.get('primary-type') or '').strip().lower(),
        'secondary': [
            str(kind).strip().lower()
            for kind in row.get('secondary-types') or []
            if kind
        ],
        'date': str(row.get('first-release-date') or ''),
        'credit': _credit(row.get('artist-credit')),
    }


def release_groups(artist_id: str) -> list[dict[str, Any]]:
    """Every release group MusicBrainz credits *artist_id* on (their own
    and the ones they are a guest on - see :func:`credited`), as
    ``{id, title, primary, secondary, date, credit}``.

    Groups made only of bootlegs are left out (``website-default``, the
    list MusicBrainz's own artist page shows): a big rapper has dozens
    of fan-made "street" compilations of songs he already released -
    Drake 24 of 37 mixtapes."""

    groups: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = _get(
            'release-group',
            artist=artist_id,
            inc='artist-credits',
            limit=100,
            offset=offset,
            **{'release-group-status': 'website-default'},
        )
        rows = page.get('release-groups') or []
        groups += [g for g in (_group(row) for row in rows) if g]
        offset += len(rows)
        if not rows or offset >= int(page.get('release-group-count') or 0):
            return groups


def credited(group: dict[str, Any], artist_id: str) -> bool:
    """Whether a release group is the artist's own: credited to them, or
    jointly ("PARTYNEXTDOOR & Drake"), not as a guest ("Rihanna feat.
    Drake")."""

    for artist, _name, join in group.get('credit') or []:
        if artist == artist_id:
            return True
        if _GUEST.search(join):
            return False
    return False


def kinds_from_setting(value: Any) -> set[str]:
    """The MusicBrainz secondary types a setting lets in (a list of
    :data:`KINDS` names; anything else is the default)."""

    if not isinstance(value, (list, tuple)):
        value = DEFAULT_KINDS
    return {KINDS[str(v).lower()] for v in value if str(v).lower() in KINDS}


def wanted(
    group: dict[str, Any],
    artist_id: str,
    primary: Iterable[str],
    kinds: set[str],
) -> bool:
    """A group Artist Watch downloads: the artist's own, of one of the
    watch's *primary* types, and with only secondary types in *kinds*
    (a remixed mixtape is out unless remixes are let in)."""

    return (
        group['primary'] in set(primary)
        and all(kind in kinds for kind in group['secondary'])
        and credited(group, artist_id)
    )


def release_summary(group: dict[str, Any]) -> dict[str, Any]:
    """A release group as Artist Watch's release summary (the shape the
    YouTube Music and Deezer discographies have)."""

    return {
        'album_id': group['id'],
        'name': group['title'],
        'artist': credit_text(group['credit']),
        'year': group['date'][:4],
        'release_type': 'EP'
        if group['primary'] == 'ep'
        else group['primary'].title(),
        'kinds': list(group['secondary']),
        'cover_url': f'{COVER_ART}release-group/{group["id"]}/front-250',
        'url': f'https://musicbrainz.org/release-group/{group["id"]}',
        'source': 'musicbrainz',
    }


# ── One edition's tracks ────────────────────────────────────────────────


def _track_count(release: dict[str, Any]) -> int:
    return sum(
        len(medium.get('tracks') or [])
        for medium in release.get('media') or []
        if isinstance(medium, dict)
    )


def _edition_rank(release: dict[str, Any]) -> tuple[Any, ...]:
    """How good an official edition of a group is to download: not a
    clean (edited) version, the most tracks (a deluxe edition holds the
    standard one), digital, then the earliest."""

    note = str(release.get('disambiguation') or '').casefold()
    digits = re.sub(r'\D', '', str(release.get('date') or ''))
    return (
        not any(word in note for word in ('clean', 'edited', 'censored')),
        _track_count(release),
        any(
            str(medium.get('format') or '') == 'Digital Media'
            for medium in release.get('media') or []
            if isinstance(medium, dict)
        ),
        -int((digits + '00000000')[:8]) if digits else -99999999,
    )


def _cover_url(release_id: str) -> str:
    """The release's front cover on the Cover Art Archive (500 px), as
    the image's own address - the archive redirects, and the cover
    download doesn't follow redirects. ``''`` without one."""

    try:
        resp = httpx.head(
            f'{COVER_ART}release/{release_id}/front-500',
            headers={'User-Agent': _user_agent()},
            follow_redirects=True,
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError:
        logger.opt(exception=True).debug('Cover Art Archive unreachable')
        return ''
    return str(resp.url) if resp.status_code == 200 else ''


def _songs(release: dict[str, Any], cover: str) -> list[dict[str, Any]]:
    album_credit = _credit(release.get('artist-credit'))
    album = str(release.get('title') or '').strip()
    date = str(release.get('date') or '')
    total = _track_count(release)
    fields = album_artist_fields(
        credit_text(album_credit),
        artist_id=album_credit[0][0] if album_credit else '',
    )
    songs: list[dict[str, Any]] = []
    number = 0
    for medium in release.get('media') or []:
        if not isinstance(medium, dict):
            continue
        for track in medium.get('tracks') or []:
            if not isinstance(track, dict):
                continue
            number += 1
            recording = (
                track.get('recording')
                if isinstance(track.get('recording'), dict)
                else {}
            )
            credit = (
                _credit(
                    track.get('artist-credit')
                    or recording.get('artist-credit')
                )
                or album_credit
            )
            title = str(track.get('title') or recording.get('title') or '')
            if not recording.get('id') or not title.strip() or not credit:
                continue
            length = track.get('length') or recording.get('length') or 0
            isrcs = [str(i) for i in recording.get('isrcs') or [] if i]
            song = {
                'song_id': f'mb-{recording["id"]}',
                'name': title.strip(),
                'artists': [name for _id, name, _join in credit if name],
                'album_name': album,
                'cover_url': cover,
                'duration': round(int(length) / 1000) if length else 0,
                'url': f'https://musicbrainz.org/recording/{recording["id"]}',
                'year': date[:4],
                'release_date': date,
                'track_number': number,
                'album_track_total': total,
                'source': 'musicbrainz',
                **fields,
            }
            if isrcs:
                song['isrc'] = isrcs[0]
            songs.append(song)
    return songs


def release_group_tracks(
    group_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """``(edition, songs)`` for a release group: its best official
    edition (:func:`_edition_rank`) and that edition's tracks as
    Downtify songs, in order. ``({}, [])`` for a group with no official
    edition - bootlegs, promos and fan uploads aren't downloaded."""

    data = _get(
        'release',
        **{'release-group': group_id},
        inc='recordings+artist-credits+isrcs+media',
        limit=100,
    )
    releases = [
        r
        for r in data.get('releases') or []
        if isinstance(r, dict) and r.get('status') == 'Official'
    ]
    if not releases:
        return {}, []
    edition = max(releases, key=_edition_rank)
    cover = _cover_url(str(edition.get('id') or ''))
    return edition, _songs(edition, cover)
