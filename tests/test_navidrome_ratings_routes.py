"""Navidrome star ratings: the job, its saved result, the schedule and the
settings (downtify/navidrome_ratings_routes.py).

``RatingRun`` is faked; the job, the state file and the schedule are real.
"""

from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import HTTPException

from downtify import api, library_only
from downtify import navidrome_ratings_routes as routes
from downtify.navidrome import SubsonicError
from downtify.navidrome_ratings import DeezerUnavailable

NOW = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
NAVIDROME = {
    'enabled': True,
    'url': 'http://navidrome.local',
    'username': 'u',
    'password': 'p',
}
RESULT = {
    'state': 'done',
    'preview': False,
    'total': 3,
    'rated': 2,
    'skipped': 1,
    'not_found': 0,
    'changes': [],
    'unmatched': [],
}


@pytest.fixture
def env(monkeypatch, tmp_path: Path) -> dict[str, Any]:
    settings = {
        'navidrome': dict(NAVIDROME),
        'navidrome_ratings': {
            'repeat': 'off',
            'skip_rated': False,
            'skip_starred': True,
            'grading': 'absolute',
        },
    }
    monkeypatch.setattr(api.state, 'settings', settings)
    monkeypatch.setattr(api.state, 'settings_path', tmp_path / 'settings.json')
    monkeypatch.setattr(routes, '_job', {})
    seen: dict[str, Any] = {'options': [], 'previews': [], 'resumed': []}

    class FakeRun:
        outcome: Any = dict(RESULT)
        #: Albums the fake run finishes before its outcome.
        finish: tuple[str, ...] = ()

        def __init__(self, client, options, *, preview=False, **kwargs):
            seen['options'].append(options)
            seen['previews'].append(preview)
            self._kwargs = kwargs

        def run(self):
            self._kwargs['progress'](1, 3, 'rating')
            seen['resumed'].append(set(self._kwargs.get('done_albums') or ()))
            for album_id in FakeRun.finish:
                self._kwargs['album_done'](album_id)
            if isinstance(FakeRun.outcome, Exception):
                raise FakeRun.outcome
            return dict(FakeRun.outcome, preview=seen['previews'][-1])

    FakeRun.outcome = dict(RESULT)
    FakeRun.finish = ()
    monkeypatch.setattr(routes, 'RatingRun', FakeRun)
    return {
        'settings': settings,
        'seen': seen,
        'run': FakeRun,
        'dir': tmp_path,
    }


async def _finished() -> dict[str, Any]:
    for _ in range(500):
        if routes._job.get('state') != 'running':
            return routes._public_job()
        await asyncio.sleep(0.01)
    raise AssertionError('the job never finished')


def _state_file(env) -> dict[str, Any]:
    return json.loads(
        (env['dir'] / 'navidrome_ratings.json').read_text(encoding='utf-8')
    )


def test_run_needs_a_configured_navidrome(env):
    env['settings']['navidrome']['password'] = ''

    async def go():
        with pytest.raises(HTTPException) as exc:
            await routes.ratings_run(routes.RunRequest())
        return exc.value

    error = asyncio.run(go())
    assert error.status_code == 400
    assert error.detail == {'code': 'navidrome_not_configured'}
    assert routes._job == {}


def test_second_run_is_refused_while_one_runs(env):
    async def go():
        routes._job.update(state='running')
        with pytest.raises(HTTPException) as exc:
            await routes.ratings_run(routes.RunRequest())
        return exc.value

    error = asyncio.run(go())
    assert error.status_code == 409
    assert error.detail == {'code': 'ratings_busy'}


def test_run_overrides_saved_options(env):
    async def go():
        job = await routes.ratings_run(routes.RunRequest(grading='artist'))
        assert job['state'] == 'running'
        assert job['trigger'] == 'manual'
        return await _finished()

    job = asyncio.run(go())
    assert env['seen']['options'] == [
        {
            'repeat': 'off',
            'skip_rated': False,
            'skip_starred': True,
            'grading': 'artist',
        }
    ]
    assert job['state'] == 'done'
    assert job['result']['rated'] == 2
    assert job['progress'] == {'done': 1, 'total': 3, 'step': 'rating'}
    assert 'cancel' not in job


def test_finished_run_is_saved_and_survives_a_restart(env):
    async def go():
        await routes.ratings_run(routes.RunRequest())
        first = await _finished()
        saved = _state_file(env)
        assert saved['last_run']['id'] == first['id']
        assert saved['last_rating_run'] == {
            'started_at': first['started_at'],
            'finished_at': first['finished_at'],
            'state': 'done',
        }
        # A preview replaces the last result but not the last real run.
        await routes.ratings_run(routes.RunRequest(preview=True))
        preview = await _finished()
        return first, preview

    first, preview = asyncio.run(go())
    saved = _state_file(env)
    assert saved['last_run']['id'] == preview['id']
    assert saved['last_run']['preview'] is True
    assert saved['last_rating_run']['started_at'] == first['started_at']
    assert not list(env['dir'].glob('*.tmp'))

    # "Restart": nothing in memory, the page still gets the last result.
    routes._job.clear()
    status = asyncio.run(routes.ratings_status())
    assert status['job'] is None
    assert status['last']['id'] == preview['id']


