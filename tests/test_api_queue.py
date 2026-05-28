"""Download queue maintenance endpoints."""

from __future__ import annotations

import downtify.api as api


def test_clear_completed_queue_removes_only_done_jobs():
    api.state.download_jobs.clear()
    try:
        done_id = api._register_job({'song_id': 'done-1', 'name': 'A'}, status='done')
        err_id = api._register_job({'song_id': 'err-1', 'name': 'B'}, status='error')
        q_id = api._register_job({'song_id': 'q-1', 'name': 'C'}, status='queued')

        result = api.clear_completed_queue()

        assert result['removed'] == 1
        assert done_id not in api.state.download_jobs
        assert err_id in api.state.download_jobs
        assert q_id in api.state.download_jobs
    finally:
        api.state.download_jobs.clear()
