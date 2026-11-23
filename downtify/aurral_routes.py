"""``/api/aurral``: Downtify as a download source for Aurral.

Used by the Downtify plugin for Aurral (``lklynet/aurral-plugins``),
with a key made under Settings > Apps > Aurral (a paired-app token).
Everything but ``GET /api/aurral`` answers ``409`` until an admin turns
hand-over on there. See :mod:`downtify.aurral`.

* ``GET    /api/aurral`` - whether hand-over is on, and Downtify's version.
* ``GET    /api/aurral/search/tracks`` - ``artist``, ``title``, ``album``:
  songs, shaped as Aurral track results.
* ``GET    /api/aurral/search/albums`` - ``artist``, ``title``: albums.
* ``POST   /api/aurral/jobs`` - ``{song}`` (a track result's
  ``data.song``) or ``{album_url}``: start a hand-over download.
* ``GET    /api/aurral/jobs/{id}`` - its status and, once done, files.
* ``GET    /api/aurral/jobs/{id}/files/{n}`` - one finished file.
* ``DELETE /api/aurral/jobs/{id}`` - cancel it, or say the files were
  taken: its folder is deleted (library files are never touched).
* ``POST   /api/aurral/key`` - admins: a new key for Aurral, shown once.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import FileResponse
from loguru import logger

from . import (
    __version__,
    api,
    aurral,
    auth_routes,
    library_only,
    providers,
)

router = APIRouter(prefix='/api/aurral')

OFF_DETAIL = (
    'Aurral hand-over is turned off in Downtify (Settings > Apps > Aurral)'
)

_jobs: Optional[aurral.Jobs] = None


def jobs() -> aurral.Jobs:
    """The job list, made on first use beside ``settings.json``."""

    global _jobs
    if _jobs is None:
        path = api.state.settings_path
        root = (
            Path(path).parent / aurral.FOLDER_NAME
            if path is not None
            else Path('data') / aurral.FOLDER_NAME
        )
        _jobs = aurral.Jobs(root)
    return _jobs


def reset(root: Optional[Path] = None) -> aurral.Jobs:
    """Start over (on start, and in tests): drop every job and clear the
    folder."""

    global _jobs
    _jobs = aurral.Jobs(root) if root is not None else None
    found = jobs()
    found.clear_folder()
    return found


def _require_on() -> None:
    if not aurral.enabled(api.state.settings):
        raise HTTPException(status_code=409, detail=OFF_DETAIL)


def _require_downloads() -> None:
    _require_on()
    if library_only.enabled(api.state.settings):
        raise HTTPException(status_code=409, detail=library_only.DETAIL)
    if api.state.downloader is None:
        raise HTTPException(status_code=503, detail='Downloader not ready')


def _own_job(job_id: str, request: Request) -> aurral.Job:
    found = jobs().get(
        job_id,
        api.request_user_id(request),
        admin=api.request_is_admin(request),
    )
    if found is None:
        raise HTTPException(status_code=404, detail='No such hand-over job')
    return found


@router.get('')
def status() -> dict[str, Any]:
    settings = api.state.settings
    fmt, kbps = aurral.audio_quality(settings)
    return {
        'enabled': aurral.enabled(settings),
        'version': __version__,
        'library_only': library_only.enabled(settings),
        'format': fmt,
        'bitrate': kbps,
    }


@router.get('/search/tracks')
async def search_tracks(
    artist: str = Query(''),
    title: str = Query(''),
    album: str = Query(''),
) -> list[dict[str, Any]]:
    _require_downloads()
    query = aurral.search_query(artist, title)
    if not query:
        return []
    rows = await asyncio.to_thread(
        providers.search_songs, query, aurral.MAX_RESULTS
    )
    if not rows and 'slskd' in api._effective_audio_providers(
        api.state.settings
    ):
        # Nothing on YouTube Music: slskd can still find it by name, as
        # with Downtify's own search.
        stub = providers.song_stub_from_text_query(
            f'{artist} - {title}' if artist and title else query
        )
        rows = [stub] if stub else []
    else:
        rows = [{**row, 'download_by_metadata': True} for row in rows]
    out = []
    for row in rows:
        found = aurral.track_result(row, api.state.settings)
        if found is not None:
            out.append(found)
    return out


@router.get('/search/albums')
async def search_albums(
    artist: str = Query(''),
    title: str = Query(''),
) -> list[dict[str, Any]]:
    _require_downloads()
    query = aurral.search_query(artist, title)
    if not query:
        return []
    rows = await asyncio.to_thread(
        providers.search_albums, query, aurral.MAX_RESULTS
    )
    out = []
    for row in rows:
        found = aurral.album_result(row)
        if found is not None:
            out.append(found)
    return out


def _song_from_result(row: Any) -> dict[str, Any]:
    """The song to download, from a search row Aurral passed back."""

    if not isinstance(row, dict) or not str(row.get('song_id') or '').strip():
        raise HTTPException(status_code=400, detail='A song is needed')
    song = dict(row)
    if song.pop('download_by_metadata', None) is True:
        # As POST /api/download/url does for a search row.
        song['_match_by_metadata'] = True
    return song


def _album_songs(url: str) -> list[dict[str, Any]]:
    parsed = providers.parse_youtube_url(url)
    if parsed is None or parsed[0] != 'album':
        raise HTTPException(
            status_code=400, detail='Only YouTube Music album links work here'
        )
    songs = providers.album_tracks_from_browse_id(parsed[1])
    if not songs:
        raise HTTPException(
            status_code=404, detail='Album not found or has no tracks'
        )
    return songs[: aurral.MAX_ALBUM_TRACKS]


@router.post('/jobs')
async def start_job(
    request: Request, payload: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    _require_downloads()
    album_url = str(payload.get('album_url') or '').strip()
    if album_url:
        songs = await asyncio.to_thread(_album_songs, album_url)
        first = songs[0]
        label = str(first.get('album_name') or album_url)[:200]
        kind = 'album'
    else:
        songs = [_song_from_result(payload.get('song'))]
        label = (api.song_label(songs[0]) or songs[0]['song_id'])[:200]
        kind = 'track'
    job = jobs().new(
        kind, label, api.request_user_id(request), total=len(songs)
    )
    job.task = api.spawn_task(
        aurral.run_job(
            job,
            songs,
            downloader=api.state.downloader,
            track_index=api.state.track_index,
            executor=api.DOWNLOAD_EXECUTOR,
            semaphore=api.state.download_semaphore,
        ),
        name=f'aurral-{job.id}',
    )
    await api.log_activity(
        request, 'download', f'For Aurral: {label}', {'songs': len(songs)}
    )
    logger.info('Aurral: {} {!r} asked for ({})', kind, label, job.id)
    return job.to_dict()


@router.get('/jobs/{job_id}')
def job_status(job_id: str, request: Request) -> dict[str, Any]:
    jobs().prune()
    return _own_job(job_id, request).to_dict()


@router.get('/jobs/{job_id}/files/{index}')
def job_file(job_id: str, index: int, request: Request) -> FileResponse:
    job = _own_job(job_id, request)
    if job.status != aurral.DONE:
        raise HTTPException(status_code=409, detail='Not finished yet')
    found = aurral.file_for(job, index)
    if found is None:
        raise HTTPException(status_code=404, detail='No such file')
    return FileResponse(
        found.path,
        filename=found.name,
        media_type='application/octet-stream',
    )


@router.delete('/jobs/{job_id}')
def drop_job(job_id: str, request: Request) -> dict[str, Any]:
    job = _own_job(job_id, request)
    jobs().drop(job.id)
    return {'id': job.id, 'dropped': True}


@router.post('/key')
async def new_key(request: Request) -> dict[str, Any]:
    """A key for Aurral: a paired-app token for the admin asking, named
    "Aurral" in Settings > Apps, where it can be revoked."""

    store = auth_routes._store()
    me = auth_routes._me(request)
    user = await asyncio.to_thread(store.users.get, me.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail='Sign in required')
    made = await auth_routes._new_device(
        {'device_name': 'Aurral', 'platform': 'aurral'},
        user,
        auth_routes._ip(request),
        None,
    )
    return {'token': made['token'], 'device': made['device']}
