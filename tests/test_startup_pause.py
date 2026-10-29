from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

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
    monkeypatch.setattr(
        api, 'DOWNLOAD_EXECUTOR', ThreadPoolExecutor(max_workers=1)
    )
    monkeypatch.setattr(api, '_shutdown_done', False)
    monkeypatch.setenv('DOWNTIFY_DISABLE_AUTH', '1')
    observed = []

    async def monitor_probe(*args, **kwargs):
        observed.append(queue_pause.paused)
        await asyncio.sleep(3600)

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
    finally:
        queue_pause.resume()
