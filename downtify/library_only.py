"""Library-only policy and deterministic recommendations, without providers."""

from __future__ import annotations

import threading
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import quote

from fastapi import HTTPException

from .library_sync import grouping_keys, split_artists

DETAIL = 'Library-only mode is enabled. Only library music is available.'

# These endpoints have local answers in api.py when the policy is enabled.
LOCAL_ROUTES = {
    '/api/songs/search',
    '/api/albums/search',
    '/api/artists/search',
    '/api/finder/search',
    '/api/similar/tracks',
    '/api/discover/chart',
    '/api/discover',
    '/api/discover/collections',
    '/api/discover/collections/deezer',
    '/api/discover/collections/spotify',
}
REMOTE_PREFIXES = (
    '/api/download/',
    '/api/stream',
    '/api/preview',
    '/api/url',
    '/api/song/url',
    '/api/finder/',
    '/api/artists/top_',
    '/api/artists/info',
    '/api/artists/similar',
    '/api/artists/photo-proxy',
    '/api/artists/art/search',
    '/api/artists/art/spotify_candidate',
    '/api/artists/art/from_url',
    '/api/artists/profile/ensure',
    '/api/artists/profile/bio/preview',
    '/api/library/replace',
    '/api/playlists/incomplete',
    '/api/playlists/batches/',
)
REMOTE_ACTIONS = {
    '/api/artists/profile/bio',
    '/api/podcasts/search',
    '/api/podcasts/resolve',
    '/api/podcasts/subscribe',
    '/api/library/upgrade/scan',
    '/api/library/upgrade/start',
    '/api/library/upgrade/resume',
    '/api/deemix/test',
    '/api/slskd/test',
}


def enabled(settings: dict[str, Any]) -> bool:
    """Only a saved JSON boolean enables the policy."""
    return settings.get('library_only') is True


def remote_route(path: str, method: str) -> bool:
    """Whether a web route can resolve, fetch or suggest external music."""
    return (
        path in LOCAL_ROUTES
        or path.startswith(REMOTE_PREFIXES)
        or (path in REMOTE_ACTIONS and method not in {'DELETE', 'PUT'})
        or (path.startswith('/api/monitor') and method in {'POST', 'PATCH'})
        or (path.startswith('/api/podcasts/') and path.endswith('/download'))
    )


