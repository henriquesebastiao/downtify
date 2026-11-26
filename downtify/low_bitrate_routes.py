"""Low-bitrate report API (admins). The logic is in
:mod:`downtify.low_bitrate`.

``GET /api/library/low-bitrate``
    The report: files under the threshold, each with the candidates its
    last search found and where its replacement stands. Writes nothing.
``POST /api/library/low-bitrate/search``
    Look for better copies of some files on Soulseek. Writes nothing:
    the candidates are kept here, in memory, for the page to show.
``POST /api/library/low-bitrate/replace``
    Replace files with the copies the admin chose. Each one is a queue
    job (the usual progress, in the shared download slot); the old file
    is merged into the new one the way the Doctor merges duplicates and
    goes to the music trash, so it can be restored.

Nothing is replaced without that last request, and it only takes
candidate ids a search on this server returned: a peer or file name
can't be sent in from outside.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from loguru import logger
from pydantic import BaseModel, Field

from . import api, doctor_routes, trash_routes
from . import low_bitrate as lb
from .admin_access import admin_user
from .download_queue import queue_pause
from .downloader import DOWNLOAD_EXECUTOR
from .duplicate_merge import (
    MergeError,
    finish_merge,
    leftover_references,
    plan_merge,
    relink_duplicates,
)
from .file_providers import guess_provider
from .library_cache_keys import file_content_key
from .library_catalog import (
    entry_content_key,
    list_library_entries,
    merge_library_listing_file,
    resolve_library_file,
)
from .library_paths import library_stored_path
from .library_trash import TrashError

router = APIRouter(
    prefix='/api/library/low-bitrate', dependencies=[Depends(admin_user)]
)

#: Files one search or replace request may name.
MAX_FILES = 50
#: Searches run at once (each also holds an slskd parallel slot).
SEARCH_PARALLEL = 2
#: A search result older than this is searched again before replacing.
SEARCH_TTL_SECONDS = 6 * 3600

#: ``{file: {state, candidates, rows, error, searched_at, lossless}}``;
#: ``rows`` (the peers' raw file rows) never leave the server.
_searches: dict[str, dict[str, Any]] = {}
#: ``{file: {state, job_id, message, code, new_file, ...}}``.
_replacements: dict[str, dict[str, Any]] = {}
_search_slots: Optional[asyncio.Semaphore] = None


class Files(BaseModel):
    files: list[str] = Field(min_length=1, max_length=MAX_FILES)
    include_lossless: bool = False


class Choice(BaseModel):
    file: str = Field(min_length=1, max_length=4096)
    candidate: str = Field(min_length=1, max_length=64)


class Choices(BaseModel):
    items: list[Choice] = Field(min_length=1, max_length=MAX_FILES)


def _norm(value: str) -> str:
    return str(value or '').strip().replace('\\', '/')


def _settings() -> dict[str, Any]:
    downloader = api.state.downloader
    return dict(getattr(downloader, 'slskd_settings', None) or {})


def _slskd_ready() -> bool:
    settings = _settings()
    return bool(
        settings.get('enabled')
        and settings.get('base_url')
        and settings.get('api_key')
    )


def _entries() -> dict[str, dict[str, Any]]:
    ctx = api.library_context()
    return {entry['file']: entry for entry in list_library_entries(ctx)}


def _sources(rows: list[dict[str, Any]], entries: dict[str, Any]) -> None:
    """Fill in where each file came from (best effort)."""

    store = api.state.file_providers
    recorded: dict[str, str] = {}
    if store is not None:
        try:
            recorded = store.lookup({
                row['file']: entry_content_key(entries[row['file']])
                for row in rows
            })
        except Exception:
            logger.opt(exception=True).debug('Low bitrate: no providers')
    for row in rows:
        row['source'] = recorded.get(row['file']) or guess_provider(
            row['file']
        )


def _search_view(file: str) -> Optional[dict[str, Any]]:
    found = _searches.get(file)
    if found is None:
        return None
    return {key: value for key, value in found.items() if key != 'rows'}


def _report(threshold: int) -> dict[str, Any]:
    entries = _entries()
    rows = lb.report_rows(entries.values(), threshold)
    _sources(rows, entries)
    hand = api.state.hand_replaced
    for row in rows:
        row['search'] = _search_view(row['file'])
        row['replacement'] = _replacements.get(row['file'])
        if hand is not None:
            try:
                row['hand_replaced'] = hand.protected(row['file'])
            except Exception:
                row['hand_replaced'] = False
    # Files replaced since are no longer in the listing; their result
    # stays on the page until it is reloaded.
    listed = {row['file'] for row in rows}
    done = [
        {'file': file, **result}
        for file, result in _replacements.items()
        if file not in listed
    ]
    return {
        'threshold': threshold,
        'tracks': rows,
        'total': len(rows),
        'size': sum(row['size'] for row in rows),
        'finished': done,
        'slskd': _slskd_ready(),
        'trash': api.state.library_trash is not None,
    }


@router.get('')
async def low_bitrate_report(
    threshold: int = Query(lb.DEFAULT_THRESHOLD_KBPS),
) -> dict[str, Any]:
    """Library files under *threshold* kbps (lossy only), lowest first,
    with their candidates and replacement state. Writes nothing."""

    return await asyncio.to_thread(_report, lb.clamp_threshold(threshold))


# ── Search ──────────────────────────────────────────────────────────────


def _search_one(file: str, entry: dict[str, Any], lossless: bool) -> None:
    song = lb.song_for_entry(entry)
    old_kbps = lb._kbps(entry.get('bitrate'))
    try:
        rows = lb.search_candidates(
            song, _settings(), old_kbps, include_lossless=lossless
        )
    except lb.UpgradeError as exc:
        _searches[file] = {
            'state': 'error',
            'code': exc.code,
            'candidates': [],
            'searched_at': time.time(),
            'lossless': lossless,
        }
        return
    except Exception:
        logger.opt(exception=True).warning(
            'Low bitrate: searching for {} failed', file
        )
        _searches[file] = {
            'state': 'error',
            'code': 'search_failed',
            'candidates': [],
            'searched_at': time.time(),
            'lossless': lossless,
        }
        return
    duration = float(entry.get('duration') or 0)
    _searches[file] = {
        'state': 'done',
        'candidates': [lb.public_candidate(row, duration) for row in rows],
        'rows': {lb.candidate_id(row): row for row in rows},
        'searched_at': time.time(),
        'lossless': lossless,
    }


async def _search_task(
    files: list[str], entries: dict[str, Any], lossless: bool
) -> None:
    global _search_slots
    if _search_slots is None:
        _search_slots = asyncio.Semaphore(SEARCH_PARALLEL)

    async def one(file: str) -> None:
        async with _search_slots:
            if _searches.get(file, {}).get('state') != 'queued':
                return
            _searches[file]['state'] = 'searching'
            await asyncio.to_thread(_search_one, file, entries[file], lossless)

    await asyncio.gather(*(one(file) for file in files))


@router.post('/search', status_code=202)
async def low_bitrate_search(payload: Files) -> dict[str, Any]:
    """Look for better copies of *files* on Soulseek, in the background:
    ``{queued}``. The report shows each file's candidates as they come."""

    if not _slskd_ready():
        raise HTTPException(409, detail={'code': 'slskd_off'})
    entries = await asyncio.to_thread(_entries)
    files = []
    for raw in dict.fromkeys(_norm(f) for f in payload.files):
        if raw not in entries:
            continue
        if _searches.get(raw, {}).get('state') in {'queued', 'searching'}:
            continue
        if _replacements.get(raw, {}).get('state') in _ACTIVE:
            continue
        _searches[raw] = {
            'state': 'queued',
            'candidates': [],
            'lossless': payload.include_lossless,
        }
        files.append(raw)
    if files:
        api.spawn_task(
            _search_task(files, entries, payload.include_lossless),
            name='low-bitrate-search',
        )
    return {'queued': len(files)}


