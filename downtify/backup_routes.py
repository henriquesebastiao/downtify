"""``/api/backups``: back up and restore a Downtify install (admins).

* ``GET  /api/backups`` - the schedule and the saved backups.
* ``POST /api/backups`` - back up now.
* ``PUT  /api/backups/schedule`` - ``{interval_hours}`` (``0``: off).
* ``GET  /api/backups/{name}`` - download one backup file.
* ``POST /api/backups/{name}/restore`` - restore a saved backup.
* ``POST /api/backups/restore`` - restore an uploaded backup file (the
  request body); both restores take ``settings``, ``watches`` and
  ``songs`` query flags saying what to bring back.

See :mod:`downtify.backup` for what a backup holds.
"""

from __future__ import annotations

import asyncio
import copy
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel

from . import __version__, api, backup, notifications
from .monitor import ALL_RELEASE_TYPES, KIND_PLAYLIST

router = APIRouter(prefix='/api/backups')

#: How often the schedule is looked at, in seconds.
SCHEDULE_CHECK_SECONDS = 600

_lock = asyncio.Lock()
_last_error: dict[str, str] = {}


def folder() -> Optional[Path]:
    """Where backups are kept: ``backups`` beside ``settings.json``."""

    path = api.state.settings_path
    return None if path is None else Path(path).parent / 'backups'


def _folder_or_503() -> Path:
    found = folder()
    if found is None:
        raise HTTPException(status_code=503, detail='No data folder')
    return found


# ── Making one ──────────────────────────────────────────────────────


def _watches() -> list[dict[str, Any]]:
    db = api.state.monitor_db
    if db is None:
        return []
    return [watch.to_dict() for watch in db.list_playlists()]


def _songs() -> list[dict[str, Any]]:
    rows = api.listing_for_request(api.library_context())
    index = api.state.track_index
    ids = index.spotify_ids_by_filename() if index is not None else {}
    providers: dict[str, str] = {}
    if api.state.file_providers is not None:
        providers = api.state.file_providers.lookup({
            str(row.get('file') or ''): '' for row in rows
        })
    return [
        backup.song_record(
            row,
            spotify_id=ids.get(str(row.get('file') or ''), ''),
            provider=providers.get(str(row.get('file') or ''), ''),
        )
        for row in rows
        if row.get('file')
    ]


def _make() -> backup.BackupInfo:
    data = backup.build(
        settings=copy.deepcopy(api.state.settings),
        watches=_watches(),
        songs=_songs(),
        app_version=__version__,
    )
    return backup.write_backup(_folder_or_503(), data)


async def back_up(trigger: str) -> backup.BackupInfo:
    """Make a backup now (one at a time)."""

    async with _lock:
        try:
            info = await asyncio.to_thread(_make)
        except Exception as exc:
            _last_error.update(
                at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                error=str(exc) or type(exc).__name__,
                trigger=trigger,
            )
            notifications.task_finished(
                'backup', 'Backup', failed=True, error=_last_error['error']
            )
            raise
        _last_error.clear()
        notifications.task_finished(
            'backup',
            'Backup',
            summary=[
                ('Watches', f'{info.watches:,}'),
                ('Songs', f'{info.songs:,}'),
            ],
        )
        return info


def _interval() -> int:
    return backup.clamp_interval(
        api.state.settings.get('backup_interval_hours', 0)
    )


async def maybe_back_up() -> bool:
    """Make a scheduled backup when one is due."""

    path = folder()
    if path is None or _lock.locked():
        return False
    saved = await asyncio.to_thread(backup.list_backups, path)
    newest = saved[0].created_at if saved else None
    if not backup.due(newest, _interval()):
        return False
    try:
        await back_up('schedule')
    except Exception:
        logger.exception('Scheduled backup failed')
        return False
    return True


async def schedule_loop(*, first_delay: float = 120) -> None:
    """Look every few minutes whether a scheduled backup is due."""

    await asyncio.sleep(first_delay)
    while True:
        try:
            await maybe_back_up()
        except Exception:
            logger.exception('Backup schedule check failed')
        await asyncio.sleep(SCHEDULE_CHECK_SECONDS)


# ── Restoring ───────────────────────────────────────────────────────


class _Body:
    """*request* with *payload* as its JSON body, for reusing the
    settings route (which also logs who changed what)."""

    def __init__(self, request: Request, payload: dict[str, Any]) -> None:
        self._request = request
        self._payload = payload

    async def json(self) -> dict[str, Any]:
        return self._payload

    def __getattr__(self, name: str) -> Any:
        return getattr(self._request, name)


async def _restore_settings(
    request: Request, saved: dict[str, Any]
) -> list[str]:
    payload = {
        key: value
        for key, value in saved.items()
        if key in api.DEFAULT_SETTINGS
    }
    await api.update_settings_endpoint(_Body(request, payload), client_id='')  # type: ignore[arg-type]
    return sorted(payload)


