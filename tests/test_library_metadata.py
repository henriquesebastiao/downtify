"""Read embedded tags for library display."""

from __future__ import annotations

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

from downtify.library_metadata import (
    library_entry_for_file,
    read_audio_metadata,
)


def test_read_audio_metadata_from_mp3_tags(tmp_path):
    track = tmp_path / 'peer' / '02-weval_-_the_most.mp3'
    track.parent.mkdir(parents=True)
    audio = MP3()
    audio.save(str(track))
    tags = EasyID3(str(track))
    tags['title'] = 'The Most'
    tags['artist'] = 'Weval'
    tags['album'] = 'Half Age'
    tags.save()

    meta = read_audio_metadata(track)
    assert meta['title'] == 'The Most'
    assert meta['artist'] == 'Weval'
    assert meta['album'] == 'Half Age'

    entry = library_entry_for_file('slskd/peer/02-weval.mp3', track)
    assert entry['title'] == 'The Most'
    assert entry['artist'] == 'Weval'
    assert entry['album'] == 'Half Age'


def test_library_entry_falls_back_to_filename(tmp_path):
    track = tmp_path / 'Artist - Song Title.mp3'
    track.write_bytes(b'\x00' * 128)

    entry = library_entry_for_file('Artist - Song Title.mp3', track)
    assert entry['title'] == 'Song Title'
    assert entry['artist'] == 'Artist'
