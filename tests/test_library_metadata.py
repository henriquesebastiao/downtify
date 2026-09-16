"""Read embedded tags for library display."""

from __future__ import annotations

from mutagen.id3 import ID3, TALB, TDRC, TIT2, TPE1, TPE2, TRCK

from downtify.library_metadata import (
    library_entry_for_file,
    read_audio_metadata,
)


def test_read_audio_metadata_from_mp3_tags(tmp_path):
    track = tmp_path / 'peer' / '02-weval_-_the_most.mp3'
    track.parent.mkdir(parents=True, exist_ok=True)
    tags = ID3()
    tags.add(TIT2(encoding=3, text='The Most'))
    tags.add(TPE1(encoding=3, text='Weval'))
    tags.add(TALB(encoding=3, text='Half Age'))
    tags.save(str(track), v2_version=3)

    meta = read_audio_metadata(track)
    assert meta['title'] == 'The Most'
    assert meta['artist'] == 'Weval'
    assert meta['album'] == 'Half Age'

    entry = library_entry_for_file('slskd/peer/02-weval.mp3', track)
    assert entry['title'] == 'The Most'
    assert entry['artist'] == 'Weval'
    assert entry['album'] == 'Half Age'
    assert entry['has_cover'] is False


def test_library_entry_falls_back_to_filename(tmp_path):
    track = tmp_path / 'Artist - Song Title.mp3'
    track.write_bytes(b'\x00' * 128)

    entry = library_entry_for_file('Artist - Song Title.mp3', track)
    assert entry['title'] == 'Song Title'
    assert entry['artist'] == 'Artist'


def test_library_entry_includes_album_and_file_details(tmp_path):
    track = tmp_path / 'Artist - Song.mp3'
    track.write_bytes(b'\x00' * 256)
    tags = ID3()
    tags.add(TIT2(encoding=3, text='Song'))
    tags.add(TPE1(encoding=3, text='Artist feat. Guest'))
    tags.add(TPE2(encoding=3, text='Artist'))
    tags.add(TALB(encoding=3, text='Album'))
    tags.add(TRCK(encoding=3, text='3/12'))
    tags.add(TDRC(encoding=3, text='2024-05-01'))
    tags.save(str(track), v2_version=3)

    entry = library_entry_for_file('Artist - Song.mp3', track)

    # The Library groups albums by album artist and sorts by track
    # number / date added, so those come back alongside the display tags.
    assert entry['album_artist'] == 'Artist'
    assert entry['track_number'] == 3
    assert entry['year'] == '2024'
    assert entry['duration'] == 0.0  # not a decodable audio stream
    assert entry['size'] == track.stat().st_size
    assert entry['added'] == int(track.stat().st_mtime)


def test_library_entry_defaults_when_tags_are_missing(tmp_path):
    track = tmp_path / 'Untagged.mp3'
    track.write_bytes(b'\x00' * 64)

    entry = library_entry_for_file('Untagged.mp3', track)

    assert not entry['album_artist']
    assert entry['track_number'] == 0
    assert not entry['year']
    assert entry['duration'] == 0.0
