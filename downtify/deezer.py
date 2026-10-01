"""Search the public Deezer API for artist photo candidates, fetch
bio/social/related-artist data from Deezer's internal web-player API,
read Deezer's own global "what's trending" chart, and resolve a pasted
Deezer track/album/playlist/artist link the same way :mod:`downtify.spotify`
and :mod:`downtify.providers` do for Spotify and YouTube Music (see
:func:`parse_deezer_url` and ``downtify.api``'s ``_deezer_details``), and
back the Finder page's Deezer-only search and artist/album/track column
view (see :func:`finder_search` and the functions after it).

``api.deezer.com`` is unauthenticated and keyless, same shape of
integration as :mod:`downtify.itunes`. Deezer's artist search never
returns a banner-shaped image, only square profile photos.

Bio/social data has no public REST equivalent at all (verified live:
``/artist/{id}`` has no bio field, and ``/artist/{id}/biography`` etc.
all 400). Related artists do - ``/artist/{id}/related``, keyless like the
search, is what :func:`related_artists` (the Discover page, see
:mod:`downtify.discover`) reads - but the artist profile keeps taking its
related-artist names from the same call as the bio. The only way to get
the bio is
Deezer's *internal*, undocumented web-player GraphQL API
(``pipe.deezer.com/api``), which is fragile by nature: it only accepts
an anonymous token's exact, full, persisted "ArtistFull" query text
(captured live from the browser, see :func:`fetch_artist_full`) - a
hand-trimmed query gets a generic, unhelpful error instead of the usual
GraphQL validation message. Treat this as append-only: if Deezer changes
that query shape, this needs a fresh capture, not a clever rewrite.
"""

from __future__ import annotations

import re
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional
from urllib.parse import urlsplit

import httpx
from loguru import logger

from . import providers
from .file_naming import file_name_key, title_key

_SEARCH_URL = 'https://api.deezer.com/search/artist'
_RELATED_URL = 'https://api.deezer.com/artist/{artist_id}/related'
_TRACK_SEARCH_URL = 'https://api.deezer.com/search/track'
# Deezer's 30 s clips are served from here (``cdnt-preview.dzcdn.net``).
_PREVIEW_HOST_SUFFIX = '.dzcdn.net'
_AUTH_URL = 'https://auth.deezer.com/login/anonymous'
_GRAPHQL_URL = 'https://pipe.deezer.com/api'
_CHART_URL = 'https://api.deezer.com/chart'
_TIMEOUT = 10
_GRAPHQL_TIMEOUT = 15

# Captured live from www.deezer.com's web player (DevTools network tab).
# Must be sent verbatim - the server enforces this as a persisted/
# allowlisted query, not just valid GraphQL. `me`/`isFavorite` come back
# as UnloggedUserError for an anonymous token; that's expected and
# doesn't block the rest of the response.
_ARTIST_FULL_QUERY = """query ArtistFull($artistId: String!, $relatedArtistFirst: Int!, $liveEventsFirst: Int!) {
  artist(artistId: $artistId) {
    ...ArtistMasthead
    relatedArtists: relatedArtist(first: $relatedArtistFirst) {
      edges {
        cursor
        node {
          ...ArtistBase
          __typename
        }
        __typename
      }
      pageInfo {
        hasNextPage
        hasPreviousPage
        startCursor
        endCursor
        __typename
      }
      __typename
    }
    liveEvents(
      first: $liveEventsFirst
      types: [CONCERT, FESTIVAL]
      statuses: [PENDING]
    ) {
      edges {
        node {
          id
          __typename
        }
        __typename
      }
      pageInfo {
        endCursor
        hasNextPage
        __typename
      }
      __typename
    }
    __typename
  }
  me {
    userFavorites {
      byArtist(artistId: $artistId) {
        estimatedTracksCount
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment ArtistMasthead on Artist {
  ...ArtistBase
  ...ArtistBio
  ...ArtistSocial
  onTour
  status
  __typename
}

fragment ArtistBase on Artist {
  id
  name
  fansCount
  hasSmartRadio
  isFavorite
  picture {
    ...PictureSmall
    ...PictureMedium
    ...PictureLarge
    __typename
  }
  __typename
}

fragment PictureSmall on Picture {
  id
  small: urls(pictureRequest: {height: 100, width: 100})
  explicitStatus
  __typename
}

fragment PictureMedium on Picture {
  id
  medium: urls(pictureRequest: {width: 264, height: 264})
  explicitStatus
  __typename
}

fragment PictureLarge on Picture {
  id
  large: urls(pictureRequest: {width: 500, height: 500})
  explicitStatus
  __typename
}

fragment ArtistBio on Artist {
  bio {
    full
    __typename
  }
  __typename
}

fragment ArtistSocial on Artist {
  social {
    twitter
    facebook
    website
    instagram
    __typename
  }
  __typename
}"""


# Deezer has no "this artist has no photo" flag: an artist without one gets
# a picture whose CDN path carries the md5 of an empty string, which turns
# out as a generic grey placeholder (found live: the obscure "Survivor" that
# ranks above the real band). Recognising that hash is the only tell.
_NO_PICTURE_HASH = 'd41d8cd98f00b204e9800998ecf8427e'


def _has_real_picture(row: dict[str, Any]) -> bool:
    """Whether a search row's artist has an actual photo, not Deezer's
    placeholder (see :data:`_NO_PICTURE_HASH`)."""

    for key in (
        'picture_xl',
        'picture_big',
        'picture_medium',
        'picture_small',
    ):
        url = str(row.get(key) or '')
        if url:
            return _NO_PICTURE_HASH not in url
    return False


def _most_popular_exact_match(
    rows: list[Any], name: str
) -> Optional[dict[str, Any]]:
    """Of the rows whose name is *name* - the same name on disk, so
    ``AC/DC`` matches ``ACDC`` (see :func:`file_name_key`) - the one with
    the most fans, or ``None``.

    Deezer doesn't rank namesakes by popularity: the well-known "Survivor"
    (261k fans) comes after an unknown one (34 fans, no photo). Taking the
    first exact match would attach the wrong artist's id or face.
    """

    wanted = file_name_key(name)
    if not wanted:
        return None
    matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and file_name_key(str(row.get('name') or '')) == wanted
    ]
    if not matches:
        return None
    return max(matches, key=lambda row: int(row.get('nb_fan') or 0))


