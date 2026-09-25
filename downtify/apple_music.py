"""Fetch artist bio/origin/formation data from Apple Music's internal
catalog API, keyed off ids resolved via the public iTunes Search API.

``itunes.apple.com/search`` (see :mod:`downtify.itunes`) is public and
keyless, but its artist schema has no bio/origin field at all - only
``artistName``/``artistId``/``primaryGenreName`` (verified live). The
richer data (``artistBio``, ``origin``, ``bornOrFormed``, ``isGroup``,
hero artwork) only exists on Apple Music's *internal* web-player API,
``amp-api.music.apple.com``.

That API needs a bearer token, but - same fragility class as Deezer's
anonymous GraphQL token (:mod:`downtify.deezer`) - it is **not** a
logged-in session: it's a fixed "developer token" Apple's own web player
embeds in its public JS bundle for itself, servable to any anonymous
visitor. :func:`_scrape_web_token` fetches ``music.apple.com``'s browse
page to find the current bundle URL, downloads that bundle, and regexes
the token out of it - no Apple ID, no credentials. Cached in memory until
its own ``exp`` claim is close, since it's long-lived (~70 days observed)
and the bundle can be several MB.

Localization is not just an ``Accept-Language`` header - confirmed live
that header alone changes nothing. The catalog is split into per-country
"storefronts", each with its own fixed ``supportedLanguageTags`` list
(``GET /v1/storefronts`` enumerates them); the ``l=`` query parameter
must be one of *that storefront's* supported tags or the response
silently falls back to the storefront's default language instead of
erroring. :data:`_STOREFRONT_LANG` maps each of Downtify's UI locales to
a ``(storefront, tag)`` pair known to work, resolved by querying that
endpoint live - ``bg`` has no working pair (the ``bg`` storefront only
supports ``en-GB``), so it always falls back to English, same shape of
gap already documented for YouTube Music's own bio fallback.
"""

from __future__ import annotations

import base64
import json
import re
import time
from threading import Lock
from typing import Any, Optional

import httpx
from loguru import logger

from .file_naming import file_name_key

_SEARCH_URL = 'https://itunes.apple.com/search'
_BROWSE_URL = 'https://music.apple.com/us/browse'
_CATALOG_URL = 'https://amp-api.music.apple.com/v1/catalog/{storefront}/artists/{artist_id}'
_TIMEOUT = 10
_BUNDLE_TIMEOUT = 20

# The exact header segment of the token's JWT ({"typ":"JWT","alg":"ES256",
# "kid":"WebPlayKid"}, base64url-encoded) - matching on this specific,
# stable prefix instead of a generic "any JWT-looking string" pattern
# avoids picking up one of the bundle's *other* embedded tokens (it also
# ships a per-storefront one, `kid` different, not accepted here).
_TOKEN_HEADER = (
    'eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IldlYlBsYXlLaWQifQ'
)
_TOKEN_RE = re.compile(
    re.escape(_TOKEN_HEADER) + r'\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'
)
_BUNDLE_SRC_RE = re.compile(r'src="(/assets/index~[^"]+\.js)"')

# (storefront, language tag) known to work for each Downtify UI locale -
# confirmed live against `GET /v1/storefronts/<id>` and by round-tripping
# an actual artist bio and checking the response `url` echoed `?l=<tag>`
# back (silent fallback otherwise). Not just the country's own top-level
# domain: e.g. Greek is served by the `gr` storefront, but Bulgarian
# genuinely isn't offered by Apple Music at all (`bg` storefront only
# supports `en-GB`) - no substitute exists, so it falls back to English.
_STOREFRONT_LANG: dict[str, tuple[str, str]] = {
    'en': ('us', 'en-US'),
    'pt-BR': ('br', 'pt-BR'),
    'es': ('es', 'es-ES'),
    'fr': ('fr', 'fr-FR'),
    'tr': ('tr', 'tr'),
    'hu': ('hu', 'hu'),
    'bg': ('bg', 'en-GB'),
    'el': ('gr', 'el'),
}
_DEFAULT_STOREFRONT_LANG = ('us', 'en-US')

_token_cache: dict[str, Any] = {'token': '', 'exp': 0.0}
_token_lock = Lock()


def _decode_jwt_exp(token: str) -> float:
    try:
        payload_b64 = token.split('.')[1]
        padded = payload_b64 + '=' * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        return float(payload.get('exp') or 0)
    except Exception:
        return 0.0


def _scrape_web_token() -> str:
    """Pull the current public "web play" developer token straight out
    of ``music.apple.com``'s own JS bundle - see module docstring."""

    resp = httpx.get(_BROWSE_URL, timeout=_TIMEOUT, follow_redirects=True)
    resp.raise_for_status()
    match = _BUNDLE_SRC_RE.search(resp.text)
    if not match:
        raise ValueError('Could not find Apple Music web bundle')
    bundle_url = 'https://music.apple.com' + match.group(1)

    bundle_resp = httpx.get(bundle_url, timeout=_BUNDLE_TIMEOUT)
    bundle_resp.raise_for_status()
    token_match = _TOKEN_RE.search(bundle_resp.text)
    if not token_match:
        raise ValueError('Could not find Apple Music web token in bundle')
    return token_match.group(0)


def _current_token() -> str:
    with _token_lock:
        if _token_cache['token'] and _token_cache['exp'] > time.time() + 60:
            return _token_cache['token']
    token = _scrape_web_token()
    with _token_lock:
        _token_cache['token'] = token
        _token_cache['exp'] = _decode_jwt_exp(token)
    return token


