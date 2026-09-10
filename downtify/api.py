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
  resolves an artist channel URL into every one of their albums/singles
  as lightweight summaries, same shape as ``/api/albums/search`` - no
  tracklists; resolve a chosen release's tracks separately)
* ``POST /api/download/url`` (optional JSON body: resolved Spotify row so
  ``track_number`` / ``album_track_total`` survive re-fetch by URL)
* ``POST /api/download/album`` (YouTube Music album/browse URL only;
  downloads every track from one shared, already-resolved tracklist so
  metadata stays consistent across the whole release)
* ``POST /api/download/csv`` (import a library-export CSV from Soundiiz,
  TuneMyMusic, Exportify, etc.; JSON body ``{csv, playlist_name,
  generate_m3u}`` - the raw CSV text, read client-side, not a multipart
  upload)
* ``POST /api/playlist/m3u``
* ``GET  /api/settings``
* ``POST /api/settings/update``
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
from .downloader import Downloader
from .monitor import (
    KIND_ARTIST,
    KIND_PLAYLIST,
    PlaylistMonitorDB,
    check_artist,
    check_playlist,
)

MIN_PARALLEL_DOWNLOADS = 1
MAX_PARALLEL_DOWNLOADS = 30

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
    'max_parallel_downloads': 3,
    'download_delay_seconds': 0,
    'cover_resolution': providers.DEFAULT_COVER_RESOLUTION,
    'download_cover_art': True,
    'organize_by_artist': False,
    'organize_by_album': False,
    'search_albums': True,
}


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
    download_jobs: dict[str, dict[str, Any]] = {}
    download_semaphore: Optional[asyncio.Semaphore] = None


state = AppState()
router = APIRouter()


def _load_settings(path: Path) -> dict[str, Any]:
    """Load saved settings from *path*, merging with DEFAULT_SETTINGS as base."""
    try:
        saved = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(saved, dict):
            merged = dict(DEFAULT_SETTINGS)
            for k, v in saved.items():
                if k in DEFAULT_SETTINGS:
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
    return None


@router.get('/api/songs/search')
def search_endpoint(query: str = Query('')) -> list[dict[str, Any]]:
    return providers.search_songs(query, limit=20)


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
            if kind == 'artist':
                return providers.artist_albums_from_channel_id(yid)
        except Exception as exc:
            logger.exception('Failed to resolve YouTube URL {}', url)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        raise HTTPException(
            status_code=400, detail=f'Unsupported entity type: {kind}'
        )

    raise HTTPException(status_code=400, detail='Invalid URL')


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
        'filename': None,
    }
    return song_id


async def _run_download(
    song: dict[str, Any],
    song_id: str,
    subdir: Optional[str] = None,
    delay_seconds: float = 0,
) -> Optional[str]:
    """Run a single download to completion, updating jobs state and broadcasting WS events.

    When *delay_seconds* is positive, the concurrency slot (semaphore
    permit) is held for that long after a successful download before
    being released, so the next queued download in a batch can't start
    until the delay has elapsed. This is only meant for multi-song
    orchestration (playlist/album batches); single manual downloads
    should pass ``delay_seconds=0`` so a one-off download never waits
    around for nothing.
    """

    if state.downloader is None:
        raise RuntimeError('Downloader not ready')

    loop = state.loop or asyncio.get_running_loop()
    job = state.download_jobs.get(song_id)
    if job is None:
        song_id = _register_job(song, status='downloading')
        job = state.download_jobs[song_id]
    else:
        job['status'] = 'downloading'

    await state.connections.broadcast({
        'song': song,
        'progress': 0,
        'message': '',
        'status': 'downloading',
    })

    def progress(pct: float, message: str) -> None:
        j = state.download_jobs.get(song_id)
        if j:
            j['progress'] = pct
            j['message'] = message
        asyncio.run_coroutine_threadsafe(
            state.connections.broadcast({
                'song': song,
                'progress': pct,
                'message': message,
                'status': 'downloading',
            }),
            loop,
        )

    sem = state.download_semaphore
    try:
        async with sem if sem is not None else contextlib.nullcontext():
            filename = await loop.run_in_executor(
                None,
                lambda: state.downloader.download(
                    song, progress, subdir=subdir
                ),
            )
            job['status'] = 'done'
            job['filename'] = filename
            job['progress'] = 100
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

    return filename


@router.post('/api/download/url')
async def download_endpoint(
    url: str = Query(...),
    client_id: str = Query(''),
    client_hints: Optional[dict[str, Any]] = Body(None),
):
    if state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')

    song = _song_for_download(url)
    tn_before = song.get('track_number')
    yr_before = song.get('year') or song.get('release_date')
    _merge_client_track_hints(song, client_hints)
    logger.debug(
        'download/url: url={} body={} tn_before={!r} tn_after={!r} '
        'date_before={!r} date_after_year={!r} date_after_rd={!r}',
        url[:140],
        'json' if isinstance(client_hints, dict) else 'none',
        tn_before,
        song.get('track_number'),
        yr_before,
        song.get('year'),
        song.get('release_date'),
    )
    song_id = _register_job(song, status='downloading')

    try:
        filename = await _run_download(song, song_id)
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
) -> None:
    entries = _m3u_entries_for(songs, resolved)
    if not entries:
        return
    # When organize-by-artist/album is on, songs land in those folders
    # instead of the playlist subfolder, so the M3U must go to the legacy
    # Playlists/ directory (playlist_subdir=None) where relative paths
    # still resolve.
    organize = _organize_enabled()
    try:
        await asyncio.to_thread(
            m3u.write_m3u,
            state.downloader.download_dir,
            playlist_name,
            entries,
            playlist_subdir=None if organize else playlist_subdir,
        )
    except Exception:
        logger.exception('Failed to write M3U for {!r}', playlist_name)


