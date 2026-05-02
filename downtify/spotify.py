"""Resolve Spotify URLs without using the official Spotify Web API.

Reads the public ``open.spotify.com/embed`` pages, which expose the same
data the Spotify embedded player consumes. No client credentials, no
authentication and no premium account are required.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

import requests
from loguru import logger

SPOTIFY_URL_RE = re.compile(
    r'(?:https?://)?(?:open\.)?spotify\.com/'
    r'(?:intl-[a-z]{2}/)?'
    r'(?P<type>track|album|playlist|artist|episode|show)/'
    r'(?P<id>[A-Za-z0-9]+)'
)

_USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)


def parse_spotify_url(url: str) -> Optional[tuple[str, str]]:
    """Return ``(type, id)`` for a Spotify URL/URI or ``None`` if not one."""

    if not url:
        return None
    if url.startswith('spotify:'):
        try:
            _, kind, sid = url.split(':', 2)
        except ValueError:
            return None
        return kind, sid
    match = SPOTIFY_URL_RE.search(url)
    if not match:
        return None
    return match.group('type'), match.group('id')


def _fetch_embed_json(kind: str, spotify_id: str) -> dict[str, Any]:
    url = f'https://open.spotify.com/embed/{kind}/{spotify_id}'
    response = requests.get(
        url,
        headers={
            'User-Agent': _USER_AGENT,
            'Accept-Language': 'en-US,en;q=0.9',
        },
        timeout=15,
    )
    response.raise_for_status()
    match = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        response.text,
        re.DOTALL,
    )
    if not match:
        raise ValueError('Spotify embed payload not found')
    return json.loads(match.group(1))


def _entity_from(payload: dict[str, Any]) -> dict[str, Any]:
    page_props = payload.get('props', {}).get('pageProps', {}) or {}
    candidates: list[Any] = [
        page_props.get('state', {}).get('data', {}).get('entity')
        if isinstance(page_props.get('state'), dict)
        else None,
        page_props.get('entity'),
        page_props.get('data', {}).get('entity')
        if isinstance(page_props.get('data'), dict)
        else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate
    raise ValueError('Spotify entity not found in embed payload')


def _largest_image(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return ''
    sized = [s for s in sources if isinstance(s, dict) and s.get('url')]
    if not sized:
        return ''
    sized.sort(key=lambda s: int(s.get('width') or 0), reverse=True)
    return sized[0]['url']


def _cover_url(entity: dict[str, Any]) -> str:
    candidates: list[dict[str, Any]] = []
    cover_art = entity.get('coverArt') or {}
    if isinstance(cover_art, dict):
        candidates += cover_art.get('sources') or []
    visual = entity.get('visualIdentity') or {}
    if isinstance(visual, dict):
        candidates += visual.get('image') or []
    album = entity.get('album') or {}
    if isinstance(album, dict):
        nested = album.get('coverArt') or {}
        if isinstance(nested, dict):
            candidates += nested.get('sources') or []
        images = album.get('images')
        if isinstance(images, list):
            candidates += images
    return _largest_image(candidates)


def _artist_names(entity: dict[str, Any]) -> list[str]:
    raw = entity.get('artists') or []
    if not isinstance(raw, list):
        return []
    names: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            name = item.get('name')
            if name:
                names.append(name)
    return names


def _release_year(entity: dict[str, Any]) -> str:
    release = entity.get('releaseDate')
    if isinstance(release, dict):
        iso = release.get('isoString') or ''
        return iso[:4]
    if isinstance(release, str):
        return release[:4]
    album = entity.get('album') or {}
    if isinstance(album, dict):
        rel = album.get('releaseDate')
        if isinstance(rel, dict):
            return (rel.get('isoString') or '')[:4]
        if isinstance(rel, str):
            return rel[:4]
    return ''


def _track_dict(
    entity: dict[str, Any],
    *,
    track_id: str,
    fallback_album: str = '',
    fallback_cover: str = '',
) -> dict[str, Any]:
    duration_ms = entity.get('duration') or entity.get('duration_ms') or 0
    album = entity.get('album') or {}
    album_name = album.get('name', '') if isinstance(album, dict) else ''
    cover = _cover_url(entity) or fallback_cover
    return {
        'song_id': track_id,
        'name': entity.get('name') or entity.get('title') or '',
        'artists': _artist_names(entity),
        'album_name': album_name or fallback_album,
        'cover_url': cover,
        'duration': int(int(duration_ms) / 1000) if duration_ms else 0,
        'url': f'https://open.spotify.com/track/{track_id}'
        if track_id
        else '',
        'explicit': bool(entity.get('isExplicit') or entity.get('explicit')),
        'year': _release_year(entity),
        'source': 'spotify',
    }


def track_from_id(track_id: str) -> dict[str, Any]:
    payload = _fetch_embed_json('track', track_id)
    entity = _entity_from(payload)
    return _track_dict(entity, track_id=track_id)


def album_tracks_from_id(album_id: str) -> list[dict[str, Any]]:
    payload = _fetch_embed_json('album', album_id)
    entity = _entity_from(payload)
    album_name = entity.get('name') or ''
    cover = _cover_url(entity)
    track_items = (
        entity.get('trackList')
        or (entity.get('tracks') or {}).get('items')
        or []
    )
    songs: list[dict[str, Any]] = []
    for item in track_items:
        if not isinstance(item, dict):
            continue
        track = item.get('track', item)
        if not isinstance(track, dict):
            continue
        track_id = track.get('id') or _id_from_uri(track.get('uri', ''))
        if not track_id:
            continue
        if not track.get('artists'):
            track['artists'] = entity.get('artists') or []
        songs.append(
            _track_dict(
                track,
                track_id=track_id,
                fallback_album=album_name,
                fallback_cover=cover,
            )
        )
    return songs


def _parse_playlist_tracks(entity: dict[str, Any]) -> list[dict[str, Any]]:
    fallback_cover = _cover_url(entity)
    track_items = entity.get('trackList') or []
    songs: list[dict[str, Any]] = []
    for item in track_items:
        if not isinstance(item, dict):
            continue
        track = item.get('track', item)
        if not isinstance(track, dict):
            continue
        track_id = track.get('id') or _id_from_uri(track.get('uri', ''))
        if not track_id:
            continue
        # Playlist embed exposes artists as a "subtitle" string ("A, B")
        # rather than the structured `artists` list other endpoints return.
        if not track.get('artists'):
            track['artists'] = _artists_from_subtitle(track.get('subtitle'))
        songs.append(
            _track_dict(
                track, track_id=track_id, fallback_cover=fallback_cover
            )
        )
    return songs


def _artists_from_subtitle(subtitle: Any) -> list[dict[str, str]]:
    if not isinstance(subtitle, str) or not subtitle:
        return []
    return [
        {'name': name.strip()}
        for name in subtitle.replace('\xa0', ' ').split(',')
        if name.strip()
    ]


def _token_from_embed_payload(payload: dict[str, Any]) -> Optional[str]:
    """Extract the Spotify access token baked into the NEXT_DATA server state."""
    try:
        return payload['props']['pageProps']['state']['settings']['session'][
            'accessToken'
        ]
    except (KeyError, TypeError):
        return None


_PARTNER_API = 'https://api-partner.spotify.com/pathfinder/v1/query'
# sha256 of the fetchPlaylist GraphQL document in the Spotify web player.
# Update when the player bundle rolls and the API returns PersistedQueryNotFound.
# Location in the bundle: new tz.l("fetchPlaylist","query","<hash>",null)
_GRAPHQL_HASH = (
    'a65e12194ed5fc443a1cdebed5fabe33ca5b07b987185d63c72483867ad13cb4'
)


def _track_dict_from_graphql_item(
    item: dict[str, Any],
) -> Optional[dict[str, Any]]:
    iv2 = item.get('itemV2') or {}
    if iv2.get('__typename') != 'TrackResponseWrapper':
        return None
    track = iv2.get('data') or {}
    if not isinstance(track, dict):
        return None
    track_id = _id_from_uri(track.get('uri') or '')
    if not track_id:
        return None
    artists = [
        a['profile']['name']
        for a in (track.get('artists') or {}).get('items', [])
        if isinstance(a, dict)
        and isinstance(a.get('profile'), dict)
        and a['profile'].get('name')
    ]
    album = track.get('albumOfTrack') or {}
    album_name = album.get('name', '') if isinstance(album, dict) else ''
    cover_sources = (album.get('coverArt') or {}).get('sources') or []
    cover_url = _largest_image(cover_sources)
    duration_ms = (track.get('trackDuration') or {}).get(
        'totalMilliseconds'
    ) or 0
    label = (track.get('contentRating') or {}).get('label') or ''
    return {
        'song_id': track_id,
        'name': track.get('name') or '',
        'artists': artists,
        'album_name': album_name,
        'cover_url': cover_url,
        'duration': int(duration_ms / 1000) if duration_ms else 0,
        'url': f'https://open.spotify.com/track/{track_id}',
        'explicit': label.upper() == 'EXPLICIT',
        'year': '',
        'source': 'spotify',
    }


def _graphql_fetch_page(
    playlist_id: str, token: str, offset: int, limit: int = 100
) -> dict[str, Any]:
    resp = requests.get(
        _PARTNER_API,
        params={
            'operationName': 'fetchPlaylist',
            'variables': json.dumps({
                'uri': f'spotify:playlist:{playlist_id}',
                'offset': offset,
                'limit': limit,
                'enableWatchFeedEntrypoint': False,
                'includeEpisodeContentRatingsV2': False,
            }),
            'extensions': json.dumps({
                'persistedQuery': {
                    'version': 1,
                    'sha256Hash': _GRAPHQL_HASH,
                }
            }),
        },
        headers={
            'Authorization': f'Bearer {token}',
            'User-Agent': _USER_AGENT,
            'app-platform': 'WebPlayer',
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if 'errors' in data:
        raise ValueError(f'GraphQL errors: {data["errors"]}')
    return data['data']['playlistV2']


def _graphql_all_tracks(
    playlist_id: str, token: str
) -> tuple[Optional[str], list[dict[str, Any]]]:
    """Return ``(playlist_name_or_None, all_tracks)`` via partner GraphQL."""
    songs: list[dict[str, Any]] = []
    playlist_name: Optional[str] = None
    offset = 0
    limit = 100
    while True:
        pv2 = _graphql_fetch_page(playlist_id, token, offset, limit)
        if playlist_name is None:
            playlist_name = pv2.get('name') or None
        content = pv2.get('content') or {}
        items = content.get('items') or []
        for item in items:
            td = _track_dict_from_graphql_item(item)
            if td:
                songs.append(td)
        total = content.get('totalCount') or 0
        offset += len(items)
        if not items or offset >= total:
            break
    return playlist_name, songs


def playlist_tracks_from_id(playlist_id: str) -> list[dict[str, Any]]:
    payload = _fetch_embed_json('playlist', playlist_id)
    entity = _entity_from(payload)
    token = _token_from_embed_payload(payload)
    if token:
        try:
            _, tracks = _graphql_all_tracks(playlist_id, token)
            return tracks
        except Exception:
            logger.opt(exception=True).warning(
                'GraphQL pagination failed for {}; using embed data (limited)',
                playlist_id,
            )
    return _parse_playlist_tracks(entity)


def playlist_info_and_tracks(
    playlist_id: str,
) -> tuple[str, list[dict[str, Any]]]:
    """Return ``(playlist_name, tracks)`` fetching all tracks via partner GraphQL."""
    payload = _fetch_embed_json('playlist', playlist_id)
    entity = _entity_from(payload)
    embed_name = entity.get('name') or entity.get('title') or playlist_id
    token = _token_from_embed_payload(payload)
    if token:
        try:
            graphql_name, tracks = _graphql_all_tracks(playlist_id, token)
            return graphql_name or embed_name, tracks
        except Exception:
            logger.opt(exception=True).warning(
                'GraphQL pagination failed for {}; using embed data (limited)',
                playlist_id,
            )
    return embed_name, _parse_playlist_tracks(entity)


def _id_from_uri(uri: str) -> str:
    if not uri:
        return ''
    parts = uri.split(':')
    return parts[-1] if parts else ''


def resolve(url: str) -> Any:
    """Resolve any Spotify URL to a single song or a list of songs."""

    parsed = parse_spotify_url(url)
    if parsed is None:
        raise ValueError('Not a Spotify URL')
    kind, sid = parsed
    if kind == 'track':
        return track_from_id(sid)
    if kind == 'album':
        return album_tracks_from_id(sid)
    if kind == 'playlist':
        return playlist_tracks_from_id(sid)
    raise ValueError(f'Unsupported Spotify entity type: {kind}')