# ── Replace ─────────────────────────────────────────────────────────────

_ACTIVE = {'queued', 'downloading', 'replacing'}


def _chosen_row(file: str, candidate: str) -> dict[str, Any]:
    found = _searches.get(file)
    if not found or found.get('state') != 'done':
        raise lb.UpgradeError('search_again')
    if time.time() - float(found.get('searched_at') or 0) > SEARCH_TTL_SECONDS:
        raise lb.UpgradeError('search_again')
    row = (found.get('rows') or {}).get(candidate)
    if row is None:
        raise lb.UpgradeError('search_again')
    return row


def _trash_preview(file: str, user_id: int) -> str:
    """A music trash confirmation for *file* (checked before anything
    is downloaded: a song the trash can't take stops here)."""

    trash = api.state.library_trash
    if trash is None:
        raise lb.UpgradeError('trash_off')
    try:
        tracks = trash_routes._selection(trash_routes.Selection(files=[file]))
        return trash.preview(user_id, tracks)['confirmation']
    except TrashError as exc:
        raise lb.UpgradeError('trash_refused', str(exc)) from None


@router.post('/replace', status_code=202)
async def low_bitrate_replace(
    payload: Choices, request: Request
) -> dict[str, Any]:
    """Replace each file with the candidate chosen for it:
    ``{started: [{file, job_id}], refused: [{file, code, detail}]}``."""

    user_id = admin_user(request)
    if api.state.downloader is None:
        raise HTTPException(503, detail={'code': 'not_ready'})
    entries = await asyncio.to_thread(_entries)
    started, refused = [], []
    for choice in payload.items:
        file = _norm(choice.file)
        try:
            if file not in entries:
                raise lb.UpgradeError('missing')
            if _replacements.get(file, {}).get('state') in _ACTIVE:
                raise lb.UpgradeError('already_running')
            row = _chosen_row(file, choice.candidate)
            await asyncio.to_thread(_trash_preview, file, user_id)
        except lb.UpgradeError as exc:
            refused.append({
                'file': file,
                'code': exc.code,
                'detail': exc.detail,
            })
            continue
        job_id = _start_job(
            file, entries[file], choice.candidate, row, user_id
        )
        started.append({'file': file, 'job_id': job_id})
    if started:
        await api.log_activity(
            request,
            'low_bitrate_replace',
            f'{len(started)} file(s)',
            {'files': [item['file'] for item in started]},
        )
    return {'started': started, 'refused': refused}


