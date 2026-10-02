"""Which artist an album is filed and tagged under, and when an album is a
various-artists compilation.

A leaf module (it imports nothing from Downtify), like ``file_naming``, so
the Spotify, Deezer and YouTube Music scrapers and the downloader can share
the one rule.

The album artist is always the one the source declares for the album, never
something worked out from its tracks: a single-artist album with a guest on
one track ("Alice feat. Bob") still belongs to Alice, and a duo album has
the same two artists on every track without being a compilation. Only when
the source credits the album to "Various Artists" is it a compilation -
which media servers like Navidrome want marked on every track (``TCMP`` /
``COMPILATION`` / ``cpil``), or they break the album up by artist.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

VARIOUS_ARTISTS = 'Various Artists'

# The "Various Artists" entity on each service. Deezer localizes its name
# ("Vários intérpretes" for a Brazilian client), so its ids are what count
# there; Spotify only exposes its id on the playlist GraphQL path. The two
# id spaces can't collide (Deezer's are numeric, Spotify's base62).
_VARIOUS_ARTISTS_IDS = frozenset({
    '0LyfQWJT6nXafLPZqxe9Of',  # Spotify
    '5080',  # Deezer
    '108420982',  # Deezer, a second "Various Artists" entity
})

# Names a source may use for it, case-insensitive. Only the first is what
# Spotify and YouTube Music have been seen to send; the rest are the
# translations services use, in case one turns up.
_VARIOUS_ARTISTS_NAMES = frozenset({
    'various artists',
    'vários artistas',
    'varios artistas',
    'vários intérpretes',
    'varios intérpretes',
    'varios interpretes',
    'artistes divers',
    'artistes variés',
    'verschiedene interpreten',
    'artisti vari',
    'artisti varie',
})


def is_various_artists(name: Any, *, artist_id: Any = '') -> bool:
    """Whether *name* (or *artist_id*, a Spotify or Deezer artist id) is
    the "Various Artists" placeholder rather than a real artist."""

    if str(artist_id or '').strip() in _VARIOUS_ARTISTS_IDS:
        return True
    text = ' '.join(str(name or '').split()).casefold()
    if text not in _VARIOUS_ARTISTS_NAMES:
        return False
    if text != VARIOUS_ARTISTS.casefold():
        logger.info('Treating album artist {!r} as Various Artists', name)
    return True


def filing_artist(song: dict[str, Any]) -> str:
    """The artist a downloaded *song* is filed under ("Organize by artist")
    and whose profile it seeds: its album artist, so every track of an
    album lands together - except for a various-artists compilation, whose
    tracks go to their own first artist instead of a "Various Artists"
    folder (the tags still say "Various Artists", which is what keeps the
    album whole in a media server). ``''`` when there is no artist."""

    album_artist = str(song.get('album_artist') or '').strip()
    if (
        album_artist
        and not song.get('compilation')
        and not is_various_artists(album_artist)
    ):
        return album_artist
    artists = song.get('artists') or []
    return str(artists[0]).strip() if artists else ''


def album_artist_fields(name: Any, *, artist_id: Any = '') -> dict[str, Any]:
    """The song fields for an album credited to *name*: ``album_artist``,
    plus ``compilation: True`` (and the canonical "Various Artists") when
    it is a various-artists compilation. Empty when *name* is blank, so
    the caller falls back to the track's first artist."""

    if is_various_artists(name, artist_id=artist_id):
        return {'album_artist': VARIOUS_ARTISTS, 'compilation': True}
    text = str(name or '').strip()
    return {'album_artist': text} if text else {}
