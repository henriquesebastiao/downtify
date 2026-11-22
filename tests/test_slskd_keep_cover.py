"""An slskd file keeps its own cover when it is larger than the fetched
one (the slskd ``keep_file_cover`` setting)."""

from __future__ import annotations

from pathlib import Path

import pytest
from mutagen.id3 import APIC, ID3, TIT2

from downtify import api, downloader
from downtify.downloader import _keep_larger_file_cover, _LookupResults
from tests.test_library_upgrade import _png


def _track(path: Path, cover_px: int = 0) -> Path:
    tags = ID3()
    tags.add(TIT2(encoding=3, text='Light'))
    if cover_px:
        tags.add(
            APIC(
                encoding=3,
                mime='image/png',
                type=3,
                desc='',
                data=_png(cover_px),
            )
        )
    tags.save(str(path), v2_version=4)
    return path


def _found(cover_px: int) -> _LookupResults:
    return _LookupResults(None, _png(cover_px) if cover_px else None, None)


@pytest.mark.parametrize(
    ('own', 'fetched', 'kept'),
    [
        (1400, 600, 1400),  # the file's own is larger: kept
        (300, 640, 640),  # smaller: the fetched one
        (600, 600, 600),  # the same: the fetched one
        (0, 600, 600),  # none in the file
        (1000, 0, 1000),  # nothing fetched
    ],
)
def test_the_larger_cover_wins(tmp_path, own, fetched, kept):
    track = _track(tmp_path / 'a.mp3', own)

    found = _keep_larger_file_cover(_found(fetched), track)

    assert found.cover_bytes == (_png(kept) if kept else None)


def test_an_unreadable_file_changes_nothing(tmp_path):
    broken = tmp_path / 'a.mp3'
    broken.write_bytes(b'not audio')
    found = _found(600)

    assert _keep_larger_file_cover(found, broken).cover_bytes == _png(600)


def test_the_setting_is_kept_off_by_default():
    assert api.DEFAULT_SETTINGS['slskd']['keep_file_cover'] is False
    assert api._effective_slskd_settings({})['keep_file_cover'] is False
    on = {'slskd': {'keep_file_cover': True}}
    assert api._effective_slskd_settings(on)['keep_file_cover'] is True
    fake = downloader.Downloader.__new__(downloader.Downloader)
    assert fake._normalize_slskd_settings({'keep_file_cover': True})[
        'keep_file_cover'
    ]
