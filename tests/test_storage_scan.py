"""``downtify/storage_scan.py``: what Downtify's folders hold besides
library songs - leftover temporary files and orphaned sidecars,
found by walking real (temporary) folders. Nothing is deleted."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from downtify.storage_scan import (
    LEFTOVER_MIN_AGE,
    Folder,
    is_temporary,
    plan_folders,
    scan_folders,
)


def _file(path: Path, size: int = 10, *, age: float = 0.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'x' * size)
    if age:
        moment = time.time() - age
        os.utime(path, (moment, moment))
    return path


@pytest.mark.parametrize(
    'name',
    [
        'Song.webm.part',
        'Song.f251.webm.part-Frag12',
        'Song.mp4.ytdl',
        'Song.temp.mp3',
        'tmpa1b2c3.tmp',
        'Song.downtify-upgrade.flac',
    ],
)
def test_temporary_files_are_told_apart(name):
    assert is_temporary(name)


@pytest.mark.parametrize(
    'name', ['Song.mp3', 'Partition.flac', 'Temperance.mp3', 'cover.jpg']
)
def test_songs_are_not_temporary(name):
    assert not is_temporary(name)


def test_only_old_temporary_files_are_leftovers(tmp_path):
    downloads = tmp_path / 'downloads'
    _file(downloads / 'Song.mp3', 100)
    _file(downloads / 'Old.webm.part', 40, age=LEFTOVER_MIN_AGE + 60)
    _file(downloads / 'Busy.webm.part', 30)

    found = scan_folders([Folder('downloads', downloads)])

    assert found['leftovers']['files'] == 1
    assert found['leftovers']['bytes'] == 40
    assert found['leftovers']['examples'][0]['file'] == 'Old.webm.part'
    kinds = found['folders'][0]['kinds']
    assert kinds['temporary'] == {'files': 2, 'bytes': 70}
    assert kinds['audio'] == {'files': 1, 'bytes': 100}


def test_sidecars_without_their_song_are_orphans(tmp_path):
    downloads = tmp_path / 'downloads'
    _file(downloads / 'Artist - Kept.mp3')
    _file(downloads / 'Artist - Kept.lrc', 5)
    _file(downloads / 'Artist - Gone.lrc', 7)
    _file(downloads / 'Album' / 'Song.flac')
    _file(downloads / 'Album' / 'cover.jpg')
    _file(downloads / 'Empty Album' / 'cover.jpg', 50)
    _file(downloads / 'Playlist' / 'Playlist.m3u8')
    _file(downloads / 'Playlist' / 'cover.jpg')

    found = scan_folders([Folder('downloads', downloads)])

    orphans = found['orphans']
    assert orphans['files'] == 2
    assert orphans['bytes'] == 57
    assert orphans['by_kind'] == {'cover': 1, 'lyrics': 1}
    assert {(o['file'], o['kind']) for o in orphans['examples']} == {
        ('Artist - Gone.lrc', 'lyrics'),
        ('Empty Album/cover.jpg', 'cover'),
    }


def test_lyrics_in_their_own_folder_belong_to_library_paths(tmp_path):
    downloads = tmp_path / 'downloads'
    lyrics = tmp_path / 'lyrics'
    _file(lyrics / 'Artist - Song.lrc')
    _file(lyrics / 'slskd' / 'u' / 'Track.lrc')
    _file(lyrics / 'Artist - Deleted.lrc', 9)

    found = scan_folders(
        [Folder('downloads', downloads)],
        lyrics=Folder('lyrics', lyrics),
        library_stems={'Artist - Song', 'slskd/u/Track'},
    )

    assert [o['file'] for o in found['orphans']['examples']] == [
        'Artist - Deleted.lrc'
    ]
    assert found['folders'][-1]['id'] == 'lyrics'
    assert found['folders'][-1]['kinds']['lyrics']['files'] == 3


def test_podcasts_and_saved_artist_art_are_kinds_of_their_own(tmp_path):
    downloads = tmp_path / 'downloads'
    _file(downloads / 'Podcasts' / 'Show' / 'Episode.mp3', 500)
    _file(downloads / '.metadata' / 'Artists' / 'A' / 'photo.jpg', 60)
    _file(downloads / 'Song.mp3', 100)
    _file(downloads / 'notes.txt', 1)

    folder = scan_folders([Folder('downloads', downloads)])['folders'][0]

    assert folder['files'] == 4
    assert folder['bytes'] == 661
    assert folder['kinds'] == {
        'audio': {'files': 1, 'bytes': 100},
        'podcasts': {'files': 1, 'bytes': 500},
        'metadata': {'files': 1, 'bytes': 60},
        'other': {'files': 1, 'bytes': 1},
    }


def test_a_folder_inside_downloads_is_walked_once(tmp_path):
    downloads = tmp_path / 'downloads'
    slskd = downloads / 'slskd'
    _file(downloads / 'Song.mp3', 10)
    _file(slskd / 'user' / 'Transfer.flac', 20)

    folders, lyrics = plan_folders(downloads, slskd, tmp_path / 'missing')
    found = scan_folders(folders, lyrics=lyrics)

    assert lyrics is None
    assert [(f['id'], f['bytes']) for f in found['folders']] == [
        ('downloads', 10),
        ('slskd', 20),
    ]


def test_the_lyrics_folder_is_skipped_when_it_holds_the_downloads(tmp_path):
    downloads = tmp_path / 'music' / 'downloads'
    downloads.mkdir(parents=True)

    folders, lyrics = plan_folders(downloads, None, tmp_path / 'music')

    assert lyrics is None
    assert [f.id for f in folders] == ['downloads']


def test_slskd_in_the_downloads_folder_itself_is_not_walked_twice(tmp_path):
    downloads = tmp_path / 'downloads'
    downloads.mkdir()

    folders, _lyrics = plan_folders(downloads, downloads, None)

    assert [f.id for f in folders] == ['downloads']


def test_a_missing_downloads_folder_walks_nothing(tmp_path):
    assert plan_folders(tmp_path / 'nope', None, None) == ([], None)
