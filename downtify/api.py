"""FastAPI router exposed by Downtify.

The endpoints intentionally mirror the surface that the previous
``spotdl``-powered backend exposed so the existing Vue frontend keeps
working without changes:

* ``GET  /api/version``
* ``GET  /api/health`` (liveness probe for the Docker ``HEALTHCHECK`` -
  see ``healthcheck.sh``; always ``200`` once the server can answer
  requests, regardless of downloader/monitor readiness)
* ``GET  /api/songs/search``
* ``GET  /api/artists/search``
* ``GET  /api/artists/top_songs`` (an artist's "Top songs" shelf preview,
  same shape as ``/api/songs/search`` - no further pagination offered)
* ``GET  /api/artists/top_albums`` (an artist's 5 most popular albums,
  sorted by YouTube Music's own "Popularity" order; same shape as
  ``/api/albums/search``; for every album/single, use ``/api/url`` on
  the artist's channel URL instead)
* ``GET  /api/artists/info`` (an artist's own profile: name, thumbnail,
  bio - not their releases)
* ``GET  /api/artists/similar`` (an artist's "Fans might also like"
  shelf, same shape as ``/api/artists/search``)
* ``GET  /api/song/url`` and ``GET /api/url`` (alias; ``/api/url`` also
  resolves an artist channel or ``@handle`` URL into every one of their
  albums/singles as lightweight summaries, same shape as
  ``/api/albums/search`` - no tracklists; resolve a chosen release's
  tracks separately). A YouTube Music playlist URL resolves to its
  tracks, like a Spotify playlist.
* ``GET  /api/artists/top_songs/url`` (a Spotify or YouTube Music artist
  URL - ``open.spotify.com/artist/...``, ``/channel/UC...`` or
  ``/@handle`` - resolved to ``{source, artist_id, name, cover_url,
  songs, available}``; ``songs`` is capped at the ``limit`` query param
  (1-10, default 5); for YouTube Music, ``limit`` beyond the ~5 item
  shelf preview triggers one extra request for the shelf's full
  auto-generated playlist)
* ``POST /api/download/url`` (optional JSON body: resolved Spotify row so
  ``track_number`` / ``album_track_total`` survive re-fetch by URL)
* ``POST /api/download/album`` (YouTube Music album/browse URL only;
  downloads every track from one shared, already-resolved tracklist so
  metadata stays consistent across the whole release)
* ``POST /api/download/batch`` (JSON body ``{songs, playlist_url,
  generate_m3u}``; ``playlist_url`` may instead be omitted in favor of an
  explicit ``playlist_name`` and ``cover_url`` - e.g. for an artist's
  top-songs selection, which isn't backed by a real playlist id)
* ``POST /api/download/csv`` (import a library-export CSV from Soundiiz,
  TuneMyMusic, Exportify, etc.; JSON body ``{csv, playlist_name,
  generate_m3u}`` - the raw CSV text, read client-side, not a multipart
  upload)
* ``POST /api/playlist/m3u``
* ``GET  /api/queue``, ``DELETE /api/queue``, ``DELETE /api/queue/item``
  and ``DELETE /api/queue/completed`` (drop finished jobs only)
* ``DELETE /api/library/playlist`` (delete a downloaded playlist's
  tracks, M3U and catalog entry)
* ``POST /api/library/reconcile`` (fix stored library paths after files
  moved on disk, then refresh M3U/Navidrome playlists)
* ``GET  /api/playlists/batches`` and
  ``GET|DELETE /api/playlists/batches/{spotify_playlist_id}`` (Spotify
  playlist downloads and their completeness against Spotify)
* ``GET  /api/playlists/incomplete`` and
  ``POST /api/playlists/incomplete/download-missing`` (queue only the
  tracks a downloaded playlist is still missing)
* ``GET  /api/settings``
* ``POST /api/settings/update``
* ``GET  /api/cookies`` (current YouTube cookie configuration)
* ``POST /api/cookies`` (upload a Netscape cookies.txt as the raw request
  body - no multipart, so no ``python-multipart`` dependency)
* ``DELETE /api/cookies`` (remove the uploaded cookies.txt)
* ``WS   /api/ws``
* ``GET  /api/check_update``
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from loguru import logger

from . import library_import, m3u, providers, spotify
from .cookies import MAX_COOKIES_BYTES, CookiesStore, InvalidCookiesFile
from .cover_cache import CoverArtCache
from .downloader import (
    AUDIO_PROVIDERS,
    DOWNLOAD_EXECUTOR,
    MAX_PARALLEL_DOWNLOADS,
    Downloader,
    NoAudioMatchError,
    save_playlist_cover,
)
from .library_catalog import LibraryContext, library_context_from_state
from .library_delete import delete_playlist_from_library
from .library_metadata_cache import LibraryMetadataCache
from .library_paths import locate_library_file, slskd_dir_from_downloader
from .library_paths_cache import invalidate_library_paths_cache
from .library_reconcile import (
    playlist_refresh_enabled,
    reconcile_and_refresh,
    refresh_playlists_after_moves,
)
from .monitor import (
    KIND_ARTIST,
    KIND_PLAYLIST,
    SOURCE_SPOTIFY,
    LibraryStores,
    PlaylistMonitorDB,
    check_watch,
    download_playlist_cover,
    fetch_playlist,
    parse_playlist_url,
)
from .navidrome import _effective_navidrome_settings, cache_navidrome_song_id
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
)
from .slskd_provider import reset_slskd_parallelism
from .track_index import (
    TrackIndex,
    normalize_spotify_track_id,
    resolve_existing_download,
)
from .update_check import UpdateChecker

MIN_PARALLEL_DOWNLOADS = 1

MIN_DOWNLOAD_DELAY_SECONDS = 0
MAX_DOWNLOAD_DELAY_SECONDS = 300

MIN_COVER_RESOLUTION = 300
MAX_COVER_RESOLUTION = 1200

DEFAULT_SETTINGS: dict[str, Any] = {
    'audio_providers': ['youtube-music'],
    'lyrics_providers': ['lrclib'],
    'download_lyrics': True,
    'format': 'mp3',
    'bitrate': '320',
    'output': '{artists} - {title}.{output-ext}',
    'generate_m3u': True,
    'download_cover_art_playlists': False,
    'max_parallel_downloads': 3,
    'download_delay_seconds': 0,
    'cover_resolution': providers.DEFAULT_COVER_RESOLUTION,
    'download_cover_art': True,
    'overwrite_existing_files': True,
    'organize_by_artist': False,
    'organize_by_album': False,
    'search_albums': True,
    'mini_player_enabled': True,
    # Soulseek via slskd, used when 'slskd' is in audio_providers.
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
    # Navidrome (Subsonic API) playlist sync after playlist downloads.
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
    # Keep extracted cover art under /data/cover_cache for faster Library
    # and Player loads.
    'cache_cover_art': False,
}

# Settings stored as nested objects: saved values are merged over the
# defaults key by key, so a settings.json from an older version still gets
# every newer option.
_NESTED_SETTINGS = ('slskd', 'navidrome')


def _clamp_parallel_downloads(value: Any) -> int:
    """Coerce and clamp a requested parallel-download count.

    Keeps the setting inside ``[MIN_PARALLEL_DOWNLOADS,
    MAX_PARALLEL_DOWNLOADS]`` regardless of what the client sends, so a
    malformed or malicious payload can't spin up an unbounded number of
    concurrent yt-dlp/ffmpeg processes.
    """
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = DEFAULT_SETTINGS['max_parallel_downloads']
    return min(MAX_PARALLEL_DOWNLOADS, max(MIN_PARALLEL_DOWNLOADS, count))


def _clamp_download_delay(value: Any) -> float:
    """Coerce and clamp the requested inter-download delay, in seconds.

    Keeps the setting inside ``[MIN_DOWNLOAD_DELAY_SECONDS,
    MAX_DOWNLOAD_DELAY_SECONDS]`` regardless of what the client sends,
    so a malformed or malicious payload can't freeze batch/monitor
    downloads for an unbounded amount of time.
    """
    try:
        delay = float(value)
    except (TypeError, ValueError):
        delay = DEFAULT_SETTINGS['download_delay_seconds']
    return min(
        MAX_DOWNLOAD_DELAY_SECONDS, max(MIN_DOWNLOAD_DELAY_SECONDS, delay)
    )


def _clamp_cover_resolution(value: Any) -> int:
    """Coerce and clamp the requested cover art target size, in pixels.

    Keeps the setting inside ``[MIN_COVER_RESOLUTION,
    MAX_COVER_RESOLUTION]``. Only affects YouTube Music-sourced cover
    art (see ``providers.set_cover_resolution``); Spotify-sourced
    covers already use the largest size Spotify's embed API offers.
    """
    try:
        px = int(value)
    except (TypeError, ValueError):
        px = DEFAULT_SETTINGS['cover_resolution']
    return min(MAX_COVER_RESOLUTION, max(MIN_COVER_RESOLUTION, px))


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


def _slskd_extensions(raw: dict[str, Any]) -> list[str]:
    value = raw.get('extensions')
    if isinstance(value, str):
        value = value.split(',')
    if not isinstance(value, list):
        value = []
    extensions = [
        str(e).strip().lower().lstrip('.') for e in value if str(e).strip()
    ]
    return extensions or ['mp3', 'flac']


def _effective_slskd_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Normalized slskd settings (URLs trimmed, numbers clamped).

    ``source_dir`` defaults to ``/slskd`` when files are left in place and
    to the download folder otherwise. The parallel-download limit is taken
    from the global setting, capped at 8 for slskd.
    """

    raw = settings.get('slskd')
    if not isinstance(raw, dict):
        raw = {}
    download_dir = str(raw.get('download_dir') or '/downloads').strip()
    leave_in_place = raw.get('leave_in_place')
    leave_in_place = True if leave_in_place is None else bool(leave_in_place)
    source_dir = str(raw.get('source_dir') or '').strip() or (
        '/slskd' if leave_in_place else download_dir
    )
    try:
        min_bitrate = int(raw.get('min_bitrate') or 256)
    except (TypeError, ValueError):
        min_bitrate = 256

    def bounded(key: str, default: int, low: int, high: int) -> int:
        return _setting_int(raw, key, default, minimum=low, maximum=high)

    return {
        'enabled': bool(raw.get('enabled', False)),
        'base_url': str(raw.get('base_url') or '').strip().rstrip('/'),
        'api_key': str(raw.get('api_key') or '').strip(),
        'download_dir': download_dir,
        'source_dir': source_dir,
        'leave_in_place': leave_in_place,
        'extensions': _slskd_extensions(raw),
        'timeout_seconds': bounded('timeout_seconds', 20, 5, 120),
        'search_retries': bounded('search_retries', 5, 1, 20),
        'search_poll_seconds': bounded('search_poll_seconds', 15, 3, 60),
        'download_attempts': bounded('download_attempts', 5, 1, 10),
        'poll_interval_seconds': bounded('poll_interval_seconds', 5, 1, 30),
        'poll_max_attempts': bounded('poll_max_attempts', 60, 1, 300),
        'download_timeout_seconds': bounded(
            'download_timeout_seconds', 600, 30, 3600
        ),
        'queued_timeout_seconds': bounded(
            'queued_timeout_seconds', 180, 15, 3600
        ),
        'duration_tolerance_seconds': bounded(
            'duration_tolerance_seconds', 10, 1, 120
        ),
        'duration_tolerance_percent': bounded(
            'duration_tolerance_percent', 15, 1, 100
        ),
        'mix_duration_tolerance_percent': bounded(
            'mix_duration_tolerance_percent', 50, 1, 200
        ),
        'min_bitrate': min_bitrate,
        'max_parallel_downloads': _setting_int(
            settings, 'max_parallel_downloads', 3, minimum=1, maximum=8
        ),
    }


