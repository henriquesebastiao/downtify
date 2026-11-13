"""Doctor API (admins): health check, slskd leftover cleanup, playlist
and Navidrome repairs. The logic is in :mod:`downtify.doctor`.

One Doctor job runs at a time, in a thread; the page polls
``GET /api/doctor`` for its progress. Every repair re-reads what it
changed afterwards (the files, Navidrome's playlists) and reports what
it found, rather than assuming it worked.

The slskd cleanup is the only one that deletes audio, and it is gated
three times: the download queue is paused (and drained) before the
scan, only files whose audio is proven identical to a library file are
offered, and each one is checked again - same size and modification
time, its library twin still there - right before it is removed.
"""

from __future__ import annotations

import asyncio
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from pydantic import BaseModel, Field

from . import api, m3u, trash_routes
from .admin_access import admin_user
from .doctor import (
    STATUS_VERIFIED,
    CopyResult,
    M3UInfo,
    PlaylistGroup,
    m3u_duplicate_groups,
    merge_m3u_files,
    navidrome_playlist_findings,
    navidrome_root,
    navidrome_song_duplicates,
    norm,
    prune_empty_dirs,
    relinked_tracks,
    summarize_copies,
    verify_copies,
    working_copy_rows,
)
from .doctor_audio import AudioHashCache
from .duplicate_merge import (
    KeptApart,
    MergeError,
    MergePlan,
    MergeStores,
    finish_merge,
    leftover_references,
    plan_merge,
    relink_duplicates,
)
from .library_catalog import drop_library_listing_files, list_library_entries
from .library_delete import delete_library_file
from .library_paths import locate_library_file
from .library_paths_cache import invalidate_library_paths_cache
from .library_trash import TrashError
from .library_usage import duplicates
from .navidrome import NavidromeClient, _effective_navidrome_settings
from .playlist_identity import made_by_downtify, playlist_key

router = APIRouter(prefix='/api/doctor', dependencies=[Depends(admin_user)])

#: How long the queue may wait for running downloads before the scan.
DRAIN_TIMEOUT = 30 * 60
#: A scan nobody acts on gives the queue back after this.
PAUSE_EXPIRY = 60 * 60
#: Examples returned per finding; counts always cover everything.
EXAMPLES = 50
#: Duplicate groups the review lists (the counts cover all of them).
REVIEW_GROUPS = 500
#: Copies one merge may remove.
MERGE_MAX = 20

_lock = threading.Lock()
_job: dict[str, Any] = {}
#: The last result of each kind of job, as the page shows it.
_last: dict[str, Any] = {}
#: What the Doctor holds between requests: the queue it paused
#: (``hold``), the last slskd check (``copies``), the Navidrome playlists
#: the last health check flagged (``flagged``).
_state: dict[str, Any] = {}
_hashes: Optional[AudioHashCache] = None
_kept: Optional[KeptApart] = None


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _data_dir() -> Path:
    path = api.state.settings_path
    return Path(path).parent if path else Path('/data')


def _hash_cache() -> AudioHashCache:
    global _hashes
    if _hashes is None:
        _hashes = AudioHashCache(_data_dir() / 'doctor' / 'audio_hashes.db')
    return _hashes


def _kept_apart() -> KeptApart:
    global _kept
    if _kept is None:
        _kept = KeptApart(_data_dir() / 'doctor' / 'duplicates.db')
    return _kept


def _busy() -> bool:
    return _job.get('state') == 'running'