def _search_rows(text: str, limit: int) -> list[Any]:
    """The rows of Deezer's artist search for *text*.

    Raises :class:`ValueError` whenever Deezer did not really answer: it
    can't be reached, refuses (an HTTP error) or - the sneaky one - reports
    a problem inside a *successful* response. Its limit of 50 requests per
    5 seconds is reported that way: HTTP 200, an ``error`` object
    (``{"code": 4, "message": "Quota limit exceeded"}``) and no ``data``,
    which would read as "no such artist" if taken at face value. Callers
    must not remember any of this as an answer.
    """

    try:
        resp = httpx.get(
            _SEARCH_URL, params={'q': text, 'limit': limit}, timeout=_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.opt(exception=True).debug('Deezer artist search failed')
        raise ValueError('Could not reach Deezer') from exc
    if not isinstance(data, dict):
        raise ValueError('Deezer sent an unexpected answer')
    if data.get('error'):
        logger.debug('Deezer refused the artist search: {}', data['error'])
        raise ValueError('Deezer refused the request')
    return data.get('data') or []


def search_artist(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Artist photo candidates for *query*, largest Deezer offers each.

    Each result is ``{source: 'deezer', name, image_url, url}`` - same
    shape the artist-image picker expects from every source. An artist
    with only Deezer's placeholder picture is left out: it isn't a photo
    anyone could pick.
    """

    text = query.strip()
    if not text:
        return []
    try:
        rows = _search_rows(text, max(1, limit))
    except ValueError:
        return []

    results: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get('name') or '').strip()
        image = (
            row.get('picture_xl')
            or row.get('picture_big')
            or row.get('picture_medium')
            or ''
        )
        if not name or not image or not _has_real_picture(row):
            continue
        results.append({
            'source': 'deezer',
            'name': name,
            'image_url': image,
            'url': row.get('link') or '',
        })
    return results


def lookup_artist_id(name: str) -> Optional[str]:
    """Deezer's numeric artist id for an exact name match, or ``None`` if
    no result's name matches exactly. Case and the characters a file name
    can't hold are ignored (``ACDC`` matches ``AC/DC``, see
    :func:`downtify.file_naming.file_name_key`).

    Deliberately stricter than :func:`search_artist`: an unrelated top
    result would silently attach the wrong bio/social/related-artists to
    this artist's profile, so a fuzzy "good enough" match isn't good
    enough here. Several artists can share the exact name; the one with
    the most fans wins (see :func:`_most_popular_exact_match`).

    Raises :class:`ValueError` when Deezer didn't really answer (see
    :func:`_search_rows`), so ``None`` always means "no such artist" -
    :func:`resolve_artist_id` is the same without that distinction.
    """

    text = name.strip()
    if not file_name_key(text):
        return None
    match = _most_popular_exact_match(_search_rows(text, 25), text)
    if match is None:
        return None
    artist_id = match.get('id')
    return str(artist_id) if artist_id is not None else None


def resolve_artist_id(name: str) -> Optional[str]:
    """:func:`lookup_artist_id`, with a failed lookup reading as ``None``
    - for the callers where "couldn't find out" and "no such artist" may
    be treated alike."""

    try:
        return lookup_artist_id(name)
    except ValueError:
        return None


def exact_artist_picture(name: str) -> Optional[str]:
    """Deezer's medium-size profile photo URL for an exact artist name
    match (same rule as :func:`resolve_artist_id`), or ``None``.

    One search call, no id needed. Same strictness as
    :func:`resolve_artist_id`, and the same pick among namesakes (the
    most popular one): a near match would show another artist's face
    under this name. If that artist has no photo - Deezer only has its
    placeholder (see :data:`_NO_PICTURE_HASH`) - the answer is ``None``,
    not a namesake's photo or the placeholder.

    Raises :class:`ValueError` when Deezer can't be reached or refuses
    (a rate limit, say, see :func:`_search_rows`): that is not "this
    artist has no photo", and the caller must not remember it as one.
    """

    text = name.strip()
    if not file_name_key(text):
        return None
    match = _most_popular_exact_match(_search_rows(text, 25), text)
    if match is None or not _has_real_picture(match):
        return None
    return match.get('picture_medium') or None


def _picture(row: dict[str, Any]) -> str:
    """A row's largest real photo, or ``""`` for Deezer's placeholder."""

    if not _has_real_picture(row):
        return ''
    return str(
        row.get('picture_big')
        or row.get('picture_xl')
        or row.get('picture_medium')
        or ''
    )


def related_artists(artist_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Deezer's "similar artists" for a Deezer artist id, best match first.

    Each is ``{deezer_id, name, picture_url, fans}`` - ``picture_url`` is
    ``""`` for an artist with only Deezer's placeholder (see
    :data:`_NO_PICTURE_HASH`). Public and keyless, like the artist search.

    Raises :class:`ValueError` when Deezer didn't really answer - including
    its rate limit, which comes back as an HTTP 200 with an ``error``
    object (see :func:`_search_rows`) - so ``[]`` always means "Deezer has
    no related artists for this one".
    """

    try:
        resp = httpx.get(
            _RELATED_URL.format(artist_id=artist_id),
            params={'limit': max(1, limit)},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.opt(exception=True).debug(
            'Deezer related-artists fetch failed for {}', artist_id
        )
        raise ValueError('Could not reach Deezer') from exc
    if not isinstance(data, dict):
        raise ValueError('Deezer sent an unexpected answer')
    if data.get('error'):
        logger.debug('Deezer refused the related artists: {}', data['error'])
        raise ValueError('Deezer refused the request')

    related: list[dict[str, Any]] = []
    for row in data.get('data') or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get('name') or '').strip()
        if not name or row.get('id') is None:
            continue
        related.append({
            'deezer_id': str(row['id']),
            'name': name,
            'picture_url': _picture(row),
            'fans': int(row.get('nb_fan') or 0),
        })
    return related


def _preview_link(url: Any) -> str:
    """*url* when it's an https link to Deezer's clip CDN, else ``""``."""

    if not isinstance(url, str):
        return ''
    parts = urlsplit(url)
    host = parts.hostname or ''
    if parts.scheme == 'https' and host.endswith(_PREVIEW_HOST_SUFFIX):
        return url
    return ''


