"""Download queue maintenance endpoints."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request

from downtify import api
from downtify.auth import Principal


def _request(user_id: int = 0) -> Request:
    scope: dict[str, Any] = {'type': 'http', 'headers': []}
    if user_id:
        scope['state'] = {
            'principal': Principal(
                'device', 'client', '', user_id, f'user{user_id}', 'user'
            )
        }
    return Request(scope)


def test_clear_completed_queue_removes_only_done_jobs():
    api.state.download_jobs.clear()
    try:
        done_id = api._register_job(
            {'song_id': 'done-1', 'name': 'A'},
            status='done',
            user_id=5,
        )
        err_id = api._register_job(
            {'song_id': 'err-1', 'name': 'B'},
            status='error',
            user_id=5,
        )
        q_id = api._register_job(
            {'song_id': 'q-1', 'name': 'C'},
            status='queued',
            user_id=5,
        )

        result = api.clear_completed_queue(_request(5))

        assert result['removed'] == 1
        assert done_id not in api.state.download_jobs
        assert err_id in api.state.download_jobs
        assert q_id in api.state.download_jobs
    finally:
        api.state.download_jobs.clear()


def test_queue_rows_carry_waiting_positions():
    api.state.download_jobs.clear()
    try:
        api._register_job(
            {'song_id': 'q-1', 'name': 'A'},
            status='downloading',
            user_id=5,
        )
        api._register_job(
            {'song_id': 'q-2', 'name': 'B'}, status='queued', user_id=5
        )
        api._register_job(
            {'song_id': 'd-1', 'name': 'C'}, status='done', user_id=5
        )

        rows = {j['song']['song_id']: j for j in api.get_queue(_request(5))}

        assert rows['q-1']['position'] == 1
        assert rows['q-2']['position'] == 2
        assert rows['d-1']['position'] is None
        assert rows['q-1']['user_ids'] == [5]
    finally:
        api.state.download_jobs.clear()
