"""FastAPI router exposed by Downtify.

The endpoints intentionally mirror the surface that the previous
``spotdl``-powered backend exposed so the existing Vue frontend keeps
working without changes:

* ``GET  /api/version``
* ``GET  /api/songs/search``
* ``GET  /api/song/url`` and ``GET /api/url`` (alias)
* ``POST /api/download/url``
* ``POST /api/playlist/m3u``
* ``GET  /api/settings``
* ``POST /api/settings/update``
* ``WS   /api/ws``
* ``GET  /api/check_update``
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Optional

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)

from . import m3u, providers, spotify
from .downloader import Downloader
from .monitor import PlaylistMonitorDB, check_playlist

logger = logging.getLogger(__name__)


DEFAULT_SETTINGS: dict[str, Any] = {
    'audio_providers': ['youtube-music'],
    'lyrics_providers': ['lrclib'],
    'format': 'mp3',
    'bitrate': '320',
    'output': '{artists} - {title}.{output-ext}',
    'generate_m3u': True,
}


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
    loop: Optional[asyncio.AbstractEventLoop] = None
    monitor_db: Optional[PlaylistMonitorDB] = None
    download_jobs: dict[str, dict[str, Any]] = {}


state = AppState()
router = APIRouter()


@router.get('/api/version')
def get_version() -> str:
    return state.version


@router.get('/api/check_update')
def check_update() -> Optional[dict[str, Any]]:
    return None


@router.get('/api/songs/search')
def search_endpoint(query: str = Query('')) -> list[dict[str, Any]]:
    return providers.search_songs(query, limit=20)


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
            return spotify.track_from_id(sid)
        if kind == 'album':
            return spotify.album_tracks_from_id(sid)
        if kind == 'playlist':
            return spotify.playlist_tracks_from_id(sid)
    except Exception as exc:
        logger.exception('Failed to resolve Spotify URL %s', url)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    raise HTTPException(
        status_code=400, detail=f'Unsupported entity type: {kind}'
    )


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
        'filename': None,
    }
    return song_id


async def _run_download(song: dict[str, Any], song_id: str) -> Optional[str]:
    """Run a single download to completion, updating jobs state and broadcasting WS events."""

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

    try:
        filename = await loop.run_in_executor(
            None, lambda: state.downloader.download(song, progress)
        )
    except Exception as exc:
        logger.exception('Download failed for %s', song_id)
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
    await state.connections.broadcast({
        'song': song,
        'progress': 100,
        'message': 'Done',
        'status': 'done',
        'filename': filename,
    })
    return filename


@router.post('/api/download/url')
async def download_endpoint(
    url: str = Query(...),
    client_id: str = Query(''),
):
    if state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')

    song = _song_for_download(url)
    song_id = _register_job(song, status='downloading')

    try:
        filename = await _run_download(song, song_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return filename


_BATCH_CONCURRENCY = 4


async def _process_batch(
    songs: list[dict[str, Any]],
    job_ids: list[str],
    playlist_url: str,
    generate_m3u: bool,
) -> None:
    semaphore = asyncio.Semaphore(_BATCH_CONCURRENCY)

    async def _bounded(song: dict[str, Any], song_id: str) -> dict[str, Any]:
        async with semaphore:
            try:
                filename = await _run_download(song, song_id)
            except Exception:
                filename = None
            return {'song': song, 'filename': filename}

    results = await asyncio.gather(
        *[_bounded(s, sid) for s, sid in zip(songs, job_ids)],
        return_exceptions=False,
    )

    if not (generate_m3u and playlist_url):
        return

    parsed = spotify.parse_spotify_url(playlist_url)
    if parsed is None or parsed[0] != 'playlist':
        return

    try:
        playlist_name, _ = await asyncio.to_thread(
            spotify.playlist_info_and_tracks, parsed[1]
        )
    except Exception:
        logger.exception(
            'Failed to resolve playlist for M3U: %s', playlist_url
        )
        return

    entries: list[dict[str, Any]] = []
    for r in results:
        if not r or not r.get('filename'):
            continue
        s = r['song']
        entries.append({
            'filename': r['filename'],
            'title': s.get('name') or '',
            'artist': ', '.join(s.get('artists') or []),
            'duration': s.get('duration') or 0,
        })
    if not entries:
        return
    try:
        await asyncio.to_thread(
            m3u.write_m3u,
            state.downloader.download_dir,
            playlist_name,
            entries,
        )
    except Exception:
        logger.exception('Failed to write M3U for %s', playlist_url)


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
            logger.exception('Batch processing crashed', exc_info=exc)

    task.add_done_callback(_log_batch_failure)
    return {'job_ids': job_ids, 'count': len(job_ids)}


@router.get('/api/queue')
def get_queue() -> list[dict[str, Any]]:
    return list(state.download_jobs.values())


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
        logger.exception('Failed to resolve playlist %s', playlist_url)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    entries = [t for t in tracks if isinstance(t, dict)]
    target, kept = m3u.write_m3u(
        state.downloader.download_dir, playlist_name, entries
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
        for key, value in payload.items():
            if key in DEFAULT_SETTINGS:
                state.settings[key] = value
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
            providers_in = payload.get('lyrics_providers')
            if isinstance(providers_in, list):
                state.downloader.lyrics_providers = [
                    p for p in providers_in if isinstance(p, str) and p
                ]
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
            spotify.playlist_info_and_tracks, spotify_id
        )
    except Exception as exc:
        logger.exception('Failed to resolve playlist %s', spotify_id)
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
                )
            except Exception:
                logger.exception('Initial check failed for playlist %d', pl.id)

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
            )
            logger.info(
                'Manual check: downloaded %d new track(s) from "%s"',
                count,
                playlist.name,
            )  # type: ignore[union-attr]
        except Exception:
            logger.exception(
                'Manual check failed for playlist %d', playlist_id
            )

    asyncio.create_task(_run())
    return {'status': 'check_started', 'id': playlist_id}
