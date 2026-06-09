"""FastAPI router exposed by Downtify.

The endpoints intentionally mirror the surface that the previous
``spotdl``-powered backend exposed so the existing Vue frontend keeps
working without changes:

* ``GET  /api/version``
* ``GET  /api/songs/search``
* ``GET  /api/song/url`` and ``GET /api/url`` (alias)
* ``POST /api/download/url`` (optional JSON body: resolved Spotify row so
  ``track_number`` / ``album_track_total`` survive re-fetch by URL)
* ``POST /api/playlist/m3u``
* ``GET  /api/playlists/batches``
* ``GET  /api/playlists/batches/{spotify_playlist_id}``
* ``DELETE /api/playlists/batches/{spotify_playlist_id}``
* ``GET  /api/playlists/incomplete``
* ``POST /api/playlists/incomplete/download-missing``
* ``GET  /api/settings``
* ``POST /api/settings/update``
* ``WS   /api/ws``
* ``GET  /api/check_update``
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
from pathlib import Path
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Body,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from loguru import logger

from downtify.download_pool import DownloadParallelLimiter
from downtify.slskd_provider import reset_slskd_parallelism

from . import m3u, providers, spotify
from .cover_cache import CoverArtCache
from .downloader import Downloader, NoAudioMatchError, inspect_youtube_cookies
from .library_catalog import library_context_from_state
from .library_delete import (
    delete_library_files,
    delete_playlist_from_library,
    tag_mismatch_delete_context_from_state,
)
from .library_metadata_cache import LibraryMetadataCache
from .library_paths import locate_library_file, slskd_dir_from_downloader
from .library_paths_cache import invalidate_library_paths_cache
from .library_reconcile import (
    playlist_refresh_enabled,
    reconcile_and_refresh,
    refresh_playlists_after_moves,
)
from .monitor import PlaylistMonitorDB, check_playlist
from .navidrome import (
    _effective_navidrome_settings,
    cache_navidrome_song_id,
    enrich_song_from_library_file,
    sync_playlist_to_navidrome,
)
from .navidrome_index import NavidromeIndex
from .playlist_batches import (
    PlaylistBatchStore,
    active_queue_count_for_playlist,
    split_tracks_by_library,
)
from .playlist_catalog import PlaylistCatalog
from .playlist_spotify_cache import (
    PlaylistSpotifyCache,
    fetch_playlist_tracks,
    fetch_track_metadata,
)
from .track_index import (
    TrackIndex,
    normalize_spotify_track_id,
    resolve_existing_download,
)


def _fetch_playlist_tracks(
    spotify_playlist_id: str,
    *,
    refresh: bool = False,
) -> tuple[str, list[dict[str, Any]]]:
    return fetch_playlist_tracks(
        spotify_playlist_id,
        cache=state.playlist_spotify_cache,
        refresh=refresh,
    )


def _fetch_track_metadata(
    track_spotify_id: str,
    *,
    playlist_id: Optional[str] = None,
    refresh: bool = False,
) -> dict[str, Any]:
    return fetch_track_metadata(
        track_spotify_id,
        cache=state.playlist_spotify_cache,
        playlist_id=playlist_id,
        refresh=refresh,
    )


def _register_download_on_disk(
    song: dict[str, Any],
    filename: str,
    *,
    playlist_name: Optional[str] = None,
    track_order: int = 0,
    spotify_playlist_id: Optional[str] = None,
) -> set[str]:
    """Update track index, catalog, monitor; return playlists to refresh."""

    return _register_download_playlists_on_disk(
        song,
        filename,
        playlist_name=playlist_name,
        spotify_playlist_id=spotify_playlist_id,
        track_order=track_order,
    )


def _playlist_context_from_hints(
    hints: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Resolve optional playlist batch/retry context from client hints."""

    if not isinstance(hints, dict):
        return {}
    name = str(
        hints.get('downtify_playlist_name') or hints.get('playlist_name') or ''
    ).strip()
    playlist_url = str(
        hints.get('downtify_playlist_url') or hints.get('playlist_url') or ''
    ).strip()
    spotify_playlist_id = (
        str(
            hints.get('downtify_spotify_playlist_id')
            or hints.get('spotify_playlist_id')
            or ''
        ).strip()
        or None
    )
    order_raw = hints.get('downtify_track_order', hints.get('track_order', 0))
    try:
        track_order = int(order_raw)
    except (TypeError, ValueError):
        track_order = 0
    track_order = max(track_order, 0)

    if not name and playlist_url:
        parsed = spotify.parse_spotify_url(playlist_url)
        if parsed is not None and parsed[0] == 'playlist':
            spotify_playlist_id = spotify_playlist_id or parsed[1]
            try:
                name, _ = _fetch_playlist_tracks(parsed[1])
            except Exception:
                logger.opt(exception=True).warning(
                    'download: failed to resolve playlist name from url'
                )
                name = ''

    subdir: Optional[str] = None
    if name and state.downloader is not None:
        organize = bool(state.settings.get('organize_by_artist', False))
        if not organize:
            subdir = m3u.sanitize_playlist_name(name)

    return {
        'playlist_name': name or None,
        'spotify_playlist_id': spotify_playlist_id,
        'track_order': track_order,
        'subdir': subdir,
    }


def _playlists_for_successful_download(
    song: dict[str, Any],
    *,
    primary_playlist: Optional[str] = None,
) -> set[str]:
    """Playlist names that should be refreshed after this track succeeds."""

    names: set[str] = set()
    primary = str(primary_playlist or '').strip()
    if primary:
        names.add(primary)
    tid = normalize_spotify_track_id(song)
    if not tid:
        return names
    if state.playlist_catalog is not None:
        names.update(state.playlist_catalog.playlists_for_track(tid))
    if state.monitor_db is not None:
        names.update(state.monitor_db.playlists_for_track(tid))
    return names


def _upsert_track_in_playlists(
    song: dict[str, Any],
    filename: str,
    playlist_names: set[str],
    *,
    primary_playlist: Optional[str] = None,
    primary_order: int = 0,
    spotify_playlist_id: Optional[str] = None,
) -> None:
    """Register the file in the catalog for every affected playlist."""

    if state.downloader is None or state.playlist_catalog is None:
        return
    if not playlist_names:
        return
    dl_dir = Path(state.downloader.download_dir)
    slskd = slskd_dir_from_downloader(state.downloader)
    full = locate_library_file(filename, dl_dir, slskd)
    if full is None:
        return
    catalog = state.playlist_catalog
    primary = str(primary_playlist or '').strip()
    for pl_name in sorted(playlist_names):
        sid = (
            spotify_playlist_id
            if pl_name == primary and spotify_playlist_id
            else catalog.spotify_id_for_playlist(pl_name)
        )
        catalog.ensure_playlist(pl_name, spotify_id=sid)
        order = primary_order if pl_name == primary else 0
        catalog.upsert_track(pl_name, song, filename, full, track_order=order)


def _register_download_playlists_on_disk(
    song: dict[str, Any],
    filename: str,
    *,
    playlist_name: Optional[str] = None,
    spotify_playlist_id: Optional[str] = None,
    track_order: int = 0,
) -> set[str]:
    """Update indexes, catalog, monitor paths; return playlists to refresh."""

    if state.downloader is None or not filename:
        return set()
    tid = normalize_spotify_track_id(song)
    if state.monitor_db is not None and tid:
        state.monitor_db.update_filename_for_spotify(tid, filename)

    affected = _playlists_for_successful_download(
        song, primary_playlist=playlist_name
    )
    _upsert_track_in_playlists(
        song,
        filename,
        affected,
        primary_playlist=playlist_name,
        primary_order=track_order,
        spotify_playlist_id=spotify_playlist_id,
    )
    if state.track_index is not None:
        dl_dir = Path(state.downloader.download_dir)
        slskd = slskd_dir_from_downloader(state.downloader)
        full = locate_library_file(filename, dl_dir, slskd)
        if full is not None:
            state.track_index.register_song(song, filename, full_path=full)
    invalidate_library_paths_cache()
    return affected


async def _schedule_playlist_refresh_after_download(
    playlist_names: set[str],
) -> None:
    if not playlist_names or state.downloader is None:
        return
    if state.playlist_catalog is None:
        return

    async def _run() -> None:
        try:
            await asyncio.to_thread(
                refresh_playlists_after_moves,
                playlist_names,
                settings=state.settings,
                downloader=state.downloader,
                playlist_catalog=state.playlist_catalog,
                track_index=state.track_index,
                monitor_db=state.monitor_db,
                navidrome_index=state.navidrome_index,
                navidrome_scan=bool(
                    state.settings.get('navidrome', {}).get(
                        'scan_after_download', True
                    )
                ),
                playlist_spotify_cache=state.playlist_spotify_cache,
                cover_cache=state.cover_cache,
                metadata_cache=state.metadata_cache,
            )
        except Exception:
            logger.exception(
                'download: playlist refresh failed for {}',
                ', '.join(sorted(playlist_names)[:5]),
            )

    asyncio.create_task(_run())


DEFAULT_YOUTUBE_COOKIES_BASENAME = 'youtube-cookies.txt'

DEFAULT_SETTINGS: dict[str, Any] = {
    'audio_providers': ['youtube-music'],
    'youtube': {
        'cookies_file': '',
        'cookies_from_browser': '',
        'download_timeout_seconds': 1800,
    },
    'slskd': {
        'enabled': False,
        'base_url': '',
        'api_key': '',
        'download_dir': '/downloads',
        'source_dir': '/slskd',
        'leave_in_place': True,
        'timeout_seconds': 20,
        'search_retries': 5,
        'search_poll_seconds': 15,
        'download_attempts': 5,
        'poll_interval_seconds': 5,
        'poll_max_attempts': 60,
        'download_timeout_seconds': 600,
        'queued_timeout_seconds': 180,
        'duration_tolerance_seconds': 10,
        'duration_tolerance_percent': 15,
        'mix_duration_tolerance_percent': 50,
        'extensions': ['mp3', 'flac'],
        'min_bitrate': 256,
    },
    'lyrics_providers': ['lrclib'],
    'download_lyrics': True,
    'format': 'mp3',
    'bitrate': '320',
    'output': '{artists} - {title}.{output-ext}',
    'generate_m3u': True,
    'sync_navidrome': True,
    'navidrome': {
        'enabled': False,
        'url': '',
        'username': '',
        'password': '',
        'admin_username': '',
        'admin_password': '',
        'public_playlist': False,
        'scan_after_download': True,
        'scan_full': False,
        'scan_wait_seconds': 120,
        'scan_poll_seconds': 5,
        'scan_retry_seconds': 15,
        'client_name': 'Downtify',
        'api_version': '1.16.1',
    },
    'max_parallel_downloads': 3,
    'organize_by_artist': False,
    'cache_cover_art': False,
}


