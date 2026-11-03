from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient

import main
from downtify import api
from downtify.download_queue import PendingDownloads, queue_pause


def test_pause_is_restored_before_the_first_startup_monitor(
    monkeypatch, tmp_path
):
    data = tmp_path / 'data'
    downloads = tmp_path / 'downloads'
    data.mkdir()
    downloads.mkdir()
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html></html>')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    PendingDownloads(data / 'downtify_library.db').set_paused(True)
    monkeypatch.setattr(main, 'DATABASE_DIR', data)
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', downloads)
    monkeypatch.setattr(api, 'state', type(api.state)())
    # Real release clears Python's process-wide thread-pool exit hooks.
    # Replacing DOWNLOAD_EXECUTOR alone leaves earlier tests' workers alive
    # without the hook that wakes and joins them at interpreter shutdown.
    release = Mock()
    monkeypatch.setattr(api, 'release_thread_pools', release)
    monkeypatch.setattr(main, 'start_catalog_worker', lambda: None)
    monkeypatch.setattr(
        api.catalog_worker, 'stop_catalog_worker', lambda: None
    )
    monkeypatch.setattr(main, '_warm_library_listing', lambda: None)
    monkeypatch.setattr(main, 'discovery_enabled', lambda: False)
    monkeypatch.setattr(api, '_shutdown_done', False)
    monkeypatch.setenv('DOWNTIFY_DISABLE_AUTH', '1')
    observed = []

    async def monitor_probe(*args, **kwargs):
        observed.append(queue_pause.paused)
        await asyncio.sleep(3600)

    async def idle_update_loop(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(main, 'update_check_loop', idle_update_loop)
    monkeypatch.setattr(main, 'monitor_loop', monitor_probe)
    try:
        with TestClient(main.build_app()) as client:
            response = client.get('/api/queue/state')
            assert response.status_code == 200
            assert response.json()['paused']
            assert response.json()['global_pause_supported']
            assert response.json()['can_control']
            assert observed
            assert all(observed)
        release.assert_called_once_with()
    finally:
        queue_pause.resume()


def test_startup_pause_allows_existing_download_workers_to_exit():
    # pytest's success summary is not enough: before the fix this child
    # returned 0 from pytest.main(), then hung joining an idle download
    # worker because the lifespan test had removed its exit hook.
    code = """
import pytest
from downtify import api

api.DOWNLOAD_EXECUTOR.submit(lambda: None).result(timeout=5)
raise SystemExit(pytest.main([
    'tests/test_startup_pause.py::test_pause_is_restored_before_the_first_startup_monitor',
    '-q',
]))
"""
    result = subprocess.run(
        [sys.executable, '-c', code],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