def test_unreadable_state_file_reads_as_empty(env):
    (env['dir'] / 'navidrome_ratings.json').write_text('{oops')
    status = asyncio.run(routes.ratings_status())
    assert status == {'job': None, 'last': None, 'next_run_at': None}


def _http_error(status: int) -> httpx.HTTPStatusError:
    url = 'http://navidrome.local/rest/getAlbum?u=u&t=SECRET&s=SALT'
    request = httpx.Request('GET', url)
    return httpx.HTTPStatusError(
        f'Server error {status} for url {url}',
        request=request,
        response=httpx.Response(status, request=request),
    )


@pytest.mark.parametrize(
    ('error', 'code', 'message'),
    [
        (SubsonicError('bad credentials'), 'navidrome_failed', None),
        (
            httpx.ConnectError('down http://x/?t=SECRET'),
            'navidrome_failed',
            'Could not reach Navidrome (ConnectError)',
        ),
        (_http_error(502), 'navidrome_failed', 'HTTP 502'),
        (
            ValueError('Invalid Subsonic response'),
            'navidrome_failed',
            routes.UNREADABLE_NAVIDROME,
        ),
        (
            json.JSONDecodeError('Expecting value', '<html>', 0),
            'navidrome_failed',
            routes.UNREADABLE_NAVIDROME,
        ),
        (RuntimeError('boom'), 'ratings_failed', None),
    ],
)
def test_navidrome_error_fails_the_job(env, error, code, message):
    env['run'].outcome = error

    async def go():
        await routes.ratings_run(routes.RunRequest())
        return await _finished()

    job = asyncio.run(go())
    assert job['state'] == 'failed'
    assert job['error'] == {'code': code, 'message': message or str(error)}
    for text in (
        job['error']['message'],
        json.dumps(asyncio.run(routes.ratings_status())),
        json.dumps(_state_file(env)),
    ):
        assert 'SECRET' not in text
        assert 'SALT' not in text
    assert job['finished_at']
    assert _state_file(env)['last_rating_run']['state'] == 'failed'


def test_shutdown_mid_run_marks_the_job_stopped(env):
    release = threading.Event()
    outcome = env['run'].outcome

    def slow(self):
        release.wait(5)
        return dict(outcome)

    env['run'].run = slow

    async def go():
        await routes.ratings_run(routes.RunRequest())
        task = next(
            t
            for t in asyncio.all_tasks()
            if t.get_name() == 'navidrome-ratings'
        )
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        release.set()
        return routes._public_job()

    job = asyncio.run(go())
    assert job['state'] == 'stopped'
    assert job['finished_at']
    assert _state_file(env)['last_run']['state'] == 'stopped'
    assert _state_file(env)['last_rating_run']['state'] == 'stopped'


def test_deezer_error_fails_the_job(env):
    env['run'].outcome = DeezerUnavailable('Deezer is not answering')

    async def go():
        await routes.ratings_run(routes.RunRequest())
        return await _finished()

    job = asyncio.run(go())
    assert job['state'] == 'failed'
    assert job['error'] == {
        'code': 'deezer_unreachable',
        'message': 'Deezer is not answering',
    }


def test_stopped_run_keeps_its_state(env):
    env['run'].outcome = dict(RESULT, state='stopped')

    async def go():
        await routes.ratings_run(routes.RunRequest())
        return await _finished()

    assert asyncio.run(go())['state'] == 'stopped'


def test_cancel_sets_the_flag_the_run_reads(env):
    async def go():
        routes._job.update(state='running', cancel=False)
        job = await routes.ratings_cancel()
        return job, routes._job['cancel']

    job, flag = asyncio.run(go())
    assert flag is True
    assert 'cancel' not in job


def test_schedule_starts_only_when_due(env):
    saved = env['settings']['navidrome_ratings']

    async def due() -> bool:
        started = routes.maybe_start_scheduled(NOW)
        if started:
            await _finished()
        return started

    def last(**kw):
        routes._job.clear()
        routes._write_state({'last_rating_run': kw})

    async def go():
        assert await due() is False  # repeat is off
        saved['repeat'] = 'weekly'
        assert await due() is True  # never run
        assert routes._job['trigger'] == 'schedule'
        last(
            started_at=(NOW - timedelta(days=2)).isoformat(),
            finished_at=(NOW - timedelta(days=2)).isoformat(),
            state='done',
        )
        assert await due() is False  # ran 2 days ago
        last(
            started_at=(NOW - timedelta(hours=7)).isoformat(),
            finished_at=(NOW - timedelta(hours=7)).isoformat(),
            state='failed',
        )
        assert await due() is True  # failed 7 hours ago: retry
        routes._write_state({})
        routes._job.update(state='running')
        assert await due() is False  # one is going

    asyncio.run(go())