def _youtube_cookies_storage_path(settings_path: Optional[Path]) -> Path:
    if settings_path is not None:
        return settings_path.parent / DEFAULT_YOUTUBE_COOKIES_BASENAME
    return Path('/data') / DEFAULT_YOUTUBE_COOKIES_BASENAME


def _effective_youtube_settings(settings: dict[str, Any]) -> dict[str, Any]:
    raw = settings.get('youtube')
    if not isinstance(raw, dict):
        raw = {}
    return {
        'cookies_file': str(raw.get('cookies_file') or '').strip(),
        'cookies_from_browser': str(
            raw.get('cookies_from_browser') or ''
        ).strip(),
        'download_timeout_seconds': _setting_int(
            raw,
            'download_timeout_seconds',
            1800,
            minimum=60,
            maximum=7200,
        ),
    }


def _youtube_settings_for_response(settings: dict[str, Any]) -> dict[str, Any]:
    yt = _effective_youtube_settings(settings)
    path = yt.get('cookies_file') or ''
    cookie_path = Path(path) if path else None
    health = (
        inspect_youtube_cookies(cookie_path)
        if cookie_path is not None
        else {
            'exists': False,
            'looks_authenticated': False,
            'auth_cookies_found': [],
            'warnings': [],
        }
    )
    return {
        **yt,
        'cookies_file_exists': bool(path and Path(path).is_file()),
        'cookies_looks_authenticated': bool(health.get('looks_authenticated')),
        'cookies_auth_names': list(health.get('auth_cookies_found') or []),
        'cookies_warnings': list(health.get('warnings') or []),
    }


def _effective_audio_providers(settings: dict[str, Any]) -> list[str]:
    allowed = {'youtube-music', 'youtube', 'slskd'}
    slskd_cfg = _effective_slskd_settings(settings)
    out: list[str] = []
    seen: set[str] = set()
    for raw in settings.get('audio_providers') or []:
        p = str(raw or '').strip()
        if p == 'slskd' and not bool(slskd_cfg.get('enabled')):
            continue
        if p in allowed and p not in seen:
            seen.add(p)
            out.append(p)
    if not out:
        return ['youtube-music']
    # UI historically stored a single provider; keep playlist downloads useful
    # by falling back to YouTube when slskd is selected without a backup.
    if 'slskd' in out and not any(
        p in out for p in ('youtube', 'youtube-music')
    ):
        for fallback in ('youtube-music', 'youtube'):
            if fallback not in seen:
                seen.add(fallback)
                out.append(fallback)
    return out