class Policy:
    """Serialize activation with admission of external work, never cancel it."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._active = 0

    @contextmanager
    def external(self, settings: dict[str, Any]) -> Iterator[None]:
        with self._lock:
            if enabled(settings):
                raise HTTPException(status_code=409, detail=DETAIL)
            self._active += 1
        try:
            yield
        finally:
            with self._lock:
                self._active -= 1

    def set_enabled(self, settings: dict[str, Any], value: Any) -> None:
        """Reject invalid or busy transitions before modifying any setting."""
        if not isinstance(value, bool):
            raise HTTPException(
                status_code=400, detail='library_only must be a boolean'
            )
        with self._lock:
            if value and not enabled(settings) and self._active:
                raise HTTPException(
                    status_code=409,
                    detail='External music operations are active. Wait for them to finish before enabling library-only mode.',
                )
            settings['library_only'] = value


policy = Policy()


def text(value: Any) -> str:
    """Accent-insensitive text shared by local search and similarity."""
    return ''.join(
        c
        for c in unicodedata.normalize('NFKD', str(value or '').casefold())
        if not unicodedata.combining(c)
    ).strip()


def song(entry: dict[str, Any]) -> dict[str, Any]:
    """A search row with a local identity; no provider URL or preview."""
    file = str(entry.get('file') or '')
    return {
        'song_id': 'library:' + file,
        'name': str(entry.get('title') or ''),
        'artists': [
            a.strip()
            for a in str(entry.get('artist') or '').split(';')
            if a.strip()
        ],
        'artist': str(entry.get('artist') or ''),
        'album_name': str(entry.get('album') or ''),
        'duration': entry.get('duration') or 0,
        'explicit': bool(entry.get('explicit')),
        'has_cover': bool(entry.get('has_cover')),
        'file': file,
        'url': '',
        'cover_url': '/cover?file=' + quote(file, safe=''),
        'source': 'library',
    }


def search(
    entries: list[dict[str, Any]], query: str, limit: int = 20
) -> list[dict[str, Any]]:
    """All query words must occur in the local tags; stable ordering."""
    words = text(query).split()
    if not words:
        return []
    matches = [
        e
        for e in entries
        if all(
            w
            in text(
                ' '.join(
                    str(e.get(k) or '') for k in ('title', 'artist', 'album')
                )
            )
            for w in words
        )
    ]
    matches.sort(key=lambda e: (text(e.get('title')), str(e.get('file'))))
    return [song(e) for e in matches[:limit]]


def artist_keys(entry: dict[str, Any]) -> set[str]:
    return {
        text(a)
        for a in split_artists(str(entry.get('artist') or ''))
        if text(a)
    }


def similarity_score(entry: dict[str, Any], seed: dict[str, Any]) -> int:
    shared_artist = bool(artist_keys(entry) & artist_keys(seed))
    same_album_artist = bool(
        text(entry.get('album_artist'))
        and text(entry.get('album_artist')) == text(seed.get('album_artist'))
    )
    same_album = bool(
        text(entry.get('album'))
        and text(entry.get('album')) == text(seed.get('album'))
        and (shared_artist or same_album_artist)
    )
    shared_genre = bool(
        text(entry.get('genre'))
        and text(entry.get('genre')) == text(seed.get('genre'))
    )
    return 4 * shared_artist + 2 * same_album + shared_genre


def similar(
    entries: list[dict[str, Any]], artist: str, track: str, limit: int
) -> dict[str, Any]:
    """Rank saved tags, never fetch radio; unknown seeds have no suggestions."""
    a, t = text(artist), text(track)
    seeds = (
        [
            e
            for e in entries
            if (not a or a == text(e.get('artist')) or a in artist_keys(e))
            and (not t or t == text(e.get('title')))
        ]
        if a or t
        else []
    )
    ranked = []
    for entry in entries:
        if entry in seeds:
            continue
        score = max(
            (similarity_score(entry, seed) for seed in seeds), default=0
        )
        if score:
            ranked.append((score, entry))
    ranked.sort(
        key=lambda pair: (
            -pair[0],
            text(pair[1].get('title')),
            str(pair[1].get('file')),
        )
    )
    seen = set()
    tracks = []
    for score, entry in ranked:
        identity = (text(entry.get('artist')), text(entry.get('title')))
        if identity not in seen:
            tracks.append({**song(entry), 'match': score})
            seen.add(identity)
        if len(tracks) >= limit:
            break
    return {
        'artist': artist,
        'track': track,
        'source': 'library',
        'tracks': tracks,
    }


def catalog(
    entries: list[dict[str, Any]], query: str = '', limit: int = 25
) -> dict[str, Any]:
    """The existing search/card shapes, populated only from visible files."""
    album_groups: dict[str, list[dict[str, Any]]] = {}
    artist_groups: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        keys = grouping_keys(entry)
        if keys['album_artist']:
            artist_groups.setdefault(keys['artist_id'], []).append(entry)
        if entry.get('album'):
            album_groups.setdefault(keys['album_id'], []).append(entry)

    def matches(label: str) -> bool:
        return all(word in text(label) for word in text(query).split())

    artists = []
    for identity, group in artist_groups.items():
        name = grouping_keys(group[0])['album_artist']
        if matches(name):
            artists.append({
                'artist_id': 'library:' + identity,
                'name': name,
                'artist': name,
                'cover_url': song(group[0])['cover_url'],
                'picture_url': song(group[0])['cover_url'],
                'source': 'library',
                'kind': 'artist',
                'url': name,
                'track_count': len(group),
                'because': [],
            })
    albums = []
    for identity, group in album_groups.items():
        first = group[0]
        artist = grouping_keys(first)['album_artist']
        name = str(first.get('album') or '')
        if matches(artist + ' ' + name):
            albums.append({
                'album_id': 'library:' + identity,
                'name': name,
                'artist': artist,
                'cover_url': song(first)['cover_url'],
                'year': str(first.get('year') or ''),
                'source': 'library',
                'kind': 'album',
                'url': artist + ' ' + name,
                'track_count': len(group),
                'release_type': 'Album',
                'reason': 'more_from',
                'because': [],
            })
    artists.sort(key=lambda row: text(row['name']))
    albums.sort(key=lambda row: (text(row['artist']), text(row['name'])))
    return {
        'source': 'library',
        'tracks': search(entries, query, limit)
        if query.strip()
        else [song(e) for e in entries[:limit]],
        'artists': artists[:limit],
        'albums': albums[:limit],
        'playlists': [],
    }


def playlist_rows(
    playlists: list[dict[str, Any]], limit: int = 25
) -> list[dict[str, Any]]:
    """Keep each accessible playlist's real identity and display name."""
    result = [
        {
            'playlist_id': 'library:' + p['name'],
            'playlist_name': p['name'],
            'name': p.get('display_name') or p['name'],
            'owner': p.get('owner', ''),
            'source': 'library',
            'kind': 'playlist',
            'url': p.get('display_name') or p['name'],
            'cover_url': '/playlist-cover?file='
            + quote(str(p['cover']), safe='')
            if p.get('cover')
            else '',
            'track_count': p.get('count', 0),
            'favorite': bool(p.get('favorite')),
            'artist': '',
            'because': [],
        }
        for p in playlists
    ]
    result.sort(key=lambda row: (not row['favorite'], text(row['name'])))
    return result[:limit]
