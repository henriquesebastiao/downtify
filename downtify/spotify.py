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

from .telemetry import json_log_blob, redact_sensitive_mapping

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

# Spotify often serves a tiny HTML shell (no ``music:release_date`` meta) to
# full Chrome-like user agents while still sending the static OG-rich document
# for a minimal ``Mozilla/5.0`` probe — reuse that behaviour here only.
_ALBUM_OPEN_PAGE_UA = 'Mozilla/5.0'

# Embed album payloads often set ``releaseDate`` to ``null``. The canonical
# open.spotify.com/album/{id} HTML still publishes ``music:release_date``.
_ALBUM_OPEN_PAGE_META_RELEASE = re.compile(
    r'<meta\s+name=["\']music:release_date["\']\s+content=["\']([^"\']+)["\']',
    re.I,
)
_ALBUM_OPEN_PAGE_DATE_PUBLISHED = re.compile(
    r'"datePublished"\s*:\s*"([^"]+)"'
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
    data = json.loads(match.group(1))
    preview = json_log_blob(redact_sensitive_mapping(data))
    logger.debug(
        'Spotify embed NEXT_DATA ({}/{}, {} chars redacted preview): {}',
        kind,
        spotify_id,
        len(preview),
        preview,
    )
    _log_spotify_embed_entity_summary(kind, spotify_id, data)
    return data


def _log_spotify_embed_entity_summary(
    kind: str,
    spotify_id: str,
    payload: dict[str, Any],
) -> None:
    """INFO line so release/track shape is visible without DEBUG."""

    try:
        ent = _entity_from(payload)
    except ValueError as ex:
        logger.warning(
            'Spotify embed: no usable entity kind={} id={}: {}',
            kind,
            spotify_id,
            ex,
        )
        return
    track_list = ent.get('trackList') or []
    alt_items = []
    nested = ent.get('tracks')
    if isinstance(nested, dict):
        alt_items = nested.get('items') or []
    rd_raw = ent.get('releaseDate')
    if isinstance(rd_raw, dict):
        rd_summary = 'dict isoString={!r}'.format(rd_raw.get('isoString'))
    elif rd_raw is None:
        rd_summary = 'null'
    elif isinstance(rd_raw, str):
        rd_summary = f'str:{rd_raw[:32]!r}'
    else:
        rd_summary = type(rd_raw).__name__
    logger.info(
        (
            'Spotify embed OK: {} {} title={!r} type={!r} '
            'trackList_len={} tracks_items_len={} releaseDate={}'
        ),
        kind,
        spotify_id,
        ent.get('name') or ent.get('title'),
        ent.get('type'),
        len(track_list),
        len(alt_items),
        rd_summary,
    )


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


def _embed_row_track(item: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Track dict for a playlist/album embed row.

    Rows often nest the payload under ``track`` while the artist line lives in
    a sibling ``subtitle`` field on the wrapper — copy it onto the track so
    :func:`_artist_names` can see it.
    """

    inner = item.get('track')
    if isinstance(inner, dict):
        sub = item.get('subtitle')
        if isinstance(sub, str) and sub.strip() and not inner.get('subtitle'):
            return {**inner, 'subtitle': sub}
        return inner
    return item if isinstance(item, dict) else None


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
    names: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                if item.strip():
                    names.append(item.strip())
            elif isinstance(item, dict):
                name = item.get('name')
                if name:
                    names.append(name)
    if names:
        return names
    return [
        d['name']
        for d in _artists_from_subtitle(entity.get('subtitle'))
        if d.get('name')
    ]


def _normalize_release_date_text(raw: Any) -> str:
    """Normalize Spotify ``isoString`` (or similar) to ``YYYY-MM-DD`` or year."""

    if not isinstance(raw, str):
        return ''
    text = raw.strip()
    if not text:
        return ''
    if 'T' in text:
        text = text.split('T', 1)[0].strip()
    if (
        len(text) >= 10
        and text[4:5] == '-'
        and text[7:8] == '-'
        and text[:4].isdigit()
        and text[5:7].isdigit()
        and text[8:10].isdigit()
    ):
        return text[:10]
    # Month precision strings like ``2024-06`` → tag-friendly first-of-month.
    if (
        len(text) >= 7
        and text[4:5] == '-'
        and text[:4].isdigit()
        and text[5:7].isdigit()
    ):
        return f'{text[:4]}-{text[5:7]}-01'
    if len(text) >= 4 and text[:4].isdigit():
        return text[:4]
    return text


def _calendar_component(raw: Any) -> Optional[int]:
    """Coerce embed/GraphQL month or day ints (reject bool)."""

    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip())
    return None


def _coerce_four_digit_year(raw: Any) -> Optional[int]:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int) and 1000 <= raw <= 9999:
        return raw
    if isinstance(raw, float) and raw.is_integer():
        y = int(raw)
        return y if 1000 <= y <= 9999 else None
    if isinstance(raw, str):
        ys = raw.strip()
        if ys.isdigit() and len(ys) == 4:
            y = int(ys)
            return y if 1000 <= y <= 9999 else None
    return None


def _release_date_raw_from_field(release: Any, *, _depth: int = 0) -> str:
    """Extract a tagging-friendly date string from Spotify embed/GraphQL fields.

    Older payloads expose ``releaseDate.isoString``. Many catalogue rows omit
    ``isoString`` and only send ``year`` (optionally ``month``/``day`` and
    ``precision``); without handling those we end up tagging files with no
    release date even though Spotify showed a year on the canvas.
    """

    if _depth > 6:
        return ''
    if isinstance(release, dict):
        cand = release.get('isoString')
        if isinstance(cand, str) and cand.strip():
            out = _normalize_release_date_text(cand.strip())
            if out:
                return out

        nested = release.get('date')
        nested_out = (
            _release_date_raw_from_field(nested, _depth=_depth + 1)
            if nested is not None
            else ''
        )
        if nested_out:
            return nested_out

        y_part = _coerce_four_digit_year(release.get('year'))
        ys = str(y_part) if y_part is not None else ''
        mi = _calendar_component(release.get('month'))
        di = _calendar_component(release.get('day'))
        pv = release.get('precision')
        precision = pv.casefold() if isinstance(pv, str) else ''

        if precision == 'year' and ys:
            return ys

        if ys and mi is not None and 1 <= mi <= 12:
            mm = f'{mi:02d}'
            if di is not None and 1 <= di <= 31:
                return f'{ys}-{mm}-{di:02d}'
            if precision in {'month', 'day'}:
                return f'{ys}-{mm}-01'

        if ys:
            return ys

        return ''
    if isinstance(release, str):
        return _normalize_release_date_text(release)
    return ''


def _album_release_date_from_open_page(album_id: str) -> str:
    """Parse release date from the public album HTML when embed omits it."""

    if not album_id or not re.fullmatch(r'[A-Za-z0-9]+', album_id):
        return ''
    try:
        resp = requests.get(
            f'https://open.spotify.com/album/{album_id}',
            headers={
                'User-Agent': _ALBUM_OPEN_PAGE_UA,
                'Accept-Language': 'en-US,en;q=0.9',
            },
            timeout=15,
        )
        resp.raise_for_status()
    except Exception:
        logger.opt(exception=True).debug(
            'Spotify open album page fetch failed for release_date id={}',
            album_id,
        )
        return ''

    html = resp.text
    m = _ALBUM_OPEN_PAGE_META_RELEASE.search(html)
    if not m:
        m = _ALBUM_OPEN_PAGE_DATE_PUBLISHED.search(html)
    if not m:
        return ''
    normalized = _normalize_release_date_text(m.group(1).strip())
    if normalized:
        logger.debug(
            'Spotify album {} release_date from open page: {!r}',
            album_id,
            normalized,
        )
    return normalized


def _release_date_str(entity: dict[str, Any]) -> str:
    """Prefer full calendar date when the embed exposes ``isoString``."""

    rd = _release_date_raw_from_field(entity.get('releaseDate'))
    if rd:
        return rd
    album = entity.get('album') or {}
    if isinstance(album, dict):
        for key in ('releaseDate', 'date'):
            rd = _release_date_raw_from_field(album.get(key))
            if rd:
                return rd
    return ''


def _year_from_release_date(rd: str) -> str:
    if len(rd) >= 4 and rd[:4].isdigit():
        return rd[:4]
    return ''


def _track_dict(
    entity: dict[str, Any],
    *,
    track_id: str,
    fallback_album: str = '',
    fallback_cover: str = '',
    fallback_release_date: str = '',
) -> dict[str, Any]:
    duration_ms = entity.get('duration') or entity.get('duration_ms') or 0
    album = entity.get('album') or {}
    album_name = album.get('name', '') if isinstance(album, dict) else ''
    cover = _cover_url(entity) or fallback_cover
    names = _artist_names(entity)
    release_date = _release_date_str(entity)
    if not release_date:
        release_date = (fallback_release_date or '').strip()
    year = _year_from_release_date(release_date)
    if not year and not release_date:
        logger.info(
            'Spotify resolved row has no year/release_date: '
            'track_id={!r} title={!r} album={!r} raw_releaseDate={!r}',
            track_id,
            entity.get('name') or entity.get('title'),
            album_name or fallback_album,
            entity.get('releaseDate'),
        )
    return {
        'song_id': track_id,
        'name': entity.get('name') or entity.get('title') or '',
        'artists': names,
        'artist': ', '.join(names),
        'album_name': album_name or fallback_album,
        'cover_url': cover,
        'duration': int(int(duration_ms) / 1000) if duration_ms else 0,
        'url': f'https://open.spotify.com/track/{track_id}'
        if track_id
        else '',
        'explicit': bool(entity.get('isExplicit') or entity.get('explicit')),
        'release_date': release_date,
        'year': year,
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
    album_track_total = len(track_items)
    album_release_date = _release_date_str(entity)
    if not album_release_date:
        album_release_date = _album_release_date_from_open_page(album_id)
    songs: list[dict[str, Any]] = []
    for tracklist_slot, item in enumerate(track_items, start=1):
        if not isinstance(item, dict):
            continue
        track = _embed_row_track(item)
        if not isinstance(track, dict):
            continue
        track_id = track.get('id') or _id_from_uri(track.get('uri', ''))
        if not track_id:
            continue
        track = dict(track)
        if not track.get('artists') and not track.get('subtitle'):
            track['artists'] = (
                entity.get('artists')
                or _artists_from_subtitle(entity.get('subtitle'))
                or []
            )
        row = _track_dict(
            track,
            track_id=track_id,
            fallback_album=album_name,
            fallback_cover=cover,
            fallback_release_date=album_release_date,
        )
        row['track_number'] = tracklist_slot
        row['album_track_total'] = album_track_total
        songs.append(row)
    return songs


def _parse_playlist_tracks(entity: dict[str, Any]) -> list[dict[str, Any]]:
    fallback_cover = _cover_url(entity)
    track_items = entity.get('trackList') or []
    songs: list[dict[str, Any]] = []
    for item in track_items:
        if not isinstance(item, dict):
            continue
        track = _embed_row_track(item)
        if not isinstance(track, dict):
            continue
        track_id = track.get('id') or _id_from_uri(track.get('uri', ''))
        if not track_id:
            continue
        songs.append(
            _track_dict(
                dict(track),
                track_id=track_id,
                fallback_cover=fallback_cover,
            )
        )
    return songs


def _artists_from_subtitle(subtitle: Any) -> list[dict[str, str]]:
    if not isinstance(subtitle, str) or not subtitle:
        return []
    normalized = subtitle.replace('\xa0', ' ')
    return [
        {'name': name.strip()}
        for name in re.split(r'\s*(?:,|，)\s*', normalized)
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
    gql_release = ''
    if isinstance(album, dict):
        for key in ('date', 'releaseDate'):
            gql_release = _release_date_raw_from_field(album.get(key))
            if gql_release:
                break
    if not gql_release:
        logger.info(
            'Spotify GraphQL track lacks album release date: '
            'track_id={!r} title={!r} album={!r} '
            'albumOfTrack_keys={}',
            track_id,
            track.get('name'),
            album_name,
            sorted(album.keys()) if isinstance(album, dict) else (),
        )
    return {
        'song_id': track_id,
        'name': track.get('name') or '',
        'artists': artists,
        'artist': ', '.join(artists),
        'album_name': album_name,
        'cover_url': cover_url,
        'duration': int(duration_ms / 1000) if duration_ms else 0,
        'url': f'https://open.spotify.com/track/{track_id}',
        'explicit': label.upper() == 'EXPLICIT',
        'release_date': gql_release,
        'year': _year_from_release_date(gql_release),
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
    logger.debug(
        'Spotify GraphQL fetchPlaylist id={} offset={}: {}',
        playlist_id,
        offset,
        json_log_blob(redact_sensitive_mapping(data))[:12000],
    )
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