def _job_song(file: str, entry: dict[str, Any], candidate: str) -> dict:
    summary = api._track_summary(file, entry)
    return {
        'song_id': f'low-bitrate:{file}',
        'name': summary['title'] or Path(file).stem,
        'artists': [
            a.strip() for a in summary['artist'].split(',') if a.strip()
        ],
        'album_name': summary['album'],
        'cover_url': f'/cover?file={quote(file)}',
        'duration': summary['duration'],
        'url': '',
        # Tells the queue this job replaces a low-bitrate file: a retry
        # replaces again with the same copy, never downloads a new track.
        'low_bitrate': {'file': file, 'candidate': candidate},
    }


def _start_job(
    file: str,
    entry: dict[str, Any],
    candidate: str,
    row: dict[str, Any],
    user_id: int,
) -> str:
    song = _job_song(file, entry, candidate)
    job_id = api._register_job(song, status='queued', user_id=user_id)
    _replacements[file] = {
        'state': 'queued',
        'job_id': job_id,
        'candidate': candidate,
        'message': '',
    }
    api.spawn_task(
        _run(job_id, song, file, entry, row, user_id),
        name=f'low-bitrate-{job_id}',
    )
    return job_id


async def _broadcast(
    job: dict[str, Any], song: dict, status: str, pct: float, message: str
) -> None:
    job.update(status=status, progress=pct, message=message)
    await api.state.connections.broadcast({
        'song': song,
        'progress': pct,
        'message': message,
        'provider': 'slskd',
        'status': status,
    })


def _fail(file: str, code: str, detail: str = '') -> None:
    _replacements[file].update(state='error', code=code, message=detail)


async def _run(
    job_id: str,
    song: dict[str, Any],
    file: str,
    entry: dict[str, Any],
    row: dict[str, Any],
    user_id: int,
) -> None:
    loop = api.state.loop or asyncio.get_running_loop()
    job = api.state.download_jobs[job_id]
    search_song = lb.song_for_entry(entry)

    def progress(pct: float, message: str, provider: Optional[str] = None):
        job.update(progress=pct, message=message, provider='slskd')
        asyncio.run_coroutine_threadsafe(
            api.state.connections.broadcast({
                'song': song,
                'progress': pct,
                'message': message,
                'provider': 'slskd',
                'status': 'downloading',
            }),
            loop,
        )

    def fetch_and_place() -> tuple[Path, Path, dict[str, Any]]:
        old = resolve_library_file(file, api.library_context())
        if old is None:
            raise lb.UpgradeError('missing')
        downloaded = lb.fetch_candidate(
            search_song, _settings(), row, progress_cb=progress
        )
        progress(96.0, 'Checking the new copy')
        try:
            new, figures = lb.place_upgrade(old, downloaded)
        except lb.UpgradeError:
            # A refused copy must not join the library from slskd's folder.
            lb.discard_transfer(downloaded, _settings())
            raise
        return downloaded, new, figures

    sem = api.state.download_semaphore
    try:
        async with sem if sem is not None else contextlib.nullcontext():
            if not await api._queue_turn(job_id, job, song):
                _fail(file, 'cancelled')
                return
            _replacements[file]['state'] = 'downloading'
            await _broadcast(job, song, 'downloading', 2, 'slskd · queued')
            async with queue_pause.running():
                downloaded, new, figures = await loop.run_in_executor(
                    DOWNLOAD_EXECUTOR, fetch_and_place
                )
        _replacements[file]['state'] = 'replacing'
        result = await _publish(file, new, downloaded, user_id)
    except lb.UpgradeError as exc:
        _fail(file, exc.code, exc.detail)
        await _broadcast(job, song, 'error', 0, f'Error: {exc.code}')
        return
    except Exception as exc:
        logger.opt(exception=True).warning(
            'Low bitrate: replacing {} failed', file
        )
        _fail(file, 'failed', str(exc))
        await _broadcast(job, song, 'error', 0, f'Error: {exc}')
        return
    _replacements[file].update(state='done', **figures, **result)
    _searches.pop(file, None)
    job.update(filename=result['new_file'])
    await _broadcast(job, song, 'done', 100, 'Replaced')
    api.announce_library_changed()


