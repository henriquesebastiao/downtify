"""ISRC codes written into downloads and matched by first
(downtify/isrc.py, the downloader's lookups, the library cache and
library_songs). Deezer is faked."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from downtify import api, isrc
from downtify import deezer as deezer_mod
from downtify import downloader as downloader_mod
from downtify.downloader import Downloader, embed_metadata
from downtify.library_metadata import read_audio_metadata
from downtify.library_metadata_cache import LibraryMetadataCache
from downtify.library_songs import LibrarySongs, same_recording

_needs_ffmpeg = pytest.mark.skipif(
    shutil.which('ffmpeg') is None, reason='no ffmpeg'
)

_CODECS = {
    'mp3': ['-c:a', 'libmp3lame', '-b:a', '64k'],
    'flac': ['-c:a', 'flac'],
    'm4a': ['-c:a', 'aac', '-b:a', '64k'],
    'opus': ['-c:a', 'libopus', '-b:a', '32k'],
    'ogg': ['-c:a', 'libvorbis', '-q:a', '1'],
}

SONG = {
    'name': 'Keep The Family Close',
    'artists': ['Drake'],
    'album_name': 'Views',
    'duration': 331,
}


def _audio(path: Path, seconds: float = 2) -> Path:
    subprocess.run(
        [
            'ffmpeg',
            '-nostdin',
            '-loglevel',
            'error',
            '-y',
            '-f',
            'lavfi',
            '-i',
            f'sine=frequency=440:duration={seconds}',
            *_CODECS[path.suffix.lstrip('.')],
            str(path),
        ],
        check=True,
    )
    return path


# ── The code and the tag ────────────────────────────────────────────────


def test_codes_are_normalized():
    assert isrc.normalize('US-CM5-16-00061') == 'USCM51600061'
    assert isrc.normalize(' uscm51600061 ') == 'USCM51600061'
    for bad in ('', None, 'USCM5160006', 'US!M51600061', '1234567890AB'):
        assert not isrc.normalize(bad)


@_needs_ffmpeg
@pytest.mark.parametrize('fmt', ['mp3', 'flac', 'm4a', 'ogg', 'opus'])
def test_the_tag_is_written_and_read_in_every_format(tmp_path, fmt):
    path = _audio(tmp_path / f'song.{fmt}')
    embed_metadata(path, SONG, download_cover=False)
    assert not isrc.read(path)

    assert isrc.write(path, 'us-cm5-16-00061')
    assert isrc.read(path) == 'USCM51600061'
    # Replaced, not added to; the other tags stay.
    assert isrc.write(path, 'GBUM71029604')
    assert isrc.read(path) == 'GBUM71029604'
    meta = read_audio_metadata(path)
    assert meta['title'] == 'Keep The Family Close'
    assert meta['isrc'] == 'GBUM71029604'


def test_nothing_is_written_without_a_code(tmp_path):
    path = tmp_path / 'song.mp3'
    path.write_bytes(b'')
    assert not isrc.write(path, 'nope')
    assert not isrc.write(tmp_path / 'gone.mp3', 'USCM51600061')
    assert not isrc.read(tmp_path / 'gone.mp3')


# ── Finding a song's code ───────────────────────────────────────────────


class _Deezer:
    """Deezer's search and tracks, from tables."""

    def __init__(self, monkeypatch, rows, codes, fail=False):
        self.asked: list[str] = []

        def get_json(url, **params):
            self.asked.append(url)
            if fail:
                raise ValueError('Could not reach Deezer')
            if url.endswith('/search'):
                return {'data': rows}
            return {'isrc': codes.get(url.rsplit('/', 1)[1], '')}

        monkeypatch.setattr(deezer_mod, '_get_json', get_json)


def _row(track_id, title, artist, duration):
    return {
        'id': track_id,
        'title': title,
        'artist': {'name': artist},
        'duration': duration,
    }


def test_a_search_finds_the_code_only_beyond_doubt(monkeypatch):
    _Deezer(
        monkeypatch,
        [
            _row(1, 'Keep The Family Close', 'Drake', 328),
            _row(2, 'Keep The Family Close (Remix)', 'Drake', 331),
            _row(3, 'Keep The Family Close', 'Cover Band', 331),
            _row(4, 'Keep The Family Close', 'Drake', 360),
            _row(5, 'Keep The Family Close', 'Drake', 331),
        ],
        {'1': 'USCM51600061', '5': 'USCM51600061'},
    )
    assert isrc.find_on_deezer(SONG) == 'USCM51600061'


