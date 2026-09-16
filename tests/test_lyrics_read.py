"""Reading back the lyrics saved with a downloaded track (GET /lyrics)."""

from __future__ import annotations

from mutagen.id3 import ID3, USLT

from downtify.lyrics import read_track_lyrics

_LRC = '[00:12.00]The harbor lights are blinking out\n[00:15.50]One by one'


def _mp3_with_lyrics(path, text):
    tags = ID3()
    tags.add(USLT(encoding=3, lang='eng', desc='', text=text))
    tags.save(str(path), v2_version=4)


def test_reads_sidecar_and_embedded_lyrics(tmp_path):
    track = tmp_path / 'Kenji Aoki - Harbor Lights.mp3'
    _mp3_with_lyrics(track, 'The harbor lights are blinking out')
    track.with_suffix('.lrc').write_text(_LRC, encoding='utf-8')

    lyrics = read_track_lyrics(track)

    assert lyrics == {
        'synced': _LRC,
        'plain': 'The harbor lights are blinking out',
    }


def test_embedded_only(tmp_path):
    track = tmp_path / 'Song.mp3'
    _mp3_with_lyrics(track, 'Only plain words')

    assert read_track_lyrics(track) == {
        'synced': '',
        'plain': 'Only plain words',
    }


def test_track_without_lyrics(tmp_path):
    track = tmp_path / 'Song.opus'
    track.write_bytes(b'not really audio')

    assert read_track_lyrics(track) == {'synced': '', 'plain': ''}