async def _publish(
    file: str, new: Path, downloaded: Path, user_id: int
) -> dict[str, Any]:
    """The new copy joins the library, the old file is merged into it
    (every reference moves) and goes to the music trash."""

    ctx = api.library_context()
    new_file = library_stored_path(
        new, ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs
    )
    try:
        if api.state.metadata_cache is not None:
            await asyncio.to_thread(
                api.state.metadata_cache.refresh, new_file, new
            )
        await asyncio.to_thread(merge_library_listing_file, ctx, new_file)
        batch = await asyncio.to_thread(_trash_preview, file, user_id)
        stores = doctor_routes._merge_stores(ctx)
        plan = await asyncio.to_thread(plan_merge, new_file, [file], ctx)
        await asyncio.to_thread(relink_duplicates, plan, stores)
    except (lb.UpgradeError, MergeError, HTTPException) as exc:
        # Nothing points at the new copy yet: it goes, the old file stays.
        await asyncio.to_thread(lb.discard_new_copy, new)
        code = getattr(exc, 'code', '') or 'merge_refused'
        raise lb.UpgradeError(code, getattr(exc, 'file', '') or '') from None
    removed, failed = await doctor_routes._remove_copies(
        plan, ctx, user_id, batch
    )
    await asyncio.to_thread(finish_merge, plan, stores, removed)
    _record_provider(new, new_file)
    _clean_transfer(downloaded, new)
    await asyncio.to_thread(
        doctor_routes._publish_library, api.library_context()
    )
    if plan.playlists:
        await api._schedule_playlist_refresh_after_delete(set(plan.playlists))
    await api.announce_playlists_changed()
    leftovers = await asyncio.to_thread(leftover_references, plan, stores)
    if failed:
        logger.warning(
            'Low bitrate: {} kept beside its new copy {}: {}',
            file,
            new_file,
            failed[0].get('error'),
        )
    return {
        'new_file': new_file,
        'trashed': bool(removed),
        'playlists': sorted(plan.playlists),
        'leftovers': leftovers,
    }


def _record_provider(new: Path, new_file: str) -> None:
    store = api.state.file_providers
    if store is None:
        return
    try:
        store.record(file_content_key(new) or '', new_file, 'slskd')
    except Exception:
        logger.opt(exception=True).debug('Low bitrate: provider not kept')


def _clean_transfer(downloaded: Path, new: Path) -> None:
    """slskd's own copy of the transfer goes, as after a download
    (only inside slskd's folder; see the downloader)."""

    downloader = api.state.downloader
    cleanup = getattr(downloader, '_remove_slskd_source_after_import', None)
    if cleanup is None:
        return
    try:
        cleanup(downloaded, new)
    except Exception:
        logger.opt(exception=True).debug('Low bitrate: transfer kept')


@router.post('/forget')
async def low_bitrate_forget(payload: Files) -> dict[str, Any]:
    """Clear the page's search results and finished replacements for
    *files* (nothing on disk changes): ``{forgotten}``."""

    count = 0
    for raw in payload.files:
        file = _norm(raw)
        if _searches.get(file, {}).get('state') not in {'queued', 'searching'}:
            count += _searches.pop(file, None) is not None
        if _replacements.get(file, {}).get('state') not in _ACTIVE:
            count += _replacements.pop(file, None) is not None
    return {'forgotten': count}
