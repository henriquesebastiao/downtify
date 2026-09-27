"""Search the public Deezer API for artist photo candidates, fetch
bio/social/related-artist data from Deezer's internal web-player API,
read Deezer's own global "what's trending" chart, and resolve a pasted
Deezer track/album/playlist/artist link the same way :mod:`downtify.spotify`
and :mod:`downtify.providers` do for Spotify and YouTube Music (see
:func:`parse_deezer_url` and ``downtify.api``'s ``_deezer_details``).

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
from typing import Any, Optional
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

    payload = _get_json(f'https://api.deezer.com/album/{album_id}')
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
    record_type = str(row.get('record_type') or '').strip().lower()
    return {
        'album_id': str(album_id),
        'name': name,
        'artist': artist_name,
        'cover_url': _cover_from_images(row),
        'year': _year_from_release_date(row.get('release_date')),
        'explicit': bool(row.get('explicit_lyrics')),
        'url': str(row.get('link') or ''),
        'source': 'deezer',
        'release_type': _RECORD_TYPE_LABELS.get(
            record_type, record_type.title() or 'Album'
        ),
    }


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