def _effective_audio_providers(settings: dict[str, Any]) -> list[str]:
    """Enabled audio providers in the configured order.

    slskd is dropped while it's disabled. When slskd is the only provider
    left, YouTube Music and YouTube are appended as fallbacks so a track
    slskd can't find still downloads.
    """

    slskd_enabled = bool(_effective_slskd_settings(settings).get('enabled'))
    out: list[str] = []
    for raw in settings.get('audio_providers') or []:
        name = str(raw or '').strip()
        if name == 'slskd' and not slskd_enabled:
            continue
        if name in AUDIO_PROVIDERS and name not in out:
            out.append(name)
    if not out:
        return ['youtube-music']
    if out == ['slskd']:
        out += ['youtube-music', 'youtube']
    return out


def _validate_integration_settings(
    slskd: dict[str, Any], navidrome: dict[str, Any]
) -> None:
    """Reject enabling slskd/Navidrome without the fields they need."""

    if slskd.get('enabled'):
        if not slskd.get('base_url'):
            raise HTTPException(
                status_code=400,
                detail='slskd base URL is required when enabled',
            )
        if not slskd.get('api_key'):
            raise HTTPException(
                status_code=400,
                detail='slskd API key is required when enabled',
            )
    if navidrome.get('enabled'):
        for key, label in (
            ('url', 'URL'),
            ('username', 'username'),
            ('password', 'password'),
        ):
            if not navidrome.get(key):
                raise HTTPException(
                    status_code=400,
                    detail=f'Navidrome {label} is required when enabled',
                )


def _organize_enabled() -> bool:
    """True when tracks are routed into per-artist/per-album folders.

    In that case per-playlist folders are bypassed, so the M3U must be
    written to the legacy ``Playlists/`` directory where its relative
    track paths still resolve.
    """

    d = state.downloader
    return bool(d and (d.organize_by_artist or d.organize_by_album))


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
        # Serialized once, sent to every client concurrently: one slow
        # client (a phone on a weak connection) no longer delays the rest.
        clients = list(self._clients.items())
        if not clients:
            return
        text = json.dumps(message)
        results = await asyncio.gather(
            *(ws.send_text(text) for _, ws in clients),
            return_exceptions=True,
        )
        for (client_id, ws), result in zip(clients, results):
            # Only drop that exact socket: the client may have reconnected
            # under the same id while the sends were in flight.
            if isinstance(result, Exception) and (
                self._clients.get(client_id) is ws
            ):
                self._clients.pop(client_id, None)


class AppState:
    version: str = '0.0.0'
    downloader: Optional[Downloader] = None
    connections: ConnectionManager = ConnectionManager()
    settings: dict[str, Any] = dict(DEFAULT_SETTINGS)
    settings_path: Optional[Path] = None
    cookies_store: Optional[CookiesStore] = None
    update_checker: Optional[UpdateChecker] = None
    loop: Optional[asyncio.AbstractEventLoop] = None
    monitor_db: Optional[PlaylistMonitorDB] = None
    download_jobs: dict[str, dict[str, Any]] = {}
    download_semaphore: Optional[asyncio.Semaphore] = None
    # Library stores in /data/downtify_library.db (opened at startup).
    track_index: Optional[TrackIndex] = None
    navidrome_index: Optional[NavidromeIndex] = None
    metadata_cache: Optional[LibraryMetadataCache] = None
    cover_cache: Optional[CoverArtCache] = None
    playlist_catalog: Optional[PlaylistCatalog] = None
    playlist_batch_store: Optional[PlaylistBatchStore] = None
    playlist_spotify_cache: Optional[PlaylistSpotifyCache] = None


