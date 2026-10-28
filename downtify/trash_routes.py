"""One administrator-only trash API for browsers and paired applications."""

from __future__ import annotations

import asyncio
import secrets
import time

from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger
from pydantic import BaseModel, Field

from . import api, lyrics
from .library_catalog import list_library_entries
from .library_paths import library_file_root
from .library_paths_cache import invalidate_library_paths_cache
from .library_trash import LibraryTrash, TrashError

router = APIRouter(prefix='/api/v1/library/trash')


class Selection(BaseModel):
    files: list[str] = Field(default_factory=list, max_length=200)
    track_ids: list[str] = Field(default_factory=list, max_length=200)


class Confirmation(BaseModel):
    confirmation: str = Field(min_length=20, max_length=100)


class Items(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=200)


_previews = {}
_preview_slots = asyncio.Semaphore(1)
_PREVIEW_JOB_TTL = 3600


def _clean_preview_jobs():
    now = time.monotonic()
    for key, job in list(_previews.items()):
        if (
            job['state'] != 'preparing'
            and now - job['created'] > _PREVIEW_JOB_TTL
        ):
            _previews.pop(key, None)


def _prepare_preview(payload: Selection, user_id: int):
    tracks = _selection(payload)
    current = api.state.auth.users.get(user_id) if api.state.auth else None
    if current is None or current.get('role') != 'admin':
        raise TrashError('admin_access_revoked')
    return store().preview(user_id, tracks)


async def _run_preview(job_id: str, payload: Selection, user_id: int):
    async with _preview_slots:
        try:
            result = await asyncio.to_thread(
                _prepare_preview, payload, user_id
            )
            _previews[job_id].update(state='ready', preview=result)
        except TrashError as error:
            _previews[job_id].update(state='failed', error=str(error))
        except OSError:
            _previews[job_id].update(
                state='failed', error='filesystem_unavailable'
            )
        except Exception as error:
            logger.warning('Trash preview failed ({})', type(error).__name__)
            _previews[job_id].update(state='failed', error='unavailable')


def admin_user(request: Request) -> int:
    principal = api.principal_of(request)
    if (
        principal is None
        or principal.kind not in {'session', 'device'}
        or not principal.is_admin
        or not principal.user_id
    ):
        raise HTTPException(403, detail={'code': 'admin_required'})
    auth = api.state.auth
    user = auth.users.get(principal.user_id) if auth else None
    if user is None or user.get('role') != 'admin':
        raise HTTPException(403, detail={'code': 'admin_required'})
    return principal.user_id


def store() -> LibraryTrash:
    value = getattr(api.state, 'library_trash', None)
    if value is None:
        raise HTTPException(503, detail={'code': 'trash_not_configured'})
    return value


async def call(function, *args, **kwargs):
    try:
        return await asyncio.to_thread(function, *args, **kwargs)
    except TrashError as exc:
        raise HTTPException(409, detail={'code': str(exc)}) from None
    except OSError:
        raise HTTPException(
            503, detail={'code': 'filesystem_unavailable'}
        ) from None


def _selection(payload: Selection) -> list[dict]:
    ctx = api.library_context()
    entries = {entry['file']: entry for entry in list_library_entries(ctx)}
    files = list(payload.files)
    for track_id in payload.track_ids:
        row = (
            api.state.library_sync.row_for(track_id)
            if api.state.library_sync
            else None
        )
        if row is None:
            raise TrashError('item_not_found')
        files.append(row['file'])
    files = list(dict.fromkeys(files))
    if not files or len(files) > 200:
        raise TrashError('invalid_selection')
    ensure_idle(files)
    ids = (
        api.state.library_sync.ids_for_paths(files)
        if api.state.library_sync
        else {}
    )
    selected = []
    for file in files:
        if file not in entries:
            raise TrashError('item_not_found')
        root, relative = library_file_root(
            file, ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs
        )
        key = next(
            (
                key
                for key, value in store().roots.items()
                if value.path.resolve() == root.resolve()
            ),
            None,
        )
        if key is None:
            raise TrashError('unsupported_collection')
        metadata = dict(entries[file])
        if api.state.track_index is not None:
            spotify_id = api.state.track_index.spotify_id_for_filename(file)
            if spotify_id:
                metadata['spotify_id'] = spotify_id
        extra_sidecars = []
        audio_path = root / relative
        configured_lrc = lyrics.lrc_sidecar_path(
            audio_path,
            settings=api.state.settings,
            download_dir=ctx.download_dir,
            slskd_dir=ctx.slskd_dir,
            extra_dirs=ctx.extra_dirs,
        )
        if configured_lrc != audio_path.with_suffix('.lrc') and (
            configured_lrc.exists() or configured_lrc.is_symlink()
        ):
            lrc_key = next(
                (
                    name
                    for name, value in store().roots.items()
                    if configured_lrc.absolute().is_relative_to(
                        value.path.absolute()
                    )
                ),
                None,
            )
            if lrc_key is None:
                raise TrashError('unsupported_lyrics_location')
            extra_sidecars.append({
                'root_key': lrc_key,
                'relative': configured_lrc
                .absolute()
                .relative_to(store().roots[lrc_key].path.absolute())
                .as_posix(),
            })
        selected.append({
            'stored': file,
            'root_key': key,
            'relative': relative,
            'track_id': ids.get(file, ''),
            'metadata': metadata,
            'extra_sidecars': extra_sidecars,
        })
    return selected


