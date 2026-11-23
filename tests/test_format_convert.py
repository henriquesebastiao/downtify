"""Converting a library file out of an unwanted format (the Doctor's
"Formats to convert") and the shared format list behind "Formats to
avoid" (downtify/format_convert.py)."""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from mutagen.mp3 import MP3

from downtify import format_convert as fc
from downtify.library_catalog import UPGRADE_STAGING_MARKER

needs_ffmpeg = pytest.mark.skipif(
    shutil.which('ffmpeg') is None, reason='needs ffmpeg'
)

# The smallest valid JPEG-ish payload mutagen will store as a picture.
COVER = b'\xff\xd8\xff\xe0' + b'cover' * 50


def _flac(path, seconds=3.0):
    subprocess.run(
        [
            shutil.which('ffmpeg'),
            '-nostdin',
            '-v',
            'error',
            '-y',
            '-f',
            'lavfi',
            '-i',
            f'sine=frequency=440:duration={seconds}',
            str(path),
        ],
        check=True,
    )
    audio = FLAC(str(path))
    audio['title'] = 'Thriller (2003 Edit)'
    audio['artist'] = ['Michael Jackson']
    audio['albumartist'] = 'Michael Jackson'
    audio['album'] = 'Number Ones'
    audio['tracknumber'] = '5'
    audio['date'] = '2003-11-18'
    audio['genre'] = 'Pop'
    audio['isrc'] = 'USSM19902991'
    audio['lyrics'] = "It's close to midnight"
    picture = Picture()
    picture.type = 3
    picture.mime = 'image/jpeg'
    picture.data = COVER
    audio.add_picture(picture)
    audio.save()
    os.utime(path, (1_600_000_000, 1_600_000_000))
    return path


@needs_ffmpeg
def test_a_flac_becomes_an_mp3_with_its_tags_cover_and_lyrics(tmp_path):
    source = _flac(tmp_path / 'Thriller.flac')

    target = fc.convert_to_mp3(source, 320)

    assert target == tmp_path / 'Thriller.mp3'
    assert source.is_file(), 'the original is left for the merge to remove'
    audio = MP3(str(target))
    assert abs(audio.info.length - 3.0) < 0.2
    assert round(audio.info.bitrate / 1000) == 320
    tags = ID3(str(target))
    assert str(tags['TIT2']) == 'Thriller (2003 Edit)'
    assert str(tags['TALB']) == 'Number Ones'
    assert str(tags['TPE2']) == 'Michael Jackson'
    assert 'Michael Jackson' in str(tags['TPE1'])
    assert str(tags['TRCK']).startswith('5')
    assert str(tags['TSRC']) == 'USSM19902991'
    assert tags.getall('APIC')[0].data == COVER
    assert "It's close to midnight" in str(tags.getall('USLT')[0].text)
    # Not "recently added" all of a sudden.
    assert int(target.stat().st_mtime) == 1_600_000_000
    # No staging file left behind.
    assert not list(tmp_path.glob(f'*{UPGRADE_STAGING_MARKER}*'))


@needs_ffmpeg
def test_the_downloads_bitrate_is_used(tmp_path):
    target = fc.convert_to_mp3(_flac(tmp_path / 'a.flac'), 256)

    assert round(MP3(str(target)).info.bitrate / 1000) == 256


@needs_ffmpeg
def test_an_existing_mp3_of_the_same_name_is_never_written_over(tmp_path):
    source = _flac(tmp_path / 'a.flac')
    (tmp_path / 'a.mp3').write_bytes(b'someone else')

    with pytest.raises(fc.ConvertError) as err:
        fc.convert_to_mp3(source, 320)

    assert err.value.code == 'exists'
    assert (tmp_path / 'a.mp3').read_bytes() == b'someone else'


@needs_ffmpeg
def test_a_file_ffmpeg_cannot_read_fails_cleanly(tmp_path):
    source = tmp_path / 'broken.flac'
    source.write_bytes(b'not audio at all')

    with pytest.raises(fc.ConvertError) as err:
        fc.convert_to_mp3(source, 320)

    assert err.value.code == 'failed'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['broken.flac']


def test_without_ffmpeg_nothing_happens(tmp_path, monkeypatch):
    monkeypatch.setattr(fc, 'ffmpeg', lambda: None)
    source = tmp_path / 'a.flac'
    source.write_bytes(b'x')

    with pytest.raises(fc.ConvertError) as err:
        fc.convert_to_mp3(source, 320)

    assert err.value.code == 'no_ffmpeg'


def test_formats_are_normalized_and_the_downloads_format_is_left_out():
    assert fc.normalize_formats(['FLAC', '.wav', 'aif', 'mp3', 'junk']) == [
        'flac',
        'wav',
        'aiff',
    ]
    assert fc.normalize_formats('flac,opus', exclude=['opus']) == ['flac']
    assert fc.normalize_formats(None) == []


def test_avoided_files_are_told_by_extension():
    assert fc.avoided('Song.FLAC', ['flac'])
    assert fc.avoided('Song.aif', ['aiff'])
    assert not fc.avoided('Song.mp3', ['flac'])
    assert not fc.avoided('Song', ['flac'])


def test_the_scan_lists_chosen_formats_biggest_first_with_an_estimate():
    rows = [
        {'file': 'a.flac', 'size': 30_000_000, 'duration': 200},
        {'file': 'b.mp3', 'size': 8_000_000, 'duration': 200},
        {'file': 'c.flac', 'size': 117_000_000, 'duration': 312},
        {'file': 'd.wav', 'size': 50_000_000, 'duration': 300},
    ]

    found = fc.files_in_formats(rows, ['flac'], 320)

    assert [r['file'] for r in found] == ['c.flac', 'a.flac']
    assert found[0]['estimated'] == 12_480_000
    assert found[0]['format'] == 'flac'


def test_the_bitrate_follows_the_downloads_quality():
    assert fc.target_bitrate({'bitrate': '256'}) == 256
    assert fc.target_bitrate({'bitrate': '320k'}) == 320
    assert fc.target_bitrate({'bitrate': 'auto'}) == 320
    assert fc.target_bitrate({}) == 320