def _setting_int(
    data: dict[str, Any],
    key: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int(data.get(key) or default)
    except (TypeError, ValueError):
        value = default
    return min(maximum, max(minimum, value))


def _slskd_core_fields(
    raw: dict[str, Any],
) -> tuple[str, str, str, str, bool]:
    base_url = str(raw.get('base_url') or '').strip().rstrip('/')
    download_dir = str(raw.get('download_dir') or '/downloads').strip()
    api_key = str(raw.get('api_key') or '').strip()
    leave_in_place = raw.get('leave_in_place')
    leave_default = leave_in_place is None or bool(leave_in_place)
    source_dir = str(raw.get('source_dir') or '').strip()
    if not source_dir:
        source_dir = '/slskd' if leave_default else download_dir
    if leave_in_place is None:
        leave_in_place = True
    else:
        leave_in_place = bool(leave_in_place)
    return base_url, download_dir, api_key, source_dir, leave_in_place


def _slskd_extensions(raw: dict[str, Any]) -> list[str]:
    raw_ext = raw.get('extensions')
    if isinstance(raw_ext, list):
        extensions = [
            str(e).strip().lower().lstrip('.')
            for e in raw_ext
            if str(e).strip()
        ]
    elif isinstance(raw_ext, str) and raw_ext.strip():
        extensions = [
            e.strip().lower().lstrip('.')
            for e in raw_ext.split(',')
            if e.strip()
        ]
    else:
        extensions = ['mp3', 'flac']
    if not extensions:
        extensions = ['mp3', 'flac']
    return extensions


def _slskd_numeric_settings(
    raw: dict[str, Any], settings: dict[str, Any]
) -> dict[str, int]:
    try:
        min_bitrate = int(raw.get('min_bitrate') or 256)
    except (TypeError, ValueError):
        min_bitrate = 256
    return {
        'timeout_seconds': _setting_int(
            raw, 'timeout_seconds', 20, minimum=5, maximum=120
        ),
        'search_retries': _setting_int(
            raw, 'search_retries', 5, minimum=1, maximum=20
        ),
        'search_poll_seconds': _setting_int(
            raw, 'search_poll_seconds', 15, minimum=3, maximum=60
        ),
        'download_attempts': _setting_int(
            raw, 'download_attempts', 5, minimum=1, maximum=10
        ),
        'poll_interval_seconds': _setting_int(
            raw, 'poll_interval_seconds', 5, minimum=1, maximum=30
        ),
        'poll_max_attempts': _setting_int(
            raw, 'poll_max_attempts', 60, minimum=1, maximum=300
        ),
        'download_timeout_seconds': _setting_int(
            raw, 'download_timeout_seconds', 600, minimum=30, maximum=3600
        ),
        'queued_timeout_seconds': _setting_int(
            raw, 'queued_timeout_seconds', 180, minimum=15, maximum=3600
        ),
        'duration_tolerance_seconds': _setting_int(
            raw, 'duration_tolerance_seconds', 10, minimum=1, maximum=120
        ),
        'duration_tolerance_percent': _setting_int(
            raw, 'duration_tolerance_percent', 15, minimum=1, maximum=100
        ),
        'mix_duration_tolerance_percent': _setting_int(
            raw, 'mix_duration_tolerance_percent', 50, minimum=1, maximum=200
        ),
        'min_bitrate': min_bitrate,
        'max_parallel_downloads': _setting_int(
            settings, 'max_parallel_downloads', 3, minimum=1, maximum=8
        ),
    }


def _effective_slskd_settings(settings: dict[str, Any]) -> dict[str, Any]:
    raw = settings.get('slskd')
    if not isinstance(raw, dict):
        raw = {}
    base_url, download_dir, api_key, source_dir, leave_in_place = (
        _slskd_core_fields(raw)
    )
    nums = _slskd_numeric_settings(raw, settings)

    return {
        'enabled': bool(raw.get('enabled', False)),
        'base_url': base_url,
        'api_key': api_key,
        'download_dir': download_dir,
        'source_dir': source_dir,
        'leave_in_place': leave_in_place,
        'extensions': _slskd_extensions(raw),
        **nums,
    }


def _effective_lyrics_providers(settings: dict[str, Any]) -> list[str]:
    if not settings.get('download_lyrics', True):
        return []
    return [
        p
        for p in (settings.get('lyrics_providers') or [])
        if isinstance(p, str) and p
    ]


class ConnectionManager:
    """Tracks the active WebSocket clients keyed by ``client_id``."""

    def __init__(self) -> None:
        self._clients: dict[str, WebSocket] = {}

    async def connect(self, client_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._clients[client_id] = ws

    def disconnect(self, client_id: str) -> None:
        self._clients.pop(client_id, None)

    async def send(self, client_id: str, message: dict[str, Any]) -> None:
        ws = self._clients.get(client_id)
        if ws is None:
            return
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            self._clients.pop(client_id, None)

    async def broadcast(self, message: dict[str, Any]) -> None:
        dead: list[str] = []
        for client_id, ws in list(self._clients.items()):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(client_id)
        for client_id in dead:
            self._clients.pop(client_id, None)


class AppState:
    version: str = '0.0.0'
    downloader: Optional[Downloader] = None
    connections: ConnectionManager = ConnectionManager()
    settings: dict[str, Any] = dict(DEFAULT_SETTINGS)
    settings_path: Optional[Path] = None
    loop: Optional[asyncio.AbstractEventLoop] = None
    monitor_db: Optional[PlaylistMonitorDB] = None
    track_index: Optional[TrackIndex] = None
    navidrome_index: Optional[NavidromeIndex] = None
    metadata_cache: Optional[LibraryMetadataCache] = None
    cover_cache: Optional[CoverArtCache] = None
    playlist_catalog: Optional[PlaylistCatalog] = None
    playlist_batch_store: Optional[PlaylistBatchStore] = None
    playlist_spotify_cache: Optional[PlaylistSpotifyCache] = None
    download_jobs: dict[str, dict[str, Any]] = {}
    download_limiter: Optional[DownloadParallelLimiter] = None


state = AppState()
router = APIRouter()


def _merge_saved_settings(saved: dict[str, Any]) -> dict[str, Any]:
    merged = dict(DEFAULT_SETTINGS)
    for k, v in saved.items():
        if k in DEFAULT_SETTINGS:
            if (
                k in {'slskd', 'navidrome', 'youtube'}
                and isinstance(v, dict)
                and isinstance(DEFAULT_SETTINGS.get(k), dict)
            ):
                merged[k] = {**DEFAULT_SETTINGS[k], **v}
            else:
                merged[k] = v
    return merged


def _settings_file_missing_defaults(
    saved: Optional[dict[str, Any]], merged: dict[str, Any]
) -> bool:
    if not isinstance(saved, dict):
        return False
    for key, default_val in DEFAULT_SETTINGS.items():
        if key not in saved:
            return True
        if key in {'slskd', 'navidrome', 'youtube'} and isinstance(
            default_val, dict
        ):
            saved_nested = saved.get(key)
            if not isinstance(saved_nested, dict):
                return True
            if set(default_val) - set(saved_nested):
                return True
    return False


def _load_settings(path: Path) -> dict[str, Any]:
    """Load saved settings from *path*, merging with DEFAULT_SETTINGS as base."""

    saved: Optional[dict[str, Any]] = None
    try:
        if path.is_file():
            raw = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(raw, dict):
                saved = raw
    except Exception:
        logger.opt(exception=True).debug('settings load failed path={}', path)

    if isinstance(saved, dict):
        merged = _merge_saved_settings(saved)
    else:
        merged = dict(DEFAULT_SETTINGS)

    if not path.is_file() or _settings_file_missing_defaults(saved, merged):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            _save_settings(path, merged)
        except Exception as exc:
            logger.warning('Could not persist merged settings: {}', exc)

    return merged


def _save_settings(path: Path, settings: dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps(settings, indent=2), encoding='utf-8')
    except Exception as exc:
        logger.warning('Could not persist settings: {}', exc)


@router.get('/api/version')
def get_version() -> str:
    return state.version


@router.get('/api/check_update')
def check_update() -> Optional[dict[str, Any]]:
    return None


@router.get('/api/songs/search')
def search_endpoint(query: str = Query('')) -> list[dict[str, Any]]:
    results = providers.search_songs(query, limit=20)
    if results:
        return results
    q = query.strip()
    if not q:
        return []
    slskd_cfg = _effective_slskd_settings(state.settings)
    providers_list = _effective_audio_providers(state.settings)
    if 'slskd' in providers_list and slskd_cfg.get('enabled'):
        stub = providers.song_stub_from_text_query(q)
        if stub:
            logger.info(
                'Search fallback for slskd: q={!r} title={!r} artists={}',
                q,
                stub.get('name'),
                stub.get('artists'),
            )
            return [stub]
    return []


@router.get('/api/song/url')
def song_url_endpoint(url: str = Query(...)):
    return _resolve_url(url)


@router.get('/api/url')
def url_endpoint(url: str = Query(...)):
    return _resolve_url(url)


def _resolve_url(url: str):
    parsed = spotify.parse_spotify_url(url)
    if parsed is None:
        raise HTTPException(status_code=400, detail='Invalid Spotify URL')
    kind, sid = parsed
    try:
        if kind == 'track':
            return _fetch_track_metadata(sid)
        if kind == 'album':
            return spotify.album_tracks_from_id(sid)
        if kind == 'playlist':
            _name, tracks = _fetch_playlist_tracks(sid)
            return tracks
    except Exception as exc:
        logger.exception('Failed to resolve Spotify URL {}', url)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    raise HTTPException(
        status_code=400, detail=f'Unsupported entity type: {kind}'
    )


def _merge_client_track_hints(
    base: dict[str, Any],
    hints: Optional[dict[str, Any]],
) -> None:
    """Copy tagging fields from the client-resolved Spotify row.

    ``POST /api/download/url`` re-fetches metadata from the URL only, which loses
    ``track_number`` for rows that came from an album/playlist browse, and drops
    a manual ``youtube_id`` override from the failed-queue retry flow.
    """

    if not isinstance(hints, dict) or not hints:
        return
    tn = hints.get('track_number')
    if tn is not None:
        try:
            iv = int(tn)
        except (TypeError, ValueError):
            pass
        else:
            if iv > 0:
                base['track_number'] = iv
    tt = hints.get('album_track_total')
    if tt is not None:
        try:
            tv = int(tt)
        except (TypeError, ValueError):
            pass
        else:
            if tv > 0:
                base['album_track_total'] = tv
    rd = hints.get('release_date')
    if isinstance(rd, str) and rd.strip():
        base['release_date'] = rd.strip()
    yr = hints.get('year')
    if isinstance(yr, str) and yr.strip():
        base['year'] = yr.strip()
    ytid = hints.get('youtube_id')
    if ytid is not None:
        if isinstance(ytid, str):
            stripped = ytid.strip()
            if stripped:
                base['youtube_id'] = stripped
                base['youtube_id_override'] = True
        else:
            converted = str(ytid).strip()
            if converted:
                base['youtube_id'] = converted
                base['youtube_id_override'] = True
    if hints.get('slskd_override'):
        base['slskd_override'] = True
        for key in ('slskd_username', 'slskd_filename'):
            val = hints.get(key)
            if isinstance(val, str) and val.strip():
                base[key] = val.strip()
        sz = hints.get('slskd_size')
        if sz is not None:
            try:
                base['slskd_size'] = int(sz)
            except (TypeError, ValueError):
                pass


def _song_from_download_request(
    url: str, client_hints: Optional[dict[str, Any]]
) -> dict[str, Any]:
    if (
        isinstance(client_hints, dict)
        and client_hints.get('source') == 'text_search'
    ):
        return dict(client_hints)
    song = _song_for_download(url)
    _merge_client_track_hints(song, client_hints)
    return song


def _song_for_download(url: str) -> dict[str, Any]:
    parsed = spotify.parse_spotify_url(url)
    if parsed is not None:
        kind, sid = parsed
        if kind == 'track':
            return _fetch_track_metadata(sid)
        raise HTTPException(
            status_code=400,
            detail='Only Spotify track URLs are supported here',
        )
    if 'youtube.com' in url or 'youtu.be' in url or 'music.youtube' in url:
        match = re.search(r'(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})', url)
        if not match:
            raise HTTPException(status_code=400, detail='Invalid YouTube URL')
        return providers.song_from_video_id(match.group(1))
    raise HTTPException(status_code=400, detail='Unsupported URL')


def _register_job(song: dict[str, Any], status: str = 'queued') -> str:
    song_id = str(song.get('song_id') or song.get('url') or id(song))
    state.download_jobs[song_id] = {
        'song': song,
        'status': status,
        'progress': 0,
        'message': '',
        'provider': '',
        'filename': None,
    }
    return song_id


async def _run_download(  # noqa: PLR0914
    song: dict[str, Any],
    song_id: str,
    subdir: Optional[str] = None,
    *,
    playlist_name: Optional[str] = None,
    spotify_playlist_id: Optional[str] = None,
    track_order: int = 0,
    refresh_playlists: bool = True,
) -> Optional[str]:
    """Run a single download to completion, updating jobs state and broadcasting WS events."""

    if state.downloader is None:
        raise RuntimeError('Downloader not ready')

    loop = state.loop or asyncio.get_running_loop()
    logger.info(
        'download start: title={!r} artists={} providers={}',
        song.get('name'),
        song.get('artists'),
        getattr(state.downloader, 'audio_providers', None),
    )
    job = state.download_jobs.get(song_id)
    if job is None:
        song_id = _register_job(song, status='queued')
        job = state.download_jobs[song_id]

    def _lookup_existing() -> Optional[tuple[str, str]]:
        return resolve_existing_download(
            state.downloader,
            song,
            subdir=subdir,
            track_index=state.track_index,
        )

    existing_hit = await loop.run_in_executor(None, _lookup_existing)
    if existing_hit:
        existing, skip_message = existing_hit
        logger.info(
            'download skip: {} title={!r} path={}',
            skip_message.lower(),
            song.get('name'),
            existing,
        )
        job['status'] = 'done'
        job['filename'] = existing
        job['progress'] = 100
        job['message'] = skip_message
        await state.connections.broadcast({
            'song': song,
            'progress': 100,
            'message': skip_message,
            'status': 'done',
            'filename': existing,
        })
        return existing

    _TERMINAL_JOB_STATUSES = frozenset({'done', 'error'})

    def progress(
        pct: float, message: str, provider: Optional[str] = None
    ) -> None:
        j = state.download_jobs.get(song_id)
        if j and j.get('status') in _TERMINAL_JOB_STATUSES:
            return
        if j:
            j['status'] = 'downloading'
            j['progress'] = pct
            if message:
                j['message'] = message
            if provider:
                j['provider'] = provider
        asyncio.run_coroutine_threadsafe(
            state.connections.broadcast({
                'song': song,
                'progress': pct,
                'message': message or (j or {}).get('message', ''),
                'provider': provider or (j or {}).get('provider', ''),
                'status': 'downloading',
            }),
            loop,
        )

    yt_timeout = 1800
    if state.downloader is not None:
        yt_timeout = int(
            (state.downloader.youtube_settings or {}).get(
                'download_timeout_seconds'
            )
            or 1800
        )
    yt_timeout = min(7200, max(60, yt_timeout))

    limiter = state.download_limiter
    try:
        async with (
            limiter if limiter is not None else contextlib.nullcontext()
        ):
            job['status'] = 'downloading'
            job['progress'] = job.get('progress') or 0
            await state.connections.broadcast({
                'song': song,
                'progress': job['progress'],
                'message': job.get('message') or '',
                'provider': job.get('provider') or '',
                'status': 'downloading',
            })
            try:
                filename = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: state.downloader.download(
                            song, progress, subdir=subdir
                        ),
                    ),
                    timeout=yt_timeout,
                )
            except TimeoutError as exc:
                msg = str(exc).strip() or (
                    f'Download timed out after {yt_timeout}s '
                    '(YouTube convert or network may have stalled)'
                )
                logger.warning(
                    'Download timed out for {!r} ({}) after {}s: {}',
                    song.get('name'),
                    song_id,
                    yt_timeout,
                    msg,
                )
                job['status'] = 'error'
                job['progress'] = 0
                job['message'] = msg
                await state.connections.broadcast({
                    'song': song,
                    'progress': 0,
                    'message': msg,
                    'status': 'error',
                })
                return None
    except NoAudioMatchError as exc:
        logger.warning(
            'No audio source for {!r} ({})',
            song.get('name'),
            song_id,
        )
        job['status'] = 'error'
        job['message'] = str(exc)
        await state.connections.broadcast({
            'song': song,
            'progress': 0,
            'message': str(exc),
            'status': 'error',
        })
        return None
    except Exception as exc:
        logger.exception('Download failed for {}', song_id)
        job['status'] = 'error'
        job['message'] = f'Error: {exc}'
        await state.connections.broadcast({
            'song': song,
            'progress': 0,
            'message': f'Error: {exc}',
            'status': 'error',
        })
        raise

    job['status'] = 'done'
    job['filename'] = filename
    job['progress'] = 100
    job['message'] = 'Done'
    await state.connections.broadcast({
        'song': song,
        'progress': 100,
        'message': 'Done',
        'status': 'done',
        'filename': filename,
    })
    if filename:
        pl_name = playlist_name
        pl_id = spotify_playlist_id
        order = track_order
        affected = await loop.run_in_executor(
            None,
            lambda: _register_download_playlists_on_disk(
                song,
                filename,
                playlist_name=pl_name,
                spotify_playlist_id=pl_id,
                track_order=order,
            ),
        )
        if refresh_playlists and affected:
            await _schedule_playlist_refresh_after_download(affected)
    if filename and state.navidrome_index is not None:
        dl_dir = Path(state.downloader.download_dir)
        slskd = slskd_dir_from_downloader(state.downloader)
        await loop.run_in_executor(
            None,
            lambda: cache_navidrome_song_id(
                state.settings,
                song,
                filename,
                state.navidrome_index,
                download_dir=dl_dir,
                slskd_dir=slskd,
            ),
        )
    if (
        filename
        and state.metadata_cache is not None
        and state.downloader is not None
    ):
        dl_dir = Path(state.downloader.download_dir)
        slskd = slskd_dir_from_downloader(state.downloader)
        cache = state.metadata_cache
        await loop.run_in_executor(
            None,
            lambda: cache.refresh_stored_path(
                filename, download_dir=dl_dir, slskd_dir=slskd
            ),
        )
    if (
        filename
        and state.settings.get('cache_cover_art')
        and state.cover_cache is not None
        and state.downloader is not None
    ):
        dl_dir = Path(state.downloader.download_dir)
        slskd = slskd_dir_from_downloader(state.downloader)
        cover_cache = state.cover_cache
        await loop.run_in_executor(
            None,
            lambda: cover_cache.refresh_stored_path(
                filename, download_dir=dl_dir, slskd_dir=slskd
            ),
        )
    return filename