def find_track_preview(
    artist: str, title: str, duration: Optional[float] = None
) -> str:
    """The 30 s preview clip Deezer has for a song, or ``""``.

    For a song with no clip of its own (a YouTube Music result, or a
    Spotify playlist track past what the embed page lists). Deezer's
    public track search is keyless; a row counts only when its artist is
    *artist* and its title is *title*, both compared the way a file name
    keeps them and ignoring ``(Live)``/``[Remastered]``/`` - Radio Edit``
    style suffixes, so another artist's cover or a different song is never
    played in its place. Among those, the one closest to *duration* wins,
    so a live version doesn't beat the studio one.

    Raises :class:`ValueError` when Deezer didn't really answer (see
    :func:`_search_rows`), so ``""`` always means "no clip found".
    """

    wanted_artist = file_name_key(artist)
    wanted_title = title_key(title)
    if not wanted_artist or not wanted_title:
        return ''
    try:
        resp = httpx.get(
            _TRACK_SEARCH_URL,
            params={'q': f'{artist} {title}', 'limit': 25},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.opt(exception=True).debug('Deezer track search failed')
        raise ValueError('Could not reach Deezer') from exc
    if not isinstance(data, dict):
        raise ValueError('Deezer sent an unexpected answer')
    if data.get('error'):
        logger.debug('Deezer refused the track search: {}', data['error'])
        raise ValueError('Deezer refused the request')

    matches = []
    for row in data.get('data') or []:
        if not isinstance(row, dict):
            continue
        preview = _preview_link(row.get('preview'))
        row_artist = str((row.get('artist') or {}).get('name') or '')
        if not preview or file_name_key(row_artist) != wanted_artist:
            continue
        titles = {
            title_key(row.get('title')),
            title_key(row.get('title_short')),
        }
        if wanted_title not in titles:
            continue
        matches.append((row, preview))
    if not matches:
        return ''
    if duration:
        matches.sort(
            key=lambda m: abs(float(m[0].get('duration') or 0) - duration)
        )
    return matches[0][1]


def fetch_artist_full(artist_id: str, lang: str) -> dict[str, Any]:
    """Bio, social links and related-artist names for a Deezer artist id.

    ``lang`` is sent as ``Accept-Language`` - the bio text itself changes
    (not just an echoed header), confirmed live for ``pt-BR``/``en``.
    Raises :class:`ValueError` if the request or the token exchange fails.

    ``social.instagram`` is a real schema field but came back ``null``
    for every artist tried live (old and current, big and small) - it
    looks unpopulated on Deezer's side. When an artist does have an
    Instagram link, Deezer sometimes stores it under ``facebook``
    instead (seen live for at least two artists) - there's no reliable
    way to detect that case from here, so it's left as-is.
    """

    try:
        auth_resp = httpx.get(
            _AUTH_URL,
            params={'jo': 'p', 'rto': 'c', 'i': 'c'},
            timeout=_TIMEOUT,
        )
        auth_resp.raise_for_status()
        token = auth_resp.json().get('jwt')
        if not token:
            raise ValueError('No anonymous Deezer token returned')

        resp = httpx.post(
            _GRAPHQL_URL,
            headers={
                'Authorization': f'Bearer {token}',
                'Accept-Language': lang or 'en',
                'Referer': 'https://www.deezer.com/',
                'Content-Type': 'application/json',
            },
            json={
                'operationName': 'ArtistFull',
                'variables': {
                    'artistId': str(artist_id),
                    'relatedArtistFirst': 10,
                    'liveEventsFirst': 1,
                },
                'query': _ARTIST_FULL_QUERY,
            },
            timeout=_GRAPHQL_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        logger.opt(exception=True).debug(
            'Deezer artist bio fetch failed for {}', artist_id
        )
        raise ValueError('Could not fetch artist info from Deezer') from exc

    artist = (payload.get('data') or {}).get('artist') or {}
    social = artist.get('social') or {}
    related_edges = (artist.get('relatedArtists') or {}).get('edges') or []
    related_names = [
        str(edge['node']['name']).strip()
        for edge in related_edges
        if isinstance(edge, dict)
        and isinstance(edge.get('node'), dict)
        and edge['node'].get('name')
    ]
    return {
        'bio_html': str((artist.get('bio') or {}).get('full') or ''),
        'social': {
            'twitter': str(social.get('twitter') or ''),
            'facebook': str(social.get('facebook') or ''),
            'website': str(social.get('website') or ''),
            'instagram': str(social.get('instagram') or ''),
        },
        'related_artist_names': related_names,
    }


def _chart_payload(limit: int) -> dict[str, Any]:
    """The raw ``GET /chart`` response (no genre id - Deezer's own overall
    "what's trending" chart), or raise :class:`ValueError`.

    Same "HTTP 200 but an ``error`` object instead of data" trap as
    :func:`_search_rows` - a rate limit would otherwise read as an empty
    chart.
    """

    try:
        resp = httpx.get(_CHART_URL, params={'limit': limit}, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.opt(exception=True).debug('Deezer chart fetch failed')
        raise ValueError('Could not reach Deezer') from exc
    if not isinstance(data, dict):
        raise ValueError('Deezer sent an unexpected answer')
    if data.get('error'):
        logger.debug('Deezer refused the chart request: {}', data['error'])
        raise ValueError('Deezer refused the request')
    return data


def _chart_track_song(row: dict[str, Any]) -> Optional[dict[str, Any]]:
    """A chart track row as a Downtify song (``source: 'deezer'``), or
    ``None`` when it's missing a title, an id or every artist name.

    Shaped like :func:`downtify.providers._result_to_song` so it can be
    queued for download exactly like a search result - see
    :func:`downtify.api._song_from_download_request`, which lets a
    ``source: 'deezer'`` row skip the Spotify/YouTube URL parsing
    ``/api/download/url`` would otherwise require, since a Deezer track
    link isn't one this app can resolve on its own.
    """

    track_id = row.get('id')
    name = str(row.get('title') or row.get('title_short') or '').strip()
    if not track_id or not name:
        return None
    artist = row.get('artist') if isinstance(row.get('artist'), dict) else {}
    album = row.get('album') if isinstance(row.get('album'), dict) else {}
    artists = []
    lead = str(artist.get('name') or '').strip()
    if lead:
        artists.append(lead)
    for contributor in row.get('contributors') or []:
        if not isinstance(contributor, dict):
            continue
        contributor_name = str(contributor.get('name') or '').strip()
        if contributor_name and contributor_name not in artists:
            artists.append(contributor_name)
    if not artists:
        return None
    cover = _cover_from_images(album)
    # A 30s MP3 clip Deezer's own player streams for unauthenticated users -
    # always https when present. See lib/preview.js on the frontend, which
    # refuses to hand anything else to an <audio> element.
    preview = str(row.get('preview') or '')
    return {
        'song_id': f'deezer-{track_id}',
        'name': name,
        'artists': artists,
        'album_name': str(album.get('title') or '').strip(),
        'cover_url': cover,
        'duration': int(row.get('duration') or 0),
        'url': str(row.get('link') or ''),
        'preview_url': preview if preview.startswith('https://') else '',
        'explicit': bool(row.get('explicit_lyrics')),
        'year': '',
        'release_date': '',
        'source': 'deezer',
    }


def _chart_album_release(row: dict[str, Any]) -> Optional[dict[str, Any]]:
    """A chart album row as a read-only release summary, or ``None``.

    Downtify has no Deezer discography resolver (unlike its Spotify/
    YouTube Music ones), so this is display-only: ``url`` opens the album
    on Deezer rather than feeding ``/api/url/resolve``.
    """

    album_id = row.get('id')
    name = str(row.get('title') or '').strip()
    if not album_id or not name:
        return None
    artist = row.get('artist') if isinstance(row.get('artist'), dict) else {}
    cover = _cover_from_images(row)
    return {
        'album_id': str(album_id),
        'name': name,
        'artist': str(artist.get('name') or '').strip(),
        'cover_url': cover,
        'url': str(row.get('link') or ''),
        'source': 'deezer',
    }


def _chart_artist_release(row: dict[str, Any]) -> Optional[dict[str, Any]]:
    """A chart artist row as a read-only release summary, or ``None``.

    Same placeholder-picture check as :func:`_has_real_picture` - the
    chart ranks by popularity, so an unphotographed artist here would be
    unusual, but it's still not worth showing Deezer's generic grey face
    for.
    """

    artist_id = row.get('id')
    name = str(row.get('name') or '').strip()
    if not artist_id or not name:
        return None
    return {
        'artist_id': str(artist_id),
        'name': name,
        'cover_url': (
            _cover_from_images(row, prefix='picture')
            if _has_real_picture(row)
            else ''
        ),
        'url': str(row.get('link') or ''),
        'source': 'deezer',
    }


def _chart_playlist_release(row: dict[str, Any]) -> Optional[dict[str, Any]]:
    """A chart playlist row as a read-only release summary, or ``None``.

    Same read-only reasoning as :func:`_chart_album_release`: Downtify has
    no way to resolve a Deezer playlist into a tracklist.
    """

    playlist_id = row.get('id')
    name = str(row.get('title') or '').strip()
    if not playlist_id or not name:
        return None
    user = row.get('user') if isinstance(row.get('user'), dict) else {}
    cover = _cover_from_images(row, prefix='picture')
    return {
        'playlist_id': str(playlist_id),
        'name': name,
        'owner': str(user.get('name') or '').strip(),
        'cover_url': cover,
        'url': str(row.get('link') or ''),
        'source': 'deezer',
    }


def _chart_section(
    data: dict[str, Any],
    key: str,
    mapper: Any,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in (data.get(key) or {}).get('data') or []:
        if not isinstance(row, dict):
            continue
        mapped = mapper(row)
        if mapped:
            rows.append(mapped)
    return rows


def fetch_chart(limit: int = 25) -> dict[str, Any]:
    """Deezer's global "what's trending" chart: top tracks, albums,
    artists and playlists - ``{tracks, albums, artists, playlists}``.

    Tracks are downloadable Downtify song rows, with a 30s preview clip
    when Deezer offers one (see :func:`_chart_track_song`); everything
    else is a read-only summary (see :func:`_chart_album_release`,
    :func:`_chart_artist_release`, :func:`_chart_playlist_release`).

    Raises :class:`ValueError` when Deezer can't be reached or refuses
    (see :func:`_chart_payload`).
    """

    data = _chart_payload(max(1, min(limit, 50)))
    return {
        'tracks': _chart_section(data, 'tracks', _chart_track_song),
        'albums': _chart_section(data, 'albums', _chart_album_release),
        'artists': _chart_section(data, 'artists', _chart_artist_release),
        'playlists': _chart_section(
            data, 'playlists', _chart_playlist_release
        ),
    }


# ── Pasted-link resolution (track/album/playlist/artist) ───────────────
#
# Unlike the chart above (rows already embedded in one response) or the
# artist-photo search (no id needed), these read a specific Deezer id the
# same way downtify.spotify/downtify.providers do for a pasted Spotify or
# YouTube Music link - see downtify.api's _deezer_details, wired into
# GET /api/url/resolve, /api/song/url and /api/artists/top_songs/url next
# to the existing Spotify/YouTube Music branches.

_DEEZER_URL_RE = re.compile(
    r'deezer\.com/(?:[a-z]{2}/)?(track|album|playlist|artist)/(\d+)',
    re.IGNORECASE,
)


def parse_deezer_url(url: str) -> Optional[tuple[str, str]]:
    """``(kind, id)`` for a Deezer track/album/playlist/artist URL, or
    ``None``.

    Matches ``deezer.com/track/123`` with or without a ``www.`` or a
    two-letter locale segment (``deezer.com/br/track/123``, as Deezer's
    own share links carry). Deezer's short ``deezer.page.link`` share
    links aren't recognized - they'd need an extra redirect-following
    request just to find out what they point at.
    """

    match = _DEEZER_URL_RE.search(str(url or ''))
    if not match:
        return None
    return match.group(1).lower(), match.group(2)


def _get_json(url: str, **params: Any) -> dict[str, Any]:
    """A Deezer REST GET, or raise :class:`ValueError`.

    Same "HTTP 200 but an ``error`` object instead of data" trap as
    :func:`_search_rows` - an invalid id, a rate limit, all read this
    way rather than as an HTTP error status.
    """

    try:
        resp = httpx.get(url, params=params or None, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.opt(exception=True).debug('Deezer request failed: {}', url)
        raise ValueError('Could not reach Deezer') from exc
    if not isinstance(data, dict):
        raise ValueError('Deezer sent an unexpected answer')
    if data.get('error'):
        logger.debug('Deezer refused {}: {}', url, data['error'])
        raise ValueError('Deezer refused the request')
    return data


def _artists_from_track_row(row: dict[str, Any]) -> list[str]:
    """Lead artist first, then any featured contributors - deduplicated,
    same convention as :func:`_chart_track_song`."""

    artist = row.get('artist') if isinstance(row.get('artist'), dict) else {}
    artists: list[str] = []
    lead = str(artist.get('name') or '').strip()
    if lead:
        artists.append(lead)
    for contributor in row.get('contributors') or []:
        if not isinstance(contributor, dict):
            continue
        name = str(contributor.get('name') or '').strip()
        if name and name not in artists:
            artists.append(name)
    return artists


# Deezer's four fixed image sizes, smallest first - unlike a YouTube Music
# thumbnail (any pixel size, by editing its URL - see
# providers._resize_thumbnail), these are separately served images at
# exactly these dimensions and nothing in between.
_COVER_SIZES = (('small', 56), ('medium', 250), ('big', 500), ('xl', 1000))


def _cover_from_images(d: dict[str, Any], prefix: str = 'cover') -> str:
    """The smallest of Deezer's four image sizes that still meets the
    configured cover size - the same ``cover_resolution`` setting Settings
    already uses for YouTube Music cover art (see
    :func:`downtify.providers.cover_resolution`). ``cover`` for a track/
    album/playlist, ``picture`` for an artist.

    When the configured size is bigger than every size Deezer offers
    (its largest, ``xl``, is 1000px), the largest one present is used
    instead - the best Deezer has, rather than nothing.
    """

    wanted = providers.cover_resolution()
    largest_seen = ''
    for suffix, pixels in _COVER_SIZES:
        url = d.get(f'{prefix}_{suffix}')
        if not url:
            continue
        largest_seen = url
        if pixels >= wanted:
            return url
    return largest_seen


def _year_from_release_date(value: str) -> str:
    text = str(value or '').strip()
    return text[:4] if len(text) >= 4 and text[:4].isdigit() else ''


def _song_from_full_track(
    row: dict[str, Any],
    *,
    track_number: int = 0,
    album_track_total: int = 0,
    release_date: str = '',
) -> Optional[dict[str, Any]]:
    """A full Deezer track resource - or an album/playlist tracklist row,
    same shape minus a couple of fields - as a downloadable Downtify song.

    Unlike a chart row (:func:`_chart_track_song`), this fills in a
    release date whenever one is available: the caller's own
    (an album's ``release_date``, for every one of its tracks), else the
    row's or its embedded album's.
    """

    track_id = row.get('id')
    name = str(row.get('title') or row.get('title_short') or '').strip()
    if not track_id or not name:
        return None
    artists = _artists_from_track_row(row)
    if not artists:
        return None
    album = row.get('album') if isinstance(row.get('album'), dict) else {}
    preview = str(row.get('preview') or '')
    rd = (
        release_date
        or str(row.get('release_date') or '').strip()
        or str(album.get('release_date') or '').strip()
    )
    song: dict[str, Any] = {
        'song_id': f'deezer-{track_id}',
        'name': name,
        'artists': artists,
        'album_name': str(album.get('title') or '').strip(),
        'cover_url': _cover_from_images(album),
        'duration': int(row.get('duration') or 0),
        'url': str(row.get('link') or ''),
        'preview_url': preview if preview.startswith('https://') else '',
        'explicit': bool(row.get('explicit_lyrics')),
        'year': _year_from_release_date(rd),
        'release_date': rd,
        'source': 'deezer',
    }
    if track_number:
        song['track_number'] = track_number
    if album_track_total:
        song['album_track_total'] = album_track_total
    return song


def track_from_id(track_id: str) -> dict[str, Any]:
    """A single Deezer track, as a downloadable Downtify song.

    Raises :class:`ValueError` when the id doesn't resolve (Deezer
    answers a missing id with an ``error`` object, not an HTTP 404 - see
    :func:`_get_json`) or has no title/artist to build a song from.
    """

    row = _get_json(f'https://api.deezer.com/track/{track_id}')
    song = _song_from_full_track(
        row, track_number=int(row.get('track_position') or 0)
    )
    if song is None:
        raise ValueError('Deezer track has no title or artist')
    return song


def _paginate_tracks(first_page: dict[str, Any]) -> list[dict[str, Any]]:
    """Every row of a Deezer tracklist, following ``next`` - a full URL
    to the following page, present whenever there is one - until Deezer
    stops offering one. Trusted the same way Spotify's playlist ``total``
    is: Deezer's own cursor, not re-derived from a track count."""

    rows: list[dict[str, Any]] = list(first_page.get('data') or [])
    next_url = first_page.get('next')
    while next_url:
        page = _get_json(next_url)
        rows.extend(page.get('data') or [])
        next_url = page.get('next')
    return rows


def album_from_id(album_id: str) -> list[dict[str, Any]]:
    """Every track of a Deezer album/single/EP, in tracklist order.

    Each track's position in the list is its ``track_number`` - Deezer
    already returns them in tracklist order - since the per-track rows
    embedded in an album's response don't carry one of their own (unlike
    a standalone :func:`track_from_id` lookup). The album's own
    ``release_date`` fills in what those rows don't carry either.

    Raises :class:`ValueError` when the id doesn't resolve or the
    request fails.
    """

    return _album_songs(_get_json(f'https://api.deezer.com/album/{album_id}'))


def _album_songs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Every track of an already-fetched ``GET /album/{id}`` response -
    see :func:`album_from_id`."""

    rows = _paginate_tracks(payload.get('tracks') or {})
    release_date = str(payload.get('release_date') or '').strip()
    total = len(rows)
    songs: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        song = _song_from_full_track(
            row,
            track_number=index + 1,
            album_track_total=total,
            release_date=release_date,
        )
        if song:
            songs.append(song)
    return songs


def playlist_info_and_tracks(
    playlist_id: str,
) -> tuple[str, list[dict[str, Any]]]:
    """``(name, tracks)`` for a Deezer playlist, fetching every track via
    :func:`_paginate_tracks`.

    Deliberately doesn't number the tracks: unlike an album, a playlist's
    position isn't a track's real position on its own album, and its
    tracks come from many different albums anyway - each keeps whatever
    ``release_date`` its own row/album happens to carry (usually none;
    Deezer's playlist-track rows carry a slimmer album reference than
    :func:`track_from_id`'s or :func:`album_from_id`'s do).

    Raises :class:`ValueError` when the id doesn't resolve or the
    request fails.
    """

    payload = _get_json(f'https://api.deezer.com/playlist/{playlist_id}')
    name = str(payload.get('title') or '').strip() or str(playlist_id)
    rows = _paginate_tracks(payload.get('tracks') or {})
    songs: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        song = _song_from_full_track(row)
        if song:
            songs.append(song)
    return name, songs


def playlist_cover_url_from_id(playlist_id: str) -> str:
    """Largest cover art of a Deezer playlist, for saving alongside its
    M3U file - same idea as
    :func:`downtify.spotify.playlist_cover_url_from_id`.

    A playlist's own image fields are named ``picture_*`` (like an
    artist's), not ``cover_*`` (like a track/album's).

    Raises :class:`ValueError` when the id doesn't resolve or the
    request fails.
    """

    payload = _get_json(f'https://api.deezer.com/playlist/{playlist_id}')
    return _cover_from_images(payload, prefix='picture')


# Deezer's own release-type classification (``record_type``), title-cased
# the same way downtify.spotify._RELEASE_TYPES is - ReleaseCard.vue only
# translates 'album'/'single'/'ep' and shows anything else (a
# 'compile'/"Compilation" release) as-is.
_RECORD_TYPE_LABELS = {
    'album': 'Album',
    'single': 'Single',
    'ep': 'EP',
    'compile': 'Compilation',
}


def _artist_release_row(
    row: dict[str, Any], artist_name: str
) -> Optional[dict[str, Any]]:
    """One row of a Deezer artist's discography as a release summary.

    Unlike an album/playlist track row, an artist's own albums listing
    doesn't repeat the artist's name on each row (it's implied), so
    *artist_name* - the artist page's own name - fills it in.
    """

    album_id = row.get('id')
    name = str(row.get('title') or '').strip()
    if not album_id or not name:
        return None
    return {
        'album_id': str(album_id),
        'name': name,
        'artist': artist_name,
        'cover_url': _cover_from_images(row),
        'year': _year_from_release_date(row.get('release_date')),
        'explicit': bool(row.get('explicit_lyrics')),
        'url': str(row.get('link') or ''),
        'source': 'deezer',
        'release_type': _release_type_label(row.get('record_type')),
    }


def _release_type_label(record_type: Any) -> str:
    """Deezer's ``record_type`` as a label (see :data:`_RECORD_TYPE_LABELS`),
    ``Album`` when it has none."""

    text = str(record_type or '').strip().lower()
    return _RECORD_TYPE_LABELS.get(text, text.title() or 'Album')


def artist_page_from_id(
    artist_id: str,
) -> tuple[str, str, list[dict[str, Any]]]:
    """``(name, cover_url, releases)`` for a Deezer artist - their full
    discography (every album, single, EP and compilation Deezer has),
    Deezer's own order (most recent first).

    Raises :class:`ValueError` when the id doesn't resolve or the
    request fails.
    """

    info = _get_json(f'https://api.deezer.com/artist/{artist_id}')
    name = str(info.get('name') or '').strip() or str(artist_id)
    cover = _cover_from_images(info, prefix='picture')
    first_page = _get_json(
        f'https://api.deezer.com/artist/{artist_id}/albums', limit=100
    )
    rows = _paginate_tracks(first_page)
    releases: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        release = _artist_release_row(row, name)
        if release:
            releases.append(release)
    return name, cover, releases


# The Deezer equivalent of downtify.api.YOUTUBE_TOP_SONGS_LIMIT - Deezer's
# own artist "top" endpoint is already ranked by popularity, so only its
# head is worth listing.
TOP_SONGS_LIMIT = 50


def artist_top_songs_from_id(
    artist_id: str,
) -> tuple[str, str, list[dict[str, Any]]]:
    """``(name, cover_url, songs)`` for a Deezer artist's own "top"
    ranking (their most-played tracks - the same shelf ``deezer.com``
    shows on an artist's page).

    Raises :class:`ValueError` when the id doesn't resolve or the
    request fails.
    """

    info = _get_json(f'https://api.deezer.com/artist/{artist_id}')
    name = str(info.get('name') or '').strip() or str(artist_id)
    cover = _cover_from_images(info, prefix='picture')
    top = _get_json(
        f'https://api.deezer.com/artist/{artist_id}/top',
        limit=TOP_SONGS_LIMIT,
    )
    songs: list[dict[str, Any]] = []
    for row in top.get('data') or []:
        if not isinstance(row, dict):
            continue
        song = _song_from_full_track(row)
        if song:
            songs.append(song)
    return name, cover, songs


# ── Finder: free-text search, then artist → albums → tracks ────────────
#
# Deezer-only, read-only browsing for the Finder page: a free-text search
# across tracks/albums/artists, then - in columns, like macOS Finder's
# column view - an artist's profile, their discography and one album's
# tracklist. Each carries as much as the public REST API offers for it,
# not just what a download needs.

_FINDER_SEARCH_URL = 'https://api.deezer.com/search'
_FINDER_WORKERS = 4

# How many album ids one album_track_counts() call looks up at most.
TRACK_COUNTS_MAX_IDS = 50

# An artist's albums listing carries no track count (only an album search
# row does - verified live), so the Finder asks for each album's on its
# own, one GET per album. Deezer allows 50 requests per 5 seconds per IP;
# staying under 40 leaves room for everything else running meanwhile.
_THROTTLE_WINDOW = 5.0
_THROTTLE_MAX = 40
_throttle_lock = threading.Lock()
_throttle_times: deque[float] = deque()

# Album id -> track count. A released album's count doesn't change, so it
# is kept for the life of the process (bounded, just in case).
_ALBUM_TRACK_COUNTS: dict[str, int] = {}
_ALBUM_TRACK_COUNTS_MAX = 5000


def _throttle() -> None:
    """Wait until another request fits under :data:`_THROTTLE_MAX` per
    :data:`_THROTTLE_WINDOW` seconds, then claim it."""

    while True:
        with _throttle_lock:
            now = time.monotonic()
            while (
                _throttle_times
                and now - _throttle_times[0] >= _THROTTLE_WINDOW
            ):
                _throttle_times.popleft()
            if len(_throttle_times) < _THROTTLE_MAX:
                _throttle_times.append(now)
                return
            wait = _THROTTLE_WINDOW - (now - _throttle_times[0])
        time.sleep(max(wait, 0.05))


def _remember_track_count(album_id: str, count: int) -> None:
    if len(_ALBUM_TRACK_COUNTS) >= _ALBUM_TRACK_COUNTS_MAX:
        _ALBUM_TRACK_COUNTS.clear()
    _ALBUM_TRACK_COUNTS[album_id] = count


def _rows_or_empty(url: str, **params: Any) -> list[Any]:
    """The ``data`` rows of a Deezer list endpoint, or ``[]`` when it
    fails - for the parts of a Finder answer that are extras."""

    try:
        return list(_get_json(url, **params).get('data') or [])
    except ValueError:
        return []


def _map_rows(
    rows: list[Any], mapper: Callable[[dict[str, Any]], Any]
) -> list[dict[str, Any]]:
    mapped_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        mapped = mapper(row)
        if mapped:
            mapped_rows.append(mapped)
    return mapped_rows


def _finder_song(row: dict[str, Any]) -> Optional[dict[str, Any]]:
    """A search/top track row as a downloadable song, plus the Deezer ids
    of its artist and album - what the Finder opens when it's clicked."""

    song = _song_from_full_track(row)
    if song is None:
        return None
    artist = row.get('artist') if isinstance(row.get('artist'), dict) else {}
    album = row.get('album') if isinstance(row.get('album'), dict) else {}
    song['deezer_artist_id'] = str(artist.get('id') or '')
    song['deezer_album_id'] = str(album.get('id') or '')
    return song


def _finder_artist_row(row: dict[str, Any]) -> Optional[dict[str, Any]]:
    """A search/related artist row: :func:`_chart_artist_release` plus its
    fan and album counts."""

    release = _chart_artist_release(row)
    if release is None:
        return None
    release['fans'] = int(row.get('nb_fan') or 0)
    release['album_count'] = int(row.get('nb_album') or 0)
    return release


def _finder_album_row(
    row: dict[str, Any], artist_id: str = ''
) -> Optional[dict[str, Any]]:
    """An album search row or a row of an artist's albums listing:
    :func:`_artist_release_row` plus the artist's id, the full release
    date, fans and the track count - ``None`` when the row doesn't carry
    one and it isn't known yet (see :func:`album_track_counts`)."""

    artist = row.get('artist') if isinstance(row.get('artist'), dict) else {}
    release = _artist_release_row(row, str(artist.get('name') or '').strip())
    if release is None:
        return None
    album_id = release['album_id']
    count = row.get('nb_tracks')
    if count is not None:
        _remember_track_count(album_id, int(count))
    else:
        count = _ALBUM_TRACK_COUNTS.get(album_id)
    release.update({
        'artist_id': str(artist.get('id') or artist_id),
        'release_date': str(row.get('release_date') or '').strip(),
        'track_count': int(count) if count is not None else None,
        'fans': int(row.get('fans') or 0),
    })
    return release


def finder_search(
    query: str, limit: int = 25
) -> dict[str, list[dict[str, Any]]]:
    """``{songs, albums, artists}`` matching *query* on Deezer, each in
    Deezer's own relevance order.

    Songs are downloadable song rows (see :func:`_finder_song`); albums
    and artists are summaries the Finder opens. Albums and artists are
    extras: their failure leaves them empty, while a failed song search
    raises :class:`ValueError` - the same split the regular search makes.
    """

    text = query.strip()
    if not text:
        return {'songs': [], 'albums': [], 'artists': []}
    size = max(1, min(limit, 50))
    with ThreadPoolExecutor(max_workers=3) as pool:
        songs = pool.submit(_get_json, _FINDER_SEARCH_URL, q=text, limit=size)
        albums = pool.submit(
            _rows_or_empty, f'{_FINDER_SEARCH_URL}/album', q=text, limit=size
        )
        artists = pool.submit(
            _rows_or_empty, f'{_FINDER_SEARCH_URL}/artist', q=text, limit=size
        )
        song_rows = list(songs.result().get('data') or [])
    return {
        'songs': _map_rows(song_rows, _finder_song),
        'albums': _map_rows(albums.result(), _finder_album_row),
        'artists': _map_rows(artists.result(), _finder_artist_row),
    }


# How many pages of a name search finder_artist_songs reads at most, 100
# rows each - a big catalogue's first few hundred songs, a handful of
# requests.
ARTIST_SONGS_MAX_PAGES = 3


def finder_artist_songs(artist_id: str, name: str) -> list[dict[str, Any]]:
    """An artist's songs for the Finder, as :func:`_finder_song` rows in
    Deezer's own relevance order: a plain search for *name*, keeping only
    the rows whose main artist is *artist_id*.

    Deezer's field search (``artist:"name"``) would be the direct way, but
    for tracks it answers nothing at all today - for any artist, even the
    documented ``artist:"..." track:"..."`` form (verified live). A plain
    search for the name mostly finds that artist anyway, and matching the
    id rather than the name keeps out a namesake, or a song merely called
    that. Reads up to :data:`ARTIST_SONGS_MAX_PAGES` pages, each through
    :func:`_throttle`. Raises :class:`ValueError` when Deezer can't be
    asked or refuses.
    """

    wanted = str(artist_id).strip()
    text = name.strip()
    if not wanted or not text:
        return []
    rows: list[Any] = []
    params: dict[str, Any] = {'q': text, 'limit': 100}
    url: Optional[str] = _FINDER_SEARCH_URL
    for _ in range(ARTIST_SONGS_MAX_PAGES):
        if not url:
            break
        _throttle()
        page = _get_json(url, **params)
        rows.extend(page.get('data') or [])
        # Deezer's own "next" already carries the query and the offset.
        url, params = page.get('next'), {}

    def by_artist(row: dict[str, Any]) -> bool:
        artist = (
            row.get('artist') if isinstance(row.get('artist'), dict) else {}
        )
        return str(artist.get('id') or '') == wanted

    return _map_rows(
        [row for row in rows if isinstance(row, dict) and by_artist(row)],
        _finder_song,
    )


def _artist_full_or_none(artist_id: str, lang: str) -> Optional[dict]:
    try:
        return fetch_artist_full(artist_id, lang)
    except ValueError:
        return None


def finder_artist(artist_id: str, lang: str = 'en') -> dict[str, Any]:
    """Everything the Finder's first column shows about a Deezer artist:
    photo, fans, album count, bio (as Deezer's HTML, in *lang* - see
    :func:`fetch_artist_full`), social links, related artists and their
    ten most-played tracks. Fetched in parallel.

    Only the artist itself is required - raises :class:`ValueError` when
    it doesn't resolve; every other part is left empty when it fails.
    """

    base = f'https://api.deezer.com/artist/{artist_id}'
    with ThreadPoolExecutor(max_workers=_FINDER_WORKERS) as pool:
        info = pool.submit(_get_json, base)
        related = pool.submit(_rows_or_empty, f'{base}/related', limit=20)
        top = pool.submit(_rows_or_empty, f'{base}/top', limit=10)
        full = pool.submit(_artist_full_or_none, artist_id, lang)
        payload = info.result()
    extra = full.result() or {}
    return {
        'artist_id': str(artist_id),
        'name': str(payload.get('name') or '').strip() or str(artist_id),
        'cover_url': (
            _cover_from_images(payload, prefix='picture')
            if _has_real_picture(payload)
            else ''
        ),
        'fans': int(payload.get('nb_fan') or 0),
        'album_count': int(payload.get('nb_album') or 0),
        'url': str(payload.get('link') or ''),
        'source': 'deezer',
        'bio_html': str(extra.get('bio_html') or ''),
        'social': extra.get('social') or {},
        'related': _map_rows(related.result(), _finder_artist_row),
        'top_songs': _map_rows(top.result(), _finder_song),
    }


def finder_artist_albums(artist_id: str) -> list[dict[str, Any]]:
    """A Deezer artist's whole discography, most recent first (Deezer's
    own order), as :func:`_finder_album_row` summaries. Track counts are
    only filled in when already known - see :func:`album_track_counts`.

    Raises :class:`ValueError` when the id doesn't resolve or the
    request fails.
    """

    first_page = _get_json(
        f'https://api.deezer.com/artist/{artist_id}/albums', limit=100
    )
    return _map_rows(
        _paginate_tracks(first_page),
        lambda row: _finder_album_row(row, artist_id=str(artist_id)),
    )


def _album_track_count(album_id: str) -> Optional[int]:
    """One album's track count - remembered, else the ``total`` of a
    one-row page of its tracklist (much lighter than the whole album) -
    or ``None`` when Deezer didn't answer."""

    cached = _ALBUM_TRACK_COUNTS.get(album_id)
    if cached is not None:
        return cached
    _throttle()
    try:
        page = _get_json(
            f'https://api.deezer.com/album/{album_id}/tracks', limit=1
        )
    except ValueError:
        return None
    total = page.get('total')
    if total is None:
        return None
    _remember_track_count(album_id, int(total))
    return int(total)


def album_track_counts(album_ids: list[str]) -> dict[str, int]:
    """``{album_id: track_count}`` for up to :data:`TRACK_COUNTS_MAX_IDS`
    album ids - the ones Deezer answered for; a failed lookup (a rate
    limit, say) is just left out, so the caller can ask again later.

    Throttled to stay under Deezer's request quota (see
    :func:`_throttle`), so a long list takes a few seconds; the caller
    asks in small batches to show counts as they arrive.
    """

    ids = list(
        dict.fromkeys(
            album_id
            for album_id in (str(raw).strip() for raw in album_ids)
            if album_id.isdigit()
        )
    )[:TRACK_COUNTS_MAX_IDS]
    if not ids:
        return {}
    # More workers than elsewhere: these are tiny requests, and _throttle
    # keeps the overall rate in check anyway.
    with ThreadPoolExecutor(max_workers=_FINDER_WORKERS * 2) as pool:
        counts = list(pool.map(_album_track_count, ids))
    return {
        album_id: count
        for album_id, count in zip(ids, counts)
        if count is not None
    }


def finder_album(album_id: str) -> dict[str, Any]:
    """A Deezer album with every detail its own resource carries - label,
    genres, UPC, length, fans, contributors - and its tracklist as
    downloadable songs (see :func:`album_from_id`).

    Raises :class:`ValueError` when the id doesn't resolve or the
    request fails.
    """

    payload = _get_json(f'https://api.deezer.com/album/{album_id}')
    name = str(payload.get('title') or '').strip() or str(album_id)
    artist = (
        payload.get('artist')
        if isinstance(payload.get('artist'), dict)
        else {}
    )
    cover = _cover_from_images(payload)
    songs = _album_songs(payload)
    for song in songs:
        song['cover_url'] = song['cover_url'] or cover
        song['album_name'] = song['album_name'] or name
    count = int(payload.get('nb_tracks') or len(songs))
    _remember_track_count(str(album_id), count)
    release_date = str(payload.get('release_date') or '').strip()
    genres = [
        str(genre['name']).strip()
        for genre in (payload.get('genres') or {}).get('data') or []
        if isinstance(genre, dict) and genre.get('name')
    ]
    contributors = [
        {
            'artist_id': str(person.get('id') or ''),
            'name': str(person['name']).strip(),
            'role': str(person.get('role') or '').strip(),
        }
        for person in payload.get('contributors') or []
        if isinstance(person, dict) and person.get('name')
    ]
    return {
        'album_id': str(album_id),
        'name': name,
        'artist': str(artist.get('name') or '').strip(),
        'artist_id': str(artist.get('id') or ''),
        'cover_url': cover,
        'release_date': release_date,
        'year': _year_from_release_date(release_date),
        'label': str(payload.get('label') or '').strip(),
        'genres': genres,
        'duration': int(payload.get('duration') or 0),
        'track_count': count,
        'fans': int(payload.get('fans') or 0),
        'release_type': _release_type_label(payload.get('record_type')),
        'explicit': bool(payload.get('explicit_lyrics')),
        'upc': str(payload.get('upc') or '').strip(),
        'url': str(payload.get('link') or ''),
        'contributors': contributors,
        'source': 'deezer',
        'tracks': songs,
    }


# ── Discover: albums, editorial playlists and matching Spotify albums ──
#
# Discover (see downtify.discover) builds its album and playlist shelves
# from Deezer first, then adds what Spotify picks on top, matched back to
# Deezer. Everything here goes through _throttle: a cold Discover page
# asks for a few dozen of these, next to its related-artist lookups.

# Deezer's own editors publish a "100% <artist>" playlist - the very best
# of one artist, the counterpart of Spotify's "This Is <artist>" - under
# this account name (verified live for a range of artists).
EDITORIAL_OWNER = 'Deezer Artist Editor'
_EDITORIAL_PREFIX = '100%'


def artist_discography(artist_id: str) -> list[dict[str, Any]]:
    """Every release of a Deezer artist, as :func:`finder_artist_albums`
    rows (with ``fans`` and ``release_type``), each page throttled.

    Raises :class:`ValueError` when Deezer can't be asked or refuses.
    """

    _throttle()
    page = _get_json(
        f'https://api.deezer.com/artist/{artist_id}/albums', limit=100
    )
    rows = list(page.get('data') or [])
    while page.get('next'):
        _throttle()
        page = _get_json(page['next'])
        rows.extend(page.get('data') or [])
    return _map_rows(
        rows, lambda row: _finder_album_row(row, artist_id=str(artist_id))
    )


def editorial_playlist(name: str) -> Optional[dict[str, Any]]:
    """Deezer's editorial "100% <name>" playlist, or ``None`` when its
    editors have none for that artist.

    ``{playlist_id, name, owner, cover_url, url}``. Only a playlist by
    :data:`EDITORIAL_OWNER` whose title is exactly "100%" and the artist's
    name (compared the way a file name is, see
    :func:`~downtify.file_naming.file_name_key`) counts - a fan's
    "100% Radiohead & friends" doesn't. Raises :class:`ValueError` when
    Deezer can't be asked or refuses, so a failure isn't taken for "none".
    """

    wanted = file_name_key(name)
    if not wanted:
        return None
    _throttle()
    rows = (
        _get_json(
            f'{_FINDER_SEARCH_URL}/playlist',
            q=f'{_EDITORIAL_PREFIX} {name}',
            limit=10,
        ).get('data')
        or []
    )
    for row in rows:
        if not isinstance(row, dict):
            continue
        user = row.get('user') if isinstance(row.get('user'), dict) else {}
        if str(user.get('name') or '') != EDITORIAL_OWNER:
            continue
        title = str(row.get('title') or '').strip()
        if not title.startswith(_EDITORIAL_PREFIX):
            continue
        if file_name_key(title[len(_EDITORIAL_PREFIX) :]) != wanted:
            continue
        playlist_id = row.get('id')
        if not playlist_id:
            continue
        return {
            'playlist_id': str(playlist_id),
            'name': title,
            'owner': EDITORIAL_OWNER,
            'cover_url': _cover_from_images(row, prefix='picture'),
            'url': str(
                row.get('link')
                or f'https://www.deezer.com/playlist/{playlist_id}'
            ),
        }
    return None


def search_albums_by(artist: str, title: str) -> list[dict[str, Any]]:
    """Deezer albums that may be *artist*'s *title*, as
    :func:`_finder_album_row` rows, best match first - for matching an
    album found elsewhere (Spotify) back to Deezer.

    Deezer's field search (``artist:"..." album:"..."``) first; when none
    of its rows is by *artist* - it's strict about punctuation, and loose
    enough to answer with other artists' albums instead of nothing (seen
    live for Blur's "Blur") - a plain search for both. Deciding which row
    really is the album is the caller's job. Raises :class:`ValueError`
    when Deezer can't be asked or refuses.
    """

    wanted = file_name_key(artist)
    queries = [f'artist:"{artist}" album:"{title}"', f'{artist} {title}']
    found: list[dict[str, Any]] = []
    for query in queries:
        _throttle()
        rows = (
            _get_json(f'{_FINDER_SEARCH_URL}/album', q=query, limit=10).get(
                'data'
            )
            or []
        )
        found = _map_rows(rows, _finder_album_row)
        if any(file_name_key(row['artist']) == wanted for row in found):
            break
    return found
