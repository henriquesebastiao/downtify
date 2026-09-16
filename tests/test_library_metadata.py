"""Read embedded tags for library display."""

from __future__ import annotations

from mutagen.id3 import ID3, TALB, TIT2, TPE1

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