@router.post('/api/download/url')
async def download_endpoint(
    url: str = Query(...),
    client_id: str = Query(''),
    client_hints: Optional[dict[str, Any]] = Body(None),
):
    if state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')

    song = _song_from_download_request(url, client_hints)
    pl_ctx = _playlist_context_from_hints(client_hints)
    logger.info(
        'download/url: title={!r} artists={} source={} url={}',
        song.get('name'),
        song.get('artists'),
        song.get('source'),
        str(song.get('url') or url)[:140],
    )
    song_id = _register_job(song, status='queued')

    try:
        filename = await _run_download(
            song,
            song_id,
            subdir=pl_ctx.get('subdir'),
            playlist_name=pl_ctx.get('playlist_name'),
            spotify_playlist_id=pl_ctx.get('spotify_playlist_id'),
            track_order=int(pl_ctx.get('track_order') or 0),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if filename is None:
        raise HTTPException(
            status_code=404,
            detail='Could not find an audio match',
        )
    return filename


def _songs_for_navidrome_sync(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    downloader = state.downloader
    download_dir = (
        Path(downloader.download_dir) if downloader is not None else None
    )
    slskd_dir = (
        slskd_dir_from_downloader(downloader)
        if downloader is not None
        else None
    )
    for r in results:
        if not r or not r.get('filename'):
            continue
        song = dict(r.get('song') or {})
        song['filename'] = r['filename']
        if download_dir is not None:
            song = enrich_song_from_library_file(song, download_dir, slskd_dir)
        out.append(song)
    return out


async def _sync_playlist_navidrome(
    playlist_name: str,
    results: list[dict[str, Any]],
) -> None:
    if not _effective_navidrome_settings(state.settings).get('enabled'):
        return
    if state.settings.get('sync_navidrome', True) is False:
        return
    songs = _songs_for_navidrome_sync(results)
    if not songs:
        return
    try:
        download_dir = (
            Path(state.downloader.download_dir)
            if state.downloader is not None
            else None
        )
        await asyncio.to_thread(
            sync_playlist_to_navidrome,
            playlist_name,
            songs,
            state.settings,
            navidrome_index=state.navidrome_index,
            download_dir=download_dir,
            delete_tag_mismatches=tag_mismatch_delete_context_from_state(state),
        )
    except Exception:
        logger.exception(
            'Navidrome sync failed for playlist {}', playlist_name
        )


def _rebuild_playlist_catalog_from_library(
    playlist_name: str,
    spotify_playlist_id: str,
) -> int:
    """Link every on-disk Spotify playlist track into the catalog (upsert)."""

    if (
        state.playlist_catalog is None
        or state.downloader is None
        or state.track_index is None
    ):
        return 0
    sid = str(spotify_playlist_id or '').strip()
    if not sid:
        return 0
    try:
        resolved_name, tracks = _fetch_playlist_tracks(sid)
    except Exception:
        logger.opt(exception=True).warning(
            'playlist batch: catalog rebuild failed for {!r}',
            playlist_name,
        )
        return 0
    pl_name = str(resolved_name or playlist_name or '').strip()
    if not pl_name:
        return 0

    subdir = _playlist_subdir_for_name(pl_name)
    catalog_filenames = _catalog_filenames_for_playlist(pl_name, sid)
    dl_dir = Path(state.downloader.download_dir)
    slskd = slskd_dir_from_downloader(state.downloader)
    state.playlist_catalog.ensure_playlist(pl_name, spotify_id=sid)

    linked = 0
    for index, track in enumerate(tracks):
        filename: Optional[str] = None
        full: Optional[Path] = None
        hit = resolve_existing_download(
            state.downloader,
            track,
            subdir=subdir,
            track_index=state.track_index,
        )
        if hit:
            filename = hit[0]
            full = locate_library_file(filename, dl_dir, slskd)
        else:
            tid = normalize_spotify_track_id(track)
            if tid and catalog_filenames:
                filename = str(catalog_filenames.get(tid) or '').strip()
                if filename:
                    full = locate_library_file(filename, dl_dir, slskd)
        if filename and full is not None:
            state.playlist_catalog.upsert_track(
                pl_name, track, filename, full, track_order=index
            )
            linked += 1
    return linked


async def _process_batch(
    songs: list[dict[str, Any]],
    job_ids: list[str],
    playlist_url: str,
    generate_m3u: bool,
    batch_id: Optional[int] = None,
) -> None:
    # Resolve the playlist name up-front so all tracks land in a single,
    # per-playlist sub-folder. Loose batches (e.g. albums or unrelated
    # tracks) keep the legacy flat layout under download_dir.
    playlist_subdir: Optional[str] = None
    playlist_name: Optional[str] = None
    spotify_playlist_id: Optional[str] = None
    spotify_track_count = 0
    parsed = spotify.parse_spotify_url(playlist_url) if playlist_url else None
    if parsed is not None and parsed[0] == 'playlist':
        spotify_playlist_id = parsed[1]
        try:
            playlist_name, tracks = await asyncio.to_thread(
                _fetch_playlist_tracks, spotify_playlist_id, refresh=True
            )
            spotify_track_count = len(tracks)
            playlist_subdir = m3u.sanitize_playlist_name(playlist_name)
        except Exception:
            logger.exception(
                'Failed to resolve playlist name for {}', playlist_url
            )

    if batch_id is not None and playlist_name and state.playlist_batch_store:
        await asyncio.to_thread(
            state.playlist_batch_store.update_batch_name,
            batch_id,
            playlist_name,
        )

    async def _bounded(
        song: dict[str, Any], song_id: str, track_order: int
    ) -> dict[str, Any]:
        try:
            filename = await _run_download(
                song,
                song_id,
                subdir=playlist_subdir,
                playlist_name=playlist_name,
                spotify_playlist_id=spotify_playlist_id,
                track_order=track_order,
                refresh_playlists=False,
            )
        except Exception:
            filename = None
        return {'song': song, 'filename': filename}

    results = await asyncio.gather(
        *[
            _bounded(s, sid, index)
            for index, (s, sid) in enumerate(zip(songs, job_ids))
        ],
        return_exceptions=False,
    )

    succeeded = sum(1 for r in results if r and r.get('filename'))
    failed = len(results) - succeeded

    if playlist_name:
        logger.info(
            'playlist batch: name={!r} downloaded={}/{} failed={}',
            playlist_name,
            succeeded,
            len(songs),
            failed,
        )

    if batch_id is not None and state.playlist_batch_store is not None:
        batch_status = 'complete' if failed == 0 else 'incomplete'
        await asyncio.to_thread(
            state.playlist_batch_store.finish_batch,
            batch_id,
            succeeded,
            failed,
            status=batch_status,
        )

    if not playlist_name:
        return

    partial_batch = (
        spotify_track_count > 0 and len(songs) < spotify_track_count
    )
    if partial_batch:
        logger.info(
            'playlist batch: partial run {}/{} tracks for {!r}; '
            'will rebuild full catalog before M3U/Navidrome sync',
            len(songs),
            spotify_track_count,
            playlist_name,
        )

    def _catalog_batch() -> int:
        if state.playlist_catalog is None or state.downloader is None:
            return 0
        dl_dir = Path(state.downloader.download_dir)
        slskd = slskd_dir_from_downloader(state.downloader)
        linked = 0
        for index, (song, result) in enumerate(zip(songs, results)):
            fn = (result or {}).get('filename')
            if not fn:
                continue
            full = locate_library_file(fn, dl_dir, slskd)
            if full is None:
                continue
            order = int(song.get('downtify_track_order') or index)
            state.playlist_catalog.upsert_track(
                playlist_name,
                song,
                fn,
                full,
                track_order=order,
            )
            linked += 1
        if spotify_playlist_id:
            state.playlist_catalog.ensure_playlist(
                playlist_name,
                spotify_id=spotify_playlist_id,
            )
        return linked

    batch_linked = await asyncio.to_thread(_catalog_batch)

    catalog_linked = batch_linked
    if spotify_playlist_id:
        catalog_linked = await asyncio.to_thread(
            _rebuild_playlist_catalog_from_library,
            playlist_name,
            spotify_playlist_id,
        )
        logger.info(
            'playlist batch: catalog has {} on-disk track(s) for {!r}',
            catalog_linked,
            playlist_name,
        )

    do_m3u, do_navidrome = playlist_refresh_enabled(state.settings)
    if not generate_m3u:
        do_m3u = False
    if do_m3u or do_navidrome:
        await asyncio.to_thread(
            refresh_playlists_after_moves,
            {playlist_name},
            settings=state.settings,
            downloader=state.downloader,
            playlist_catalog=state.playlist_catalog,
            track_index=state.track_index,
            monitor_db=state.monitor_db,
            navidrome_index=state.navidrome_index,
            navidrome_scan=bool(
                state.settings.get('navidrome', {}).get(
                    'scan_after_download', True
                )
            ),
            playlist_spotify_cache=state.playlist_spotify_cache,
            cover_cache=state.cover_cache,
            metadata_cache=state.metadata_cache,
        )


def _playlist_subdir_for_name(playlist_name: str) -> str:
    return m3u.sanitize_playlist_name(playlist_name)


def _catalog_filenames_for_playlist(
    playlist_name: str,
    spotify_playlist_id: str,
) -> dict[str, str]:
    """Map Spotify track id to on-disk filename from the playlist catalog."""

    if state.playlist_catalog is None:
        return {}
    sid = str(spotify_playlist_id or '').strip()
    names: list[str] = []
    if str(playlist_name or '').strip():
        names.append(str(playlist_name).strip())
    for row in state.playlist_catalog.list_playlists_with_spotify_id():
        if sid and row['spotify_id'] != sid:
            continue
        name = str(row['name'] or '').strip()
        if name and name not in names:
            names.append(name)
    by_tid: dict[str, str] = {}
    for name in names:
        for row in state.playlist_catalog.list_tracks(name):
            tid = str(row.get('track_spotify_id') or '').strip()
            filename = str(row.get('filename') or '').strip()
            if tid and filename:
                by_tid[tid] = filename
    return by_tid


def _song_row_hint(song: dict[str, Any]) -> dict[str, Any]:
    return {
        'song_id': song.get('song_id'),
        'name': song.get('name') or '',
        'artists': list(song.get('artists') or []),
        'album_name': song.get('album_name') or '',
        'cover_url': song.get('cover_url') or '',
        'url': song.get('url') or '',
        'duration': song.get('duration') or 0,
    }


def _known_spotify_playlist_sources() -> dict[str, dict[str, Any]]:
    """Merge Spotify playlist ids from batch store, catalog, and monitor."""

    sources: dict[str, dict[str, Any]] = {}
    if state.playlist_batch_store is not None:
        for batch in state.playlist_batch_store.list_latest_batches():
            sid = str(batch['spotify_playlist_id'] or '').strip()
            if not sid:
                continue
            sources[sid] = {
                'playlist_name': batch['playlist_name'],
                'playlist_url': batch['playlist_url'],
                'expected_hint': int(batch.get('expected_count') or 0),
                'batch': batch,
            }
    if state.playlist_catalog is not None:
        for row in state.playlist_catalog.list_playlists_with_spotify_id():
            sid = str(row['spotify_id'] or '').strip()
            if not sid:
                continue
            if sid not in sources:
                sources[sid] = {
                    'playlist_name': row['name'],
                    'playlist_url': f'https://open.spotify.com/playlist/{sid}',
                    'expected_hint': int(row.get('track_count') or 0),
                    'batch': None,
                }
            else:
                entry = sources[sid]
                if not entry.get('playlist_name'):
                    entry['playlist_name'] = row['name']
                if int(row.get('track_count') or 0) > int(
                    entry.get('expected_hint') or 0
                ):
                    entry['expected_hint'] = int(row['track_count'])
        monitor_by_name: dict[str, Any] = {}
        if state.monitor_db is not None:
            for pl in state.monitor_db.list_playlists():
                name = str(pl.name or '').strip()
                if name:
                    monitor_by_name[name] = pl
        batch_by_name: dict[str, dict[str, Any]] = {}
        if state.playlist_batch_store is not None:
            for batch in state.playlist_batch_store.list_latest_batches():
                name = str(batch.get('playlist_name') or '').strip()
                if name:
                    batch_by_name[name] = batch
        for name in state.playlist_catalog.list_playlist_names():
            sid = state.playlist_catalog.spotify_id_for_playlist(name) or ''
            if not sid:
                mon = monitor_by_name.get(name)
                if mon and mon.spotify_id:
                    sid = str(mon.spotify_id).strip()
                else:
                    batch = batch_by_name.get(name)
                    if batch:
                        sid = str(batch['spotify_playlist_id']).strip()
            if not sid or sid in sources:
                continue
            track_count = len(state.playlist_catalog.list_tracks(name))
            sources[sid] = {
                'playlist_name': name,
                'playlist_url': f'https://open.spotify.com/playlist/{sid}',
                'expected_hint': track_count,
                'batch': batch_by_name.get(name),
            }
    if state.monitor_db is not None:
        for pl in state.monitor_db.list_playlists():
            sid = str(pl.spotify_id or '').strip()
            if not sid:
                continue
            if sid not in sources:
                sources[sid] = {
                    'playlist_name': pl.name,
                    'playlist_url': pl.url,
                    'expected_hint': int(pl.last_track_count or 0),
                    'batch': None,
                }
            else:
                entry = sources[sid]
                if pl.name and (
                    not entry.get('playlist_name')
                    or entry['playlist_name'] == sid
                ):
                    entry['playlist_name'] = pl.name
                if pl.url:
                    entry['playlist_url'] = pl.url
    return sources


def known_spotify_playlist_ids() -> list[str]:
    """Spotify playlist ids tracked by batches, catalog, and monitor."""

    return list(_known_spotify_playlist_sources().keys())


def _resolve_playlist_batch_status(
    *,
    missing_count: int,
    active_count: int,
    expected_count: int,
    batch: Optional[dict[str, Any]] = None,
) -> str:
    """Derive batch status from live counts (not stale DB status alone)."""

    if active_count > 0:
        return 'in_progress'
    if missing_count == 0 and expected_count > 0:
        if batch is not None and state.playlist_batch_store is not None:
            if batch.get('status') != 'complete':
                state.playlist_batch_store.mark_complete(batch['id'])
        return 'complete'
    if missing_count > 0:
        return 'incomplete'
    if batch is not None and batch.get('status') == 'complete':
        return 'complete'
    if batch is not None:
        return str(batch.get('status') or 'incomplete')
    return 'complete'


def _playlist_batch_summary(
    spotify_id: str,
    playlist_name: str,
    playlist_url: str,
    *,
    batch: Optional[dict[str, Any]] = None,
    expected_hint: int = 0,
) -> dict[str, Any]:
    """Counts from cached Spotify track list + library scan."""

    active_count = active_queue_count_for_playlist(
        spotify_id, state.download_jobs
    )

    if state.playlist_catalog is not None:
        for row in state.playlist_catalog.list_playlists_with_spotify_id():
            if row['spotify_id'] != spotify_id:
                continue
            if not playlist_name or playlist_name == spotify_id:
                playlist_name = str(row['name'])
            break

    cached_name: Optional[str] = None
    cached_tracks: Optional[list[dict[str, Any]]] = None
    if state.playlist_spotify_cache is not None:
        hit = state.playlist_spotify_cache.get(spotify_id)
        if hit is not None:
            cached_name, cached_tracks = hit

    if cached_tracks is not None:
        if cached_name:
            playlist_name = cached_name
        expected_count = len(cached_tracks)
        downloaded_count = 0
        missing_count = expected_count
        if (
            cached_tracks
            and state.downloader is not None
            and state.track_index is not None
        ):
            subdir = _playlist_subdir_for_name(playlist_name)
            catalog_filenames = _catalog_filenames_for_playlist(
                playlist_name,
                spotify_id,
            )
            downloaded_count, missing_tracks = split_tracks_by_library(
                cached_tracks,
                downloader=state.downloader,
                track_index=state.track_index,
                subdir=subdir,
                catalog_filenames=catalog_filenames,
            )
            missing_count = len(missing_tracks)
        status = _resolve_playlist_batch_status(
            missing_count=missing_count,
            active_count=active_count,
            expected_count=expected_count,
            batch=batch,
        )
        if status == 'complete':
            missing_count = 0
        return {
            'batch_id': batch['id'] if batch else None,
            'spotify_playlist_id': spotify_id,
            'playlist_name': playlist_name,
            'playlist_url': playlist_url,
            'expected_count': expected_count,
            'downloaded_count': downloaded_count,
            'missing_count': missing_count,
            'missing_tracks': [],
            'active_in_queue': active_count,
            'status': status,
            'source': 'cache',
            'started_at': batch.get('started_at') if batch else None,
            'finished_at': batch.get('finished_at') if batch else None,
        }

    downloaded_count = 0
    if state.playlist_catalog is not None:
        for row in state.playlist_catalog.list_playlists_with_spotify_id():
            if row['spotify_id'] != spotify_id:
                continue
            downloaded_count = int(row.get('track_count') or 0)
            break
        if not downloaded_count and playlist_name:
            downloaded_count = len(
                state.playlist_catalog.list_tracks(playlist_name)
            )

    expected_count = max(int(expected_hint or 0), 0)
    if batch is not None:
        expected_count = max(
            expected_count, int(batch.get('expected_count') or 0)
        )

    status = 'in_progress' if active_count > 0 else 'pending'
    return {
        'batch_id': batch['id'] if batch else None,
        'spotify_playlist_id': spotify_id,
        'playlist_name': playlist_name,
        'playlist_url': playlist_url,
        'expected_count': expected_count,
        'downloaded_count': downloaded_count,
        'missing_count': 0,
        'missing_tracks': [],
        'active_in_queue': active_count,
        'status': status,
        'source': 'pending',
        'started_at': batch.get('started_at') if batch else None,
        'finished_at': batch.get('finished_at') if batch else None,
    }


def _playlist_completeness_report(
    spotify_id: str,
    playlist_name: str,
    playlist_url: str,
    *,
    batch: Optional[dict[str, Any]] = None,
    expected_hint: int = 0,
    include_missing_tracks: bool = True,
    refresh: bool = False,
) -> dict[str, Any]:
    tracks: list[dict[str, Any]] = []
    try:
        fetched_name, tracks = _fetch_playlist_tracks(
            spotify_id, refresh=refresh
        )
        if fetched_name:
            playlist_name = fetched_name
    except Exception:
        logger.opt(exception=True).debug(
            'playlist batch: Spotify fetch failed for {}',
            spotify_id,
        )

    subdir = _playlist_subdir_for_name(playlist_name)
    catalog_filenames = _catalog_filenames_for_playlist(
        playlist_name,
        spotify_id,
    )
    downloaded_count, missing_tracks = split_tracks_by_library(
        tracks,
        downloader=state.downloader,
        track_index=state.track_index,
        subdir=subdir,
        catalog_filenames=catalog_filenames,
    )
    expected_count = len(tracks) or int(expected_hint or 0)
    if batch is not None and not expected_count:
        expected_count = int(batch.get('expected_count') or 0)
    missing_count = len(missing_tracks)
    if not tracks and expected_count > downloaded_count:
        missing_count = expected_count - downloaded_count

    active_count = active_queue_count_for_playlist(
        spotify_id, state.download_jobs
    )

    status = _resolve_playlist_batch_status(
        missing_count=missing_count,
        active_count=active_count,
        expected_count=expected_count,
        batch=batch,
    )

    track_hints = (
        [_song_row_hint(t) for t in missing_tracks]
        if include_missing_tracks
        else []
    )

    return {
        'batch_id': batch['id'] if batch else None,
        'spotify_playlist_id': spotify_id,
        'playlist_name': playlist_name,
        'playlist_url': playlist_url,
        'expected_count': expected_count,
        'downloaded_count': downloaded_count,
        'missing_count': missing_count,
        'missing_tracks': track_hints,
        'active_in_queue': active_count,
        'status': status,
        'source': 'spotify',
        'started_at': batch.get('started_at') if batch else None,
        'finished_at': batch.get('finished_at') if batch else None,
    }


def _report_for_spotify_playlist(
    spotify_playlist_id: str,
    *,
    mode: str = 'estimate',
    include_missing_tracks: bool = True,
    refresh: bool = False,
) -> Optional[dict[str, Any]]:
    sid = str(spotify_playlist_id or '').strip()
    if not sid:
        return None
    meta = _known_spotify_playlist_sources().get(sid)
    if meta is None:
        return None
    batch = meta.get('batch')
    name = str(meta.get('playlist_name') or sid)
    url = str(
        meta.get('playlist_url') or f'https://open.spotify.com/playlist/{sid}'
    )
    hint = int(meta.get('expected_hint') or 0)
    if mode == 'spotify':
        return _playlist_completeness_report(
            sid,
            name,
            url,
            batch=batch if isinstance(batch, dict) else None,
            expected_hint=hint,
            include_missing_tracks=include_missing_tracks,
            refresh=refresh,
        )
    report = _playlist_batch_summary(
        sid,
        name,
        url,
        batch=batch if isinstance(batch, dict) else None,
        expected_hint=hint,
    )
    return report


def _build_playlist_batch_reports(
    *,
    include_tracks: bool = False,
) -> list[dict[str, Any]]:
    if state.downloader is None or state.track_index is None:
        return []

    builder = (
        _playlist_completeness_report
        if include_tracks
        else _playlist_batch_summary
    )
    reports: list[dict[str, Any]] = []
    for sid, meta in _known_spotify_playlist_sources().items():
        batch = meta.get('batch')
        reports.append(
            builder(
                sid,
                str(meta.get('playlist_name') or sid),
                str(
                    meta.get('playlist_url')
                    or f'https://open.spotify.com/playlist/{sid}'
                ),
                batch=batch if isinstance(batch, dict) else None,
                expected_hint=int(meta.get('expected_hint') or 0),
            )
        )
    reports.sort(
        key=lambda row: (
            row.get('status') != 'complete',
            row.get('playlist_name') or '',
        )
    )
    return reports


def collect_playlist_batch_sync_rows() -> list[dict[str, Any]]:
    """Playlist rows for startup batch registration."""

    rows: list[dict[str, Any]] = []
    for sid, meta in _known_spotify_playlist_sources().items():
        rows.append({
            'spotify_id': sid,
            'name': str(meta.get('playlist_name') or sid),
            'url': str(
                meta.get('playlist_url')
                or f'https://open.spotify.com/playlist/{sid}'
            ),
            'track_count': int(meta.get('expected_hint') or 0),
        })
    return rows


def _build_incomplete_playlist_reports(
    *,
    include_tracks: bool = False,
) -> list[dict[str, Any]]:
    """Playlists that still need work (missing tracks or active queue jobs)."""

    return [
        row
        for row in _build_playlist_batch_reports(include_tracks=include_tracks)
        if row['status'] != 'complete'
    ]


def _missing_tracks_for_playlist(
    spotify_playlist_id: str,
) -> tuple[str, str, list[dict[str, Any]]]:
    if state.downloader is None or state.track_index is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')

    sid = str(spotify_playlist_id or '').strip()
    if not sid:
        raise HTTPException(
            status_code=400, detail='spotify_playlist_id required'
        )

    try:
        playlist_name, tracks = _fetch_playlist_tracks(sid)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail='Failed to fetch playlist from Spotify'
        ) from exc

    subdir = _playlist_subdir_for_name(playlist_name)
    catalog_filenames = _catalog_filenames_for_playlist(
        playlist_name,
        sid,
    )
    _downloaded, missing = split_tracks_by_library(
        tracks,
        downloader=state.downloader,
        track_index=state.track_index,
        subdir=subdir,
        catalog_filenames=catalog_filenames,
    )
    playlist_url = f'https://open.spotify.com/playlist/{sid}'
    return playlist_name, playlist_url, missing


async def _submit_playlist_batch(
    songs: list[dict[str, Any]],
    playlist_url: str,
    *,
    generate_m3u: bool,
    batch_id: Optional[int] = None,
) -> dict[str, Any]:
    valid_songs: list[dict[str, Any]] = []
    job_ids: list[str] = []
    for song in songs:
        if not isinstance(song, dict):
            continue
        song_id = _register_job(song, status='queued')
        valid_songs.append(song)
        job_ids.append(song_id)
        await state.connections.broadcast({
            'song': song,
            'progress': 0,
            'message': '',
            'status': 'queued',
        })

    if not valid_songs:
        raise HTTPException(status_code=400, detail='No valid songs in batch')

    task = asyncio.create_task(
        _process_batch(
            valid_songs,
            job_ids,
            playlist_url,
            generate_m3u,
            batch_id,
        )
    )

    def _log_batch_failure(t: asyncio.Task) -> None:
        if t.cancelled():
            return
        exc = t.exception()
        if exc is not None:
            logger.opt(exception=exc).error('Batch processing crashed')

    task.add_done_callback(_log_batch_failure)
    return {'job_ids': job_ids, 'count': len(job_ids)}


@router.post('/api/library/reconcile')
async def reconcile_library_endpoint() -> dict[str, Any]:
    """Detect moved files and refresh playlist M3U / Navidrome."""

    if state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')
    download_dir = Path(state.downloader.download_dir)

    def _run() -> dict[str, Any]:
        result = reconcile_and_refresh(
            download_dir,
            state.settings,
            state.downloader,
            track_index=state.track_index,
            playlist_catalog=state.playlist_catalog,
            monitor_db=state.monitor_db,
            navidrome_index=state.navidrome_index,
            refresh_playlists=True,
            playlist_spotify_cache=state.playlist_spotify_cache,
            cover_cache=state.cover_cache,
            metadata_cache=state.metadata_cache,
        )
        invalidate_library_paths_cache()
        return result

    return await asyncio.to_thread(_run)


async def _schedule_playlist_refresh_after_delete(
    playlist_names: set[str],
) -> None:
    if not playlist_names or state.downloader is None:
        return
    if state.playlist_catalog is None:
        return

    async def _run() -> None:
        logger.info(
            'Library delete: scheduling M3U/Navidrome refresh for {}',
            ', '.join(sorted(playlist_names)[:8])
            + ('; ...' if len(playlist_names) > 8 else ''),
        )
        try:
            await asyncio.to_thread(
                refresh_playlists_after_moves,
                playlist_names,
                settings=state.settings,
                downloader=state.downloader,
                playlist_catalog=state.playlist_catalog,
                track_index=state.track_index,
                monitor_db=state.monitor_db,
                navidrome_index=state.navidrome_index,
                playlist_spotify_cache=state.playlist_spotify_cache,
                cover_cache=state.cover_cache,
                metadata_cache=state.metadata_cache,
            )
        except Exception:
            logger.exception(
                'library delete: background playlist refresh failed for {}',
                ', '.join(sorted(playlist_names)[:5]),
            )

    asyncio.create_task(_run())


@router.post('/api/library/delete/batch')
async def delete_library_batch_endpoint(
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """Delete multiple library files by stored relative path."""

    if state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')
    raw = body.get('files')
    if not isinstance(raw, list) or not raw:
        raise HTTPException(
            status_code=400, detail='files must be a non-empty list'
        )
    ctx = library_context_from_state(
        Path(state.downloader.download_dir),
        state.settings,
        track_index=state.track_index,
    )
    result = await asyncio.to_thread(
        delete_library_files,
        [str(f) for f in raw],
        ctx,
        state,
    )
    affected = set(result.get('playlists_affected') or [])
    if affected:
        await _schedule_playlist_refresh_after_delete(affected)
    result['playlists_refresh_scheduled'] = bool(affected)
    return result


@router.delete('/api/library/playlist')
async def delete_library_playlist_endpoint(
    playlist_name: str = Query(..., min_length=1),
) -> dict[str, Any]:
    """Delete all tracks in a playlist, its M3U, and catalog entry."""

    if state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')

    def _run() -> dict[str, Any]:
        return delete_playlist_from_library(
            playlist_name,
            Path(state.downloader.download_dir),
            state.settings,
            state,
        )

    result = await asyncio.to_thread(_run)
    if not result.get('ok'):
        raise HTTPException(
            status_code=400,
            detail=str(result.get('error') or 'Playlist delete failed'),
        )
    affected = set(result.get('playlists_affected') or [])
    if affected:
        asyncio.create_task(_schedule_playlist_refresh_after_delete(affected))
    result['playlists_refresh_scheduled'] = bool(affected)
    return result


@router.post('/api/download/batch')
async def download_batch_endpoint(request: Request) -> dict[str, Any]:
    if state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail='Invalid JSON') from exc

    songs = payload.get('songs') or []
    if not isinstance(songs, list) or not songs:
        raise HTTPException(
            status_code=400, detail='songs must be a non-empty list'
        )
    playlist_url = str(payload.get('playlist_url') or '')
    generate_m3u = bool(payload.get('generate_m3u', True))

    batch_id: Optional[int] = None
    parsed = spotify.parse_spotify_url(playlist_url) if playlist_url else None
    if (
        parsed is not None
        and parsed[0] == 'playlist'
        and state.playlist_batch_store is not None
    ):
        spotify_playlist_id = parsed[1]
        playlist_name = str(songs[0].get('album_name') or '').strip()
        if not playlist_name:
            playlist_name = spotify_playlist_id
        batch_id = await asyncio.to_thread(
            state.playlist_batch_store.start_batch,
            spotify_playlist_id,
            playlist_name,
            playlist_url,
            len(songs),
        )

    return await _submit_playlist_batch(
        songs,
        playlist_url,
        generate_m3u=generate_m3u,
        batch_id=batch_id,
    )


@router.get('/api/playlists/batches')
async def list_playlist_batches_endpoint() -> dict[str, Any]:
    """Tracked Spotify playlist batches (summary from Spotify cache)."""

    reports = await asyncio.to_thread(_build_playlist_batch_reports)
    return {'playlists': reports, 'count': len(reports)}


@router.get('/api/playlists/batches/{spotify_playlist_id}')
async def get_playlist_batch_detail_endpoint(
    spotify_playlist_id: str,
    tracks: bool = Query(default=True),
    refresh: bool = Query(default=False),
) -> dict[str, Any]:
    """Completeness for one playlist using cached Spotify track list."""

    report = await asyncio.to_thread(
        _report_for_spotify_playlist,
        spotify_playlist_id,
        mode='spotify',
        include_missing_tracks=tracks,
        refresh=refresh,
    )
    if report is None:
        raise HTTPException(status_code=404, detail='Playlist not found')
    return report


def _purge_playlist_tracking(spotify_playlist_id: str) -> None:
    sid = str(spotify_playlist_id or '').strip()
    if not sid:
        return
    batches_removed = 0
    if state.playlist_batch_store is not None:
        batches_removed = (
            state.playlist_batch_store.delete_for_spotify_playlist(sid)
        )
    if state.playlist_spotify_cache is not None:
        state.playlist_spotify_cache.delete_playlist(sid)
    monitor_removed = False
    if state.monitor_db is not None:
        monitored = state.monitor_db.get_by_spotify_id(sid)
        if monitored is not None:
            state.monitor_db.delete_playlist(monitored.id)
            monitor_removed = True
    logger.info(
        'Playlist delete: cleared tracking for {} '
        '(batch_rows={}, spotify_cache=yes, monitor={})',
        sid,
        batches_removed,
        'removed' if monitor_removed else 'none',
    )


@router.delete('/api/playlists/batches/{spotify_playlist_id}')
async def delete_playlist_batch_endpoint(
    spotify_playlist_id: str,
) -> dict[str, Any]:
    """Delete playlist audio, catalog, M3U, and batch/monitor/cache tracking."""

    sid = str(spotify_playlist_id or '').strip()
    if not sid:
        raise HTTPException(
            status_code=400, detail='spotify_playlist_id required'
        )
    if state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')

    meta = _known_spotify_playlist_sources().get(sid)
    if meta is None:
        raise HTTPException(status_code=404, detail='Playlist not found')

    playlist_name = str(meta.get('playlist_name') or sid).strip() or sid
    logger.info(
        'Playlist batch delete requested for {!r} (spotify_id={})',
        playlist_name,
        sid,
    )

    def _run() -> dict[str, Any]:
        result = delete_playlist_from_library(
            playlist_name,
            Path(state.downloader.download_dir),
            state.settings,
            state,
        )
        _purge_playlist_tracking(sid)
        return result

    result = await asyncio.to_thread(_run)
    if not result.get('ok'):
        raise HTTPException(
            status_code=400,
            detail=str(result.get('error') or 'Playlist delete failed'),
        )
    affected = set(result.get('playlists_affected') or [])
    if affected:
        asyncio.create_task(_schedule_playlist_refresh_after_delete(affected))
    result['spotify_playlist_id'] = sid
    result['playlists_refresh_scheduled'] = bool(affected)
    return result


@router.get('/api/playlists/incomplete')
async def list_incomplete_playlists_endpoint() -> dict[str, Any]:
    """Playlist batches that are still missing tracks vs Spotify."""

    reports = await asyncio.to_thread(_build_incomplete_playlist_reports)
    return {'playlists': reports, 'count': len(reports)}


@router.post('/api/playlists/incomplete/download-missing')
async def download_missing_playlist_tracks_endpoint(
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """Queue only tracks from a Spotify playlist that are not in the library."""

    if state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')

    spotify_playlist_id = str(body.get('spotify_playlist_id') or '').strip()
    playlist_url = str(body.get('playlist_url') or '').strip()
    if not spotify_playlist_id and playlist_url:
        parsed = spotify.parse_spotify_url(playlist_url)
        if parsed is not None and parsed[0] == 'playlist':
            spotify_playlist_id = parsed[1]
    if not spotify_playlist_id:
        raise HTTPException(
            status_code=400,
            detail='spotify_playlist_id or playlist_url required',
        )

    playlist_name, resolved_url, missing = await asyncio.to_thread(
        _missing_tracks_for_playlist, spotify_playlist_id
    )
    if not missing:
        if state.playlist_batch_store is not None:
            for batch in state.playlist_batch_store.list_open_batches():
                if batch['spotify_playlist_id'] == spotify_playlist_id:
                    state.playlist_batch_store.mark_complete(batch['id'])
        linked = await asyncio.to_thread(
            _rebuild_playlist_catalog_from_library,
            playlist_name,
            spotify_playlist_id,
        )
        do_m3u, do_navidrome = playlist_refresh_enabled(state.settings)
        if linked and (do_m3u or do_navidrome):
            await asyncio.to_thread(
                refresh_playlists_after_moves,
                {playlist_name},
                settings=state.settings,
                downloader=state.downloader,
                playlist_catalog=state.playlist_catalog,
                track_index=state.track_index,
                monitor_db=state.monitor_db,
                navidrome_index=state.navidrome_index,
                navidrome_scan=bool(
                    state.settings.get('navidrome', {}).get(
                        'scan_after_download', True
                    )
                ),
                playlist_spotify_cache=state.playlist_spotify_cache,
                cover_cache=state.cover_cache,
                metadata_cache=state.metadata_cache,
            )
        return {
            'count': 0,
            'message': 'Playlist already complete',
            'catalog_linked': linked,
            'playlist_refresh': bool(linked and (do_m3u or do_navidrome)),
        }

    generate_m3u = bool(body.get('generate_m3u', True))
    batch_id: Optional[int] = None
    if state.playlist_batch_store is not None:
        batch_id = await asyncio.to_thread(
            state.playlist_batch_store.start_batch,
            spotify_playlist_id,
            playlist_name,
            resolved_url,
            len(missing),
        )

    songs: list[dict[str, Any]] = []
    for index, track in enumerate(missing):
        song = dict(track)
        song['downtify_playlist_url'] = resolved_url
        song['downtify_track_order'] = index
        songs.append(song)

    result = await _submit_playlist_batch(
        songs,
        resolved_url,
        generate_m3u=generate_m3u,
        batch_id=batch_id,
    )
    result['missing_count'] = len(missing)
    result['playlist_name'] = playlist_name
    return result


@router.get('/api/queue')
def get_queue() -> list[dict[str, Any]]:
    return list(state.download_jobs.values())


@router.delete('/api/queue')
def clear_queue() -> dict:
    state.download_jobs.clear()
    return {'cleared': True}


@router.delete('/api/queue/completed')
def clear_completed_queue() -> dict:
    """Remove finished jobs so a new playlist queue is easier to read."""
    removed = [
        song_id
        for song_id, job in list(state.download_jobs.items())
        if job.get('status') == 'done'
    ]
    for song_id in removed:
        del state.download_jobs[song_id]
    return {'removed': len(removed)}


@router.delete('/api/queue/item')
def remove_queue_item(song_id: str = Query(...)) -> dict:
    if song_id in state.download_jobs:
        del state.download_jobs[song_id]
        return {'removed': True}
    return {'removed': False}


@router.post('/api/playlist/m3u')
async def write_playlist_m3u_endpoint(request: Request) -> dict[str, Any]:
    """Write an M3U for the playlist after the per-track downloads.

    The frontend POSTs ``{playlist_url, tracks: [{filename, title,
    artist, duration}, ...]}``. The playlist name is resolved
    server-side via :func:`spotify.playlist_info_and_tracks` so the
    existing ``/api/song/url`` shape stays untouched.
    """

    if state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail='Invalid JSON') from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail='Invalid payload')

    playlist_url = str(payload.get('playlist_url') or '').strip()
    if not playlist_url:
        raise HTTPException(status_code=400, detail='Missing playlist_url')
    parsed = spotify.parse_spotify_url(playlist_url)
    if parsed is None or parsed[0] != 'playlist':
        raise HTTPException(
            status_code=400, detail='Not a Spotify playlist URL'
        )

    tracks = payload.get('tracks') or []
    if not isinstance(tracks, list):
        raise HTTPException(status_code=400, detail='tracks must be a list')

    try:
        playlist_name, _tracks = await asyncio.to_thread(
            _fetch_playlist_tracks, parsed[1], refresh=True
        )
    except Exception as exc:
        logger.exception('Failed to resolve playlist {}', playlist_url)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    entries = [t for t in tracks if isinstance(t, dict)]
    playlist_subdir = m3u.sanitize_playlist_name(playlist_name)
    organize = bool(state.downloader and state.downloader.organize_by_artist)
    target, kept = m3u.write_m3u(
        state.downloader.download_dir,
        playlist_name,
        entries,
        playlist_subdir=None if organize else playlist_subdir,
        slskd_dir=slskd_dir_from_downloader(state.downloader),
    )
    if target is None:
        raise HTTPException(
            status_code=400, detail='No tracks resolved to a file on disk'
        )
    return {'path': str(target), 'count': kept}