async def _process_batch(
    songs: list[dict[str, Any]],
    job_ids: list[str],
    playlist_url: str,
    generate_m3u: bool,
    playlist_name: Optional[str] = None,
) -> None:
    # Resolve the playlist name up-front so all tracks land in a single,
    # per-playlist sub-folder. Loose batches (e.g. albums or unrelated
    # tracks) keep the legacy flat layout under download_dir. A caller
    # without a Spotify playlist_url (e.g. a CSV library import) can
    # instead pass playlist_name directly.
    playlist_subdir: Optional[str] = None
    parsed = spotify.parse_spotify_url(playlist_url) if playlist_url else None
    if parsed is not None and parsed[0] == 'playlist':
        try:
            playlist_name, _ = await asyncio.to_thread(
                spotify.playlist_info_and_tracks, parsed[1]
            )
            playlist_subdir = m3u.sanitize_playlist_name(playlist_name)
        except Exception:
            logger.exception(
                'Failed to resolve playlist name for {}', playlist_url
            )
    elif playlist_name:
        playlist_subdir = m3u.sanitize_playlist_name(playlist_name)

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
        await _write_batch_m3u(songs, resolved, playlist_name, playlist_subdir)


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
        _process_batch(valid_songs, job_ids, playlist_url, generate_m3u)
    )

    def _log_batch_failure(t: asyncio.Task) -> None:
        if t.cancelled():
            return
        exc = t.exception()
        if exc is not None:
            logger.opt(exception=exc).error('Batch processing crashed')

    task.add_done_callback(_log_batch_failure)
    return {'job_ids': job_ids, 'count': len(job_ids)}


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

    songs = _songs_for_album_download(url)
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


@router.get('/api/queue')
def get_queue() -> list[dict[str, Any]]:
    return list(state.download_jobs.values())


@router.delete('/api/queue')
def clear_queue() -> dict:
    state.download_jobs.clear()
    return {'cleared': True}


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
        playlist_name, _ = await asyncio.to_thread(
            spotify.playlist_info_and_tracks, parsed[1]
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
    return {'path': str(target), 'count': kept}


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
        for key, raw_value in payload.items():
            if key not in DEFAULT_SETTINGS:
                continue
            if key == 'max_parallel_downloads':
                state.settings[key] = _clamp_parallel_downloads(raw_value)
            elif key == 'download_delay_seconds':
                state.settings[key] = _clamp_download_delay(raw_value)
            elif key == 'cover_resolution':
                state.settings[key] = _clamp_cover_resolution(raw_value)
            else:
                state.settings[key] = raw_value
        if state.downloader is not None:
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
        if 'max_parallel_downloads' in payload:
            state.download_semaphore = asyncio.Semaphore(
                state.settings['max_parallel_downloads']
            )
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

    Accepts a Spotify playlist URL (watched by its tracks), a Spotify
    artist URL or a YouTube Music artist/channel URL (watched by their
    discography).
    """

    spotify_parsed = spotify.parse_spotify_url(url)
    if spotify_parsed is not None and spotify_parsed[0] == 'playlist':
        _, playlist_id = spotify_parsed
        try:
            name, _tracks = await asyncio.to_thread(
                spotify.playlist_info_and_tracks, playlist_id
            )
        except Exception as exc:
            logger.exception('Failed to resolve playlist {}', playlist_id)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return KIND_PLAYLIST, playlist_id, name

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
        _, channel_id = youtube_parsed
        try:
            info = await asyncio.to_thread(
                providers.artist_info_from_channel_id, channel_id
            )
        except Exception as exc:
            logger.exception('Failed to resolve artist channel {}', channel_id)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return KIND_ARTIST, channel_id, str(info.get('name') or channel_id)

    raise HTTPException(
        status_code=400,
        detail=(
            'A Spotify playlist URL, a Spotify artist URL or a YouTube '
            'Music artist URL is required'
        ),
    )


async def _check_watch(
    playlist: Any,
    db: PlaylistMonitorDB,
    downloader: Any,
    broadcast: Any,
    loop: asyncio.AbstractEventLoop,
    settings: dict[str, Any],
) -> int:
    """Run the right check for a watch, by kind."""
    check = check_artist if playlist.kind == KIND_ARTIST else check_playlist
    return await check(playlist, db, downloader, broadcast, loop, settings)


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
                await _check_watch(
                    pl,
                    db,
                    state.downloader,  # type: ignore[arg-type]
                    state.connections.broadcast,
                    loop,
                    state.settings,
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
            count = await _check_watch(
                playlist,
                db,
                state.downloader,
                state.connections.broadcast,
                loop,
                # Was omitted before, which silently ignored the
                # delay-between-downloads setting on a manual check.
                state.settings,
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
