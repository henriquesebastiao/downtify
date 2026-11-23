"""Navidrome star ratings API (admins): run now, preview, stop, and the
repeat schedule. The logic is in :mod:`downtify.navidrome_ratings`.

One job runs at a time, in a thread; the Settings page polls
``GET /api/navidrome/ratings`` for its progress. Every outcome is saved
to ``navidrome_ratings.json`` in the data directory, so the last result
and the time of the last real run survive a restart.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel

from . import api, library_only
from .admin_access import admin_user
from .navidrome import (
    NavidromeClient,
    SubsonicError,
    _effective_navidrome_settings,
)
from .navidrome_ratings import (
    DeezerUnavailable,
    RatingRun,
    effective_settings,
    next_run_at,
)

router = APIRouter(
    prefix='/api/navidrome/ratings', dependencies=[Depends(admin_user)]
)

STATE_FILE = 'navidrome_ratings.json'

UNREADABLE_NAVIDROME = 'Navidrome sent an answer Downtify could not read'

_lock = threading.Lock()
_job: dict[str, Any] = {}


class RunRequest(BaseModel):
    preview: bool = False
    skip_rated: Optional[bool] = None
    skip_starred: Optional[bool] = None
    grading: Optional[str] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _data_dir() -> Path:
    path = api.state.settings_path
    return Path(path).parent if path else Path('/data')


def _read_state() -> dict[str, Any]:
    try:
        data = json.loads(
            (_data_dir() / STATE_FILE).read_text(encoding='utf-8')
        )
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_state(data: dict[str, Any]) -> None:
    path = _data_dir() / STATE_FILE
    tmp = path.with_name(path.name + '.tmp')
    try:
        tmp.write_text(json.dumps(data), encoding='utf-8')
        os.replace(tmp, path)
    except OSError:
        logger.exception('ratings: could not save {}', path)
        with contextlib.suppress(OSError):
            tmp.unlink()


def _public_job() -> dict[str, Any]:
    return {
        k: v for k, v in _job.items() if k not in {'cancel', 'albums_done'}
    }


def _navidrome_ready() -> Optional[dict[str, Any]]:
    cfg = _effective_navidrome_settings(api.state.settings)
    if cfg['enabled'] and NavidromeClient(cfg).configured():
        return cfg
    return None


def _saved_options() -> dict[str, Any]:
    return effective_settings(api.state.settings.get('navidrome_ratings'))


def _finish(job: dict[str, Any]) -> None:
    job['finished_at'] = _now()
    result = job.get('result') or {}
    logger.info(
        'ratings: run {} (preview={}): rated {}, skipped {}, not found {}',
        job['state'],
        job['preview'],
        result.get('rated', 0),
        result.get('skipped', 0),
        result.get('not_found', 0),
    )
    state = _read_state()
    state['last_run'] = {
        k: v for k, v in job.items() if k not in {'cancel', 'albums_done'}
    }
    if not job['preview']:
        # An unfinished run leaves the albums it finished, so the next
        # one (scheduled again within hours after a failure) carries on
        # from there; a finished run starts the next one afresh.
        if job['state'] == 'done':
            state.pop('resume', None)
        else:
            state['resume'] = {
                'options': job.get('options'),
                'albums': sorted(job.get('albums_done') or ()),
            }
        state['last_rating_run'] = {
            'started_at': job['started_at'],
            'finished_at': job['finished_at'],
            'state': job['state'],
        }
    _write_state(state)


def start_run(
    *, preview: bool, options: dict[str, Any], trigger: str
) -> dict[str, Any]:
    """Start the one ratings job; raises 400/409 when it cannot."""

    global _job
    with _lock:
        if _job.get('state') == 'running':
            raise HTTPException(409, detail={'code': 'ratings_busy'})
        cfg = _navidrome_ready()
        if cfg is None:
            raise HTTPException(
                400, detail={'code': 'navidrome_not_configured'}
            )
        job: dict[str, Any] = {
            'id': secrets.token_urlsafe(8),
            'state': 'running',
            'trigger': trigger,
            'preview': preview,
            'started_at': _now(),
            'finished_at': None,
            'progress': {'done': 0, 'total': 0, 'step': ''},
            'result': None,
            'error': None,
            'cancel': False,
            'options': dict(options),
            'albums_done': set(),
        }
        resume = (_read_state().get('resume') or {}) if not preview else {}
        if resume.get('options') == dict(options):
            job['albums_done'] = set(resume.get('albums') or ())
            job['resumed_albums'] = len(job['albums_done'])

        logger.info(
            'ratings: run started (trigger={}, preview={}, options={})',
            trigger,
            preview,
            options,
        )

        def progress(done: int, total: int, step: str) -> None:
            job['progress'] = {'done': done, 'total': total, 'step': step}

        async def work() -> None:
            try:
                run = RatingRun(
                    NavidromeClient(cfg),
                    options,
                    preview=preview,
                    cancelled=lambda: bool(job['cancel']),
                    progress=progress,
                    done_albums=set(job['albums_done']),
                    album_done=job['albums_done'].add,
                )
                result = await asyncio.to_thread(run.run)
                job['state'] = result['state']
                job['result'] = result
            except asyncio.CancelledError:
                # Shutdown mid-run: record it, then let the cancel go on.
                job['state'] = 'stopped'
                _finish(job)
                raise
            except DeezerUnavailable as exc:
                _fail(job, 'deezer_unreachable', str(exc))
            except (SubsonicError, httpx.HTTPError) as exc:
                _fail(job, 'navidrome_failed', _navidrome_message(exc))
            except ValueError:
                # Navidrome's "Invalid Subsonic response", or a proxy's
                # login page that is not JSON.
                _fail(job, 'navidrome_failed', UNREADABLE_NAVIDROME)
            except Exception as exc:
                logger.exception('ratings: run failed')
                _fail(job, 'ratings_failed', str(exc))
            _finish(job)

        # Raises the library-only 409 itself (and closes the coroutine).
        api.spawn_task(work(), name='navidrome-ratings')
        _job = job
        return _public_job()


def _navidrome_message(exc: Exception) -> str:
    """A message for a Navidrome failure that never holds a URL (the
    request URL carries the Subsonic token and salt)."""

    if isinstance(exc, SubsonicError):
        return str(exc)[:160]
    if isinstance(exc, httpx.HTTPStatusError):
        return f'HTTP {exc.response.status_code}'
    return f'Could not reach Navidrome ({type(exc).__name__})'


def _fail(job: dict[str, Any], code: str, message: str) -> None:
    job['state'] = 'failed'
    job['error'] = {'code': code, 'message': message}
    logger.warning('ratings: run failed ({}): {}', code, message)


def maybe_start_scheduled(now: datetime) -> bool:
    """Start a scheduled run when one is due; whether it did."""

    options = _saved_options()
    if options['repeat'] == 'off':
        return False
    if _navidrome_ready() is None:
        return False
    if library_only.enabled(api.state.settings) or _job.get('state') == (
        'running'
    ):
        return False
    due = next_run_at(options, _read_state().get('last_rating_run'))
    if due is None or due > now:
        return False
    try:
        start_run(preview=False, options=options, trigger='schedule')
    except HTTPException as exc:
        logger.info('ratings: scheduled run not started: {}', exc.detail)
        return False
    return True


async def schedule_loop(
    *, first_delay: float = 600, interval: float = 3600
) -> None:
    """Check hourly whether a scheduled run is due."""

    await asyncio.sleep(first_delay)
    while True:
        try:
            maybe_start_scheduled(datetime.now(timezone.utc))
        except Exception:
            logger.exception('ratings: schedule check failed')
        await asyncio.sleep(interval)


@router.get('')
async def ratings_status() -> dict[str, Any]:
    """The running or last job, the saved last result and the next run."""

    state = _read_state()
    due = None
    if _navidrome_ready() is not None and not library_only.enabled(
        api.state.settings
    ):
        due = next_run_at(_saved_options(), state.get('last_rating_run'))
    return {
        'job': _public_job() or None,
        'last': state.get('last_run'),
        'next_run_at': due.isoformat() if due else None,
    }


@router.post('/run')
async def ratings_run(body: RunRequest) -> dict[str, Any]:
    given = {
        k: v
        for k, v in body.model_dump().items()
        if v is not None and k != 'preview'
    }
    options = effective_settings({**_saved_options(), **given})
    return start_run(preview=body.preview, options=options, trigger='manual')


@router.post('/cancel')
async def ratings_cancel() -> dict[str, Any]:
    if _job:
        _job['cancel'] = True
    return _public_job()
