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


def search_artist(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Artist photo candidates for *query*, largest Deezer offers each.

    Each result is ``{source: 'deezer', name, image_url, url}`` - same
    shape the artist-image picker expects from every source.
    """

    text = query.strip()
    if not text:
        return []
    try:
        resp = httpx.get(
            _SEARCH_URL,
            params={'q': text, 'limit': max(1, limit)},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.opt(exception=True).debug('Deezer artist search failed')
        return []

    results: list[dict[str, Any]] = []
    for row in data.get('data') or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get('name') or '').strip()
        image = (
            row.get('picture_xl')
            or row.get('picture_big')
            or row.get('picture_medium')
            or ''
        )
        if not name or not image:
            continue
        results.append({
            'source': 'deezer',
            'name': name,
            'image_url': image,
            'url': row.get('link') or '',
        })
    return results


def resolve_artist_id(name: str) -> Optional[str]:
    """Deezer's numeric artist id for an exact (case-insensitive) name
    match, or ``None`` if no result's name matches exactly.

    Deliberately stricter than :func:`search_artist`: an unrelated top
    result would silently attach the wrong bio/social/related-artists to
    this artist's profile, so a fuzzy "good enough" match isn't good
    enough here.
    """

    text = name.strip()
    if not text:
        return None
    try:
        resp = httpx.get(
            _SEARCH_URL, params={'q': text, 'limit': 25}, timeout=_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.opt(exception=True).debug('Deezer artist id lookup failed')
        return None
    wanted = text.lower()
    for row in data.get('data') or []:
        if not isinstance(row, dict):
            continue
        if str(row.get('name') or '').strip().lower() == wanted:
            artist_id = row.get('id')
            return str(artist_id) if artist_id is not None else None
    return None


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
