"""The Wanted list: what the artist watches still miss, across artists.

``GET /api/monitor/wanted`` gathers, per enabled artist watch (an admin's
view covers every watch, a user's only their own), the releases the watch
downloads that the library only partly has or lacks, with the tracks
missing in total. It reads what the last sweep and "Check what I have"
kept; nothing is fetched. A release whose tracklist isn't read yet counts
as unchecked: its size is unknown.

``POST .../check-all`` reads the tracklists of the artists with unchecked
releases, ``POST .../download-all`` downloads what the ones with gaps
miss - one artist at a time, as one background job for everyone; ``POST
.../stop`` ends it after the artist it is on.
"""

from __future__ import annotations

import asyncio
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from . import api, artist_catalogue
from .monitor import (
    KIND_ARTIST,
    MonitoredPlaylist,
    PlaylistMonitorDB,
    check_running,
    check_watch,
    take_inventory,
)

router = APIRouter(prefix='/api/monitor/wanted')


def scoped_artist_watches(
    db: PlaylistMonitorDB, request: Request
) -> list[MonitoredPlaylist]:
    """The enabled artist watches *request* may see: all for an admin,
    their own otherwise."""

    scope = (
        None if api.request_is_admin(request) else api.request_user_id(request)
    )
    return [
        watch
        for watch in db.list_playlists(scope)
        if watch.kind == KIND_ARTIST and watch.enabled
    ]


def wanted_view(
    db: PlaylistMonitorDB, watches: list[MonitoredPlaylist]
) -> dict[str, Any]:
    """The wanted releases of *watches*, grouped by artist (by name).

    The library is read once for all of them. An artist with nothing
    wanted and nothing unread is left out."""

    artists: list[dict[str, Any]] = []
    if watches:
        index = api._library_songs()
        for watch in watches:
            view = api._artist_releases(db, watch, songs=index)
            releases = artist_catalogue.wanted_releases(view['releases'])
            missing = view['missing']
            if not releases and not missing['unread']:
                continue
            artists.append({
                'watch': view['watch'],
                'releases': releases,
                'missing': missing,
                'checking': bool(view['checking']),
            })
    artists.sort(key=lambda a: str(a['watch']['name']).casefold())
    return {
        'artists': artists,
        'totals': {
            'tracks': sum(a['missing']['tracks'] for a in artists),
            'releases': sum(a['missing']['releases'] for a in artists),
            'artists': len(artists),
            'unchecked': sum(1 for a in artists if a['missing']['unread']),
        },
    }


#: The one job (``{}`` until the first): ``id, kind, running, done, total,
#: current, failed, skipped, stopped, started_at, finished_at`` and, kept
#: private, ``cancel``, ``user_id``, ``is_admin`` and ``watch_ids``.
_job: dict[str, Any] = {}

_PRIVATE = ('cancel', 'user_id', 'is_admin', 'watch_ids')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def public_job(job: dict[str, Any]) -> dict[str, Any] | None:
    """*job* as the page sees it (``None`` when there was none)."""

    if not job:
        return None
    return {k: v for k, v in job.items() if k not in _PRIVATE}


def _visible_job(request: Request) -> dict[str, Any] | None:
    """The job, only for whoever started it and for admins."""

    if not _job:
        return None
    if api.request_is_admin(request) or _job['user_id'] == (
        api.request_user_id(request)
    ):
        return _job
    return None


async def _check_one(
    job: dict[str, Any], watch: MonitoredPlaylist, db: PlaylistMonitorDB
) -> bool:
    """Read the unread tracklists of *watch*, mirroring the progress into
    the artist's own "Check what I have" state. ``False``: skipped."""

    if (api._inventories.get(watch.id) or {}).get('running'):
        return False
    state: dict[str, Any] = {
        'running': True,
        'done': 0,
        'total': 0,
        'checked': 0,
        'failed': 0,
        'started_at': _now(),
        'finished_at': '',
    }
    api._inventories[watch.id] = state

    def progress(done: int, total: int) -> None:
        state.update(done=done, total=total)

    try:
        state.update(
            await asyncio.to_thread(
                take_inventory,
                watch,
                db,
                progress=progress,
                stop=lambda: bool(job['cancel']),
            )
        )
    except Exception:
        state['error'] = True
        raise
    finally:
        state.update(running=False, finished_at=_now())
    return True


