import shutil
import subprocess
from pathlib import Path

import pytest
from mutagen.id3 import APIC, ID3, TALB, TIT2, TPE1, TXXX

from downtify.library_metadata import read_audio_metadata
from downtify.metadata_edit import edit_file, validate_changes


def test_validation():
    assert validate_changes({'title': '  Name  ', 'track_number': None}) == {
        'title': 'Name',
        'track_number': None,
    }
    for changes in (
        {},
        {'unknown': 'x'},
        {'track_number': True},
        {'explicit': 'yes'},
    ):
        with pytest.raises(ValueError, match='.+'):
            validate_changes(changes)


def test_edit_preserves_other_tags_and_clears_artist_override(tmp_path: Path):
    path = tmp_path / 'track.mp3'
    if not shutil.which('ffmpeg'):
        pytest.skip('ffmpeg required')
    subprocess.run(
        [
            'ffmpeg',
            '-v',
            'error',
            '-f',
            'lavfi',
            '-i',
            'anullsrc=r=44100:cl=mono',
            '-t',
            '0.1',
            str(path),
        ],
        check=True,
    )
    tags = ID3(path)
    tags.add(TIT2(encoding=3, text=['Old']))
    tags.add(TPE1(encoding=3, text=['Old artist']))
    tags.add(TALB(encoding=3, text=['Album']))
    tags.add(TXXX(encoding=3, desc='ARTISTS', text=['Stale artist']))
    tags.add(APIC(encoding=3, mime='image/jpeg', type=3, data=b'image'))
    tags.save(path)
    edit_file(
        path,
        validate_changes({
            'title': 'New',
            'artist': 'New artist',
            'explicit': True,
        }),
    )
    metadata = read_audio_metadata(path)
    assert metadata['title'] == 'New'
    assert metadata['artist'] == 'New artist'
    assert metadata['artists'] == ['New artist']
    assert metadata['album'] == 'Album'
    assert metadata['explicit'] is True
    assert ID3(path).getall('APIC')[0].data == b'image'