def _search_artist_row(name: str) -> Optional[dict[str, Any]]:
    """The full iTunes Search API row for an exact name match - ignoring
    case and the characters a file name can't hold, so ``ACDC`` matches
    ``AC/DC`` (see :func:`downtify.file_naming.file_name_key`) - or
    ``None`` when the search answered and nothing matches.

    Raises :class:`ValueError` when the search itself failed: that is not
    "no such artist", and a caller that saves what it finds must not treat
    it as one (see :func:`lookup_artist_id`).

    Deliberately strict, same reasoning as
    :func:`downtify.deezer.resolve_artist_id`: an unrelated top result
    would silently attach the wrong artist's bio/origin.
    """

    text = name.strip()
    wanted = file_name_key(text)
    if not wanted:
        return None
    try:
        resp = httpx.get(
            _SEARCH_URL,
            params={'term': text, 'entity': 'musicArtist', 'limit': 25},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get('results') or []
    except Exception as exc:
        logger.opt(exception=True).debug('Apple Music artist id lookup failed')
        raise ValueError('Could not reach Apple Music') from exc
    for row in results:
        if (
            isinstance(row, dict)
            and file_name_key(str(row.get('artistName') or '')) == wanted
        ):
            return row
    return None


def _resolve_artist_row(name: str) -> Optional[dict[str, Any]]:
    """:func:`_search_artist_row`, with a failed search reading as no match
    (``None``) - for the callers where that is good enough. Shared by
    :func:`resolve_artist_id` (numeric id) and :func:`resolve_artist_slug_id`
    (``slug/numeric-id``, for ``platforms_id``), so both reuse the one search
    call/match loop instead of each doing their own."""

    try:
        return _search_artist_row(name)
    except ValueError:
        return None


def resolve_artist_id(name: str) -> Optional[str]:
    """Apple Music's numeric artist id for an exact name match on the
    public iTunes Search API (see :func:`_resolve_artist_row`), or ``None``.
    """

    row = _resolve_artist_row(name)
    if row is None:
        return None
    artist_id = row.get('artistId')
    return str(artist_id) if artist_id is not None else None


def lookup_artist_id(name: str) -> Optional[str]:
    """Like :func:`resolve_artist_id`, but a failed search raises
    :class:`ValueError` instead of reading as ``None``: ``None`` here really
    means Apple Music has no artist by that name."""

    row = _search_artist_row(name)
    if row is None:
        return None
    artist_id = row.get('artistId')
    return str(artist_id) if artist_id is not None else None


_ARTIST_LINK_SLUG_RE = re.compile(r'/artist/([^/?]+/\d+)')


def resolve_artist_slug_id(name: str) -> Optional[str]:
    """*name*'s ``slug/numeric-id`` form (e.g. ``'paramore/75950796'``) -
    the shape ``platforms_id.applemusic`` actually needs (see
    :func:`downtify.artist_profile._default_profile`) - parsed straight
    out of the matched search result's own ``artistLinkUrl``, no extra
    request needed (unlike :func:`fetch_artist_full`, which needs a full
    catalog fetch just to read this off its own ``url`` field - worth
    paying for a bio fetch, not just to resolve an id).

    ``None`` if nothing matched, or the matched row's link isn't a
    ``music.apple.com`` artist page - the search API occasionally
    returns a same-named non-music result (an author, a book) even with
    ``entity=musicArtist``, confirmed live.
    """

    row = _resolve_artist_row(name)
    if row is None:
        return None
    link = str(row.get('artistLinkUrl') or '')
    if 'music.apple.com' not in link:
        return None
    match = _ARTIST_LINK_SLUG_RE.search(link)
    return match.group(1) if match else None


def fetch_artist_full(artist_id: str, lang: str) -> dict[str, Any]:
    """Bio, origin, formation year, genre and hero colour for an Apple Music
    artist id, localized to *lang* when a storefront supports it (see
    module docstring - falls back to that storefront's own default
    language rather than erroring). Raises :class:`ValueError` if the
    token can't be obtained or the request fails.
    """

    storefront, tag = _STOREFRONT_LANG.get(lang, _DEFAULT_STOREFRONT_LANG)
    try:
        token = _current_token()
        resp = httpx.get(
            _CATALOG_URL.format(storefront=storefront, artist_id=artist_id),
            params={
                'extend': 'artistBio,bornOrFormed,origin,isGroup,hero',
                'l': tag,
            },
            headers={
                'Authorization': f'Bearer {token}',
                'Origin': 'https://music.apple.com',
                'Referer': 'https://music.apple.com/',
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        logger.opt(exception=True).debug(
            'Apple Music artist fetch failed for {}', artist_id
        )
        raise ValueError(
            'Could not fetch artist info from Apple Music'
        ) from exc

    rows = payload.get('data') or []
    attrs = rows[0].get('attributes', {}) if rows else {}

    hero_bg = ''
    hero = attrs.get('hero') or []
    if hero:
        content = (hero[0] or {}).get('content') or []
        if content:
            hero_bg = str(
                (content[0] or {}).get('artwork', {}).get('bgColor') or ''
            )

    url_match = re.search(r'/artist/([^/?]+/\d+)', str(attrs.get('url') or ''))
    # Always a single entry in practice (checked live across a dozen
    # artists), localized by the storefront's language like the bio is
    # ('Hard rock' / 'Alternativo' in pt-BR, 'Alternative' in en).
    genres = [g for g in attrs.get('genreNames') or [] if isinstance(g, str)]

    return {
        'bio_html': str(attrs.get('artistBio') or ''),
        'origin': str(attrs.get('origin') or ''),
        'born_or_formed': str(attrs.get('bornOrFormed') or ''),
        'is_group': bool(attrs.get('isGroup')),
        'genre': genres[0].strip() if genres else '',
        'banner_bg_color': hero_bg,
        'applemusic_id': url_match.group(1) if url_match else '',
    }