async def _download_one(
    watch: MonitoredPlaylist, db: PlaylistMonitorDB
) -> bool:
    """Download what *watch* misses. ``False``: it is being checked."""

    if check_running(watch.id):
        return False
    loop = api.state.loop or asyncio.get_running_loop()
    await check_watch(
        watch,
        db,
        api.state.downloader,  # type: ignore[arg-type]
        api.state.connections.broadcast,
        loop,
        api.state.settings,
        api.library_stores(),
        api.state.podcasts,
        fill_missing=True,
    )
    return True


async def _work(job: dict[str, Any], db: PlaylistMonitorDB) -> None:
    """Go through the job's artists, one at a time."""

    try:
        for watch_id in job['watch_ids']:
            if job['cancel']:
                job['stopped'] = True
                break
            watch = await asyncio.to_thread(db.get_playlist, watch_id)
            if watch is None or not watch.enabled:
                job['skipped'] += 1
                job['done'] += 1
                continue
            job['current'] = watch.name
            try:
                if job['kind'] == 'check':
                    worked = await _check_one(job, watch, db)
                else:
                    worked = await _download_one(watch, db)
                if not worked:
                    job['skipped'] += 1
            except Exception:
                logger.opt(exception=True).warning(
                    'Wanted: {} failed for "{}"', job['kind'], watch.name
                )
                job['failed'] += 1
            job['done'] += 1
    finally:
        job.update(running=False, current='', finished_at=_now())


async def _start(kind: str, request: Request) -> dict[str, Any]:
    db = api._require_monitor_db()
    if _job.get('running'):
        raise HTTPException(409, detail={'code': 'wanted_busy'})
    if kind == 'download' and api.state.downloader is None:
        raise HTTPException(status_code=500, detail='Downloader not ready')
    watches = await asyncio.to_thread(scoped_artist_watches, db, request)
    view = await asyncio.to_thread(wanted_view, db, watches)
    if kind == 'check':
        picked = [a for a in view['artists'] if a['missing']['unread'] > 0]
    else:
        picked = [
            a
            for a in view['artists']
            if a['missing']['tracks'] > 0 or a['missing']['unread'] > 0
        ]
    if _job.get('running'):  # another start got in while the view was read
        raise HTTPException(409, detail={'code': 'wanted_busy'})
    job: dict[str, Any] = {
        'id': secrets.token_urlsafe(8),
        'kind': kind,
        'running': True,
        'done': 0,
        'total': len(picked),
        'current': '',
        'failed': 0,
        'skipped': 0,
        'stopped': False,
        'started_at': _now(),
        'finished_at': '',
        'cancel': False,
        'user_id': api.request_user_id(request),
        'is_admin': api.request_is_admin(request),
        'watch_ids': [a['watch']['id'] for a in picked],
    }
    # _job is the live record the worker updates; a refused spawn
    # (library-only) puts the previous one back.
    before = dict(_job)
    _job.clear()
    _job.update(job)
    try:
        api.spawn_task(_work(_job, db), name=f'monitor-wanted-{kind}')
    except BaseException:
        _job.clear()
        _job.update(before)
        raise
    return public_job(_job)  # type: ignore[return-value]


@router.post('/check-all')
async def check_all(request: Request) -> dict[str, Any]:
    """Read the tracklists of every artist with unchecked releases."""

    return await _start('check', request)


@router.post('/download-all')
async def download_all(request: Request) -> dict[str, Any]:
    """Download what every artist with gaps (or unchecked releases)
    misses."""

    return await _start('download', request)


@router.post('/stop')
async def stop(request: Request) -> dict[str, Any] | None:
    """End the job after the artist it is on; the job as the page sees it."""

    job = _visible_job(request)
    if job is None and _job:
        raise HTTPException(404, detail={'code': 'no_job'})
    if job is not None and job['running']:
        job['cancel'] = True
    return public_job(job) if job is not None else None


@router.get('')
async def wanted(request: Request) -> dict[str, Any]:
    """What the artist watches still miss; ``job`` is the running or last
    check-all / download-all, to its starter and admins (``None``
    otherwise)."""

    db = api._require_monitor_db()
    watches = await asyncio.to_thread(scoped_artist_watches, db, request)
    view = await asyncio.to_thread(wanted_view, db, watches)
    job = _visible_job(request)
    return {**view, 'job': public_job(job) if job is not None else None}
