"""Tests for the disc-number tag written alongside track_number.

Downtify never handles multi-disc releases, so disc is always written as
"1" whenever a track_number is known. This isn't just cosmetic: cross-source
track matching (e.g. Music Assistant merging a track downloaded here with
the same recording added via another provider) compares disc_number
alongside track_number, and a missing disc tag is read back as 0 (not 1) by
most scanners/taggers - so a track downloaded here would otherwise never
match the same recording tagged by another source.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from downtify import downloader as dl


def _song(**overrides):
    song = {
        'name': 'Title',
        'artists': ['Artist'],
        'album_name': 'Album',
        'track_number': 3,
        'album_track_total': 10,
    }
    song.update(overrides)
    return song


def test_tag_mp3_writes_disc_one_when_track_number_known(tmp_path):
    path = tmp_path / 'song.mp3'
    path.touch()
    mock_audio = MagicMock(tags=MagicMock())
    with patch.object(dl, 'MP3', return_value=mock_audio):
        dl.embed_metadata(path, _song())
    disc_frames = [
        call.args[0]
        for call in mock_audio.tags.add.call_args_list
        if isinstance(call.args[0], dl.TPOS)
    ]
    assert len(disc_frames) == 1
    assert disc_frames[0].text == ['1']


def test_tag_mp3_skips_disc_when_track_number_unknown(tmp_path):
    path = tmp_path / 'song.mp3'
    path.touch()
    mock_audio = MagicMock(tags=MagicMock())
    with patch.object(dl, 'MP3', return_value=mock_audio):
        dl.embed_metadata(path, _song(track_number=None))
    disc_frames = [
        call.args[0]
        for call in mock_audio.tags.add.call_args_list
        if isinstance(call.args[0], dl.TPOS)
    ]
    assert disc_frames == []


def test_tag_mp4_writes_disc_one_when_track_number_known(tmp_path):
    path = tmp_path / 'song.m4a'
    path.touch()
    mock_audio = MagicMock()
    with patch.object(dl, 'MP4', return_value=mock_audio):
        dl.embed_metadata(path, _song())
    disk_values = [
        call.args[1]
        for call in mock_audio.__setitem__.call_args_list
        if call.args[0] == 'disk'
    ]
    assert disk_values == [[(1, 0)]]


def test_tag_flac_writes_disc_one_when_track_number_known(tmp_path):
    path = tmp_path / 'song.flac'
    path.touch()
    mock_audio = MagicMock()
    with patch.object(dl, 'FLAC', return_value=mock_audio):
        dl.embed_metadata(path, _song())
    disc_values = [
        call.args[1]
        for call in mock_audio.__setitem__.call_args_list
        if call.args[0] == 'discnumber'
    ]
    assert disc_values == ['1']


def test_tag_flac_skips_disc_when_track_number_unknown(tmp_path):
    path = tmp_path / 'song.flac'
    path.touch()
    mock_audio = MagicMock()
    with patch.object(dl, 'FLAC', return_value=mock_audio):
        dl.embed_metadata(path, _song(track_number=None))
    disc_values = [
        call.args[1]
        for call in mock_audio.__setitem__.call_args_list
        if call.args[0] == 'discnumber'
    ]
    assert disc_values == []


def test_tag_ogg_vorbis_writes_disc_one_when_track_number_known(tmp_path):
    path = tmp_path / 'song.ogg'
    path.touch()
    mock_audio = MagicMock()
    with patch.object(dl, 'OggVorbis', return_value=mock_audio):
        dl.embed_metadata(path, _song())
    disc_values = [
        call.args[1]
        for call in mock_audio.__setitem__.call_args_list
        if call.args[0] == 'DISCNUMBER'
    ]
    assert disc_values == ['1']


def test_tag_opus_writes_disc_one_when_track_number_known(tmp_path):
    path = tmp_path / 'song.opus'
    path.touch()
    mock_audio = MagicMock()
    with patch.object(dl, 'OggOpus', return_value=mock_audio):
        dl.embed_metadata(path, _song())
    disc_values = [
        call.args[1]
        for call in mock_audio.__setitem__.call_args_list
        if call.args[0] == 'DISCNUMBER'
    ]
    assert disc_values == ['1']
