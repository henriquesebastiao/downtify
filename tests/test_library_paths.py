"""Tests for ``downtify.library_paths``."""

from __future__ import annotations

import os
from pathlib import Path

from downtify import library_paths as lp


def test_locate_library_file_external_slskd_mount(tmp_path, monkeypatch):
    download_dir = tmp_path / 'downloads'
    slskd_mount = tmp_path / 'slskd_vol'
    download_dir.mkdir()
    track = slskd_mount / 'Album' / 'song.mp3'
    track.parent.mkdir(parents=True)
    track.write_bytes(b'\x00')

    monkeypatch.setenv('DOWNTIFY_SLSKD_SOURCE_DIR', str(slskd_mount))
    found = lp.locate_library_file('slskd/Album/song.mp3', download_dir, None)
    assert found == track.resolve()


def test_locate_prefers_configured_slskd_dir_over_legacy_copy(tmp_path):
    download_dir = tmp_path / 'downloads'
    slskd_dir = tmp_path / 'slskd'
    download_dir.mkdir()
    slskd_dir.mkdir()
    legacy = download_dir / 'slskd' / 'song.mp3'
    external = slskd_dir / 'song.mp3'
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b'legacy')
    external.write_bytes(b'external')

    found = lp.locate_library_file('slskd/song.mp3', download_dir, slskd_dir)
    assert found == external.resolve()


def test_slskd_dir_from_downloader_falls_back_to_env_mount(tmp_path, monkeypatch):
    slskd_mount = tmp_path / 'slskd_vol'
    slskd_mount.mkdir()

    class _Downloader:
        slskd_settings = {
            'enabled': True,
            'source_dir': '',
            'download_dir': str(tmp_path / 'downloads'),
            'leave_in_place': True,
        }

    monkeypatch.setenv('DOWNTIFY_SLSKD_SOURCE_DIR', str(slskd_mount))
    assert lp.slskd_dir_from_downloader(_Downloader()) == slskd_mount