state = AppState()
router = APIRouter()


def library_context() -> LibraryContext:
    """Where library files live (downloads + slskd folder) and the
    stores that describe them."""

    download_dir = (
        Path(state.downloader.download_dir)
        if state.downloader is not None
        else Path('/downloads')
    )
    return library_context_from_state(
        download_dir,
        state.settings,
        state.track_index,
        metadata_cache=state.metadata_cache,
        playlist_catalog=state.playlist_catalog,
    )


def library_stores() -> LibraryStores:
    """The library stores Playlist Monitor sweeps keep up to date."""

    return LibraryStores(
        track_index=state.track_index,
        playlist_catalog=state.playlist_catalog,
        navidrome_index=state.navidrome_index,
        metadata_cache=state.metadata_cache,
        cover_cache=state.cover_cache,
        playlist_spotify_cache=state.playlist_spotify_cache,
    )


def forget_library_file(stored_path: str) -> list[str]:
    """Drop a deleted file from the library stores.

    Removes it from the track index, playlist catalog, Navidrome song-id
    index and the metadata/cover caches, all keyed by its library path
    (the file itself is already gone). Returns the playlists it belonged
    to.
    """

    name = str(stored_path or '').strip().replace('\\', '/')
    if not name:
        return []
    affected: list[str] = []
    if state.playlist_catalog is not None:
        affected = state.playlist_catalog.remove_tracks_for_filename(name)
    if state.track_index is not None:
        state.track_index.remove_by_filename(name)
    if state.navidrome_index is not None:
        state.navidrome_index.forget_filename(name)
    if state.metadata_cache is not None:
        state.metadata_cache.forget(name)
    if state.cover_cache is not None:
        state.cover_cache.forget_by_stored_path(name)
    return affected


async def after_library_delete(
    results: dict[str, dict[str, Any]], response: dict[str, Any]
) -> dict[str, Any]:
    """Update the library stores after ``DELETE /delete`` or
    ``/delete/batch`` and report affected playlists on ``response``."""

    deleted = [f for f, r in results.items() if r.get('deleted')]
    affected: set[str] = set()
    if deleted:

        def _forget() -> None:
            for name in deleted:
                affected.update(forget_library_file(name))
            invalidate_library_paths_cache()

        await asyncio.to_thread(_forget)
    response['playlists_affected'] = sorted(affected)
    # The deleted tracks' playlists get their M3U/Navidrome playlist
    # rewritten in the background (can take minutes).
    response['playlists_refresh_scheduled'] = bool(affected)
    if affected:
        await _schedule_playlist_refresh_after_delete(affected)
    return response


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
    if name and state.downloader is not None and not _organize_enabled():
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


def _load_settings(path: Path) -> dict[str, Any]:
    """Load saved settings from *path*, merging with DEFAULT_SETTINGS as base."""
    try:
        saved = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(saved, dict):
            merged = dict(DEFAULT_SETTINGS)
            for k, v in saved.items():
                if k not in DEFAULT_SETTINGS:
                    continue
                if k in _NESTED_SETTINGS and isinstance(v, dict):
                    merged[k] = {**DEFAULT_SETTINGS[k], **v}
                else:
                    merged[k] = v
            merged['max_parallel_downloads'] = _clamp_parallel_downloads(
                merged['max_parallel_downloads']
            )
            merged['download_delay_seconds'] = _clamp_download_delay(
                merged['download_delay_seconds']
            )
            merged['cover_resolution'] = _clamp_cover_resolution(
                merged['cover_resolution']
            )
            return merged
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def _save_settings(path: Path, settings: dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps(settings, indent=2), encoding='utf-8')
    except Exception as exc:
        logger.warning('Could not persist settings: {}', exc)


@router.get('/api/version')
def get_version() -> str:
    return state.version


@router.get('/api/health')
def get_health() -> dict[str, Any]:
    """Liveness probe: the process is up and FastAPI is serving requests.

    Deliberately doesn't check the downloader/monitor DB — those are
    only set up once ``main.py``'s startup hook finishes, so gating
    health on them would report unhealthy during the brief, normal
    window right after boot. Docker's ``HEALTHCHECK`` already has a
    ``--start-period`` for that; this endpoint just needs to answer.
    """
    return {'status': 'ok', 'version': state.version}


@router.get('/api/check_update')
def check_update() -> Optional[dict[str, Any]]:
    """Result of the last hourly GitHub Releases check (see
    ``downtify/update_check.py``), or ``None`` before the first one has
    run — briefly, right after startup.
    """
    if state.update_checker is None:
        return None
    return state.update_checker.status(state.version)


@router.get('/api/songs/search')
def search_endpoint(query: str = Query('')) -> list[dict[str, Any]]:
    results = providers.search_songs(query, limit=20)
    if results:
        return results
    q = query.strip()
    if not q or 'slskd' not in _effective_audio_providers(state.settings):
        return []
    # With slskd enabled, a search YouTube Music has nothing for can still
    # be downloaded from Soulseek: offer the query itself as a track
    # ("Artist - Title" is split into artist and title).
    stub = providers.song_stub_from_text_query(q)
    if stub is None:
        return []
    logger.info(
        'Search fallback for slskd: q={!r} title={!r} artists={}',
        q,
        stub.get('name'),
        stub.get('artists'),
    )
    return [stub]


@router.get('/api/albums/search')
def search_albums_endpoint(
    query: str = Query(''),
    limit: int = Query(25, ge=1, le=50),
) -> list[dict[str, Any]]:
    if not state.settings.get('search_albums', True):
        return []
    return providers.search_albums(query, limit=limit)


@router.get('/api/artists/search')
def search_artists_endpoint(query: str = Query('')) -> list[dict[str, Any]]:
    return providers.search_artists(query, limit=10)


@router.get('/api/artists/top_songs')
def artist_top_songs_endpoint(
    channel_id: str = Query(...),
) -> list[dict[str, Any]]:
    return providers.artist_top_songs_from_channel_id(channel_id)


@router.get('/api/artists/top_albums')
def artist_top_albums_endpoint(
    channel_id: str = Query(...),
) -> list[dict[str, Any]]:
    return providers.artist_top_albums_from_channel_id(channel_id)


@router.get('/api/artists/info')
def artist_info_endpoint(channel_id: str = Query(...)) -> dict[str, Any]:
    return providers.artist_info_from_channel_id(channel_id)


@router.get('/api/artists/similar')
def artist_similar_endpoint(
    channel_id: str = Query(...),
) -> list[dict[str, Any]]:
    return providers.artist_similar_from_channel_id(channel_id)


@router.get('/api/song/url')
def song_url_endpoint(url: str = Query(...)):
    return _resolve_url(url)


@router.get('/api/url')
def url_endpoint(url: str = Query(...)):
    return _resolve_url(url)


