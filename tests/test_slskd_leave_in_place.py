"""slskd leave-in-place avoids copying into download_dir."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from downtify.library_paths import library_stored_path
from downtify.slskd_provider import _finalize_slskd_path


def test_finalize_slskd_path_leave_in_place_skips_copy(tmp_path):
    download_dir = tmp_path / 'downloads'
    slskd_dir = tmp_path / 'slskd'
    download_dir.mkdir()
    slskd_dir.mkdir()
    src = slskd_dir / 'Artist - Track.mp3'
    src.write_bytes(b'audio')

    with patch('downtify.slskd_provider.shutil.copy2') as copy_mock:
        result = _finalize_slskd_path(src, download_dir, leave_in_place=True)
        copy_mock.assert_not_called()

    assert result == src
    rel = library_stored_path(src, download_dir, slskd_dir)
    assert rel == 'slskd/Artist - Track.mp3'


def test_finalize_slskd_path_migrate_copies(tmp_path):
    download_dir = tmp_path / 'downloads'
    slskd_dir = tmp_path / 'slskd'
    download_dir.mkdir()
    slskd_dir.mkdir()
    src = slskd_dir / 'Artist - Track.mp3'
    src.write_bytes(b'audio')

    result = _finalize_slskd_path(src, download_dir, leave_in_place=False)
    assert result.parent == download_dir
    assert result.name == 'Artist - Track.mp3'
    assert result.is_file()
