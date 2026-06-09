"""Manual slskd override (failed-queue retry) tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from downtify.api import _merge_client_track_hints
from downtify.slskd_provider import (
    _download_slskd_direct,
    parse_slskd_override_text,
)


def test_parse_slskd_override_pipe_format():
    text = (
        'Manelo | @@wibgr\\EUROPA\\Ivi Adamou - San Ena Oniro (2012)\\'
        '06 - Ivi Adamou, Melisses - Krata Ta Matia Sou klista.mp3'
    )
    parsed = parse_slskd_override_text(text)
    assert parsed is not None
    assert parsed['username'] == 'Manelo'
    assert parsed['filename'].startswith('@@wibgr')
    assert parsed['filename'].endswith('.mp3')


def test_parse_slskd_override_space_format():
    parsed = parse_slskd_override_text('peer1 @@x\\Artist - Track.mp3')
    assert parsed == {
        'username': 'peer1',
        'filename': '@@x\\Artist - Track.mp3',
    }


def test_merge_applies_slskd_override_hints():
    base: dict[str, Any] = {
        'song_id': 'spotify:id',
        'url': 'https://open.spotify.com/track/x',
    }
    _merge_client_track_hints(
        base,
        {
            'slskd_override': True,
            'slskd_username': ' Manelo ',
            'slskd_filename': '@@wibgr\\track.mp3',
            'slskd_size': 6780000,
        },
    )
    assert base['slskd_override'] is True
    assert base['slskd_username'] == 'Manelo'
    assert base['slskd_filename'] == '@@wibgr\\track.mp3'
    assert base['slskd_size'] == 6780000


def test_download_slskd_direct_skips_search(monkeypatch, tmp_path: Path):
    slskd_dir = tmp_path / 'slskd'
    slskd_dir.mkdir()
    track = slskd_dir / '06 - Track.mp3'
    track.write_bytes(b'0' * 80_000)

    enqueued: list[dict[str, Any]] = []

    class FakeClient:
        base_url = 'http://slskd:5030'

        def configured(self) -> bool:
            return True

        def can_connect(self) -> bool:
            return True

        def enqueue_download(self, row: dict[str, Any]) -> bool:
            enqueued.append(dict(row))
            return True

        def find_transfer(self, username: str, filename: str) -> dict[str, Any]:
            return {
                'state': 'Completed',
                'bytesTransferred': 80_000,
                'size': 80_000,
                'percentComplete': 100,
            }

        def remote_download_directories(self) -> list[str]:
            return []

    monkeypatch.setattr(
        'downtify.slskd_provider.SlskdClient',
        lambda settings: FakeClient(),
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._find_on_disk_for_song',
        lambda *args, **kwargs: track,
    )
    monkeypatch.setattr(
        'downtify.slskd_provider.verify_downloaded_file_matches_spotify',
        lambda path, row: True,
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._slskd_semaphore',
        lambda settings: MagicMock(
            __enter__=lambda self: self, __exit__=lambda *a: None
        ),
    )

    settings = {
        'enabled': True,
        'source_dir': str(slskd_dir),
        'output_dir': str(tmp_path / 'downloads'),
        'leave_in_place': True,
        'download_timeout_seconds': 600,
        'queued_timeout_seconds': 180,
    }
    song = {
        'name': 'Krata Ta Matia Sou klista',
        'artists': ['Ivi Adamou', 'Melisses'],
        'slskd_override': True,
        'slskd_username': 'Manelo',
        'slskd_filename': '@@wibgr\\Album\\06 - Track.mp3',
        'slskd_size': 80_000,
    }

    result = _download_slskd_direct(song, settings)
    assert result == track
    assert len(enqueued) == 1
    assert enqueued[0]['username'] == 'Manelo'
    assert enqueued[0]['filename'].startswith('@@wibgr')
