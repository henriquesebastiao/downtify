"""Telling playlists apart: the same playlist under its Spotify name, its
M3U file name and the Navidrome playlists made from either.

A leaf module (no Downtify imports) so both :mod:`downtify.navidrome`
and :mod:`downtify.doctor` can use it.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

#: Playlists Downtify creates in Navidrome carry this comment.
DOWNTIFY_COMMENT = 'Synced from Spotify via Downtify'
#: Navidrome's comment on a playlist it imported from an M3U file.
_IMPORTED_COMMENT = re.compile(r"^Auto-imported from '(?P<file>.+)'$")


def playlist_key(name: str) -> str:
    """A playlist name with case, accents, punctuation and the
    characters a filename can't hold folded away - ``Chill: Vibes`` and
    the ``Chill Vibes.m3u`` written for it compare equal."""

    text = unicodedata.normalize('NFKD', str(name or ''))
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = ''.join(ch if ch.isalnum() else ' ' for ch in text.casefold())
    return ' '.join(text.split())


def made_by_downtify(playlist: dict[str, Any]) -> bool:
    """A Navidrome playlist Downtify created through the API."""

    return str(playlist.get('comment') or '') == DOWNTIFY_COMMENT


def imported_from(playlist: dict[str, Any]) -> str:
    """The M3U a Navidrome playlist was imported from ('' when none):
    the native API's ``path``, else the file named in its comment."""

    path = str(playlist.get('path') or '').strip().replace('\\', '/')
    if playlist.get('sync') or path:
        return path
    match = _IMPORTED_COMMENT.match(str(playlist.get('comment') or ''))
    return match.group('file') if match else ''
