"""Start-up steps are timed in the log (downtify/startup_timing.py)."""

from __future__ import annotations

import asyncio
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from loguru import logger

import main
from downtify import api
from downtify.download_queue import queue_pause
from downtify.startup_timing import StartupTimings


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def lines():
    captured: list[str] = []
    sink = logger.add(lambda m: captured.append(m.record['message']))
    yield captured
    logger.remove(sink)


def test_a_slow_step_gets_its_own_line(lines):
    clock = FakeClock()
    timings = StartupTimings(clock)

    with timings.step('quick'):
        clock.now += 0.2
    with timings.step('watch history'):
        clock.now += 42.0

    assert lines == ['Start-up: watch history took 42.0 s']
    assert timings.steps == [
        ('quick', pytest.approx(0.2)),
        ('watch history', pytest.approx(42.0)),
    ]


def test_a_failed_step_is_timed_and_still_raises(lines):
    clock = FakeClock()
    timings = StartupTimings(clock)

    def restore():
        with timings.step('queue restore'):
            clock.now += 0.3
            raise RuntimeError('boom')

    with pytest.raises(RuntimeError):
        restore()

    assert lines == ['Start-up: queue restore failed after 0.3 s']
    assert timings.steps == [('queue restore', pytest.approx(0.3))]


def test_the_summary_names_the_slowest_steps_first():
    clock = FakeClock()
    timings = StartupTimings(clock)
    for name, seconds in [
        ('a', 1.0),
        ('b', 30.0),
        ('tiny', 0.01),
        ('c', 2.0),
        ('d', 0.5),
        ('e', 4.0),
        ('f', 0.2),
    ]:
        began = clock()
        clock.now += seconds
        timings.since(name, began)

    assert timings.summary() == (
        'Start-up finished in 37.7 s; slowest: b 30.0 s, e 4.0 s, '
        'c 2.0 s, a 1.0 s, d 0.5 s'
    )


def test_a_quick_start_has_a_short_summary():
    clock = FakeClock()
    timings = StartupTimings(clock)
    with timings.step('tiny'):
        clock.now += 0.01

    assert timings.summary() == 'Start-up finished in 0.0 s'


def test_the_server_logs_its_start_up_summary(monkeypatch, tmp_path, lines):
    data = tmp_path / 'data'
    downloads = tmp_path / 'downloads'
    web = tmp_path / 'web'
    for folder in (data, downloads, web):
        folder.mkdir()
    (web / 'index.html').write_text('<html></html>')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    monkeypatch.setattr(main, 'DATABASE_DIR', data)
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', downloads)
    monkeypatch.setattr(api, 'state', type(api.state)())
    monkeypatch.setattr(api, 'release_thread_pools', Mock())
    monkeypatch.setattr(main, 'start_catalog_worker', lambda: None)
    monkeypatch.setattr(
        api.catalog_worker, 'stop_catalog_worker', lambda: None
    )
    monkeypatch.setattr(main, '_warm_library_listing', lambda: None)
    monkeypatch.setattr(main, 'discovery_enabled', lambda: False)
    monkeypatch.setattr(api, '_shutdown_done', False)
    monkeypatch.setenv('DOWNTIFY_DISABLE_AUTH', '1')

    async def idle(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(main, 'update_check_loop', idle)
    monkeypatch.setattr(main, 'monitor_loop', idle)
    monkeypatch.setattr(main, 'reconcile_loop', idle)
    try:
        with TestClient(main.build_app()) as client:
            assert client.get('/api/queue/state').status_code == 200
            ready = [
                line for line in lines if line.startswith('Start-up finished')
            ]
            assert len(ready) == 1
            # The history check still logs its own line, too.
            assert any(
                line.startswith('Watch history checked against the library')
                for line in lines
            )
    finally:
        queue_pause.resume()