def test_two_codes_for_one_song_write_none(monkeypatch):
    _Deezer(
        monkeypatch,
        [
            _row(1, 'Keep The Family Close', 'Drake', 331),
            _row(2, 'Keep The Family Close', 'Drake', 330),
        ],
        {'1': 'USCM51600061', '2': 'USCM51699999'},
    )
    assert not isrc.find_on_deezer(SONG)


def test_no_length_no_answer_or_no_match_write_none(monkeypatch):
    deezer = _Deezer(monkeypatch, [], {})
    assert not isrc.find_on_deezer({**SONG, 'duration': 0})
    assert deezer.asked == []
    assert not isrc.find_on_deezer(SONG)
    _Deezer(monkeypatch, [], {}, fail=True)
    assert not isrc.find_on_deezer(SONG)


def test_a_songs_own_code_comes_first(monkeypatch):
    deezer = _Deezer(monkeypatch, [], {'777': 'USCM51600061'})
    assert isrc.for_song({**SONG, 'isrc': 'GBUM71029604'}) == 'GBUM71029604'
    assert deezer.asked == []
    # A Deezer song: its track has it.
    assert isrc.for_song({**SONG, 'song_id': 'deezer-777'}) == 'USCM51600061'
    assert deezer.asked == ['https://api.deezer.com/track/777']


# ── Downloads ───────────────────────────────────────────────────────────


@_needs_ffmpeg
def test_a_download_gets_its_code(tmp_path, monkeypatch):
    path = _audio(tmp_path / 'Drake - Keep The Family Close.mp3')
    loader = Downloader(tmp_path)
    found = downloader_mod._LookupResults(
        None, None, None, isrc='USCM51600061'
    )
    loader._tag_file(path, tmp_path, SONG, found, save_album_cover=False)
    assert isrc.read(path) == 'USCM51600061'


def test_the_lookup_runs_only_when_asked(tmp_path, monkeypatch):
    asked = []
    monkeypatch.setattr(
        downloader_mod.isrc_mod,
        'lookup',
        lambda song: asked.append(song['name']) or 'USCM51600061',
    )
    loader = Downloader(tmp_path, download_cover_art=False)
    lookups = downloader_mod._MetadataLookups(loader, dict(SONG))
    assert lookups.collect().isrc == 'USCM51600061'
    lookups.cancel()

    loader.write_isrc = False
    lookups = downloader_mod._MetadataLookups(loader, dict(SONG))
    assert lookups.collect().isrc is None
    lookups.cancel()
    assert asked == ['Keep The Family Close']
    assert api.DEFAULT_SETTINGS['write_isrc'] is True


# ── Matching by it ──────────────────────────────────────────────────────


@_needs_ffmpeg
def test_the_library_cache_keeps_the_code(tmp_path):
    path = _audio(tmp_path / 'Drake - Keep The Family Close.mp3')
    embed_metadata(path, SONG, download_cover=False)
    isrc.write(path, 'USCM51600061')
    cache = LibraryMetadataCache(tmp_path / 'library.db')
    cache.refresh(path.name, path)
    assert cache.get_entry(path.name, path)['isrc'] == 'USCM51600061'


def test_a_song_is_found_by_its_code_first():
    songs = LibrarySongs([
        {
            'file': 'Lata/Kal Ho Na Ho.mp3',
            'artist': 'Sonu Nigam',
            'title': 'Kal Ho Na Ho',
            'duration': 321,
            'isrc': 'INS170300147',
        }
    ])
    song = {
        'artists': ['Sonu Nigam'],
        'name': 'Kal Ho Naa Ho',  # another spelling: no name match
        'duration': 322,
        'isrc': 'INS170300147',
    }
    assert songs.find(song) == 'Lata/Kal Ho Na Ho.mp3'
    assert songs.find({**song, 'isrc': ''}) is None
    # The code says the same recording; a length this far off says not.
    assert songs.find({**song, 'duration': 400}) is None


@_needs_ffmpeg
def test_same_recording_by_code(tmp_path):
    path = _audio(tmp_path / 'a.mp3', seconds=3)
    embed_metadata(
        path,
        {'name': 'Kal Ho Na Ho', 'artists': ['Sonu Nigam']},
        download_cover=False,
    )
    isrc.write(path, 'INS170300147')
    song = {
        'name': 'Kal Ho Naa Ho',
        'artists': ['Sonu Nigam'],
        'duration': 3,
        'isrc': 'INS170300147',
    }
    assert same_recording(path, song)
    assert not same_recording(path, {**song, 'isrc': 'INS170300148'})