@router.get('/api/settings')
def get_settings_endpoint(client_id: str = Query('')) -> dict[str, Any]:
    out = dict(state.settings)
    out['youtube'] = _youtube_settings_for_response(state.settings)
    return out


@router.post('/api/settings/update')
async def update_settings_endpoint(
    request: Request, client_id: str = Query('')
) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in DEFAULT_SETTINGS:
                state.settings[key] = value
        if 'youtube' in payload:
            state.settings['youtube'] = _effective_youtube_settings(
                state.settings
            )
        if 'slskd' in payload:
            state.settings['slskd'] = _effective_slskd_settings(state.settings)
            slskd_cfg = state.settings['slskd']
            if slskd_cfg.get('enabled'):
                if not str(slskd_cfg.get('base_url') or '').strip():
                    raise HTTPException(
                        status_code=400,
                        detail='slskd base URL is required when enabled',
                    )
                if not str(slskd_cfg.get('api_key') or '').strip():
                    raise HTTPException(
                        status_code=400,
                        detail='slskd API key is required when enabled',
                    )
        if 'navidrome' in payload:
            state.settings['navidrome'] = _effective_navidrome_settings(
                state.settings
            )
            nav_cfg = state.settings['navidrome']
            if nav_cfg.get('enabled'):
                if not str(nav_cfg.get('url') or '').strip():
                    raise HTTPException(
                        status_code=400,
                        detail='Navidrome URL is required when enabled',
                    )
                if not str(nav_cfg.get('username') or '').strip():
                    raise HTTPException(
                        status_code=400,
                        detail='Navidrome username is required when enabled',
                    )
                if not str(nav_cfg.get('password') or ''):
                    raise HTTPException(
                        status_code=400,
                        detail='Navidrome password is required when enabled',
                    )
        if 'audio_providers' in payload or 'slskd' in payload:
            state.settings['audio_providers'] = _effective_audio_providers(
                state.settings
            )
        if state.downloader is not None:
            if 'audio_providers' in payload:
                state.downloader.audio_providers = _effective_audio_providers(
                    state.settings
                )
            if 'slskd' in payload:
                state.downloader.slskd_settings = _effective_slskd_settings(
                    state.settings
                )
                state.downloader.audio_providers = _effective_audio_providers(
                    state.settings
                )
            fmt = payload.get('format')
            if isinstance(fmt, str) and fmt:
                state.downloader.audio_format = fmt
            bitrate = payload.get('bitrate')
            if isinstance(bitrate, str) and bitrate:
                state.downloader.audio_bitrate = bitrate
            output = payload.get('output')
            if isinstance(output, str) and output:
                state.downloader.output_template = output.replace(
                    '.{output-ext}', ''
                )
            if 'lyrics_providers' in payload or 'download_lyrics' in payload:
                state.downloader.lyrics_providers = (
                    _effective_lyrics_providers(state.settings)
                )
            if 'organize_by_artist' in payload:
                state.downloader.organize_by_artist = bool(
                    payload['organize_by_artist']
                )
            if 'youtube' in payload:
                state.downloader.youtube_settings = (
                    _effective_youtube_settings(state.settings)
                )
        if 'max_parallel_downloads' in payload:
            try:
                count = max(1, int(payload['max_parallel_downloads']))
                count = min(8, count)
                if state.download_limiter is not None:
                    await state.download_limiter.apply_limit(count)
                else:
                    state.download_limiter = DownloadParallelLimiter(count)
                if state.downloader is not None:
                    state.downloader.slskd_settings = (
                        _effective_slskd_settings(state.settings)
                    )

                reset_slskd_parallelism(state.settings)
            except (TypeError, ValueError):
                pass
    if state.settings_path is not None:
        _save_settings(state.settings_path, state.settings)
    out = dict(state.settings)
    out['youtube'] = _youtube_settings_for_response(state.settings)
    return out


