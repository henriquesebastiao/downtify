"""slskd per-track timeout and provider fallback."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from downtify.downloader import Downloader
from downtify.slskd_provider import _wait_for_slskd_file


def test_wait_for_slskd_file_queued_timeout_without_transfer(monkeypatch):
    client = MagicMock()
    client.find_transfer.return_value = None

    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr('downtify.slskd_provider.time.sleep', fake_sleep)
    monkeypatch.setattr(
        'downtify.slskd_provider._find_on_disk_for_song', lambda *a, **k: None
    )

    settings = {
        'poll_interval_seconds': 1,
        'poll_max_attempts': 10,
        'queued_timeout_seconds': 2,
    }
    clock = {'t': 1000.0}

    def tick() -> float:
        clock['t'] += 1.0
        return clock['t']

    monkeypatch.setattr('downtify.slskd_provider.time.monotonic', tick)

    result = _wait_for_slskd_file(
        client,
        {'name': 'Song'},
        'peer',
        'file.mp3',
        settings,
        [Path('/slskd')],
        deadline=1600.0,
    )
    assert result is None
    assert client.find_transfer.called


def test_resolve_video_id_falls_back_after_slskd_timeout(
    monkeypatch, tmp_path
):
    d = Downloader(
        tmp_path,
        audio_format='mp3',
        audio_providers=['slskd', 'youtube-music'],
        slskd_settings={'enabled': True, 'queued_timeout_seconds': 1},
    )
    monkeypatch.setattr(
        'downtify.downloader.download_from_slskd', lambda *a, **k: None
    )
    monkeypatch.setattr(
        'downtify.downloader.find_match',
        lambda song: ('yt123', {'name': song.get('name')}),
    )

    video_id, match, provider, local = d._resolve_source(
        {'name': 'Track', 'artists': ['Artist']}, None
    )
    assert provider == 'youtube-music'
    assert video_id == 'yt123'
    assert local is None


@pytest.mark.parametrize(
    'state', ['Completed, Rejected', 'Completed, TimedOut']
)
def test_wait_for_slskd_file_stops_on_terminal_failed_state(
    monkeypatch, state
):
    client = MagicMock()
    client.find_transfer.return_value = {
        'state': state,
        'bytesTransferred': 0,
        'size': 1000,
    }
    monkeypatch.setattr('downtify.slskd_provider.time.sleep', lambda s: None)
    monkeypatch.setattr(
        'downtify.slskd_provider._find_on_disk_for_song', lambda *a, **k: None
    )
    # The clock never advances, so only the transfer state can end the wait
    monkeypatch.setattr(
        'downtify.slskd_provider.time.monotonic', lambda: 1000.0
    )

    result = _wait_for_slskd_file(
        client,
        {'name': 'Song'},
        'peer',
        'file.mp3',
        {'poll_interval_seconds': 1, 'poll_max_attempts': 10},
        [Path('/slskd')],
    )

    assert result is None
    assert client.find_transfer.call_count == 1
