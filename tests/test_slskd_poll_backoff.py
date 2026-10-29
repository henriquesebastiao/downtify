"""Bound idle polling work without changing transfer failure decisions."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock

import pytest

from downtify import slskd_provider as provider


@pytest.fixture(autouse=True)
def _isolated_cache(monkeypatch):
    provider._TRANSFERS_CACHE.clear()
    for name in (
        'DOWNTIFY_TRANSFERS_TTL',
        'DOWNTIFY_POLL_INTERVAL',
        'DOWNTIFY_POLL_IDLE_INTERVAL',
        'DOWNTIFY_POLL_DEEP_SCAN_EVERY',
    ):
        monkeypatch.delenv(name, raising=False)
    yield
    provider._TRANSFERS_CACHE.clear()


@pytest.fixture
def clock(monkeypatch):
    now = [0.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(provider.time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(provider.time, 'sleep', sleep)
    return now, sleeps


def client_with_transfers(
    monkeypatch, rows, *, url='http://slskd:5030', key='test'
):
    client = provider.SlskdClient({'base_url': url, 'api_key': key})
    request = Mock(return_value=rows)
    monkeypatch.setattr(client, '_request', request)
    return client, request


def test_two_pass_lookup_uses_one_snapshot(monkeypatch):
    row = {'filename': 'album/track.flac', 'state': 'Queued'}
    rows = [{'username': 'other', 'directories': [{'files': [row]}]}]
    client, request = client_with_transfers(monkeypatch, rows)
    try:
        assert client.find_transfer('requested', 'album/track.flac') is row
        assert client.find_transfer('requested', 'missing.flac') is None
        request.assert_called_once_with('GET', '/api/v0/transfers/downloads')
    finally:
        client.session.close()


def test_cache_is_shared_by_endpoint_and_expires(monkeypatch, clock):
    first, request = client_with_transfers(monkeypatch, [])
    second, other_request = client_with_transfers(monkeypatch, [])
    try:
        first.find_transfer('peer', 'missing')
        clock[0][0] = 2.9
        second.find_transfer('peer', 'missing')
        assert request.call_count == 1
        other_request.assert_not_called()
        clock[0][0] = 3.0
        second.find_transfer('peer', 'missing')
        assert other_request.call_count == 1
    finally:
        first.session.close()
        second.session.close()


@pytest.mark.parametrize(
    ('url', 'key'),
    [('http://other:5030', 'test'), ('http://slskd:5030', 'different')],
)
def test_cache_does_not_cross_server_or_credentials(monkeypatch, url, key):
    first, _ = client_with_transfers(monkeypatch, [])
    second, request = client_with_transfers(monkeypatch, [], url=url, key=key)
    try:
        first.list_download_transfers()
        second.list_download_transfers()
        assert request.call_count == 1
    finally:
        first.session.close()
        second.session.close()


def test_failed_request_is_not_cached(monkeypatch):
    client, request = client_with_transfers(monkeypatch, [])
    request.side_effect = [RuntimeError('offline'), []]
    try:
        assert client.list_download_transfers() == []
        assert client.list_download_transfers() == []
        assert request.call_count == 2
    finally:
        client.session.close()


def test_enqueue_invalidates_snapshot(monkeypatch):
    client, request = client_with_transfers(monkeypatch, [])
    try:
        client.list_download_transfers()
        assert client.enqueue_download({
            'username': 'peer',
            'filename': 'track.flac',
        })
        client.list_download_transfers()
        assert request.call_count == 3
    finally:
        client.session.close()


def wait(client, roots, **kwargs):
    return provider._wait_for_slskd_file(
        client,
        {'name': 'Track'},
        'peer',
        'album/track.flac',
        {'poll_max_attempts': 300, **kwargs.pop('settings', {})},
        roots,
        **kwargs,
    )


@pytest.mark.parametrize(
    ('transfer', 'interval'),
    [(None, 60), ({'state': 'InProgress', 'bytesTransferred': 1}, 5)],
)
def test_idle_and_active_intervals(monkeypatch, clock, transfer, interval):
    client = Mock()
    client.find_transfer.return_value = transfer
    monkeypatch.setattr(
        provider, '_find_on_disk_for_song', lambda *a, **k: None
    )
    wait(client, [], deadline=interval)
    assert clock[1] == [interval]


def test_recursive_scan_every_twelve_ticks(monkeypatch, clock, tmp_path):
    client = Mock()
    client.find_transfer.return_value = None
    monkeypatch.setenv('DOWNTIFY_POLL_IDLE_INTERVAL', '5')
    scans = []

    def rglob(_root, pattern):
        if pattern == 'track.flac':
            scans.append(clock[0][0])
        return iter(())

    monkeypatch.setattr(Path, 'rglob', rglob)
    wait(client, [tmp_path], deadline=125)
    assert scans == [0, 60, 120]


def test_idle_scan_catches_renamed_final_file_within_sixty_seconds(
    monkeypatch, clock, tmp_path
):
    client = Mock()
    client.find_transfer.return_value = None
    folder = tmp_path / 'unexpected'
    folder.mkdir()
    completed = folder / 'renamed track.flac'
    original_sleep = provider.time.sleep

    def complete_after_sleep(seconds):
        completed.write_bytes(b'a' * 60_000)
        original_sleep(seconds)

    monkeypatch.setattr(provider.time, 'sleep', complete_after_sleep)
    assert wait(client, [tmp_path], deadline=180) == completed
    assert clock[0][0] == 60


def test_predictable_file_is_probed_without_deep_scan(
    monkeypatch, clock, tmp_path
):
    client = Mock()
    client.find_transfer.return_value = None
    target = tmp_path / 'track.flac'
    monkeypatch.setenv('DOWNTIFY_POLL_IDLE_INTERVAL', '5')
    scans = []
    monkeypatch.setattr(
        Path, 'rglob', lambda *a: scans.append(clock[0][0]) or iter(())
    )
    original_sleep = provider.time.sleep

    def complete(seconds):
        target.write_bytes(b'a' * 60_000)
        original_sleep(seconds)

    monkeypatch.setattr(provider.time, 'sleep', complete)
    assert wait(client, [tmp_path]) == target
    assert set(scans) == {0}
    assert clock[0][0] == 5


def test_queued_timeout_is_not_extended_by_backoff(monkeypatch, clock):
    client = Mock()
    client.find_transfer.return_value = None
    assert wait(client, [], settings={'queued_timeout_seconds': 15}) is None
    assert clock[0][0] == 16


def test_stalled_transfer_timeout_still_applies(monkeypatch, clock):
    client = Mock()
    client.find_transfer.return_value = {
        'state': 'Queued',
        'bytesTransferred': 0,
    }
    assert wait(client, [], settings={'queued_timeout_seconds': 15}) is None
    assert clock[0][0] == 16


def test_backoff_preserves_attempt_time_budget(clock):
    client = Mock()
    client.find_transfer.return_value = None
    assert wait(client, [], settings={'poll_max_attempts': 2}) is None
    assert clock[0][0] == 10


def test_cancellation_during_idle_sleep(clock):
    client = Mock()
    client.find_transfer.return_value = None

    class Cancelled(Exception):
        pass

    def cancel():
        if clock[0][0] >= 2:
            raise Cancelled

    with pytest.raises(Cancelled):
        wait(client, [], cancel_check=cancel)
    assert clock[0][0] == 2


@pytest.mark.parametrize('value', ['invalid', '-20', '0', '99999'])
def test_poll_environment_is_bounded(monkeypatch, clock, value):
    monkeypatch.setenv('DOWNTIFY_POLL_IDLE_INTERVAL', value)
    client = Mock()
    client.find_transfer.return_value = None
    wait(client, [], deadline=60)
    assert all(0 < seconds <= 60 for seconds in clock[1])


def test_ttl_can_be_disabled(monkeypatch):
    monkeypatch.setenv('DOWNTIFY_TRANSFERS_TTL', '0')
    client, request = client_with_transfers(monkeypatch, [])
    try:
        client.find_transfer('peer', 'missing')
        client.find_transfer('peer', 'missing')
        assert request.call_count == 2
    finally:
        client.session.close()


def test_concurrent_lookups_share_one_request(monkeypatch):
    client, request = client_with_transfers(monkeypatch, [])
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(
                pool.map(
                    lambda _: client.find_transfer('peer', 'missing'),
                    range(16),
                )
            )
        assert results == [None] * 16
        assert request.call_count == 1
    finally:
        client.session.close()


def test_snapshot_cache_is_bounded(monkeypatch):
    client, request = client_with_transfers(monkeypatch, [])
    try:
        for i in range(40):
            client.base_url = f'http://slskd-{i}:5030'
            client.list_download_transfers()
        assert len(provider._TRANSFERS_CACHE) == 32
        assert request.call_count == 40
    finally:
        client.session.close()


def test_active_transfer_keeps_recursive_probe_each_tick(
    monkeypatch, clock, tmp_path
):
    client = Mock()
    client.find_transfer.return_value = {
        'state': 'InProgress',
        'bytesTransferred': 1,
    }
    scans = []

    def rglob(_root, pattern):
        if pattern == 'track.flac':
            scans.append(clock[0][0])
        return iter(())

    monkeypatch.setattr(Path, 'rglob', rglob)
    wait(client, [tmp_path], deadline=15)
    assert scans == [0, 5, 10]


def test_environment_overrides_active_interval(monkeypatch, clock):
    monkeypatch.setenv('DOWNTIFY_POLL_INTERVAL', '7')
    client = Mock()
    client.find_transfer.return_value = {
        'state': 'InProgress',
        'bytesTransferred': 1,
    }
    wait(client, [], deadline=7)
    assert clock[1] == [7]


def test_five_idle_minutes_use_five_snapshots_and_deep_probes(
    monkeypatch, clock, tmp_path
):
    client, request = client_with_transfers(monkeypatch, [])
    scans = []

    def rglob(_root, pattern):
        if pattern == 'track.flac':
            scans.append(clock[0][0])
        return iter(())

    monkeypatch.setattr(Path, 'rglob', rglob)
    try:
        wait(
            client,
            [tmp_path],
            settings={'queued_timeout_seconds': 3600},
            deadline=300,
        )
        assert request.call_count == 5
        assert scans == [0, 60, 120, 180, 240]
    finally:
        client.session.close()