def _validate_youtube_cookies_bytes(raw: bytes) -> None:
    if not raw or not raw.strip():
        raise HTTPException(status_code=400, detail='cookies file is empty')
    if len(raw) > 512_000:
        raise HTTPException(
            status_code=400, detail='cookies file is too large'
        )
    try:
        text = raw.decode('utf-8', errors='replace')
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail='cookies file must be UTF-8 text'
        ) from exc
    if 'youtube.com' not in text and 'youtube' not in text.casefold():
        raise HTTPException(
            status_code=400,
            detail='file does not look like YouTube cookies (export from youtube.com while signed in)',
        )


@router.post('/api/settings/youtube-cookies')
async def upload_youtube_cookies_endpoint(
    file: UploadFile = File(...),
    client_id: str = Query(''),
) -> dict[str, Any]:
    raw = await file.read()
    _validate_youtube_cookies_bytes(raw)
    dest = _youtube_cookies_storage_path(state.settings_path)
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f'could not write cookies file: {exc}',
        ) from exc
    merged = dict(state.settings)
    yt = _effective_youtube_settings(merged)
    yt['cookies_file'] = str(dest)
    merged['youtube'] = yt
    state.settings['youtube'] = yt
    if state.downloader is not None:
        state.downloader.youtube_settings = dict(yt)
    if state.settings_path is not None:
        _save_settings(state.settings_path, state.settings)
    logger.info('YouTube cookies saved to {}', dest)
    health = inspect_youtube_cookies(dest)
    for warning in health.get('warnings') or []:
        logger.warning('YouTube cookies upload: {}', warning)
    if health.get('looks_authenticated'):
        logger.info(
            'YouTube cookies upload: login session detected ({})',
            ', '.join(health.get('auth_cookies_found') or []),
        )
    out = dict(state.settings)
    out['youtube'] = _youtube_settings_for_response(state.settings)
    return out


