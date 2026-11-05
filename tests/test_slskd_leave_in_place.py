"""Completed slskd transfers stay at their source until import succeeds."""

from __future__ import annotations

from downtify.library_paths import library_stored_path
from downtify.slskd_provider import _finalize_slskd_path


def test_finalize_slskd_path_defers_copy_until_library_import(tmp_path):
    download_dir = tmp_path / 'downloads'
    slskd_dir = tmp_path / 'slskd'
    download_dir.mkdir()
    slskd_dir.mkdir()
    src = slskd_dir / 'Artist - Track.mp3'
    src.write_bytes(b'audio')

    result = _finalize_slskd_path(src)
    assert result == src
    assert src.is_file()
    assert not (download_dir / src.name).exists()
    assert library_stored_path(src, download_dir, slskd_dir) == (
        'slskd/Artist - Track.mp3'
    )