def ensure_idle(files: list[str]):
    active = {
        str(p.get('track', {}).get('file') or '')
        for p in api.state.now_playing.active()
        if not p.get('paused', False)
    }
    if active.intersection(files):
        raise TrashError('track_is_playing')
    runner = getattr(api.state, 'upgrade_runner', None)
    if runner is not None:
        status = runner.status()
        if status.get('state') in {
            'running',
            'scanning',
            'pausing',
        } or status.get('counts', {}).get('running', 0):
            raise TrashError('library_task_active')


@router.get('/capabilities')
def capabilities(request: Request):
    try:
        admin_user(request)
    except HTTPException:
        return {
            'can_manage': False,
            'enabled': getattr(api.state, 'library_trash', None) is not None,
            'retention_days': 30,
        }
    return {
        'can_manage': getattr(api.state, 'library_trash', None) is not None,
        'enabled': getattr(api.state, 'library_trash', None) is not None,
        'retention_days': 30,
    }


@router.post('/preview', status_code=202)
async def preview(payload: Selection, request: Request):
    user = admin_user(request)
    store()
    if not payload.files and not payload.track_ids:
        raise HTTPException(409, detail={'code': 'invalid_selection'})
    _clean_preview_jobs()
    if any(
        j['user_id'] == user and j['state'] == 'preparing'
        for j in _previews.values()
    ):
        raise HTTPException(409, detail={'code': 'preview_busy'})
    if sum(j['state'] == 'preparing' for j in _previews.values()) >= 4:
        raise HTTPException(429, detail={'code': 'preview_busy'})
    job_id = secrets.token_urlsafe(32)
    _previews[job_id] = {
        'user_id': user,
        'state': 'preparing',
        'created': time.monotonic(),
    }
    asyncio.create_task(_run_preview(job_id, payload, user))
    return {'request_id': job_id, 'state': 'preparing'}


@router.get('/preview/{job_id}')
async def preview_status(job_id: str, request: Request):
    user = admin_user(request)
    _clean_preview_jobs()
    job = _previews.get(job_id)
    if job is None or job['user_id'] != user:
        raise HTTPException(404, detail={'code': 'preview_unavailable'})
    if job['state'] == 'failed':
        raise HTTPException(409, detail={'code': job['error']})
    if job['state'] == 'ready':
        return {'state': 'ready', 'preview': job['preview']}
    return {'state': 'preparing'}


@router.post('/confirm', status_code=202)
async def confirm(payload: Confirmation, request: Request):
    user = admin_user(request)
    files = await call(store().confirmation_files, user, payload.confirmation)
    await call(ensure_idle, files)
    ids = await call(store().confirm, user, payload.confirmation)
    await publish_changes()
    await api.log_activity(request, 'library_trash_requested', str(len(ids)))
    return {'ids': ids, 'state': 'pending'}


@router.get('')
async def listing(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str = Query('', max_length=200),
):
    admin_user(request)
    await publish_changes()
    return await call(store().list, offset=offset, limit=limit, search=search)


@router.get('/exclusions')
async def exclusions(request: Request):
    admin_user(request)
    return {'items': await call(store().exclusions)}


@router.post('/restore', status_code=202)
async def restore(payload: Items, request: Request):
    user = admin_user(request)
    await call(store().request_restore, payload.ids, user_id=user)
    await api.log_activity(
        request, 'library_trash_restore_requested', str(len(payload.ids))
    )
    return {'state': 'restore_pending'}


@router.post('/allow-download')
async def allow_download(payload: Items, request: Request):
    admin_user(request)
    await call(store().allow_download, payload.ids)
    await publish_changes()
    return {'ok': True}


@router.post('/retry', status_code=202)
async def retry(payload: Items, request: Request):
    user = admin_user(request)
    await call(store().retry, payload.ids, user_id=user)
    return {'state': 'pending'}


_revision = None


async def publish_changes():
    global _revision
    value = getattr(api.state, 'library_trash', None)
    if value is None:
        return
    revision = await asyncio.to_thread(value.revision)
    if revision == _revision:
        return
    invalidate_library_paths_cache(drop_entries=True)
    if api.state.library_visibility is not None:
        api.state.library_visibility.invalidate()
    if api.state.library_sync is not None:
        await asyncio.to_thread(
            lambda: api.state.library_sync.refresh(
                list_library_entries(api.library_context())
            )
        )
    api.announce_library_changed()
    await api.announce_playlists_changed()
    _revision = revision


async def watch_trash():
    while True:
        try:
            await publish_changes()
        except Exception as error:
            logger.warning(
                'Trash synchronization deferred ({})', type(error).__name__
            )
        await asyncio.sleep(2)
