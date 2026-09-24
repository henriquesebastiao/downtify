"""Resolve Spotify URLs without using the official Spotify Web API.

Reads the public ``open.spotify.com/embed`` pages, which expose the same
data the Spotify embedded player consumes. No client credentials, no
authentication and no premium account are required.
"""

from __future__ import annotations

import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

import httpx
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


_EMBED_TRANSIENT_HTTP = frozenset({429, 502, 503, 504})
_EMBED_FETCH_ATTEMPTS = 3


def _fetch_embed_json(kind: str, spotify_id: str) -> dict[str, Any]:
    url = f'https://open.spotify.com/embed/{kind}/{spotify_id}'
    response: httpx.Response | None = None
    for attempt in range(_EMBED_FETCH_ATTEMPTS):
        response = httpx.get(
            url,
            headers={
                'User-Agent': _USER_AGENT,
                'Accept-Language': 'en-US,en;q=0.9',
            },
            timeout=15,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if (
                status in _EMBED_TRANSIENT_HTTP
                and attempt < _EMBED_FETCH_ATTEMPTS - 1
            ):
                logger.debug(
                    'Spotify embed HTTP {} for {}/{}, retry {}/{}',
                    status,
                    kind,
                    spotify_id,
                    attempt + 1,
                    _EMBED_FETCH_ATTEMPTS,
                )
                time.sleep(1.0 * (attempt + 1))
                continue
            raise
        break
    if response is None:
        raise RuntimeError('Spotify embed fetch did not run')
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


def fetch_embed_entity(kind: str, spotify_id: str) -> dict[str, Any]:
    """The raw embed entity for a Spotify URL of any ``kind``.

    Tracks/albums/playlists are read through the richer helpers below
    (:func:`playlist_info_and_tracks` and friends); this is for kinds
    those don't model, namely ``show`` and ``episode`` — see
    :mod:`downtify.podcasts`. The embed always resolves a show or
    episode link to an ``entity`` of type ``"episode"`` (the show's most
    recent one for a ``/show/`` link), whose ``subtitle`` is the show's
    name — there is no separate "show" entity shape to parse.
    """

    return _entity_from(_fetch_embed_json(kind, spotify_id))


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
    # Track/album/playlist covers use ``width``; an artist's
    # ``visualIdentity.image`` entries use ``maxWidth`` instead - check
    # both so an artist photo actually sorts by size instead of staying
    # in whatever order the embed happened to list it.
    sized.sort(
        key=lambda s: int(s.get('width') or s.get('maxWidth') or 0),
        reverse=True,
    )
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
        resp = httpx.get(
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
    row: dict[str, Any] = {
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
    raw_tn = entity.get('trackNumber')
    if raw_tn is None:
        raw_tn = entity.get('track_number')
    if raw_tn is not None:
        try:
            tn = int(raw_tn)
        except (TypeError, ValueError):
            tn = 0
        if tn > 0:
            row['track_number'] = tn
    if isinstance(album, dict):
        raw_total = album.get('trackCount')
        if raw_total is None and isinstance(album.get('tracks'), dict):
            raw_total = album['tracks'].get('total')
        if raw_total is not None:
            try:
                tt = int(raw_total)
            except (TypeError, ValueError):
                tt = 0
            if tt > 0:
                row['album_track_total'] = tt
    return row


def _merge_full_track_metadata(
    song: dict[str, Any], full: dict[str, Any]
) -> dict[str, Any]:
    """Apply per-track embed fields onto a sparse playlist/browse row."""

    merged = dict(song)
    for key in (
        'cover_url',
        'year',
        'release_date',
        'album_name',
        'artists',
        'artist',
        'track_number',
        'album_track_total',
    ):
        value = full.get(key)
        if value is None or not value or value == []:
            continue
        if key in {'track_number', 'album_track_total'}:
            if merged.get(key) is not None:
                continue
            try:
                iv = int(value)
            except (TypeError, ValueError):
                continue
            if iv <= 0:
                continue
            merged[key] = iv
            continue
        if key == 'artists':
            if merged.get('artists'):
                continue
            merged['artists'] = value
            merged['artist'] = full.get('artist') or ', '.join(value)
            continue
        merged[key] = value
    return merged


def enrich_track_from_spotify_if_sparse(
    song: dict[str, Any],
) -> dict[str, Any]:
    """Fill missing Spotify tagging fields from the per-track embed.

    Playlist browse rows often omit ``year``, ``release_date``, and
    ``track_number``; monitored playlists re-fetch each track the same way.
    """

    if song.get('source') != 'spotify':
        return song
    track_id = song.get('song_id')
    if not isinstance(track_id, str) or not re.fullmatch(
        r'[A-Za-z0-9]{22}', track_id
    ):
        return song
    has_date = bool(
        str(song.get('release_date') or '').strip()
        or str(song.get('year') or '').strip()
    )
    has_track = song.get('track_number') is not None
    if has_date and has_track:
        return song
    try:
        full = track_from_id(track_id)
    except Exception:
        logger.opt(exception=True).debug(
            'Per-track Spotify enrich failed for {}', track_id
        )
        return song
    return _merge_full_track_metadata(song, full)


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
    resp = httpx.get(
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


_GRAPHQL_PAGE_LIMIT = 100
# Pages after the first are fetched this many at a time — enough to make
# a long playlist resolve several times faster, few enough to stay polite
# to Spotify's API.
_GRAPHQL_PAGE_CONCURRENCY = 4


def _graphql_page_items(pv2: dict[str, Any]) -> tuple[list[Any], int]:
    content = pv2.get('content') or {}
    return content.get('items') or [], content.get('totalCount') or 0


def _graphql_sequential_items(
    playlist_id: str, token: str, offset: int
) -> list[Any]:
    """Every item from ``offset`` on, one page after another, advancing by
    however many items each page actually returned."""

    items: list[Any] = []
    while True:
        page, total = _graphql_page_items(
            _graphql_fetch_page(
                playlist_id, token, offset, _GRAPHQL_PAGE_LIMIT
            )
        )
        items.extend(page)
        offset += len(page)
        if not page or offset >= total:
            return items


def _graphql_all_tracks(
    playlist_id: str, token: str
) -> tuple[Optional[str], list[dict[str, Any]]]:
    """Return ``(playlist_name_or_None, all_tracks)`` via partner GraphQL.

    The first page reports the playlist's size, so the remaining pages are
    requested concurrently (:data:`_GRAPHQL_PAGE_CONCURRENCY` at a time)
    at fixed offsets instead of one after another. That assumes every page
    but the last comes back full; if one doesn't, the fixed offsets would
    skip items, so the rest is walked sequentially from the first short
    page — the old behavior — instead.
    """

    first = _graphql_fetch_page(playlist_id, token, 0, _GRAPHQL_PAGE_LIMIT)
    playlist_name = first.get('name') or None
    items, total = _graphql_page_items(first)
    page_size = len(items)
    if page_size and page_size < total:
        offsets = list(range(page_size, total, page_size))
        with ThreadPoolExecutor(
            max_workers=_GRAPHQL_PAGE_CONCURRENCY,
            thread_name_prefix='downtify-spotify-page',
        ) as pool:
            pages = list(
                pool.map(
                    lambda offset: _graphql_page_items(
                        _graphql_fetch_page(
                            playlist_id, token, offset, _GRAPHQL_PAGE_LIMIT
                        )
                    )[0],
                    offsets,
                )
            )
        for offset, page in zip(offsets, pages):
            if len(page) < page_size and offset != offsets[-1]:
                items.extend(
                    _graphql_sequential_items(playlist_id, token, offset)
                )
                break
            items.extend(page)
    songs = [
        td for item in items if (td := _track_dict_from_graphql_item(item))
    ]
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


def playlist_cover_url_from_id(playlist_id: str) -> str:
    """Largest cover art Spotify's public playlist embed page offers.

    Playlist tracks carry no cover of their own — every track's
    ``cover_url`` already falls back to this same image (see
    ``_parse_playlist_tracks``) — so this reads it once, directly off
    the playlist entity, for saving alongside the playlist's M3U file.
    """
    payload = _fetch_embed_json('playlist', playlist_id)
    entity = _entity_from(payload)
    return _cover_url(entity)


def _id_from_uri(uri: str) -> str:
    if not uri:
        return ''
    parts = uri.split(':')
    return parts[-1] if parts else ''


def artist_name_from_id(artist_id: str) -> str:
    """Return an artist's display name from their embed page.

    The artist embed only carries the name, image and a top-tracks
    preview — Spotify does not expose a discography there, so callers
    that need releases resolve the artist against another provider by
    name. Raises ``ValueError`` when the name can't be read.
    """

    payload = _fetch_embed_json('artist', artist_id)
    entity = _entity_from(payload)
    name = (entity.get('name') or entity.get('title') or '').strip()
    if not name:
        raise ValueError(f'Could not read artist name for {artist_id}')
    return name


def _artist_entity(
    artist_id: str,
) -> tuple[dict[str, Any], str, str, Optional[str]]:
    """``(entity, name, cover_url, token)`` from an artist embed page.

    ``token`` is the anonymous session token baked into the same payload.
    Raises ``ValueError`` when the artist name can't be read.
    """

    payload = _fetch_embed_json('artist', artist_id)
    entity = _entity_from(payload)
    name = (entity.get('name') or entity.get('title') or '').strip()
    if not name:
        raise ValueError(f'Could not read artist name for {artist_id}')
    return entity, name, _cover_url(entity), _token_from_embed_payload(payload)


# sha256 of the queryArtistOverview GraphQL document in the Spotify web
# player. Update when the player bundle rolls and the API returns
# PersistedQueryNotFound. Location in the bundle:
# new tz.l("queryArtistOverview","query","<hash>",null)
_ARTIST_OVERVIEW_HASH = (
    '9f8134ef565e78621f1e1793555bd6633c5ac144ae0f89604ed3ae3f80b3c8e6'
)


# sha256 of the artist discography GraphQL document (queryArtistDiscography
# Albums / Singles / Compilations / All / Overview all share it). It lives
# in a lazily loaded chunk of the web player, not the main bundle:
# web-player/xpui-routes-artist.<hash>.js, as
# new tz.l("queryArtistDiscographyAll","query","<hash>",null)
_ARTIST_DISCOGRAPHY_HASH = (
    '5e07d323febb57b4a56a42abbf781490e58764aa45feb6e3dc0591564fc56599'
)
# Unlike the overview, this query pages: ``limit`` is required (the
# request fails without it) and larger values are accepted.
_DISCOGRAPHY_PAGE_LIMIT = 100
_DISCOGRAPHY_MAX_PAGES = 20


def _partner_query(
    operation: str,
    variables: dict[str, Any],
    sha256_hash: str,
    token: str,
) -> dict[str, Any]:
    """The ``data`` of one persisted query against the player's GraphQL."""

    resp = httpx.get(
        _PARTNER_API,
        params={
            'operationName': operation,
            'variables': json.dumps(variables),
            'extensions': json.dumps({
                'persistedQuery': {'version': 1, 'sha256Hash': sha256_hash}
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
    return data['data']


def _artist_discography(artist_id: str, token: str) -> dict[str, Any]:
    """The ``discography`` section of the player's artist overview.

    It holds ``topTracks`` (each with its album's uri only) and the
    artist's releases (albums, singles, compilations) with names, cover
    and date — though only the first page of each list: all the albums,
    but for a long catalogue just the ten latest singles.
    """

    data = _partner_query(
        'queryArtistOverview',
        {
            'uri': f'spotify:artist:{artist_id}',
            'locale': '',
            'includePrerelease': True,
        },
        _ARTIST_OVERVIEW_HASH,
        token,
    )
    return data['artistUnion']['discography']


def _artist_full_discography(artist_id: str, token: str) -> dict[str, Any]:
    """Every release of an artist, paging through ``queryArtistDiscographyAll``.

    Returns ``{'all': {'items': [...]}}``: one item per release group
    (a release and its alternate editions), in the same shape
    :func:`_artist_releases` reads from the overview.
    """

    items: list[Any] = []
    for _ in range(_DISCOGRAPHY_MAX_PAGES):
        data = _partner_query(
            'queryArtistDiscographyAll',
            {
                'uri': f'spotify:artist:{artist_id}',
                'locale': '',
                'offset': len(items),
                'limit': _DISCOGRAPHY_PAGE_LIMIT,
            },
            _ARTIST_DISCOGRAPHY_HASH,
            token,
        )
        page = data['artistUnion']['discography']['all']
        batch = page.get('items') or []
        items.extend(batch)
        if not batch or len(items) >= (page.get('totalCount') or 0):
            break
    return {'all': {'items': items}}


_RELEASE_TYPES = {
    'ALBUM': 'Album',
    'SINGLE': 'Single',
    'EP': 'EP',
    'COMPILATION': 'Compilation',
}


def _release_nodes(node: Any) -> list[dict[str, Any]]:
    """Every named ``spotify:album:`` node under *node*, in document order."""

    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        uri = node.get('uri')
        name = node.get('name')
        if (
            isinstance(uri, str)
            and uri.startswith('spotify:album:')
            and isinstance(name, str)
            and name.strip()
        ):
            found.append(node)
        for value in node.values():
            found.extend(_release_nodes(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(_release_nodes(value))
    return found


def _release_sort_key(release: dict[str, Any]) -> tuple[int, int, int]:
    date = release.get('date')
    date = date if isinstance(date, dict) else {}

    def part(key: str) -> int:
        value = _calendar_component(date.get(key))
        return value or 0

    return part('year'), part('month'), part('day')


def _artist_releases(
    discography: dict[str, Any], artist_name: str
) -> list[dict[str, Any]]:
    """Release summaries (albums, singles, compilations), newest first.

    Same shape as ``providers.artist_albums_from_channel_id`` so the
    frontend lists them the same way. Reads either the full discography
    or the overview's shorter one; a release can appear in more than one
    section of the latter, so this de-duplicates.
    """

    nodes = _release_nodes({
        k: v for k, v in discography.items() if k != 'topTracks'
    })
    unique: dict[str, dict[str, Any]] = {}
    for node in nodes:
        unique.setdefault(node['uri'], node)
    releases: list[dict[str, Any]] = []
    for node in sorted(unique.values(), key=_release_sort_key, reverse=True):
        album_id = _id_from_uri(node['uri'])
        cover = node.get('coverArt') or {}
        kind = str(node.get('type') or '').upper()
        year, _month, _day = _release_sort_key(node)
        releases.append({
            'album_id': album_id,
            'name': node['name'].strip(),
            'artists': [artist_name] if artist_name else [],
            'artist': artist_name,
            'cover_url': _largest_image(
                cover.get('sources') or [] if isinstance(cover, dict) else []
            ),
            'year': str(year) if year else '',
            'explicit': False,
            'url': f'https://open.spotify.com/album/{album_id}',
            'source': 'spotify',
            'release_type': _RELEASE_TYPES.get(kind, kind.title() or 'Album'),
        })
    return releases


def artist_page_from_id(
    artist_id: str,
) -> tuple[str, str, list[dict[str, Any]]]:
    """``(name, cover_url, releases)`` for a Spotify artist.

    The name and photo come from the artist embed. The embed has no
    discography, so the releases come from the player's GraphQL: the
    full, paged discography, or — if that query no longer resolves (its
    hash rolled) — the overview's shorter list. If both fail the
    releases are just empty.
    """

    _, name, cover_url, token = _artist_entity(artist_id)
    releases: list[dict[str, Any]] = []
    if token:
        for source, fetch in (
            ('full discography', _artist_full_discography),
            ('overview', _artist_discography),
        ):
            try:
                releases = _artist_releases(fetch(artist_id, token), name)
                break
            except Exception:
                logger.opt(exception=True).warning(
                    'Spotify releases unavailable for artist {} ({})',
                    artist_id,
                    source,
                )
    return name, cover_url, releases


def _album_names_by_uri(node: Any) -> dict[str, str]:
    """Every ``spotify:album:`` uri that comes with a name under *node*."""

    found: dict[str, str] = {}
    if isinstance(node, dict):
        uri = node.get('uri')
        name = node.get('name')
        if (
            isinstance(uri, str)
            and uri.startswith('spotify:album:')
            and isinstance(name, str)
            and name.strip()
        ):
            found[uri] = name.strip()
        for value in node.values():
            found.update(_album_names_by_uri(value))
    elif isinstance(node, list):
        for value in node:
            found.update(_album_names_by_uri(value))
    return found


def _album_name_from_embed(album_uri: str) -> str:
    try:
        payload = _fetch_embed_json('album', _id_from_uri(album_uri))
        entity = _entity_from(payload)
    except Exception:
        logger.opt(exception=True).debug(
            'Spotify album embed lookup failed for {}', album_uri
        )
        return ''
    return str(entity.get('name') or entity.get('title') or '').strip()


def _play_count(raw: Any) -> int:
    """A ``playcount`` (the player sends it as a string), or 0 if unusable."""

    if isinstance(raw, bool):
        return 0
    try:
        return max(int(raw), 0)
    except (TypeError, ValueError):
        return 0


def _top_track_overview(
    artist_id: str, token: str
) -> dict[str, dict[str, Any]]:
    """``{track id: {'album_name', 'play_count'}}`` for an artist's top tracks.

    The artist embed's shelf rows carry neither an album nor a play count,
    and neither does the per-track embed. The web player's
    ``queryArtistOverview`` query (the same anonymous-token GraphQL endpoint
    playlists use) lists each top track's play count and its album by uri
    and, in the same response, the artist's releases by name — one request
    covers almost every track. An album missing from that list is looked up
    in its own embed instead.

    Best effort: any failure (the persisted-query hash rolled, the
    network) returns ``{}``, leaving those fields blank rather than failing
    the whole artist. A track only carries the keys that are known.
    """

    try:
        discography = _artist_discography(artist_id, token)
        names = _album_names_by_uri(discography)
        top = (discography.get('topTracks') or {}).get('items') or []
        tracks: dict[str, tuple[str, int]] = {}
        for item in top:
            track = item.get('track') if isinstance(item, dict) else None
            if not isinstance(track, dict):
                continue
            track_id = track.get('id') or _id_from_uri(track.get('uri') or '')
            album = track.get('albumOfTrack') or {}
            album_uri = album.get('uri') if isinstance(album, dict) else ''
            if track_id:
                tracks[track_id] = (
                    album_uri or '',
                    _play_count(track.get('playcount')),
                )
    except Exception:
        logger.opt(exception=True).warning(
            'Spotify top track details unavailable for artist {}', artist_id
        )
        return {}

    result: dict[str, dict[str, Any]] = {}
    for track_id, (album_uri, plays) in tracks.items():
        info: dict[str, Any] = {}
        if album_uri:
            if album_uri not in names:
                names[album_uri] = _album_name_from_embed(album_uri)
            if names[album_uri]:
                info['album_name'] = names[album_uri]
        if plays:
            info['play_count'] = plays
        if info:
            result[track_id] = info
    return result


# Top songs are each enriched with their own embed fetch (~0.6 s apiece):
# a handful at a time keeps a full shelf under a few seconds without
# hammering Spotify.
_TOP_SONGS_CONCURRENCY = 5


def artist_top_songs_from_id(
    artist_id: str,
    limit: Optional[int] = None,
) -> tuple[str, str, list[dict[str, Any]]]:
    """``(name, cover_url, songs)`` from an artist embed's top-tracks shelf.

    This is Spotify's own "Popular"/top-tracks preview shown at the top of
    the artist's home page (up to ~10 tracks, the same shelf a "This is
    <Artist>" playlist draws its first entries from) — not a discography,
    which :func:`artist_name_from_id`'s docstring already explains isn't
    exposed here. Named ``artist_top_songs_*`` (not ``*_top_tracks_*``) to
    match the equivalent YouTube Music primitive,
    :func:`providers.artist_top_songs_from_channel_id`, even though Spotify
    itself calls this shelf "Top Tracks". Raises ``ValueError`` when the
    artist name can't be read; returns an empty song list (not an error)
    when the shelf itself can't be parsed.

    The shelf lives under ``entity['trackList']`` — the same field name
    (and flat row shape, no ``track`` wrapper) already used by
    :func:`_parse_playlist_tracks` for playlists/albums; confirmed against
    a live embed fetch, since :func:`artist_name_from_id`'s own docstring
    only promised the preview was *somewhere* in the payload. Unlike a
    playlist row, a shelf row carries no per-track album art at all (no
    ``album``/``coverArt``), so each track is enriched via
    :func:`enrich_track_from_spotify_if_sparse` — the same per-track
    re-fetch a monitored playlist already does — so every song gets its
    own album cover instead of falling back to the artist's photo. The
    album *name* and the play count aren't in either embed; see
    :func:`_top_track_overview`.

    *limit* keeps only the first that many songs, and is applied *before*
    the per-track enrichment - which is where the time goes - so asking
    for 5 of the shelf's 10 costs about half. The enrichments (and the
    overview request) run concurrently, in the shelf's own order.
    """

    entity, name, cover_url, token = _artist_entity(artist_id)

    items = entity.get('trackList') or []
    songs: list[dict[str, Any]] = []
    for item in items:
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
                dict(track), track_id=track_id, fallback_cover=cover_url
            )
        )
        if limit is not None and len(songs) >= limit:
            break
    if not songs:
        logger.warning(
            'No top-songs parsed from Spotify artist embed for {}', artist_id
        )
        return name, cover_url, songs
    with ThreadPoolExecutor(
        max_workers=min(_TOP_SONGS_CONCURRENCY, len(songs)) + 1,
        thread_name_prefix='downtify-spotify-top',
    ) as pool:
        overview_future = (
            pool.submit(_top_track_overview, artist_id, token)
            if token
            else None
        )
        # map() keeps the shelf's order whichever enrichment finishes first.
        songs = list(pool.map(enrich_track_from_spotify_if_sparse, songs))
        overview = overview_future.result() if overview_future else None
    if overview is not None:
        for song in songs:
            info = overview.get(song['song_id']) or {}
            if not song.get('album_name') and info.get('album_name'):
                song['album_name'] = info['album_name']
            if info.get('play_count'):
                song['play_count'] = info['play_count']
    return name, cover_url, songs


def artist_image_url_from_id(artist_id: str) -> str:
    """Largest square photo an artist's embed page offers, or ``""``.

    Reads the same ``visualIdentity.image`` field :func:`_cover_url`
    already checks for tracks/albums/playlists — see
    :func:`artist_name_from_id` for why an artist embed carries nothing
    richer than a name and this one photo. The wide banner shown on an
    artist's real Spotify page is a separate image the embed doesn't
    expose at all - see :func:`artist_banner_url_from_id`.
    """

    payload = _fetch_embed_json('artist', artist_id)
    entity = _entity_from(payload)
    return _cover_url(entity)


# sha256 of the queryArtistOverview GraphQL document in the Spotify web
# player - same persisted-query mechanism as _GRAPHQL_HASH above, just a
# different operation. Update when the player bundle rolls and the API
# returns PersistedQueryNotFound.
# Location in the bundle: new tz.l("queryArtistOverview","query","<hash>",null)
_ARTIST_OVERVIEW_HASH = (
    '9f8134ef565e78621f1e1793555bd6633c5ac144ae0f89604ed3ae3f80b3c8e6'
)


def _artist_overview(artist_id: str) -> dict[str, Any]:
    """Raw ``artistUnion`` from the persisted-GraphQL pathfinder API's
    ``queryArtistOverview`` operation, or ``{}`` on any failure -
    :func:`artist_banner_url_from_id` (``headerImage``) and
    :func:`related_artist_names_from_id` (``relatedContent.
    relatedArtists``) both read different fields off the same response,
    so a caller wanting both only pays for the request once by calling
    this directly instead.
    """

    payload = _fetch_embed_json('artist', artist_id)
    token = _token_from_embed_payload(payload)
    if not token:
        return {}
    try:
        resp = httpx.get(
            _PARTNER_API,
            params={
                'operationName': 'queryArtistOverview',
                'variables': json.dumps({
                    'uri': f'spotify:artist:{artist_id}',
                    'locale': '',
                    'preReleaseV2': False,
                }),
                'extensions': json.dumps({
                    'persistedQuery': {
                        'version': 1,
                        'sha256Hash': _ARTIST_OVERVIEW_HASH,
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
    except Exception:
        logger.opt(exception=True).debug(
            'Spotify artist overview fetch failed for {}', artist_id
        )
        return {}
    artist = (data.get('data') or {}).get('artistUnion') or {}
    return artist if artist.get('__typename') == 'Artist' else {}


def artist_banner_url_from_id(artist_id: str) -> str:
    """Largest wide header/banner image an artist has set, or ``""``.

    Not exposed by the embed page at all (see
    :func:`artist_image_url_from_id`) - reuses the embed's anonymous
    access token against the same persisted-GraphQL pathfinder API
    :func:`_graphql_fetch_page` already calls for playlist pagination,
    just a different operation (``queryArtistOverview``, see
    :func:`_artist_overview`) that happens to surface the artist page's
    real header image alongside data we don't need here. Many artists
    simply don't have one set - this returns ``""`` rather than falling
    back to the square photo, so callers don't silently save the wrong
    shape as a "banner".
    """

    header = (_artist_overview(artist_id).get('headerImage') or {}).get(
        'data'
    ) or {}
    if header.get('__typename') != 'ImageV2':
        return ''
    return _largest_image(header.get('sources') or [])


def related_artist_names_from_id(artist_id: str) -> list[str]:
    """ "Fans also like"-equivalent names for a Spotify artist id, or
    ``[]`` - from the same ``queryArtistOverview`` call
    :func:`artist_banner_url_from_id` uses (see :func:`_artist_overview`),
    just ``relatedContent.relatedArtists`` instead of ``headerImage``.
    Spotify's own version of this also carries an id and photo per
    related artist, thrown away here since callers only want a name list
    to merge with Deezer's own related-artist names (see
    :func:`downtify.artist_profile.fetch_bio`).
    """

    items = (
        (_artist_overview(artist_id).get('relatedContent') or {}).get(
            'relatedArtists'
        )
        or {}
    ).get('items') or []
    names = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str((item.get('profile') or {}).get('name') or '').strip()
        if name:
            names.append(name)
    return names


# sha256 of the searchSuggestions GraphQL document (the web player's
# search-as-you-type box) - same persisted-query mechanism as above.
# Update when the player bundle rolls and the API returns
# PersistedQueryNotFound.
# Location in the bundle: new tz.l("searchSuggestions","query","<hash>",null)
_SEARCH_SUGGESTIONS_HASH = (
    'b50ebd72524415b132ddaca04158fd7aca529da28be322c9924643c0633df5bd'
)
# Any public embed page carries an anonymous access token; this artist's
# is only fetched to get one.
_TOKEN_SEED_ARTIST_ID = '6XyY86QOPPrYVGvF9ch6wz'
_TOKEN_FALLBACK_TTL = 300.0
_token_lock = threading.Lock()
_token_cache: Optional[tuple[str, float]] = None


def _anonymous_token() -> Optional[str]:
    """An anonymous web-player access token, cached until it expires."""

    global _token_cache  # noqa: PLW0603
    with _token_lock:
        cached = _token_cache
    if cached is not None and time.time() < cached[1]:
        return cached[0]
    try:
        payload = _fetch_embed_json('artist', _TOKEN_SEED_ARTIST_ID)
    except Exception:
        logger.opt(exception=True).debug(
            'Spotify anonymous token fetch failed'
        )
        return None
    token = _token_from_embed_payload(payload)
    if not token:
        return None
    try:
        expires = (
            int(
                payload['props']['pageProps']['state']['settings']['session'][
                    'accessTokenExpirationTimestampMs'
                ]
            )
            / 1000
            - 60
        )
    except (KeyError, TypeError, ValueError):
        expires = time.time() + _TOKEN_FALLBACK_TTL
    with _token_lock:
        _token_cache = (token, expires)
    return token


def search_artist_by_name(name: str) -> Optional[dict[str, str]]:
    """``{id, name}`` of the Spotify artist whose name matches *name*
    exactly (case-insensitively), or ``None``.

    Spotify has no public search API, but the web player's own
    search-as-you-type box (``searchSuggestions``) also returns the top
    entities, artists included, and that persisted query works with the
    same anonymous token the embed pages hand out. It needs a large
    ``numberOfTopResults`` (20): the default 5 often leaves the artist
    out. The response mixes in other artists, so only an exact name match
    counts - same strictness as every platform's own ``resolve_artist_id``
    - never the first artist row. A name that's ambiguous on Spotify
    resolves to whichever exact match ranks first, which is why an id
    resolved from one of the artist's own downloaded tracks (see
    :func:`primary_artist_id_from_track_id`) is always preferred.
    """

    text = name.strip()
    if not text:
        return None
    token = _anonymous_token()
    if not token:
        return None
    try:
        resp = httpx.get(
            _PARTNER_API,
            params={
                'operationName': 'searchSuggestions',
                'variables': json.dumps({
                    'query': text,
                    'limit': 20,
                    'numberOfTopResults': 20,
                    'offset': 0,
                    'includeAuthors': False,
                }),
                'extensions': json.dumps({
                    'persistedQuery': {
                        'version': 1,
                        'sha256Hash': _SEARCH_SUGGESTIONS_HASH,
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
    except Exception:
        logger.opt(exception=True).debug(
            'Spotify artist search failed for {!r}', text
        )
        return None
    items = (
        ((data.get('data') or {}).get('searchV2') or {}).get('topResultsV2')
        or {}
    ).get('itemsV2') or []
    wanted = text.lower()
    for entry in items:
        item = entry.get('item') if isinstance(entry, dict) else None
        if not isinstance(item, dict):
            continue
        if item.get('__typename') != 'ArtistResponseWrapper':
            continue
        artist = item.get('data') or {}
        artist_name = str((artist.get('profile') or {}).get('name') or '')
        artist_id = _id_from_uri(str(artist.get('uri') or ''))
        if artist_id and artist_name.strip().lower() == wanted:
            return {'id': artist_id, 'name': artist_name.strip()}
    return None


def primary_artist_id_from_track_id(track_id: str) -> Optional[str]:
    """Spotify id of *track_id*'s first credited artist, or ``None``.

    A track embed's raw ``artists`` entries carry ``{name, uri}`` each;
    :func:`_artist_names` throws the ``uri`` away since no other caller
    needs it. Used to find an artist's photo starting from a track
    already in the library (see :mod:`downtify.track_index`) - the most
    reliable route, since it can't pick a namesake the way
    :func:`search_artist_by_name` can.
    """

    payload = _fetch_embed_json('track', track_id)
    entity = _entity_from(payload)
    raw = entity.get('artists') or []
    if not isinstance(raw, list) or not raw:
        return None
    first = raw[0]
    if not isinstance(first, dict):
        return None
    return _id_from_uri(str(first.get('uri') or '')) or None


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