def test_schedule_waits_for_a_configured_navidrome(env):
    env['settings']['navidrome_ratings']['repeat'] = 'daily'
    env['settings']['navidrome']['enabled'] = False

    async def go():
        assert routes.maybe_start_scheduled(NOW) is False
        env['settings']['navidrome']['enabled'] = True
        env['settings']['navidrome']['url'] = ''
        assert routes.maybe_start_scheduled(NOW) is False

    asyncio.run(go())
    assert routes._job == {}


def test_status_reports_the_next_run(env):
    env['settings']['navidrome_ratings']['repeat'] = 'weekly'
    started = (NOW - timedelta(days=2)).isoformat()
    routes._write_state({'last_rating_run': {'started_at': started}})
    status = asyncio.run(routes.ratings_status())
    assert status['next_run_at'] == (NOW + timedelta(days=5)).isoformat()
    env['settings']['navidrome']['enabled'] = False
    assert asyncio.run(routes.ratings_status())['next_run_at'] is None


def test_status_has_no_next_run_in_library_only_mode(env):
    env['settings']['navidrome_ratings']['repeat'] = 'weekly'
    assert asyncio.run(routes.ratings_status())['next_run_at'] is not None
    env['settings']['library_only'] = True
    assert asyncio.run(routes.ratings_status())['next_run_at'] is None


def test_run_merges_the_cleaned_saved_options(env):
    env['settings']['navidrome_ratings'] = 'junk'

    async def go():
        await routes.ratings_run(routes.RunRequest(skip_starred=True))
        return await _finished()

    assert asyncio.run(go())['state'] == 'done'
    assert env['seen']['options'] == [
        {
            'repeat': 'off',
            'skip_rated': True,
            'skip_starred': True,
            'grading': 'absolute',
        }
    ]


def test_library_only_blocks_run_and_schedule(env):
    env['settings']['library_only'] = True
    env['settings']['navidrome_ratings']['repeat'] = 'daily'

    async def go():
        with pytest.raises(HTTPException) as exc:
            await routes.ratings_run(routes.RunRequest())
        assert exc.value.status_code == 409
        assert routes.maybe_start_scheduled(NOW) is False

    asyncio.run(go())
    assert routes._job == {}
    assert library_only.remote_route('/api/navidrome/ratings/run', 'POST')


def test_settings_update_coerces_ratings_options(env, monkeypatch):
    class Request:
        @staticmethod
        async def json():
            return {'navidrome_ratings': {'repeat': 'hourly'}}

    monkeypatch.setattr(
        api.state, 'settings', dict(api.DEFAULT_SETTINGS), raising=True
    )
    monkeypatch.setattr(api.state, 'settings_path', None)
    monkeypatch.setattr(api.state, 'downloader', None)
    result = asyncio.run(api.update_settings_endpoint(Request(), client_id=''))
    assert result['navidrome_ratings']['repeat'] == 'off'
    assert result['navidrome_ratings']['grading'] == 'absolute'
    assert api.DEFAULT_SETTINGS['navidrome_ratings'] == {
        'repeat': 'off',
        'skip_rated': True,
        'skip_starred': False,
        'grading': 'absolute',
    }


def _run(env, **request) -> dict[str, Any]:
    async def go():
        await routes.ratings_run(routes.RunRequest(**request))
        return await _finished()

    return asyncio.run(go())


def test_an_interrupted_run_carries_on_where_it_stopped(env):
    env['run'].finish = ('al1', 'al2')
    env['run'].outcome = DeezerUnavailable('Deezer is not answering')
    assert _run(env)['state'] == 'failed'
    assert _state_file(env)['resume']['albums'] == ['al1', 'al2']

    # The next run skips them, and a finished run forgets them.
    env['run'].finish = ('al3',)
    env['run'].outcome = dict(RESULT)
    assert _run(env)['state'] == 'done'
    assert env['seen']['resumed'][-1] == {'al1', 'al2'}
    assert 'resume' not in _state_file(env)
    _run(env)
    assert env['seen']['resumed'][-1] == set()


def test_a_run_with_other_options_starts_afresh(env):
    env['run'].finish = ('al1',)
    env['run'].outcome = dict(RESULT, state='stopped')
    _run(env)
    env['settings']['navidrome_ratings']['grading'] = 'artist'
    env['run'].outcome = dict(RESULT)
    _run(env)
    assert env['seen']['resumed'][-1] == set()


def test_a_preview_neither_resumes_nor_forgets(env):
    env['run'].finish = ('al1',)
    env['run'].outcome = dict(RESULT, state='stopped')
    _run(env)
    env['run'].outcome = dict(RESULT)
    _run(env, preview=True)
    assert env['seen']['resumed'][-1] == set()
    assert _state_file(env)['resume']['albums'] == ['al1']
