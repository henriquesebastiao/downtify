"""Looking for a song already in the library reads the folder once, not
once per song.

Before downloading, ``Downloader.find_existing_download`` looks for the
song's file name anywhere in the library (another playlist's folder, an
older layout). It used to walk the whole downloads folder for every song
that was not at its exact path - twice per new song - so an artist
watch of 200 songs on a NAS read the library 400 times.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from downtify import library_name_index
from downtify.downloader import Downloader


@pytest.fixture
def clock(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(library_name_index, '_now', lambda: now[0])
    return now


@pytest.fixture
def walks(monkeypatch):
    count = [0]
    real_walk = os.walk

    def counting_walk(*args, **kwargs):
        count[0] += 1
        return real_walk(*args, **kwargs)

    monkeypatch.setattr(library_name_index.os, 'walk', counting_walk)
    return count


def _downloader(root: Path) -> Downloader:
    return Downloader(
        download_dir=root,
        output_template='{artists} - {title}.{output-ext}',
        organize_by_artist=False,
        organize_by_album=False,
    )


def _song(title: str) -> dict:
    return {'name': title, 'artists': ['Artist'], 'artist': 'Artist'}


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'x' * 10)
    return path


def test_finds_a_song_saved_in_another_folder(tmp_path):
    _touch(tmp_path / 'Other playlist' / 'Artist - One.mp3')

    found = _downloader(tmp_path).find_existing_download(_song('One'))

    assert found == 'Other playlist/Artist - One.mp3'


def test_many_lookups_read_the_folder_once(tmp_path, clock, walks):
    for i in range(20):
        _touch(tmp_path / f'Folder {i}' / f'Artist - Song {i}.mp3')
    dl = _downloader(tmp_path)

    for i in range(20):
        assert dl.find_existing_download(_song(f'Song {i}')) is not None
    for i in range(20):
        assert dl.find_existing_download(_song(f'Missing {i}')) is None

    assert walks[0] == 1


def test_a_song_downtify_just_saved_is_found_without_a_new_walk(
    tmp_path, clock, walks
):
    dl = _downloader(tmp_path)
    assert dl.find_existing_download(_song('New')) is None

    _touch(tmp_path / 'Playlist A' / 'Artist - New.mp3')
    dl._downloaded(_song('New'), 'Playlist A/Artist - New.mp3')

    assert dl.find_existing_download(_song('New')) == (
        'Playlist A/Artist - New.mp3'
    )
    assert walks[0] == 1


def test_a_deleted_file_is_not_offered(tmp_path, clock):
    path = _touch(tmp_path / 'Old' / 'Artist - Gone.mp3')
    dl = _downloader(tmp_path)
    assert dl.find_existing_download(_song('Gone')) is not None

    path.unlink()

    assert dl.find_existing_download(_song('Gone')) is None


def test_a_file_added_by_hand_shows_up_after_the_recheck_time(tmp_path, clock):
    dl = _downloader(tmp_path)
    assert dl.find_existing_download(_song('Manual')) is None

    _touch(tmp_path / 'Dropped in' / 'Artist - Manual.mp3')
    clock[0] += library_name_index.RECHECK_SECONDS + 1

    assert dl.find_existing_download(_song('Manual')) == (
        'Dropped in/Artist - Manual.mp3'
    )


def test_the_first_file_in_folder_order_wins_as_before(tmp_path, clock):
    _touch(tmp_path / 'b' / 'Artist - Twice.mp3')
    _touch(tmp_path / 'a' / 'deeper' / 'Artist - Twice.mp3')
    _touch(tmp_path / 'a' / 'Artist - Twice.mp3')
    dl = _downloader(tmp_path)

    assert dl.find_existing_download(_song('Twice')) == 'a/Artist - Twice.mp3'


def test_a_file_saved_later_keeps_folder_order(tmp_path, clock):
    _touch(tmp_path / 'b' / 'Artist - Order.mp3')
    dl = _downloader(tmp_path)
    assert dl.find_existing_download(_song('Order')) == 'b/Artist - Order.mp3'

    _touch(tmp_path / 'a' / 'Artist - Order.mp3')
    dl._downloaded(_song('Order'), 'a/Artist - Order.mp3')

    assert dl.find_existing_download(_song('Order')) == 'a/Artist - Order.mp3'


def test_hidden_folders_and_other_files_are_skipped(tmp_path, clock):
    _touch(tmp_path / '.downtify-trash' / 'Artist - Hidden.mp3')
    _touch(tmp_path / 'x' / 'Artist - Hidden.txt')
    dl = _downloader(tmp_path)

    assert dl.find_existing_download(_song('Hidden')) is None


def test_each_library_folder_has_its_own_listing(tmp_path, clock):
    first = tmp_path / 'one'
    second = tmp_path / 'two'
    _touch(first / 'x' / 'Artist - Here.mp3')
    second.mkdir()

    assert _downloader(first).find_existing_download(_song('Here'))
    assert _downloader(second).find_existing_download(_song('Here')) is None
