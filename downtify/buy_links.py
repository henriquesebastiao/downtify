"""Where to buy a song, an album or an artist's music.

Downtify downloads from YouTube; someone who likes what they found may
want to pay for it, so the artist is supported directly. For a song (or
an album, or an artist) this lists, in order:

* the **iTunes Store** item itself, with its price, in the listener's
  store - looked up with the public iTunes Search API (see
  :func:`downtify.itunes.store_match`); when nothing there clearly is it,
  a search on Apple Music instead;
* a search on **Bandcamp**, where most of the money goes to the artist,
  and on **Qobuz**, which sells lossless downloads - neither has a public
  lookup, so a search is the honest link;
* the artist's own **website**, when their saved profile has one (see
  :mod:`downtify.artist_profile`).

Nothing is bought, opened or tracked here: these are plain links, and the
only request made is the iTunes lookup.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Optional
from urllib.parse import quote, quote_plus

from loguru import logger

from . import itunes

KIND_TRACK = 'track'
KIND_ALBUM = 'album'
KIND_ARTIST = 'artist'

DEFAULT_COUNTRY = 'US'
_COUNTRY = re.compile(r'^[A-Za-z]{2}$')

# What each store calls the kind of item in its search.
_BANDCAMP_TYPES = {KIND_TRACK: 't', KIND_ALBUM: 'a', KIND_ARTIST: 'b'}
_QOBUZ_TYPES = {
    KIND_TRACK: 'tracks',
    KIND_ALBUM: 'albums',
    KIND_ARTIST: 'artists',
}

StoreLookup = Callable[..., Optional[dict[str, Any]]]


def normalize_country(value: Any) -> str:
    """A two-letter store country, upper-case; the US store otherwise."""

    text = str(value or '').strip()
    return text.upper() if _COUNTRY.fullmatch(text) else DEFAULT_COUNTRY


def website_url(raw: Any) -> str:
    """An artist's website as a link: http(s) as it is, a bare domain made
    https, anything else (another scheme, nothing) ``''``."""

    text = str(raw or '').strip()
    if not text or any(ch.isspace() for ch in text):
        return ''
    if re.match(r'^https?://', text, re.IGNORECASE):
        return text
    if re.match(r'^[a-z][a-z0-9+.-]*:', text, re.IGNORECASE):
        return ''
    return f'https://{text}'


def kind_of(title: str, album: str) -> str:
    """What is being bought: a song when there is a title, else an album
    when there is one, else everything by the artist."""

    if title:
        return KIND_TRACK
    return KIND_ALBUM if album else KIND_ARTIST


def buy_links(
    artist: str,
    title: str = '',
    album: str = '',
    *,
    country: str = DEFAULT_COUNTRY,
    website: str = '',
    lookup: StoreLookup = itunes.store_match,
) -> dict[str, Any]:
    """``{kind, query, links}`` for a song, album or artist - each link
    ``{store, label, url, match, price, currency}``. ``match`` says the
    link opens the item itself (``False``: a search for it); ``price`` is
    set only on an iTunes Store item sold on its own."""

    artist = str(artist or '').strip()
    title = str(title or '').strip()
    album = str(album or '').strip()
    kind = kind_of(title, album)
    country = normalize_country(country)
    query = ' '.join(
        part
        for part in (artist, {KIND_TRACK: title, KIND_ALBUM: album}.get(kind))
        if part
    )
    links = [
        _itunes_link(kind, artist, title, album, country, query, lookup),
        _link(
            'bandcamp',
            'Bandcamp',
            'https://bandcamp.com/search?q='
            f'{quote_plus(query)}&item_type={_BANDCAMP_TYPES[kind]}',
        ),
        _link(
            'qobuz',
            'Qobuz',
            'https://www.qobuz.com/us-en/search/'
            f'{_QOBUZ_TYPES[kind]}/{quote(query, safe="")}',
        ),
    ]
    site = website_url(website)
    if site:
        links.append(_link('website', 'Official website', site, match=True))
    return {'kind': kind, 'query': query, 'links': links}


def _link(
    store: str,
    label: str,
    url: str,
    *,
    match: bool = False,
    price: Optional[float] = None,
    currency: str = '',
) -> dict[str, Any]:
    return {
        'store': store,
        'label': label,
        'url': url,
        'match': match,
        'price': price,
        'currency': currency,
    }


def _itunes_link(
    kind: str,
    artist: str,
    title: str,
    album: str,
    country: str,
    query: str,
    lookup: StoreLookup,
) -> dict[str, Any]:
    found = None
    if artist:
        try:
            found = lookup(kind, artist, title, album, country)
        except Exception:
            logger.opt(exception=True).debug(
                'iTunes Store lookup failed for {!r}', query
            )
    if found:
        return _link(
            'itunes',
            'iTunes Store',
            found['url'],
            match=True,
            price=found.get('price'),
            currency=str(found.get('currency') or ''),
        )
    return _link(
        'itunes',
        'iTunes Store',
        f'https://music.apple.com/{country.lower()}/search?term='
        f'{quote_plus(query)}',
    )