def _resolve_url(url: str):
    spotify_parsed = spotify.parse_spotify_url(url)
    if spotify_parsed is not None:
        kind, sid = spotify_parsed
        try:
            if kind == 'track':
                return spotify.track_from_id(sid)
            if kind == 'album':
                return spotify.album_tracks_from_id(sid)
            if kind == 'playlist':
                return spotify.playlist_tracks_from_id(sid)
        except Exception as exc:
            logger.exception('Failed to resolve Spotify URL {}', url)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        raise HTTPException(
            status_code=400, detail=f'Unsupported entity type: {kind}'
        )

    youtube_parsed = providers.parse_youtube_url(url)
    if youtube_parsed is not None:
        kind, yid = youtube_parsed
        try:
            if kind == 'track':
                return providers.song_from_video_id(yid)
            if kind == 'album':
                return providers.album_tracks_from_browse_id(yid)
            if kind == 'playlist':
                return providers.playlist_tracks_from_id(yid)
            if kind == 'artist':
                return providers.artist_albums_from_channel_id(
                    providers.resolve_artist_channel_id(yid)
                )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception('Failed to resolve YouTube URL {}', url)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        raise HTTPException(
            status_code=400, detail=f'Unsupported entity type: {kind}'
        )

    raise HTTPException(status_code=400, detail='Invalid URL')


def _resolve_artist_top_songs(url: str, limit: int) -> dict[str, Any]:
    """Artist name, cover and up to ``limit`` top songs for a pasted
    Spotify or YouTube Music artist URL.

    Spotify is resolved against its own top-tracks shelf preview (see
    :func:`spotify.artist_top_songs_from_id`). YouTube Music uses its own
    "Top songs" shelf preview; when ``limit`` exceeds that preview, the
    shelf's own full auto-generated playlist is fetched instead (see
    :func:`providers.artist_full_top_songs_from_channel_id`).
    """

    spotify_parsed = spotify.parse_spotify_url(url)
    if spotify_parsed is not None and spotify_parsed[0] == 'artist':
        _, artist_id = spotify_parsed
        try:
            name, cover_url, songs = spotify.artist_top_songs_from_id(
                artist_id
            )
        except Exception as exc:
            logger.exception('Failed to resolve Spotify artist {}', url)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {
            'source': 'spotify',
            'artist_id': artist_id,
            'name': name,
            'cover_url': cover_url,
            'songs': songs[:limit],
            'available': len(songs),
        }

    youtube_parsed = providers.parse_youtube_url(url)
    if youtube_parsed is not None and youtube_parsed[0] == 'artist':
        _, channel_or_handle = youtube_parsed
        try:
            channel_id = providers.resolve_artist_channel_id(
                channel_or_handle
            )
            info = providers.artist_info_from_channel_id(channel_id)
            songs = providers.artist_top_songs_from_channel_id(channel_id)
            if limit > len(songs):
                fuller = providers.artist_full_top_songs_from_channel_id(
                    channel_id
                )
                if fuller:
                    songs = fuller
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception('Failed to resolve YouTube artist {}', url)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {
            'source': 'youtube',
            'artist_id': channel_id,
            'name': info.get('name') or channel_id,
            'cover_url': info.get('cover_url') or '',
            'songs': songs[:limit],
            'available': len(songs),
        }

    raise HTTPException(
        status_code=400,
        detail='A Spotify or YouTube Music artist URL is required',
    )


@router.get('/api/artists/top_songs/url')
async def artist_top_songs_from_url_endpoint(
    url: str = Query(...), limit: int = Query(5, ge=1, le=10)
) -> dict[str, Any]:
    return await asyncio.to_thread(_resolve_artist_top_songs, url, limit)