def _start(kind: str, work: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    """Run *work* in a thread as the Doctor's one job."""

    with _lock:
        if _busy():
            raise HTTPException(409, detail={'code': 'doctor_busy'})
        job: dict[str, Any] = {
            'id': secrets.token_urlsafe(8),
            'kind': kind,
            'state': 'running',
            'started_at': _now(),
            'progress': {'done': 0, 'total': 0, 'step': ''},
            'cancel': False,
        }
        _job.clear()
        _job.update(job)

    async def run() -> None:
        try:
            result = await work(_job)
            _job.update(state='done', result=result, finished_at=_now())
            _last[kind] = {'at': _now(), 'result': result}
        except HTTPException as exc:
            _job.update(state='failed', error=exc.detail, finished_at=_now())
        except Exception as exc:
            logger.exception('doctor: {} failed', kind)
            _job.update(
                state='failed',
                error={'code': 'doctor_failed', 'message': str(exc)},
                finished_at=_now(),
            )

    asyncio.get_running_loop().create_task(run())
    return _public_job()


def _step(job: dict[str, Any], step: str, done: int = 0, total: int = 0):
    job['progress'] = {'done': done, 'total': total, 'step': step}


def _public_job() -> dict[str, Any]:
    return {k: v for k, v in _job.items() if k != 'cancel'}


@router.get('')
async def doctor_status() -> dict[str, Any]:
    """The running or last job, the last result of each kind, and
    whether the Doctor is holding the download queue."""

    return {
        'job': _public_job() or None,
        'last': _last,
        'queue': api._global_queue_status(),
        'holding_queue': bool(_state.get('hold')),
    }


@router.post('/cancel')
async def doctor_cancel() -> dict[str, Any]:
    _job['cancel'] = True
    return _public_job()


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def _ctx():
    return api.library_context()


def _organized() -> bool:
    dl = api.state.downloader
    return bool(
        dl is not None
        and (
            getattr(dl, 'organize_by_artist', False)
            or getattr(dl, 'organize_by_album', False)
        )
    )


def _m3u_infos(ctx) -> list[M3UInfo]:
    root = Path(ctx.download_dir)
    organize = _organized()
    infos: list[M3UInfo] = []
    for path in m3u.iter_m3u_files(root):
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue
        entries = m3u.read_m3u_entries(
            path, root, ctx.slskd_dir, ctx.extra_dirs
        )
        present = [
            stored
            for stored, _extinf in entries
            if locate_library_file(stored, root, ctx.slskd_dir, ctx.extra_dirs)
        ]
        text = m3u.read_m3u_text(path) or ''
        lines = sum(
            1
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith('#')
        )
        name = path.stem
        expected = m3u.m3u_path_for(
            root,
            name,
            playlist_subdir=None
            if organize
            else m3u.sanitize_playlist_name(name),
        )
        infos.append(
            M3UInfo(
                path=rel,
                name=name,
                manual=m3u.is_manual_m3u(path),
                entries=present,
                lines=lines,
                cover=path.with_suffix('.jpg').is_file(),
                expected=expected == path,
            )
        )
    return infos


def _referenced(inputs: dict[str, Any], infos: list[M3UInfo]) -> set[str]:
    """Every library path something still points at: the track index,
    the provider records, every M3U and every monitored playlist."""

    referenced = set(inputs['referenced'])
    for info in infos:
        referenced.update(info.entries)
    db = api.state.monitor_db
    if db is not None:
        for row in db.list_all_downloaded_tracks():
            referenced.add(norm(row.get('filename')))
    referenced.discard('')
    return referenced


def _navidrome() -> Optional[tuple[NavidromeClient, dict[str, Any]]]:
    cfg = _effective_navidrome_settings(api.state.settings)
    if not cfg.get('enabled'):
        return None
    client = NavidromeClient(cfg)
    if not client.configured():
        return None
    return client, cfg


def _navidrome_playlists(client: NavidromeClient) -> tuple[list[dict], bool]:
    native = client.native_playlists()
    if native is not None:
        return native, True
    return client.list_playlists(admin=True), False


def _rescan(
    client: NavidromeClient, cfg: dict[str, Any], *, full: bool
) -> bool:
    try:
        client.start_scan(full=full)
    except Exception as exc:
        logger.info('doctor: navidrome scan failed err={}', exc)
        return False
    return client.wait_scan_complete(int(cfg.get('scan_wait_seconds') or 120))


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@router.post('/scan')
async def doctor_scan() -> dict[str, Any]:
    """Look for everything the Doctor knows how to find. Changes nothing."""

    async def work(job: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(_health, job)

    return _start('health', work)


def _health(job: dict[str, Any]) -> dict[str, Any]:
    ctx = _ctx()
    _step(job, 'library')
    inputs = api._usage_library_inputs(ctx)
    _step(job, 'playlists')
    infos = _m3u_infos(ctx)
    referenced = _referenced(inputs, infos)
    library, leftovers = working_copy_rows(
        inputs['entries'],
        sources=inputs['sources'],
        slskd_in_place=inputs['slskd_in_place'],
        referenced=referenced,
    )
    _step(job, 'duplicates')
    dupes = duplicates(library, inputs['providers'], limit=None)
    groups = m3u_duplicate_groups(infos)
    report: dict[str, Any] = {
        'scanned_at': _now(),
        'slskd': {
            'in_place': inputs['slskd_in_place'],
            'leftovers': len(leftovers),
            'bytes': sum(int(r.get('size') or 0) for r in leftovers),
        },
        'duplicates': _duplicate_review(dupes.get('examples', []), infos),
        'playlists': {
            'm3u': len(infos),
            'groups': [g.as_dict() for g in groups],
            'list': [i.as_dict() for i in sorted(infos, key=lambda i: i.path)],
        },
    }
    _step(job, 'monitor')
    report['relinked'] = _relinked(inputs['entries'])
    _step(job, 'navidrome')
    report['navidrome'] = _navidrome_health(infos)
    _state['flagged'] = {
        m['id']
        for g in report['navidrome'].get('duplicates', [])
        for m in g['members']
    } | {o['id'] for o in report['navidrome'].get('orphans', [])}
    return report


def _duplicate_review(
    found: list[dict[str, Any]], infos: list[M3UInfo]
) -> dict[str, Any]:
    """The duplicate groups to decide on: all but those kept apart, each
    file with the playlists it is in (from the M3U files)."""

    kept = _kept_apart()
    pairs = kept.pairs()
    review = [
        g
        for g in found
        if not kept.settled([f['file'] for f in g['files']], pairs)
    ]
    playlists: dict[str, list[str]] = {}
    for info in infos:
        for stored in info.entries:
            names = playlists.setdefault(norm(stored), [])
            if info.name not in names:
                names.append(info.name)
    for group in review:
        for item in group['files']:
            item['playlists'] = sorted(playlists.get(norm(item['file']), []))
    _state['duplicates'] = {
        norm(item['file']): index
        for index, group in enumerate(review)
        for item in group['files']
    }
    return {
        'totals': _duplicate_totals(review),
        'groups': review[:REVIEW_GROUPS],
        'kept_apart': len(found) - len(review),
        # Where a merge's extra copies go: the music trash, or for good.
        'trash': api.state.library_trash is not None,
    }


def _duplicate_totals(groups: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        kind: {
            'groups': sum(1 for g in groups if g['kind'] == kind),
            'files': sum(
                len(g['files']) - 1 for g in groups if g['kind'] == kind
            ),
            'bytes': sum(g['bytes'] for g in groups if g['kind'] == kind),
        }
        for kind in ('exact', 'likely')
    }


def _relinked(entries: list[dict[str, Any]]) -> dict[str, Any]:
    db = api.state.monitor_db
    if db is None:
        return {'songs': 0, 'extra_files': 0, 'playlists': {}, 'examples': []}
    names = {p.id: p.name for p in db.list_playlists()}
    listing = {norm(e.get('file')): e for e in entries}
    return relinked_tracks(
        db.list_all_downloaded_tracks(), names, listing, limit=EXAMPLES
    )


def _navidrome_health(infos: list[M3UInfo]) -> dict[str, Any]:
    found = _navidrome()
    if found is None:
        return {'enabled': False}
    client, cfg = found
    if not client.ping():
        return {'enabled': True, 'reachable': False}
    playlists, native = _navidrome_playlists(client)
    root = navidrome_root(playlists, [i.path for i in infos])
    findings = navidrome_playlist_findings(playlists, infos, root=root)
    try:
        songs = client.all_songs()
    except Exception as exc:
        logger.info('doctor: navidrome song list failed err={}', exc)
        songs = []
    pairs = sum(
        1 for d in findings['duplicates'] if d['reason'] == 'm3u_and_api'
    )
    return {
        'enabled': True,
        'reachable': True,
        'native': native,
        'admin': bool(cfg.get('admin_username') and cfg.get('admin_password')),
        'root': root,
        'm3u_import': bool(cfg.get('m3u_import')),
        'suggest_m3u_import': pairs > 0 and not cfg.get('m3u_import'),
        'playlists': len(playlists),
        'songs': len(songs),
        'song_duplicates': navidrome_song_duplicates(songs, limit=EXAMPLES),
        **findings,
    }


# ---------------------------------------------------------------------------
# slskd leftovers
# ---------------------------------------------------------------------------


@router.post('/slskd/scan')
async def slskd_scan() -> dict[str, Any]:
    """Pause the queue, wait for running downloads, then check every
    slskd leftover against the library. Deletes nothing."""

    async def work(job: dict[str, Any]) -> dict[str, Any]:
        await _hold_queue(job)
        results = await asyncio.to_thread(_slskd_verify, job)
        hold = _state.get('hold') or {}
        hold['token'] = job['id']
        _state['hold'] = hold
        _state['copies'] = {r.file: r for r in results}
        asyncio.get_running_loop().create_task(_expire_hold(job['id']))
        return {
            'summary': summarize_copies(results),
            'checked': len(results),
            'paused_by_doctor': bool(hold.get('paused_by_doctor')),
            'expires_in': PAUSE_EXPIRY,
        }

    return _start('slskd', work)


async def _hold_queue(job: dict[str, Any]) -> None:
    paused_before = api.queue_pause.paused
    if not paused_before:
        await api._set_queue_paused(True)
    _state['hold'] = {'paused_by_doctor': not paused_before}
    deadline = time.monotonic() + DRAIN_TIMEOUT
    while True:
        status = api._global_queue_status()
        if status.get('state') != 'pausing':
            return
        if time.monotonic() > deadline or job.get('cancel'):
            await _release_queue()
            raise HTTPException(409, detail={'code': 'queue_busy'})
        _step(job, 'pausing', 0, int(status.get('active') or 0))
        await asyncio.sleep(2)


async def _release_queue() -> None:
    hold = _state.pop('hold', None) or {}
    _state.pop('copies', None)
    if hold.get('paused_by_doctor'):
        await api._set_queue_paused(False)


async def _expire_hold(token: str) -> None:
    """Give the queue back if the scan *token* started is still
    waiting for a decision after :data:`PAUSE_EXPIRY`."""

    await asyncio.sleep(PAUSE_EXPIRY)
    if (_state.get('hold') or {}).get('token') == token and not _busy():
        logger.info('doctor: slskd cleanup not confirmed; queue resumed')
        await _release_queue()


@router.get('/slskd/files')
async def slskd_files(
    status: str = '', offset: int = 0, limit: int = 100
) -> dict[str, Any]:
    """The last slskd check, a page at a time, biggest first."""

    copies: dict[str, CopyResult] = _state.get('copies') or {}
    rows = [r for r in copies.values() if not status or r.status == status]
    rows.sort(key=lambda r: (-r.bytes, r.file))
    offset = max(0, offset)
    limit = min(500, max(1, limit))
    return {
        'total': len(rows),
        'files': [r.as_dict() for r in rows[offset : offset + limit]],
    }


def _slskd_verify(job: dict[str, Any]) -> list[CopyResult]:
    ctx = _ctx()
    _step(job, 'listing')
    inputs = api._usage_library_inputs(ctx)
    infos = _m3u_infos(ctx)
    library, leftovers = working_copy_rows(
        inputs['entries'],
        sources=inputs['sources'],
        slskd_in_place=inputs['slskd_in_place'],
        referenced=_referenced(inputs, infos),
    )

    def locate(stored: str) -> Optional[Path]:
        return locate_library_file(
            stored, ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs
        )

    cache = _hash_cache()
    return verify_copies(
        leftovers,
        library,
        locate=locate,
        digest=cache.digest,
        now=time.time(),
        progress=lambda done, total: _step(job, 'verifying', done, total),
        cancelled=lambda: bool(job.get('cancel')),
    )


class Cleanup(BaseModel):
    files: list[str] = Field(default_factory=list, max_length=200_000)


@router.post('/slskd/clean')
async def slskd_clean(payload: Cleanup) -> dict[str, Any]:
    """Delete verified leftovers from the last scan (all of them, or the
    listed ones), resume the queue, and have Navidrome rescan."""

    results: dict[str, CopyResult] = _state.get('copies') or {}
    if not results:
        raise HTTPException(409, detail={'code': 'scan_first'})
    wanted = set(payload.files) or set(results)
    chosen = [
        r
        for name, r in results.items()
        if name in wanted and r.status == STATUS_VERIFIED
    ]

    async def work(job: dict[str, Any]) -> dict[str, Any]:
        outcome = await asyncio.to_thread(_slskd_delete, job, chosen)
        await _release_queue()
        outcome['queue'] = api._global_queue_status()
        outcome['navidrome'] = await asyncio.to_thread(_after_slskd_clean, job)
        return outcome

    return _start('slskd_clean', work)


@router.post('/slskd/release')
async def slskd_release() -> dict[str, Any]:
    """Leave the leftovers alone and give the queue back."""

    if _busy() and _job.get('kind') == 'slskd':
        _job['cancel'] = True
    await _release_queue()
    return {'queue': api._global_queue_status()}


def _slskd_delete(job: dict[str, Any], chosen: list[CopyResult]) -> dict:
    ctx = _ctx()
    root = Path(ctx.slskd_dir) if ctx.slskd_dir else None
    deleted: list[str] = []
    kept: list[dict[str, str]] = []
    freed = 0
    cache = _hash_cache()
    for done, result in enumerate(chosen):
        if job.get('cancel'):
            break
        _step(job, 'deleting', done, len(chosen))
        path = locate_library_file(
            result.file, ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs
        )
        twin = locate_library_file(
            result.match, ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs
        )
        reason = ''
        if path is None:
            reason = 'gone'
        elif twin is None:
            reason = 'library_copy_gone'
        else:
            try:
                stat = path.stat()
            except OSError:
                reason = 'gone'
            else:
                if (
                    stat.st_size != result.bytes
                    or stat.st_mtime_ns != result.mtime_ns
                ):
                    reason = 'changed'
        if reason or path is None:
            kept.append({'file': result.file, 'reason': reason})
            continue
        try:
            path.unlink()
        except OSError as exc:
            kept.append({'file': result.file, 'reason': f'error: {exc}'})
            continue
        deleted.append(result.file)
        freed += result.bytes
        cache.forget([str(path)])
        if root is not None:
            prune_empty_dirs(path.parent, root)
    if deleted:
        drop_library_listing_files(ctx, deleted)
        invalidate_library_paths_cache()
    still_there = [
        name
        for name in deleted
        if locate_library_file(
            name, ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs
        )
    ]
    logger.info(
        'doctor: removed {} slskd leftover(s), {} bytes; kept {}',
        len(deleted),
        freed,
        len(kept),
    )
    return {
        'deleted': len(deleted),
        'bytes': freed,
        'kept': kept,
        'verified_gone': not still_there,
    }


def _after_slskd_clean(job: dict[str, Any]) -> dict[str, Any]:
    found = _navidrome()
    if found is None:
        return {'enabled': False}
    client, cfg = found
    _step(job, 'navidrome_scan')
    complete = _rescan(client, cfg, full=False)
    try:
        songs = client.all_songs()
    except Exception:
        return {'enabled': True, 'scan_complete': complete}
    return {
        'enabled': True,
        'scan_complete': complete,
        'song_duplicates': navidrome_song_duplicates(songs, limit=0),
    }


# ---------------------------------------------------------------------------
# Playlists
# ---------------------------------------------------------------------------


class Merge(BaseModel):
    paths: list[str] = Field(min_length=2, max_length=20)


@router.post('/playlists/preview')
async def playlists_preview(payload: Merge) -> dict[str, Any]:
    """What merging these M3U files would do. Changes nothing."""

    group = await asyncio.to_thread(_group_for, payload.paths)
    return group.as_dict()


def _group_for(paths: list[str]) -> PlaylistGroup:
    infos = {i.path: i for i in _m3u_infos(_ctx())}
    members: list[M3UInfo] = []
    for raw in dict.fromkeys(norm(p) for p in paths):
        info = infos.get(raw)
        if info is None:
            raise HTTPException(
                404, detail={'code': 'm3u_not_found', 'path': raw}
            )
        if info.manual:
            raise HTTPException(
                400, detail={'code': 'm3u_manual', 'path': raw}
            )
        members.append(info)
    if len(members) < 2:
        raise HTTPException(400, detail={'code': 'need_two'})
    return PlaylistGroup('manual:' + members[0].path, members, 'manual')


@router.post('/playlists/merge')
async def playlists_merge(payload: Merge) -> dict[str, Any]:
    """Merge M3U files of one playlist, then tidy Navidrome to match."""

    group = await asyncio.to_thread(_group_for, payload.paths)
    if not group.safe():
        raise HTTPException(
            400,
            detail={
                'code': 'playlists_differ',
                'overlap': round(group.min_overlap(), 3),
            },
        )

    async def work(job: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(_merge, job, group)

    return _start('merge', work)


def _merge(job: dict[str, Any], group: PlaylistGroup) -> dict[str, Any]:
    ctx = _ctx()
    root = Path(ctx.download_dir)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = _data_dir() / 'doctor' / 'backups' / stamp
    _step(job, 'merging')
    done = merge_m3u_files(
        [root / m.path for m in group.members],
        root / group.keeper.path,
        download_dir=root,
        slskd_dir=ctx.slskd_dir,
        extra_dirs=ctx.extra_dirs,
        backup_dir=backup,
    )
    done['backup'] = str(backup)
    after = {i.path: i for i in _m3u_infos(ctx)}
    keeper = after.get(group.keeper.path)
    done['check'] = {
        'keeper_songs': len(keeper.entries) if keeper else 0,
        'keeper_cover': bool(keeper and keeper.cover),
        'others_gone': all(
            m.path not in after for m in group.members if m is not group.keeper
        ),
    }
    removed = {m.path for m in group.members if m is not group.keeper}
    done['navidrome'] = _navidrome_after_merge(job, group, removed)
    return done


def _navidrome_after_merge(
    job: dict[str, Any], group: PlaylistGroup, removed: set[str]
) -> dict[str, Any]:
    found = _navidrome()
    if found is None:
        return {'enabled': False}
    client, cfg = found
    infos = _m3u_infos(_ctx())
    playlists, _native = _navidrome_playlists(client)
    root = navidrome_root(playlists, [i.path for i in infos] + sorted(removed))
    deleted: list[str] = []
    for playlist in playlists:
        path = norm(playlist.get('path'))
        if root and path.startswith(root) and path[len(root) :] in removed:
            try:
                client.delete_playlist(str(playlist['id']), admin=True)
                deleted.append(str(playlist['id']))
            except Exception as exc:
                logger.info('doctor: could not delete {} err={}', path, exc)
    _step(job, 'navidrome_scan')
    complete = _rescan(client, cfg, full=False)
    playlists, _native = _navidrome_playlists(client)
    key = playlist_key(group.keeper.name)
    same = [
        p for p in playlists if playlist_key(str(p.get('name') or '')) == key
    ]
    return {
        'enabled': True,
        'deleted': deleted,
        'scan_complete': complete,
        'now': [
            {
                'id': str(p.get('id') or ''),
                'songs': int(p.get('songCount') or 0),
                'downtify': made_by_downtify(p),
                'm3u': norm(p.get('path'))[len(root) :] if root else '',
            }
            for p in same
        ],
    }


# ---------------------------------------------------------------------------
# Navidrome
# ---------------------------------------------------------------------------


class NavidromeRepair(BaseModel):
    delete: list[str] = Field(default_factory=list, max_length=500)
    enable_m3u_import: bool = False
    full_scan: bool = False


@router.post('/navidrome/repair')
async def navidrome_repair(payload: NavidromeRepair) -> dict[str, Any]:
    """Delete playlists the last health check flagged (duplicates and
    orphans only), optionally switch on M3U import, rescan, re-check."""

    flagged = _state.get('flagged') or set()
    unknown = [pid for pid in payload.delete if pid not in flagged]
    if unknown:
        raise HTTPException(
            400, detail={'code': 'not_flagged', 'ids': unknown[:20]}
        )

    async def work(job: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(_navidrome_repair, job, payload)

    return _start('navidrome', work)


def _navidrome_repair(job: dict[str, Any], payload: NavidromeRepair) -> dict:
    found = _navidrome()
    if found is None:
        raise HTTPException(409, detail={'code': 'navidrome_off'})
    client, cfg = found
    if payload.enable_m3u_import:
        settings = api.state.settings
        settings.setdefault('navidrome', {})['m3u_import'] = True
        if api.state.settings_path is not None:
            api._save_settings(api.state.settings_path, settings)
        cfg['m3u_import'] = True
    deleted: list[str] = []
    failed: list[dict[str, str]] = []
    for pid in payload.delete:
        _step(job, 'deleting', len(deleted), len(payload.delete))
        try:
            try:
                client.delete_playlist(pid)
            except Exception:
                client.delete_playlist(pid, admin=True)
            deleted.append(pid)
        except Exception as exc:
            failed.append({'id': pid, 'error': str(exc)[:200]})
    _step(job, 'navidrome_scan')
    complete = _rescan(client, cfg, full=payload.full_scan)
    playlists, _native = _navidrome_playlists(client)
    present = {str(p.get('id') or '') for p in playlists}
    infos = _m3u_infos(_ctx())
    root = navidrome_root(playlists, [i.path for i in infos])
    findings = navidrome_playlist_findings(playlists, infos, root=root)
    return {
        'deleted': deleted,
        'failed': failed,
        'still_listed': [pid for pid in deleted if pid in present],
        'scan_complete': complete,
        'm3u_import': bool(cfg.get('m3u_import')),
        'remaining': {
            'duplicates': len(findings['duplicates']),
            'orphans': len(findings['orphans']),
            'incomplete': len(findings['incomplete']),
        },
    }


# ---------------------------------------------------------------------------
# Duplicate songs: merge, keep both
# ---------------------------------------------------------------------------


class DuplicateMerge(BaseModel):
    keep: str = Field(min_length=1, max_length=4096)
    remove: list[str] = Field(min_length=1, max_length=MERGE_MAX)


class DuplicateFiles(BaseModel):
    files: list[str] = Field(min_length=2, max_length=MERGE_MAX + 1)


def _same_group(files: list[str]) -> None:
    """Only files the last health check grouped together are merged or
    kept apart: a stale page can't act on files it never saw grouped."""

    groups = _state.get('duplicates')
    if groups is None:
        raise HTTPException(409, detail={'code': 'dedupe_rescan'})
    found = {groups.get(norm(f)) for f in files}
    if None in found or len(found) != 1:
        raise HTTPException(409, detail={'code': 'dedupe_rescan'})


def _settle_review(gone: list[str], kept_apart: list[str]) -> None:
    """Take merged files (*gone*) and groups kept apart out of the last
    health check's list, so the page doesn't need a new scan."""

    last = (_last.get('health') or {}).get('result') or {}
    review = last.get('duplicates')
    if not review:
        return
    gone_set = {norm(f) for f in gone}
    apart = {norm(f) for f in kept_apart}
    groups = []
    for group in review['groups']:
        names = {norm(f['file']) for f in group['files']}
        if apart and names <= apart:
            review['kept_apart'] = review.get('kept_apart', 0) + 1
            continue
        group['files'] = [
            f for f in group['files'] if norm(f['file']) not in gone_set
        ]
        if len(group['files']) > 1:
            sizes = [int(f.get('bytes') or 0) for f in group['files']]
            group['bytes'] = sum(sizes) - max(sizes)
            groups.append(group)
    review['groups'] = groups
    review['totals'] = _duplicate_totals(groups)
    for name in gone_set:
        _state.get('duplicates', {}).pop(name, None)


@router.post('/duplicates/keep')
async def duplicates_keep(payload: DuplicateFiles) -> dict[str, Any]:
    """Keep both (or all): the files are different songs. The Doctor
    stops listing them until another look-alike turns up."""

    _same_group(payload.files)
    added = await asyncio.to_thread(_kept_apart().keep, payload.files)
    _settle_review([], payload.files)
    return {'pairs': added}


@router.post('/duplicates/keep/reset')
async def duplicates_keep_reset() -> dict[str, Any]:
    """List every group kept apart again (on the next health check)."""

    return {'forgotten': await asyncio.to_thread(_kept_apart().forget)}


@router.post('/duplicates/merge')
async def duplicates_merge(
    payload: DuplicateMerge, request: Request
) -> dict[str, Any]:
    """Keep *keep*, move every reference to the copies in *remove* onto
    it, then remove them - to the music trash when it is on."""

    user_id = admin_user(request)
    _same_group([payload.keep, *payload.remove])

    async def work(job: dict[str, Any]) -> dict[str, Any]:
        return await _merge_duplicates(job, payload, user_id)

    return _start('dedupe', work)


def _merge_stores(ctx) -> MergeStores:
    if api.state.audio_replacements is None:
        raise HTTPException(503, detail={'code': 'doctor_not_ready'})
    return MergeStores(
        ctx=ctx,
        replacements=api.state.audio_replacements,
        monitor_db=api.state.monitor_db,
        library_visibility=api.state.library_visibility,
        playlist_hidden=api.state.playlist_hidden,
        file_providers=api.state.file_providers,
        playlist_catalog=api.state.playlist_catalog,
    )


async def _merge_duplicates(
    job: dict[str, Any], payload: DuplicateMerge, user_id: int
) -> dict[str, Any]:
    ctx = _ctx()
    stores = _merge_stores(ctx)
    _step(job, 'dedupe_check')
    try:
        plan = await asyncio.to_thread(
            plan_merge, payload.keep, payload.remove, ctx
        )
    except MergeError as exc:
        raise HTTPException(
            409, detail={'code': exc.code, 'file': exc.file}
        ) from None
    extras = [name for name, _path in plan.extras]
    trash = api.state.library_trash
    batch = ''
    if trash is not None:
        # Checked before anything moves: a copy the trash can't take
        # (a folder it doesn't cover, a song playing) stops the merge.
        try:
            tracks = await asyncio.to_thread(
                trash_routes._selection, trash_routes.Selection(files=extras)
            )
            batch = (await asyncio.to_thread(trash.preview, user_id, tracks))[
                'confirmation'
            ]
        except TrashError as exc:
            raise HTTPException(
                409, detail={'code': 'dedupe_trash', 'reason': str(exc)}
            ) from None
    _step(job, 'dedupe_relink')
    try:
        await asyncio.to_thread(relink_duplicates, plan, stores)
    except MergeError as exc:
        raise HTTPException(
            409, detail={'code': exc.code, 'file': exc.file}
        ) from None
    _step(job, 'dedupe_remove')
    removed, failed = await _remove_copies(plan, ctx, user_id, batch)
    await asyncio.to_thread(finish_merge, plan, stores, removed)
    await asyncio.to_thread(_kept_apart().forget_files, removed)
    await asyncio.to_thread(_publish_library, ctx)
    if plan.playlists:
        await api._schedule_playlist_refresh_after_delete(set(plan.playlists))
    await api.announce_playlists_changed()
    leftovers = await asyncio.to_thread(leftover_references, plan, stores)
    _settle_review(removed, [])
    return {
        'kept': plan.keep,
        'removed': removed,
        'failed': failed,
        'playlists': sorted(plan.playlists),
        'trash': bool(batch),
        'leftovers': leftovers,
    }


async def _remove_copies(
    plan: MergePlan, ctx, user_id: int, batch: str
) -> tuple[list[str], list[dict[str, str]]]:
    extras = [name for name, _path in plan.extras]
    if batch:
        trash = api.state.library_trash
        try:
            await asyncio.to_thread(trash.confirm, user_id, batch)
        except TrashError as exc:
            return [], [{'file': f, 'error': str(exc)} for f in extras]
        await trash_routes.publish_changes()
        trash_routes.wake_worker()
        return extras, []
    removed, failed = [], []
    for name in extras:
        result = await asyncio.to_thread(
            delete_library_file,
            name,
            ctx,
            cover_cache=api.state.cover_cache,
            metadata_cache=api.state.metadata_cache,
            playlist_catalog=api.state.playlist_catalog,
            track_index=api.state.track_index,
            navidrome_index=api.state.navidrome_index,
        )
        if result.get('deleted'):
            removed.append(name)
        else:
            failed.append({
                'file': name,
                'error': str(result.get('error') or 'Delete failed'),
            })
    return removed, failed


def _publish_library(ctx) -> None:
    """What Replace audio does after publishing: hidden songs, listings
    and the mobile apps' library see the change."""

    if api.state.library_visibility is not None:
        api.state.library_visibility.invalidate()
    invalidate_library_paths_cache(drop_entries=True)
    if api.state.library_sync is not None:
        api.state.library_sync.refresh(list_library_entries(ctx))
