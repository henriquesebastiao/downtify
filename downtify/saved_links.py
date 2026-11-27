"""Playlist and album links an account keeps to stream (issue #731).

Pasting a Spotify, Deezer or YouTube Music playlist or album link opens
the link page: songs already in the library play from it, the rest
stream through the server. Saving the link keeps that page one click
away, in its own section of Library > Playlists. It is a bookmark and
nothing more: nothing is downloaded, no M3U or Navidrome playlist is
written, and the playlist catalog never hears of it. Opening it reads
the link again, so it always shows the playlist as it is now.

Each account has its own list, private like favorite playlists, and
deleting the account deletes it (:meth:`SavedLinks.remove_user`).

A link is stored under its canonical URL (:func:`saved_link_target`),
rebuilt from the service, the kind and the id the app's own link
parsers read off it - so the same playlist pasted with a ``?si=``
tracking parameter, a locale segment or another host is saved once,
and nothing but those three URL shapes is ever stored or rendered.

Stored in ``downtify_library.db`` (``saved_links``), or in PostgreSQL
when the server uses it (migration ``0008_saved_links``).
"""

from __future__ import annotations

import re
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlsplit

from . import deezer, providers, spotify
from .db.config import Dialect
from .db.core import Connection, Database, as_database
from .db.dialect import insertion_order_col

SOURCE_SPOTIFY = 'spotify'
SOURCE_YOUTUBE = 'youtube'
SOURCE_DEEZER = 'deezer'

#: What can be saved: the link kinds whose page lists songs to stream.
KINDS = frozenset({'playlist', 'album'})

#: Saved links one account may keep.
MAX_SAVED_LINKS = 500
#: Longest name kept (longer ones are cut, they come from the service).
MAX_NAME_LENGTH = 200
#: Longest cover URL kept (a longer one is dropped).
MAX_COVER_LENGTH = 2048
#: Longest link read at all.
MAX_URL_LENGTH = 2048

# Ids as the services write them; also keeps a ``spotify:`` URI, whose id
# the Spotify parser doesn't check, from smuggling anything in.
_ID = re.compile(r'^[A-Za-z0-9_-]{1,128}$')

# The link parsers, in the order ``GET /api/url/resolve`` tries them.
_PARSERS = (
    (SOURCE_SPOTIFY, spotify.parse_spotify_url),
    (SOURCE_YOUTUBE, providers.parse_youtube_url),
    (SOURCE_DEEZER, deezer.parse_deezer_url),
)


class SavedLinksFull(Exception):
    """The account already keeps :data:`MAX_SAVED_LINKS` links."""


@dataclass(frozen=True)
class LinkTarget:
    """What a saved link points at, and the URL it is stored under."""

    source: str
    kind: str
    id: str
    url: str


def _canonical_url(source: str, kind: str, item_id: str) -> str:
    if source == SOURCE_SPOTIFY:
        return f'https://open.spotify.com/{kind}/{item_id}'
    if source == SOURCE_DEEZER:
        return f'https://www.deezer.com/{kind}/{item_id}'
    # YouTube Music: an album is either a browse id or the audio
    # playlist (``OLAK5uy_``) behind it; both open the album page.
    if kind == 'album' and item_id.startswith('MPREb_'):
        return f'https://music.youtube.com/browse/{item_id}'
    return f'https://music.youtube.com/playlist?list={item_id}'


def saved_link_target(url: Any) -> Optional[LinkTarget]:
    """The playlist or album *url* points at, or ``None`` when it isn't a
    Spotify, Deezer or YouTube Music playlist or album link.

    Reads the link with the same parsers, in the same order, as
    ``GET /api/url/resolve`` (what the link page shows).
    """

    text = str(url or '').strip()
    if not text or len(text) > MAX_URL_LENGTH:
        return None
    for source, parse in _PARSERS:
        parsed = parse(text)
        if parsed:
            break
    else:
        return None
    kind, item_id = parsed
    if kind not in KINDS or not _ID.match(item_id or ''):
        return None
    return LinkTarget(
        source, kind, item_id, _canonical_url(source, kind, item_id)
    )


def clean_name(name: Any) -> str:
    """*name* on one line, cut to :data:`MAX_NAME_LENGTH` characters."""

    return ' '.join(str(name or '').split())[:MAX_NAME_LENGTH].strip()