def _restore_watches(saved: list[Any]) -> tuple[int, int]:
    """Add the backup's watches this install doesn't have yet. Returns
    ``(added, already there)``."""

    db = api.state.monitor_db
    if db is None:
        raise HTTPException(status_code=503, detail='Monitor not ready')
    added = present = 0
    for raw in saved:
        if not isinstance(raw, dict):
            continue
        key = str(raw.get('spotify_id') or '')
        url = str(raw.get('url') or '')
        if not key or not url:
            continue
        user_id = int(raw.get('user_id') or 0)
        if db.get_by_spotify_id(key, user_id) is not None:
            present += 1
            continue
        types = raw.get('release_types')
        watch = db.add_playlist(
            key,
            str(raw.get('name') or key),
            url,
            interval_minutes=int(raw.get('interval_minutes') or 60),
            kind=str(raw.get('kind') or KIND_PLAYLIST),
            release_types=(
                ','.join(types)
                if isinstance(types, list)
                else str(types or '')
            )
            or ALL_RELEASE_TYPES,
            new_only=bool(raw.get('new_only')),
            user_id=user_id,
        )
        options = {
            name: raw[name] for name in backup.WATCH_OPTIONS if name in raw
        }
        if options:
            db.update_playlist(watch.id, **options)
        added += 1
    return added, present


def _on_disk(stored: str) -> bool:
    try:
        return (
            api.resolve_library_file(stored, api.library_context()) is not None
        )
    except Exception:
        return False


async def _restore_songs(
    request: Request, saved: list[Any]
) -> tuple[int, int]:
    """Queue the backup's songs whose file is missing. Returns
    ``(missing, queued)``."""

    missing = await asyncio.to_thread(backup.missing_songs, saved, _on_disk)
    if not missing:
        return 0, 0
    token = uuid.uuid4().hex[:12]
    for position, song in enumerate(missing):
        song.setdefault('song_id', f'backup:{token}:{position}')
    result = await api._submit_playlist_batch(  # noqa: SLF001
        missing,
        '',
        generate_m3u=False,
        user_id=api.request_user_id(request),
    )
    queued = len(result.get('job_ids') or []) or len(missing)
    return len(missing), queued


def _flag(request: Request, name: str) -> bool:
    return request.query_params.get(name, '1') not in {'0', 'false', ''}


async def _restore(request: Request, data: dict[str, Any]) -> dict[str, Any]:
    if api.state.downloader is None:
        raise HTTPException(status_code=503, detail='Downloader not ready')
    result: dict[str, Any] = {
        'created_at': data.get('created_at'),
        'settings': [],
        'watches_added': 0,
        'watches_present': 0,
        'songs_checked': False,
        'songs_missing': 0,
        'songs_queued': 0,
    }
    if _flag(request, 'settings'):
        result['settings'] = await _restore_settings(request, data['settings'])
    if _flag(request, 'watches'):
        added, present = await asyncio.to_thread(
            _restore_watches, data['watches']
        )
        result.update(watches_added=added, watches_present=present)
    if _flag(request, 'songs'):
        missing, queued = await _restore_songs(request, data['songs'])
        result.update(
            songs_checked=True, songs_missing=missing, songs_queued=queued
        )
    await api.log_activity(
        request,
        'backup_restored',
        str(data.get('created_at') or ''),
        {k: v for k, v in result.items() if k != 'settings'},
    )
    logger.info('Backup restored: {}', result)
    return result


# ── Routes ──────────────────────────────────────────────────────────


@router.get('')
async def backups_status() -> dict[str, Any]:
    path = folder()
    saved = await asyncio.to_thread(backup.list_backups, path) if path else []
    return {
        'interval_hours': _interval(),
        'intervals': list(backup.INTERVALS),
        'keep': backup.KEEP,
        'running': _lock.locked(),
        'folder': str(path) if path else '',
        'last_error': dict(_last_error) or None,
        'backups': [info.to_dict() for info in saved],
    }


@router.post('')
async def backups_create() -> dict[str, Any]:
    if _lock.locked():
        raise HTTPException(status_code=409, detail='A backup is running')
    try:
        info = await back_up('manual')
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Backup failed')
        raise HTTPException(status_code=500, detail='Backup failed') from exc
    return info.to_dict()


class ScheduleRequest(BaseModel):
    interval_hours: int


@router.put('/schedule')
async def backups_schedule(body: ScheduleRequest) -> dict[str, Any]:
    if body.interval_hours not in backup.INTERVALS:
        raise HTTPException(status_code=400, detail='Unknown interval')
    api.state.settings['backup_interval_hours'] = body.interval_hours
    if api.state.settings_path is not None:
        await asyncio.to_thread(
            api._save_settings,  # noqa: SLF001
            api.state.settings_path,
            api.state.settings,
        )
    return await backups_status()


@router.post('/restore')
async def backups_restore_upload(request: Request) -> dict[str, Any]:
    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=400, detail='No backup file sent')
    if len(raw) > backup.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail='Backup file too large')
    try:
        data = await asyncio.to_thread(backup.parse, raw)
    except backup.BackupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return await _restore(request, data)


@router.get('/{name}')
async def backups_download(name: str) -> FileResponse:
    path = backup.path_of(_folder_or_503(), name)
    if path is None:
        raise HTTPException(status_code=404, detail='No such backup')
    return FileResponse(
        path, media_type='application/gzip', filename=path.name
    )


@router.post('/{name}/restore')
async def backups_restore_saved(name: str, request: Request) -> dict[str, Any]:
    path = backup.path_of(_folder_or_503(), name)
    if path is None:
        raise HTTPException(status_code=404, detail='No such backup')
    try:
        data = await asyncio.to_thread(backup.read, path)
    except backup.BackupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return await _restore(request, data)
