"""Library listing includes slskd tree; media paths resolve outside download_dir."""

from __future__ import annotations

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

from downtify.library_catalog import (
    LibraryContext,
    list_library_entries,
    list_library_paths,
    resolve_library_file,
)
from downtify.library_paths import library_stored_path


def test_list_library_includes_slskd_tree(tmp_path):
    download_dir = tmp_path / 'downloads'
    slskd_dir = tmp_path / 'slskd'
    download_dir.mkdir()
    slskd_dir.mkdir()
    (download_dir / 'YouTube - Song.mp3').write_bytes(b'y')
    slskd_track = slskd_dir / 'peer' / 'Artist - Slskd.mp3'
    slskd_track.parent.mkdir(parents=True)
    slskd_track.write_bytes(b's')

    ctx = LibraryContext(download_dir=download_dir, slskd_dir=slskd_dir)
    paths = list_library_paths(ctx)

    assert 'YouTube - Song.mp3' in paths
    rel = library_stored_path(slskd_track, download_dir, slskd_dir)
    assert rel == 'slskd/peer/Artist - Slskd.mp3'
    assert rel in paths


def test_resolve_library_file_allows_slskd_relative_path(tmp_path):
    download_dir = tmp_path / 'downloads'
    slskd_dir = tmp_path / 'slskd'
    download_dir.mkdir()
    track = slskd_dir / 'Artist - Track.mp3'
    slskd_dir.mkdir()
    track.write_bytes(b'x')

    ctx = LibraryContext(download_dir=download_dir, slskd_dir=slskd_dir)
    stored = library_stored_path(track, download_dir, slskd_dir)
    assert stored == 'slskd/Artist - Track.mp3'
    resolved = resolve_library_file(stored, ctx)
    assert resolved == track.resolve()


def test_list_library_entries_reads_embedded_tags(tmp_path):
    download_dir = tmp_path / 'downloads'
    slskd_dir = tmp_path / 'slskd'
    download_dir.mkdir()
    track = slskd_dir / 'peer' / 'scene-name.mp3'
    track.parent.mkdir(parents=True)
    audio = MP3()
    audio.save(str(track))
    tags = EasyID3(str(track))
    tags['title'] = 'Real Title'
    tags['artist'] = 'Real Artist'
    tags.save()

    ctx = LibraryContext(download_dir=download_dir, slskd_dir=slskd_dir)
    entries = list_library_entries(ctx)
    assert len(entries) == 1
    assert entries[0]['title'] == 'Real Title'
    assert entries[0]['artist'] == 'Real Artist'
    assert entries[0]['file'].startswith('slskd/')


def test_resolve_library_file_legacy_dotdot_slskd_path(tmp_path):
    download_dir = tmp_path / 'downloads'
    slskd_dir = tmp_path / 'slskd'
    download_dir.mkdir()
    track = slskd_dir / 'Legacy.mp3'
    slskd_dir.mkdir()
    track.write_bytes(b'x')

    ctx = LibraryContext(download_dir=download_dir, slskd_dir=slskd_dir)
    legacy = '../slskd/Legacy.mp3'
    resolved = resolve_library_file(legacy, ctx)
    assert resolved == track.resolve()