@router.delete('/api/settings/youtube-cookies')
def delete_youtube_cookies_endpoint(
    client_id: str = Query(''),
) -> dict[str, Any]:
    yt = _effective_youtube_settings(state.settings)
    path_str = yt.get('cookies_file') or ''
    if path_str:
        try:
            Path(path_str).unlink(missing_ok=True)
        except OSError as exc:
            logger.warning(
                'Could not delete cookies file {}: {}', path_str, exc
            )
    state.settings['youtube'] = {
        'cookies_file': '',
        'cookies_from_browser': '',
    }
    if state.downloader is not None:
        state.downloader.youtube_settings = _effective_youtube_settings(
            state.settings
        )
    if state.settings_path is not None:
        _save_settings(state.settings_path, state.settings)
    out = dict(state.settings)
    out['youtube'] = _youtube_settings_for_response(state.settings)
    return out


@router.websocket('/api/ws')
async def websocket_endpoint(
    ws: WebSocket, client_id: str = Query(...)
) -> None:
    await state.connections.connect(client_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        state.connections.disconnect(client_id)
    except Exception:
        state.connections.disconnect(client_id)


# ---------------------------------------------------------------------------
# Playlist monitoring endpoints
# ---------------------------------------------------------------------------


def _require_monitor_db() -> PlaylistMonitorDB:
    if state.monitor_db is None:
        raise HTTPException(
            status_code=500, detail='Monitor database not ready'
        )
    return state.monitor_db


@router.get('/api/monitor/playlists')
async def list_monitor_playlists() -> list[dict[str, Any]]:
    db = _require_monitor_db()
    playlists = await asyncio.to_thread(db.list_playlists)
    return [p.to_dict() for p in playlists]


@router.post('/api/monitor/playlists')
async def add_monitor_playlist(request: Request) -> dict[str, Any]:
    db = _require_monitor_db()
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    url = payload.get('url', '')
    interval_minutes = int(payload.get('interval_minutes', 60))

    parsed = spotify.parse_spotify_url(url)
    if parsed is None or parsed[0] != 'playlist':
        raise HTTPException(
            status_code=400, detail='A valid Spotify playlist URL is required'
        )

    _, spotify_id = parsed

    existing = await asyncio.to_thread(db.get_by_spotify_id, spotify_id)
    if existing is not None:
        raise HTTPException(
            status_code=409, detail='This playlist is already being monitored'
        )

    try:
        name, _tracks = await asyncio.to_thread(
            _fetch_playlist_tracks, spotify_id, refresh=True
        )
    except Exception as exc:
        logger.exception('Failed to resolve playlist {}', spotify_id)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    playlist = await asyncio.to_thread(
        db.add_playlist, spotify_id, name, url, interval_minutes
    )

    # Kick off the first download pass immediately so the user does not have
    # to wait up to a full monitor sweep interval for the initial backfill.
    if state.downloader is not None:
        loop = state.loop or asyncio.get_running_loop()

        async def _initial_check(pl=playlist) -> None:
            try:
                await check_playlist(
                    pl,
                    db,
                    state.downloader,  # type: ignore[arg-type]
                    state.connections.broadcast,
                    loop,
                    state.settings,
                    track_index=state.track_index,
                    playlist_catalog=state.playlist_catalog,
                    playlist_spotify_cache=state.playlist_spotify_cache,
                    cover_cache=state.cover_cache,
                    metadata_cache=state.metadata_cache,
                )
            except Exception:
                logger.exception('Initial check failed for playlist {}', pl.id)

        asyncio.create_task(_initial_check())

    return playlist.to_dict()


@router.patch('/api/monitor/playlists/{playlist_id}')
async def update_monitor_playlist(
    playlist_id: int, request: Request
) -> dict[str, Any]:
    db = _require_monitor_db()
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    kwargs: dict[str, Any] = {}
    if 'interval_minutes' in payload:
        kwargs['interval_minutes'] = int(payload['interval_minutes'])
    if 'enabled' in payload:
        kwargs['enabled'] = bool(payload['enabled'])

    updated = await asyncio.to_thread(
        db.update_playlist, playlist_id, **kwargs
    )
    if updated is None:
        raise HTTPException(
            status_code=404, detail='Monitored playlist not found'
        )
    return updated.to_dict()


@router.delete('/api/monitor/playlists/{playlist_id}')
async def delete_monitor_playlist(playlist_id: int) -> dict[str, Any]:
    db = _require_monitor_db()
    deleted = await asyncio.to_thread(db.delete_playlist, playlist_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail='Monitored playlist not found'
        )
    return {'deleted': True, 'id': playlist_id}


@router.post('/api/monitor/playlists/{playlist_id}/check')
async def manual_check_playlist(playlist_id: int) -> dict[str, Any]:
    db = _require_monitor_db()
    playlist = await asyncio.to_thread(db.get_playlist, playlist_id)
    if playlist is None:
        raise HTTPException(
            status_code=404, detail='Monitored playlist not found'
        )
    if state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')

    loop = state.loop or asyncio.get_running_loop()

    async def _run() -> None:
        try:
            count = await check_playlist(
                playlist,  # type: ignore[arg-type]
                db,
                state.downloader,  # type: ignore[arg-type]
                state.connections.broadcast,
                loop,
                state.settings,
                track_index=state.track_index,
                playlist_catalog=state.playlist_catalog,
                playlist_spotify_cache=state.playlist_spotify_cache,
                cover_cache=state.cover_cache,
                metadata_cache=state.metadata_cache,
            )
            logger.info(
                'Manual check: downloaded {} new track(s) from "{}"',
                count,
                playlist.name,
            )  # type: ignore[union-attr]
        except Exception:
            logger.exception(
                'Manual check failed for playlist {}', playlist_id
            )

    asyncio.create_task(_run())
    return {'status': 'check_started', 'id': playlist_id}
