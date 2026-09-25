"""Search the public Deezer API for artist photo candidates, and fetch
bio/social/related-artist data from Deezer's internal web-player API.

``api.deezer.com`` is unauthenticated and keyless, same shape of
integration as :mod:`downtify.itunes`. Deezer's artist search never
returns a banner-shaped image, only square profile photos.

Bio/social/related-artist data has no public REST equivalent at all
(verified live: ``/artist/{id}`` has no bio field, and
``/artist/{id}/biography`` etc. all 400). The only way to get it is
Deezer's *internal*, undocumented web-player GraphQL API
(``pipe.deezer.com/api``), which is fragile by nature: it only accepts
an anonymous token's exact, full, persisted "ArtistFull" query text
(captured live from the browser, see :func:`fetch_artist_full`) - a
hand-trimmed query gets a generic, unhelpful error instead of the usual
GraphQL validation message. Treat this as append-only: if Deezer changes
that query shape, this needs a fresh capture, not a clever rewrite.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx
from loguru import logger

from .file_naming import file_name_key

_SEARCH_URL = 'https://api.deezer.com/search/artist'
_AUTH_URL = 'https://auth.deezer.com/login/anonymous'
_GRAPHQL_URL = 'https://pipe.deezer.com/api'
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