def _merge_client_track_hints(
    base: dict[str, Any],
    hints: Optional[dict[str, Any]],
) -> None:
    """Copy tagging fields from the client-resolved Spotify row.

    ``POST /api/download/url`` re-fetches metadata from the URL only, which loses
    ``track_number`` for rows that came from an album/playlist browse.
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
    # A video id the user pasted to retry a failed track: download exactly
    # that video instead of matching again.
    ytid = str(hints.get('youtube_id') or '').strip()
    if ytid:
        base['youtube_id'] = ytid
        base['youtube_id_override'] = True


def _song_from_download_request(
    url: str, client_hints: Optional[dict[str, Any]]
) -> dict[str, Any]:
    """The song to download for ``POST /api/download/url``.

    A slskd search stub (``source == 'text_search'``, see
    :func:`search_endpoint`) has no URL to resolve and is taken from the
    request body as-is.
    """

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
            return spotify.track_from_id(sid)
        raise HTTPException(
            status_code=400,
            detail='Only Spotify track URLs are supported here',
        )
    youtube_parsed = providers.parse_youtube_url(url)
    if youtube_parsed is not None:
        kind, yid = youtube_parsed
        if kind == 'track':
            return providers.song_from_video_id(yid)
        raise HTTPException(
            status_code=400,
            detail='Only single YouTube video URLs are supported here',
        )
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


async def _run_download(
    song: dict[str, Any],
    song_id: str,
    subdir: Optional[str] = None,
    delay_seconds: float = 0,
    *,
    playlist_name: Optional[str] = None,
    spotify_playlist_id: Optional[str] = None,
    track_order: int = 0,
    refresh_playlists: bool = True,
) -> Optional[str]:
    """Run a single download to completion, updating jobs state and broadcasting WS events.

    When *delay_seconds* is positive, the concurrency slot (semaphore
    permit) is held for that long after a successful download before
    being released, so the next queued download in a batch can't start
    until the delay has elapsed. This is only meant for multi-song
    orchestration (playlist/album batches); single manual downloads
    should pass ``delay_seconds=0`` so a one-off download never waits
    around for nothing.

    With *Overwrite existing files* off, a song already in the library is
    not downloaded again: by its Spotify id in the track index (wherever it
    was saved, slskd folder included) or by its filename at the
    destination.

    A finished file is registered in the track index, the playlist catalog
    (for ``playlist_name``, at ``track_order``) and the caches. Unless
    ``refresh_playlists`` is off (a batch refreshes once at the end), the
    M3U/Navidrome playlists that contain the track are refreshed in the
    background.
    """

    if state.downloader is None:
        raise RuntimeError('Downloader not ready')

    loop = state.loop or asyncio.get_running_loop()
    job = state.download_jobs.get(song_id)
    if job is None:
        song_id = _register_job(song, status='downloading')
        job = state.download_jobs[song_id]

    if not getattr(state.downloader, 'overwrite_existing_files', True):
        existing_hit = await asyncio.to_thread(
            resolve_existing_download,
            state.downloader,
            song,
            subdir=subdir,
            track_index=state.track_index,
        )
        if existing_hit:
            existing, skip_message = existing_hit
            logger.info(
                'Skipping download ({}): {}', skip_message.lower(), existing
            )
            job.update(
                status='done',
                filename=existing,
                progress=100,
                message=skip_message,
            )
            await state.connections.broadcast({
                'song': song,
                'progress': 100,
                'message': skip_message,
                'status': 'done',
                'filename': existing,
            })
            return existing

    job['status'] = 'downloading'

    await state.connections.broadcast({
        'song': song,
        'progress': 0,
        'message': '',
        'status': 'downloading',
    })

    def progress(
        pct: float, message: str, provider: Optional[str] = None
    ) -> None:
        j = state.download_jobs.get(song_id)
        if j:
            j['progress'] = pct
            j['message'] = message
            if provider:
                j['provider'] = provider
        asyncio.run_coroutine_threadsafe(
            state.connections.broadcast({
                'song': song,
                'progress': pct,
                'message': message,
                'provider': provider or (j or {}).get('provider', ''),
                'status': 'downloading',
            }),
            loop,
        )

    sem = state.download_semaphore
    try:
        async with sem if sem is not None else contextlib.nullcontext():
            filename = await loop.run_in_executor(
                DOWNLOAD_EXECUTOR,
                lambda: state.downloader.download(
                    song, progress, subdir=subdir
                ),
            )
            job['status'] = 'done'
            job['filename'] = filename
            job['progress'] = 100
            # /list and /tracks cache the directory scan briefly.
            invalidate_library_paths_cache()
            await state.connections.broadcast({
                'song': song,
                'progress': 100,
                'message': 'Done',
                'status': 'done',
                'filename': filename,
            })
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
    except Exception as exc:
        if isinstance(exc, NoAudioMatchError):
            # An expected outcome, not a crash: no traceback in the log.
            logger.warning('{} ({})', exc, song_id)
            message = str(exc)
        else:
            logger.exception('Download failed for {}', song_id)
            message = f'Error: {exc}'
        job['status'] = 'error'
        job['message'] = message
        await state.connections.broadcast({
            'song': song,
            'progress': 0,
            'message': message,
            'status': 'error',
        })
        raise

    if filename:
        await _record_finished_download(
            song,
            filename,
            playlist_name=playlist_name,
            spotify_playlist_id=spotify_playlist_id,
            track_order=track_order,
            refresh_playlists=refresh_playlists,
        )
    return filename


async def _record_finished_download(
    song: dict[str, Any],
    filename: str,
    *,
    playlist_name: Optional[str],
    spotify_playlist_id: Optional[str],
    track_order: int,
    refresh_playlists: bool,
) -> None:
    """Register a downloaded file in the library stores (best effort)."""

    downloader = state.downloader
    if downloader is None:
        return

    def _record() -> set[str]:
        affected = _register_download_playlists_on_disk(
            song,
            filename,
            playlist_name=playlist_name,
            spotify_playlist_id=spotify_playlist_id,
            track_order=track_order,
        )
        download_dir = Path(downloader.download_dir)
        slskd_dir = slskd_dir_from_downloader(downloader)
        if state.navidrome_index is not None:
            cache_navidrome_song_id(
                state.settings,
                song,
                filename,
                state.navidrome_index,
                download_dir=download_dir,
                slskd_dir=slskd_dir,
            )
        if state.metadata_cache is not None:
            state.metadata_cache.refresh_stored_path(
                filename, download_dir=download_dir, slskd_dir=slskd_dir
            )
        if state.settings.get('cache_cover_art') and state.cover_cache:
            state.cover_cache.refresh_stored_path(
                filename, download_dir=download_dir, slskd_dir=slskd_dir
            )
        return affected

    try:
        affected = await asyncio.to_thread(_record)
    except Exception:
        logger.exception('Could not register {} in the library', filename)
        return
    if refresh_playlists and affected:
        await _schedule_playlist_refresh_after_download(affected)


@router.post('/api/download/url')
async def download_endpoint(
    url: str = Query(...),
    client_id: str = Query(''),
    client_hints: Optional[dict[str, Any]] = Body(None),
):
    if state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')

    # Spotify/YouTube Music network calls: off the event loop, or every
    # other request and WebSocket stalls until they return.
    song = await asyncio.to_thread(
        _song_from_download_request, url, client_hints
    )
    # A retried track from a playlist carries its playlist in the hints,
    # so it lands in that playlist's folder and catalog.
    pl_ctx = await asyncio.to_thread(
        _playlist_context_from_hints, client_hints
    )
    logger.debug(
        'download/url: url={} body={} track_number={!r} year={!r} '
        'release_date={!r} playlist={!r}',
        url[:140],
        'json' if isinstance(client_hints, dict) else 'none',
        song.get('track_number'),
        song.get('year'),
        song.get('release_date'),
        pl_ctx.get('playlist_name'),
    )
    song_id = _register_job(song, status='downloading')

    try:
        filename = await _run_download(
            song,
            song_id,
            subdir=pl_ctx.get('subdir'),
            playlist_name=pl_ctx.get('playlist_name'),
            spotify_playlist_id=pl_ctx.get('spotify_playlist_id'),
            track_order=int(pl_ctx.get('track_order') or 0),
        )
    except NoAudioMatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return filename


def _m3u_entries_for(
    songs: list[dict[str, Any]], resolved: dict[int, Optional[str]]
) -> list[dict[str, Any]]:
    """Build M3U entries for the songs downloaded so far.

    Iterates ``songs`` in playlist order (not completion order, which
    varies with concurrency) and keeps only those with a filename in
    ``resolved``, so a partially-finished batch still produces a
    correctly-ordered file.
    """
    entries: list[dict[str, Any]] = []
    for index, song in enumerate(songs):
        filename = resolved.get(index)
        if not filename:
            continue
        entries.append({
            'filename': filename,
            'title': song.get('name') or '',
            'artist': ', '.join(song.get('artists') or []),
            'duration': song.get('duration') or 0,
        })
    return entries


async def _write_batch_m3u(
    songs: list[dict[str, Any]],
    resolved: dict[int, Optional[str]],
    playlist_name: str,
    playlist_subdir: str,
) -> Optional[Path]:
    entries = _m3u_entries_for(songs, resolved)
    if not entries:
        return None
    # When organize-by-artist/album is on, songs land in those folders
    # instead of the playlist subfolder, so the M3U must go to the legacy
    # Playlists/ directory (playlist_subdir=None) where relative paths
    # still resolve.
    organize = _organize_enabled()
    try:
        m3u_path, _kept = await asyncio.to_thread(
            m3u.write_m3u,
            state.downloader.download_dir,
            playlist_name,
            entries,
            playlist_subdir=None if organize else playlist_subdir,
            slskd_dir=slskd_dir_from_downloader(state.downloader),
        )
    except Exception:
        logger.exception('Failed to write M3U for {!r}', playlist_name)
        return None
    return m3u_path


def _save_explicit_playlist_cover(
    cover_url: str, m3u_path: Path, settings: dict[str, Any]
) -> None:
    """Save *cover_url* beside *m3u_path*, when enabled.

    Counterpart to :func:`download_playlist_cover` for a batch that isn't
    backed by a real Spotify/YouTube Music playlist id (e.g. an artist's
    top-songs selection) — the caller already knows the cover to use, so
    there's no playlist to re-fetch it from. Gated by the same
    ``download_cover_art_playlists`` setting.
    """
    if not settings.get('download_cover_art_playlists'):
        return
    try:
        save_playlist_cover(cover_url, m3u_path)
    except Exception:
        logger.exception('Failed to save cover art for {}', m3u_path)


async def _process_batch(
    songs: list[dict[str, Any]],
    job_ids: list[str],
    playlist_url: str,
    generate_m3u: bool,
    playlist_name: Optional[str] = None,
    *,
    batch_id: Optional[int] = None,
    cover_url: Optional[str] = None,
) -> None:
    # Resolve the playlist name up-front so all tracks land in a single,
    # per-playlist sub-folder. Loose batches (e.g. albums or unrelated
    # tracks) keep the legacy flat layout under download_dir. A caller
    # without a Spotify/YouTube Music playlist_url (e.g. a CSV library
    # import) can instead pass playlist_name directly.
    playlist_subdir: Optional[str] = None
    spotify_playlist_id: Optional[str] = None
    spotify_track_count = 0
    target = parse_playlist_url(playlist_url) if playlist_url else None
    if target is not None:
        try:
            playlist_name, tracks = await asyncio.to_thread(
                fetch_playlist, *target
            )
            playlist_subdir = m3u.sanitize_playlist_name(playlist_name)
            if target[0] == SOURCE_SPOTIFY:
                spotify_playlist_id = target[1]
                spotify_track_count = len(tracks)
                # Fresh Spotify track list for the playlist batch reports.
                if state.playlist_spotify_cache is not None:
                    await asyncio.to_thread(
                        state.playlist_spotify_cache.store,
                        spotify_playlist_id,
                        playlist_name,
                        tracks,
                    )
        except Exception:
            logger.exception(
                'Failed to resolve playlist name for {}', playlist_url
            )
    elif playlist_name:
        playlist_subdir = m3u.sanitize_playlist_name(playlist_name)

    if batch_id is not None and playlist_name and state.playlist_batch_store:
        await asyncio.to_thread(
            state.playlist_batch_store.update_batch_name,
            batch_id,
            playlist_name,
        )

    # A per-song delay only makes sense when there's a "next" song to
    # wait for; skip it entirely for a lone track so a single download
    # never waits around for nothing.
    delay_seconds = (
        state.settings.get('download_delay_seconds', 0)
        if len(songs) > 1
        else 0
    )

    wants_m3u = bool(generate_m3u and playlist_subdir and playlist_name)
    # Filename per song index, filled in as downloads land. The M3U is
    # rewritten from this after every completed download, so the playlist
    # grows as it downloads instead of appearing all at once at the end,
    # and one slow or hung track can't hold up what's already on disk.
    resolved: dict[int, Optional[str]] = {}
    m3u_lock = asyncio.Lock()

    async def _bounded(index: int, song: dict[str, Any], song_id: str) -> None:
        try:
            filename = await _run_download(
                song,
                song_id,
                subdir=playlist_subdir,
                delay_seconds=delay_seconds,
                playlist_name=playlist_name,
                spotify_playlist_id=spotify_playlist_id,
                track_order=int(song.get('downtify_track_order') or index),
                refresh_playlists=False,
            )
        except Exception:
            filename = None
        resolved[index] = filename
        if not (filename and wants_m3u):
            return
        # Serialized so concurrent downloads can't interleave writes to
        # the same file.
        async with m3u_lock:
            await _write_batch_m3u(
                songs, resolved, playlist_name, playlist_subdir
            )

    await asyncio.gather(
        *[
            _bounded(i, s, sid)
            for i, (s, sid) in enumerate(zip(songs, job_ids))
        ],
        return_exceptions=False,
    )

    if wants_m3u:
        m3u_path = await _write_batch_m3u(
            songs, resolved, playlist_name, playlist_subdir
        )
        if m3u_path is not None and target is not None:
            await asyncio.to_thread(
                download_playlist_cover,
                *target,
                m3u_path,
                state.settings,
            )
        elif m3u_path is not None and cover_url:
            await asyncio.to_thread(
                _save_explicit_playlist_cover,
                cover_url,
                m3u_path,
                state.settings,
            )

    await _finish_playlist_batch(
        songs,
        resolved,
        batch_id=batch_id,
        playlist_name=playlist_name,
        spotify_playlist_id=spotify_playlist_id,
        spotify_track_count=spotify_track_count,
        generate_m3u=generate_m3u,
    )


async def _finish_playlist_batch(
    songs: list[dict[str, Any]],
    resolved: dict[int, Optional[str]],
    *,
    batch_id: Optional[int],
    playlist_name: Optional[str],
    spotify_playlist_id: Optional[str],
    spotify_track_count: int,
    generate_m3u: bool,
) -> None:
    """Close a playlist batch: record its outcome, relink the playlist's
    on-disk tracks in the catalog and refresh its M3U/Navidrome playlist.

    A batch can cover only part of a Spotify playlist (e.g. downloading
    just the missing tracks), so the catalog is rebuilt from every track
    of the playlist already in the library before the refresh — otherwise
    the refreshed playlist would only contain this batch's tracks.
    """

    succeeded = sum(1 for filename in resolved.values() if filename)
    failed = len(songs) - succeeded
    if playlist_name:
        logger.info(
            'playlist batch: name={!r} downloaded={}/{} failed={}',
            playlist_name,
            succeeded,
            len(songs),
            failed,
        )
    if batch_id is not None and state.playlist_batch_store is not None:
        await asyncio.to_thread(
            state.playlist_batch_store.finish_batch,
            batch_id,
            succeeded,
            failed,
            status='complete' if failed == 0 else 'incomplete',
        )
    if not playlist_name or state.playlist_catalog is None:
        return
    if spotify_track_count and len(songs) < spotify_track_count:
        logger.info(
            'playlist batch: partial run {}/{} tracks for {!r}; rebuilding '
            'the catalog from the library before the playlist refresh',
            len(songs),
            spotify_track_count,
            playlist_name,
        )

    def _catalog_batch() -> None:
        catalog = state.playlist_catalog
        downloader = state.downloader
        if catalog is None or downloader is None:
            return
        download_dir = Path(downloader.download_dir)
        slskd_dir = slskd_dir_from_downloader(downloader)
        if spotify_playlist_id:
            catalog.ensure_playlist(
                playlist_name, spotify_id=spotify_playlist_id
            )
        for index, song in enumerate(songs):
            filename = resolved.get(index)
            full = (
                locate_library_file(filename, download_dir, slskd_dir)
                if filename
                else None
            )
            if full is None:
                continue
            catalog.upsert_track(
                playlist_name,
                song,
                filename,
                full,
                track_order=int(song.get('downtify_track_order') or index),
            )
        if spotify_playlist_id:
            linked = _rebuild_playlist_catalog_from_library(
                playlist_name, spotify_playlist_id
            )
            logger.info(
                'playlist batch: catalog has {} on-disk track(s) for {!r}',
                linked,
                playlist_name,
            )

    await asyncio.to_thread(_catalog_batch)

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
                _effective_navidrome_settings(state.settings).get(
                    'scan_after_download', True
                )
            ),
            playlist_spotify_cache=state.playlist_spotify_cache,
            cover_cache=state.cover_cache,
            metadata_cache=state.metadata_cache,
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
    playlist_name: Optional[str] = None,
    cover_url: Optional[str] = None,
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
            playlist_name,
            batch_id=batch_id,
            cover_url=cover_url,
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
    # No real Spotify/YouTube Music playlist id backs this batch (e.g. an
    # artist's top-songs selection) - the caller names the playlist and its
    # cover directly instead of us deriving them from playlist_url.
    playlist_name = str(payload.get('playlist_name') or '') or None
    cover_url = str(payload.get('cover_url') or '') or None

    # A Spotify playlist download is tracked as a playlist batch, so an
    # incomplete one can be finished later (see /api/playlists/incomplete).
    batch_id: Optional[int] = None
    target = parse_playlist_url(playlist_url) if playlist_url else None
    if (
        target is not None
        and target[0] == SOURCE_SPOTIFY
        and state.playlist_batch_store is not None
    ):
        first = next((s for s in songs if isinstance(s, dict)), {})
        batch_id = await asyncio.to_thread(
            state.playlist_batch_store.start_batch,
            target[1],
            str(first.get('album_name') or '').strip() or target[1],
            playlist_url,
            len(songs),
        )

    return await _submit_playlist_batch(
        songs,
        playlist_url,
        generate_m3u=generate_m3u,
        batch_id=batch_id,
        playlist_name=playlist_name,
        cover_url=cover_url,
    )


@router.post('/api/download/csv')
async def download_csv_endpoint(request: Request) -> dict[str, Any]:
    """Import a library-export CSV (Soundiiz, TuneMyMusic, Exportify, ...).

    Body: ``{"csv": "<raw file text>", "playlist_name": "...",
    "generate_m3u": true}``. The CSV is read client-side and sent as
    plain text in the JSON body rather than as a multipart upload, to
    match every other endpoint here and avoid an extra dependency.

    Each row is resolved the same way a free-text search would be, via
    :func:`providers.find_match` inside :meth:`Downloader.download` -
    there is no Spotify/YouTube URL per row, only a title and artist.
    """
    if state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail='Invalid JSON') from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail='Invalid payload')

    csv_text = payload.get('csv')
    if not isinstance(csv_text, str) or not csv_text.strip():
        raise HTTPException(
            status_code=400, detail='csv must be a non-empty string'
        )

    try:
        songs = await asyncio.to_thread(
            library_import.parse_library_csv, csv_text
        )
    except library_import.LibraryCsvError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    playlist_name = (
        str(payload.get('playlist_name') or '').strip() or 'Imported Library'
    )
    generate_m3u = bool(payload.get('generate_m3u', True))

    job_ids: list[str] = []
    for song in songs:
        song_id = _register_job(song, status='queued')
        job_ids.append(song_id)
        await state.connections.broadcast({
            'song': song,
            'progress': 0,
            'message': '',
            'status': 'queued',
        })

    task = asyncio.create_task(
        _process_batch(
            songs, job_ids, '', generate_m3u, playlist_name=playlist_name
        )
    )

    def _log_batch_failure(t: asyncio.Task) -> None:
        if t.cancelled():
            return
        exc = t.exception()
        if exc is not None:
            logger.opt(exception=exc).error('CSV batch processing crashed')

    task.add_done_callback(_log_batch_failure)
    return {
        'job_ids': job_ids,
        'count': len(job_ids),
        'playlist_name': playlist_name,
    }


def _songs_for_album_download(url: str) -> list[dict[str, Any]]:
    youtube_parsed = providers.parse_youtube_url(url)
    if youtube_parsed is None or youtube_parsed[0] != 'album':
        raise HTTPException(
            status_code=400,
            detail='Only YouTube Music album/browse URLs are supported here',
        )
    _, browse_id = youtube_parsed
    songs = providers.album_tracks_from_browse_id(browse_id)
    if not songs:
        raise HTTPException(
            status_code=404, detail='Album not found or has no tracks'
        )
    return songs


@router.post('/api/download/album')
async def download_album_endpoint(url: str = Query(...)) -> dict[str, str]:
    """Download every track of a YouTube Music album/browse URL.

    Unlike ``POST /api/download/url`` (which only accepts a single video URL
    and therefore re-resolves catalog metadata independently, per track),
    this resolves the album's full tracklist once via
    :func:`providers.album_tracks_from_browse_id` and downloads each track
    using that shared, already-consistent metadata (track number, album
    name/artist, cover, year). This matters for compilations/"best of"
    albums, whose tracks would otherwise be re-matched one video at a time
    and can drift to their original, differently-tagged source album.

    Returns a mapping of ``song_id -> downloaded filename`` for every track
    that downloaded successfully (failed tracks are omitted, not raised).
    """
    if state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')

    songs = await asyncio.to_thread(_songs_for_album_download, url)
    # See _process_batch: only meaningful when there's a "next" track to
    # wait for, so a single-track album never waits around for nothing.
    delay_seconds = (
        state.settings.get('download_delay_seconds', 0)
        if len(songs) > 1
        else 0
    )

    async def _one(song: dict[str, Any]) -> tuple[str, Optional[str]]:
        song_id = str(song.get('song_id') or '')
        if not song_id:
            return '', None
        job_id = _register_job(song, status='downloading')
        try:
            filename = await _run_download(
                song, job_id, delay_seconds=delay_seconds
            )
        except Exception:
            logger.exception('Album track download failed for {}', song_id)
            return song_id, None
        return song_id, filename

    results = await asyncio.gather(*(_one(song) for song in songs))
    return {
        song_id: filename
        for song_id, filename in results
        if song_id and filename
    }


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
    artist, duration}, ...]}``, where ``playlist_url`` is a Spotify or
    YouTube Music playlist. The playlist name is resolved server-side
    via :func:`monitor.fetch_playlist` so the existing ``/api/song/url``
    shape stays untouched.
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
    source_and_id = parse_playlist_url(playlist_url)
    if source_and_id is None:
        raise HTTPException(
            status_code=400,
            detail='Not a Spotify or YouTube Music playlist URL',
        )

    tracks = payload.get('tracks') or []
    if not isinstance(tracks, list):
        raise HTTPException(status_code=400, detail='tracks must be a list')

    try:
        playlist_name, _ = await asyncio.to_thread(
            fetch_playlist, *source_and_id
        )
    except Exception as exc:
        logger.exception('Failed to resolve playlist {}', playlist_url)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    entries = [t for t in tracks if isinstance(t, dict)]
    playlist_subdir = m3u.sanitize_playlist_name(playlist_name)
    organize = _organize_enabled()
    target, kept = m3u.write_m3u(
        state.downloader.download_dir,
        playlist_name,
        entries,
        playlist_subdir=None if organize else playlist_subdir,
    )
    if target is None:
        raise HTTPException(
            status_code=400, detail='No tracks resolved to a file on disk'
        )
    await asyncio.to_thread(
        download_playlist_cover,
        *source_and_id,
        target,
        state.settings,
    )
    return {'path': str(target), 'count': kept}


def _require_cookies_store() -> CookiesStore:
    if state.cookies_store is None:
        raise HTTPException(
            status_code=503, detail='Cookie storage is not ready yet'
        )
    return state.cookies_store


@router.get('/api/cookies')
def get_cookies_endpoint() -> dict[str, Any]:
    """Current cookie configuration, for the settings UI.

    ``locked`` means ``DOWNTIFY_COOKIES_FILE`` is set: that deployment
    manages its own cookie file, so uploads and deletions are refused.
    """
    return _require_cookies_store().status()


@router.post('/api/cookies')
async def upload_cookies_endpoint(request: Request) -> dict[str, Any]:
    """Store an uploaded Netscape ``cookies.txt``, replacing any previous one.

    The body is the raw file rather than a multipart form so Downtify
    doesn't need ``python-multipart`` just for this — a cookies.txt is
    plain text and never large.
    """
    store = _require_cookies_store()
    if store.is_locked():
        raise HTTPException(
            status_code=409,
            detail=(
                'Cookies are configured through the DOWNTIFY_COOKIES_FILE '
                'environment variable. Unset it to manage the file here.'
            ),
        )
    content = await request.body()
    if len(content) > MAX_COOKIES_BYTES:
        raise HTTPException(status_code=413, detail='File is too large')
    try:
        warnings = await asyncio.to_thread(store.save, content)
    except InvalidCookiesFile as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        logger.exception('Failed to store uploaded cookies file')
        raise HTTPException(
            status_code=500, detail=f'Could not save the file: {exc}'
        ) from exc
    return {**store.status(), 'warnings': warnings}


@router.delete('/api/cookies')
async def delete_cookies_endpoint() -> dict[str, Any]:
    store = _require_cookies_store()
    if store.is_locked():
        raise HTTPException(
            status_code=409,
            detail=(
                'Cookies are configured through the DOWNTIFY_COOKIES_FILE '
                'environment variable. Unset it to manage the file here.'
            ),
        )
    try:
        deleted = await asyncio.to_thread(store.delete)
    except OSError as exc:
        logger.exception('Failed to delete stored cookies file')
        raise HTTPException(
            status_code=500, detail=f'Could not delete the file: {exc}'
        ) from exc
    return {**store.status(), 'deleted': deleted}


@router.get('/api/settings')
def get_settings_endpoint(client_id: str = Query('')) -> dict[str, Any]:
    return state.settings


@router.post('/api/settings/update')
async def update_settings_endpoint(
    request: Request, client_id: str = Query('')
) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if isinstance(payload, dict):
        # Validated up front so a rejected save changes nothing.
        pending = {**state.settings, **payload}
        slskd_cfg = _effective_slskd_settings(pending)
        navidrome_cfg = _effective_navidrome_settings(pending)
        _validate_integration_settings(
            slskd_cfg if 'slskd' in payload else {},
            navidrome_cfg if 'navidrome' in payload else {},
        )
        for key, raw_value in payload.items():
            if key not in DEFAULT_SETTINGS:
                continue
            if key == 'max_parallel_downloads':
                state.settings[key] = _clamp_parallel_downloads(raw_value)
            elif key == 'download_delay_seconds':
                state.settings[key] = _clamp_download_delay(raw_value)
            elif key == 'cover_resolution':
                state.settings[key] = _clamp_cover_resolution(raw_value)
            elif key == 'slskd':
                # The parallel limit is derived from max_parallel_downloads,
                # not stored with slskd's own options.
                state.settings[key] = {
                    k: v
                    for k, v in slskd_cfg.items()
                    if k != 'max_parallel_downloads'
                }
            elif key == 'navidrome':
                state.settings[key] = navidrome_cfg
            else:
                state.settings[key] = raw_value
        if {'audio_providers', 'slskd'} & set(payload):
            state.settings['audio_providers'] = _effective_audio_providers(
                state.settings
            )
        if state.downloader is not None:
            if {'audio_providers', 'slskd', 'max_parallel_downloads'} & set(
                payload
            ):
                state.downloader.slskd_settings = (
                    state.downloader._normalize_slskd_settings(
                        _effective_slskd_settings(state.settings)
                    )
                )
                state.downloader.slskd_settings['output_dir'] = str(
                    state.downloader.download_dir
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
            if 'organize_by_album' in payload:
                state.downloader.organize_by_album = bool(
                    payload['organize_by_album']
                )
            if 'download_cover_art' in payload:
                state.downloader.download_cover_art = bool(
                    payload['download_cover_art']
                )
            if 'overwrite_existing_files' in payload:
                state.downloader.overwrite_existing_files = bool(
                    payload['overwrite_existing_files']
                )
        if 'max_parallel_downloads' in payload:
            state.download_semaphore = asyncio.Semaphore(
                state.settings['max_parallel_downloads']
            )
            reset_slskd_parallelism(_effective_slskd_settings(state.settings))
        if 'cover_resolution' in payload:
            providers.set_cover_resolution(state.settings['cover_resolution'])
    if state.settings_path is not None:
        _save_settings(state.settings_path, state.settings)
    return state.settings


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


def _youtube_artist_for_name(name: str) -> tuple[str, str]:
    """Find the YouTube Music artist channel that matches *name*.

    Spotify's artist embed exposes no discography (only a top-tracks
    preview), so a watched Spotify artist is followed through YouTube
    Music instead — which is also where the audio is fetched from, so
    every release we can see is one we can actually download. Returns
    ``(channel_id, resolved_name)``.
    """

    results = providers.search_artists(name, limit=10)
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f'No YouTube Music artist found for {name!r}',
        )
    wanted = name.casefold().strip()
    exact = [
        r
        for r in results
        if str(r.get('name') or '').casefold().strip() == wanted
    ]
    best = (exact or results)[0]
    channel_id = str(best.get('artist_id') or '')
    if not channel_id:
        raise HTTPException(
            status_code=502,
            detail=f'YouTube Music artist for {name!r} has no channel id',
        )
    return channel_id, str(best.get('name') or name)


async def _resolve_watch_target(url: str) -> tuple[str, str, str]:
    """Resolve a pasted URL into ``(kind, watch_key, display_name)``.

    Accepts a Spotify or YouTube Music playlist URL (watched by its
    tracks), and a Spotify artist URL or a YouTube Music artist URL
    (``/channel/UC...`` or ``/@handle``, watched by their discography).
    """

    playlist_target = parse_playlist_url(url)
    if playlist_target is not None:
        _, playlist_id = playlist_target
        try:
            name, _tracks = await asyncio.to_thread(
                fetch_playlist, *playlist_target
            )
        except Exception as exc:
            logger.exception('Failed to resolve playlist {}', playlist_id)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return KIND_PLAYLIST, playlist_id, name

    spotify_parsed = spotify.parse_spotify_url(url)
    if spotify_parsed is not None and spotify_parsed[0] == 'artist':
        _, artist_id = spotify_parsed
        try:
            spotify_name = await asyncio.to_thread(
                spotify.artist_name_from_id, artist_id
            )
        except Exception as exc:
            logger.exception('Failed to resolve artist {}', artist_id)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        channel_id, name = await asyncio.to_thread(
            _youtube_artist_for_name, spotify_name
        )
        return KIND_ARTIST, channel_id, name

    youtube_parsed = providers.parse_youtube_url(url)
    if youtube_parsed is not None and youtube_parsed[0] == 'artist':
        _, channel_or_handle = youtube_parsed
        try:
            channel_id = await asyncio.to_thread(
                providers.resolve_artist_channel_id, channel_or_handle
            )
            info = await asyncio.to_thread(
                providers.artist_info_from_channel_id, channel_id
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception(
                'Failed to resolve artist channel {}', channel_or_handle
            )
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return KIND_ARTIST, channel_id, str(info.get('name') or channel_id)

    raise HTTPException(
        status_code=400,
        detail=(
            'A Spotify or YouTube Music playlist URL, or a Spotify or '
            'YouTube Music artist URL, is required'
        ),
    )


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

    kind, watch_key, name = await _resolve_watch_target(url)

    existing = await asyncio.to_thread(db.get_by_spotify_id, watch_key)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                'This artist is already being watched'
                if kind == KIND_ARTIST
                else 'This playlist is already being monitored'
            ),
        )

    playlist = await asyncio.to_thread(
        db.add_playlist, watch_key, name, url, interval_minutes, kind
    )

    # Kick off the first download pass immediately so the user does not have
    # to wait up to a full monitor sweep interval for the initial backfill.
    if state.downloader is not None:
        loop = state.loop or asyncio.get_running_loop()

        async def _initial_check(pl=playlist) -> None:
            try:
                await check_watch(
                    pl,
                    db,
                    state.downloader,  # type: ignore[arg-type]
                    state.connections.broadcast,
                    loop,
                    state.settings,
                    library_stores(),
                )
            except Exception:
                logger.exception('Initial check failed for watch {}', pl.id)

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
            count = await check_watch(
                playlist,
                db,
                state.downloader,
                state.connections.broadcast,
                loop,
                # Was omitted before, which silently ignored the
                # delay-between-downloads setting on a manual check.
                state.settings,
                library_stores(),
            )
            logger.info(
                'Manual check: downloaded {} new track(s) from "{}"',
                count,
                playlist.name,
            )  # type: ignore[union-attr]
        except Exception:
            logger.exception('Manual check failed for watch {}', playlist_id)

    asyncio.create_task(_run())
    return {'status': 'check_started', 'id': playlist_id}