def clean_cover(cover: Any) -> str:
    """*cover* when it is an ``https`` image URL the page may show, else
    ``''``: no other scheme (``javascript:``, ``data:``, plain ``http``)
    is ever stored, so none is ever rendered."""

    text = str(cover or '').strip()
    if not text or len(text) > MAX_COVER_LENGTH:
        return ''
    if any(ch.isspace() or ord(ch) < 32 for ch in text):
        return ''
    try:
        parts = urlsplit(text)
    except ValueError:
        return ''
    if parts.scheme != 'https' or not parts.hostname:
        return ''
    return text


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _link(row: Any) -> dict[str, Any]:
    return {
        'url': str(row['url']),
        'source': str(row['source']),
        'kind': str(row['kind']),
        'name': str(row['name'] or ''),
        'cover': str(row['cover'] or ''),
        'saved_at': str(row['saved_at']),
    }


class SavedLinks:
    """``saved_links`` rows: each account's saved links, newest first."""

    def __init__(self, path_or_db: str | Path | Database) -> None:
        self.db = as_database(path_or_db, 'library')
        self._init_db()

    def _connect(self) -> AbstractContextManager[Connection]:
        return self.db.connect()

    def _init_db(self) -> None:
        # On PostgreSQL the 0008 migration already created the table,
        # with an ``id`` column standing in for SQLite's ``rowid``.
        if self.db.dialect is not Dialect.SQLITE:
            return
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saved_links (
                    user_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    name TEXT NOT NULL DEFAULT '',
                    cover TEXT NOT NULL DEFAULT '',
                    saved_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, url)
                )
            """)

    def list(self, user_id: int) -> list[dict[str, Any]]:
        """*user_id*'s saved links, the most recently saved first."""

        with self._connect() as conn:
            order = insertion_order_col(conn.dialect)
            rows = conn.execute(
                'SELECT url, source, kind, name, cover, saved_at '
                'FROM saved_links WHERE user_id = ? '
                f'ORDER BY saved_at DESC, {order} DESC',
                (int(user_id),),
            ).fetchall()
        return [_link(row) for row in rows]

    def get(self, user_id: int, url: str) -> Optional[dict[str, Any]]:
        """The saved link stored under the canonical *url*, if any."""

        with self._connect() as conn:
            row = conn.execute(
                'SELECT url, source, kind, name, cover, saved_at '
                'FROM saved_links WHERE user_id = ? AND url = ?',
                (int(user_id), str(url)),
            ).fetchone()
        return _link(row) if row else None

    def save(
        self, user_id: int, target: LinkTarget, name: Any, cover: Any = ''
    ) -> dict[str, Any]:
        """Save *target* for *user_id*, or refresh the name and cover of
        the link already saved (it keeps its place in the list, so a
        second tap never moves it). Raises :class:`SavedLinksFull` for a
        new link once the account keeps :data:`MAX_SAVED_LINKS`."""

        if not user_id:
            raise ValueError('A user is required')
        with self.db.transaction(lock=True) as conn:
            have = conn.execute(
                'SELECT 1 FROM saved_links WHERE user_id = ? AND url = ?',
                (int(user_id), target.url),
            ).fetchone()
            if have is None:
                count = conn.execute(
                    'SELECT COUNT(*) FROM saved_links WHERE user_id = ?',
                    (int(user_id),),
                ).fetchone()[0]
                if int(count) >= MAX_SAVED_LINKS:
                    raise SavedLinksFull(
                        f'You can keep up to {MAX_SAVED_LINKS} saved '
                        'links. Remove one first.'
                    )
            conn.execute(
                'INSERT INTO saved_links '
                '(user_id, url, source, kind, name, cover, saved_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?) '
                'ON CONFLICT (user_id, url) DO UPDATE SET '
                'name = excluded.name, cover = excluded.cover',
                (
                    int(user_id),
                    target.url,
                    target.source,
                    target.kind,
                    clean_name(name),
                    clean_cover(cover),
                    _now(),
                ),
            )
            row = conn.execute(
                'SELECT url, source, kind, name, cover, saved_at '
                'FROM saved_links WHERE user_id = ? AND url = ?',
                (int(user_id), target.url),
            ).fetchone()
        return _link(row)

    def remove(self, user_id: int, url: str) -> bool:
        """Forget *user_id*'s link saved under *url*; whether there was
        one."""

        with self._connect() as conn:
            gone = conn.execute(
                'DELETE FROM saved_links WHERE user_id = ? AND url = ?',
                (int(user_id), str(url)),
            ).rowcount
        return bool(gone)

    def remove_user(self, user_id: int) -> None:
        """A deleted account's saved links."""

        with self._connect() as conn:
            conn.execute(
                'DELETE FROM saved_links WHERE user_id = ?', (int(user_id),)
            )
