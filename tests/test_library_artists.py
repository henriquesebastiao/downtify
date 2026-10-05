"""Every credited artist of a library file: read from its ARTISTS tag (one
artist per value) when it has one, else split from its artist text - then
kept in the tag cache, served by ``/tracks`` and the mobile sync rows.

Aliases only - no real artist names.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from mutagen.id3 import ID3, TALB, TIT2, TPE1, TPE2, TXXX

from downtify.downloader import embed_metadata
from downtify.library_catalog import (
    LibraryContext,
    filter_library_entries,
    library_album_index,
    library_artist_index,
    library_home_summary,
    list_library_entries,
)
from downtify.library_metadata import (
    library_entry_for_file,
    read_audio_metadata,
    split_artists,
)
from downtify.library_metadata_cache import LibraryMetadataCache
from downtify.library_paths_cache import invalidate_library_paths_cache
from downtify.library_sync import grouping_keys, public_row, row_artists

needs_ffmpeg = pytest.mark.skipif(
    shutil.which('ffmpeg') is None, reason='no ffmpeg'
)

_CODECS = {
    'mp3': ['-c:a', 'libmp3lame', '-b:a', '64k'],
    'flac': ['-c:a', 'flac'],
    'm4a': ['-c:a', 'aac', '-b:a', '64k'],
    'opus': ['-c:a', 'libopus', '-b:a', '32k'],
    'ogg': ['-c:a', 'libvorbis', '-q:a', '1'],
}

# One artist whose own name holds a comma, and a guest.
_ARTISTS = ['Coast, Hill & Vale', 'AliasGuest']


def _audio(path: Path) -> Path:
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
            'sine=frequency=440:duration=0.2',
            *_CODECS[path.suffix.lstrip('.')],
            str(path),
        ],
        check=True,
    )
    return path


@needs_ffmpeg
@pytest.mark.parametrize('fmt', sorted(_CODECS))
def test_the_artists_tag_is_read_one_artist_per_value(tmp_path, fmt):
    path = _audio(tmp_path / f'song.{fmt}')
    embed_metadata(
        path,
        {'name': 'Harbor Lights', 'artists': list(_ARTISTS)},
        download_cover=False,
    )

    assert read_audio_metadata(path)['artists'] == _ARTISTS
    assert library_entry_for_file(f'song.{fmt}', path)['artists'] == _ARTISTS


def _mp3_without_artists_tag(path: Path, artist: str) -> Path:
    _audio(path)
    tags = ID3()
    tags.add(TIT2(encoding=3, text='Harbor Lights'))
    tags.add(TPE1(encoding=3, text=artist))
    tags.save(str(path), v2_version=4)
    return path


@needs_ffmpeg
@pytest.mark.parametrize(
    ('artist', 'expected'),
    [
        ('AliasNorth; AliasSouth', ['AliasNorth', 'AliasSouth']),
        ('AC/DC', ['AC/DC']),
        ('AliasNorth / AliasSouth', ['AliasNorth', 'AliasSouth']),
        # Without an ARTISTS tag a comma still splits (another tool's
        # "A, B"); a file Downtify wrote has the tag, so this is rare.
        ('AliasNorth, AliasSouth', ['AliasNorth', 'AliasSouth']),
    ],
)
def test_without_the_tag_the_artist_text_is_split(tmp_path, artist, expected):
    path = _mp3_without_artists_tag(tmp_path / 'song.mp3', artist)
    assert read_audio_metadata(path)['artists'] == expected


@needs_ffmpeg
def test_a_name_that_is_also_the_album_artist_is_not_split(tmp_path):
    # Another tool's file: no ARTISTS tag, a comma in a single name.
    path = _mp3_without_artists_tag(
        tmp_path / 'song.mp3', 'Coast, Hill & Vale'
    )
    tags = ID3(str(path))
    tags.add(TPE2(encoding=3, text='Coast, Hill & Vale'))
    tags.save(str(path), v2_version=4)

    assert read_audio_metadata(path)['artists'] == ['Coast, Hill & Vale']
    assert library_entry_for_file('song.mp3', path)['artists'] == [
        'Coast, Hill & Vale'
    ]


def test_split_artists_matches_the_web_app():
    assert split_artists('A; B, C') == ['A', 'B, C']
    assert split_artists('AC/DC') == ['AC/DC']
    assert split_artists('') == []
    assert split_artists('A, B', 'a, b') == ['A, B']
    assert row_artists({'artist': 'A, B', 'album_artist': 'A, B'}) == ['A, B']


def test_an_act_split_into_its_members_reads_as_its_album_artist():
    # An older Downtify wrote a YouTube Music duo credited as its members
    # this way: one act, named as its album is - no page per member.
    assert split_artists('Mica; Tomas', 'Mica, Tomas') == ['Mica, Tomas']
    assert split_artists('Mica; Tomas', 'Mica & Tomas') == ['Mica & Tomas']
    # A guest on a duo's album is still one.
    assert split_artists('Mica; Tomas; Solenne', 'Mica, Tomas') == [
        'Mica',
        'Tomas',
        'Solenne',
    ]
    # A real collaboration on one artist's album keeps both.
    assert split_artists('Mica; Tomas', 'Mica') == ['Mica', 'Tomas']


@needs_ffmpeg
def test_the_tag_cache_keeps_every_artist(tmp_path):
    path = _audio(tmp_path / 'song.mp3')
    embed_metadata(
        path,
        {'name': 'Harbor Lights', 'artists': list(_ARTISTS)},
        download_cover=False,
    )
    cache = LibraryMetadataCache(tmp_path / 'lib.db')

    first = cache.get_entries_batch([('song.mp3', path)])
    second = cache.get_entries_batch([('song.mp3', path)])

    assert first[0]['artists'] == _ARTISTS
    assert second == first


def test_sync_rows_use_the_artist_list():
    entry = {
        'file': 'a.mp3',
        'artist': 'Coast, Hill & Vale; AliasGuest',
        'artists': list(_ARTISTS),
        'album': 'Glass Harbor',
    }
    assert row_artists(entry) == _ARTISTS
    assert public_row(entry)['artists'] == _ARTISTS
    assert grouping_keys(entry)['album_artist'] == 'Coast, Hill & Vale'
    # A row without the list falls back to splitting its text.
    assert row_artists({'artist': 'A; B'}) == ['A', 'B']


# ── The Library's album and artist indexes ───────────────────────────────


def _tagged(
    path: Path,
    title: str,
    artists: list[str],
    *,
    album: str,
    album_artist: str,
) -> None:
    tags = ID3()
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text='; '.join(artists)))
    tags.add(TXXX(encoding=3, desc='ARTISTS', text=list(artists)))
    tags.add(TPE2(encoding=3, text=album_artist))
    tags.add(TALB(encoding=3, text=album))
    tags.save(str(path), v2_version=4)


def _library(tmp_path: Path) -> LibraryContext:
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    # A compilation with two tracks, and a regular album with a guest.
    _tagged(
        download_dir / 'a.mp3',
        'Marmalade',
        ['AliasNorth', 'AliasSouth'],
        album='Soundtrack',
        album_artist='Various Artists',
    )
    _tagged(
        download_dir / 'b.mp3',
        'Nature',
        ['AliasEast'],
        album='Soundtrack',
        album_artist='Various Artists',
    )
    _tagged(
        download_dir / 'c.mp3',
        'Harbor Lights',
        ['AliasNorth', 'AliasGuest'],
        album='Glass Harbor',
        album_artist='AliasNorth',
    )
    invalidate_library_paths_cache()
    cache = LibraryMetadataCache(tmp_path / 'library.db')
    return LibraryContext(download_dir=download_dir, metadata_cache=cache)


def test_a_compilation_stays_one_album(tmp_path):
    ctx = _library(tmp_path)
    albums = {
        (row['artist'], row['title']): row['track_count']
        for row in library_album_index(ctx)
    }
    assert albums == {
        ('Various Artists', 'Soundtrack'): 2,
        ('AliasNorth', 'Glass Harbor'): 1,
    }


def test_every_credited_artist_is_in_the_artist_index(tmp_path):
    ctx = _library(tmp_path)
    rows = {row['name']: row for row in library_artist_index(ctx)}
    assert sorted(rows) == [
        'AliasEast',
        'AliasGuest',
        'AliasNorth',
        'AliasSouth',
    ]
    assert rows['AliasNorth']['track_count'] == 2
    # Albums only count for their own album artist.
    assert rows['AliasNorth']['album_count'] == 1
    assert rows['AliasGuest']['album_count'] == 0
    assert library_home_summary(ctx)['artist_count'] == 4


def test_tracks_by_artist_include_guest_and_compilation_tracks(tmp_path):
    ctx = _library(tmp_path)
    entries = list_library_entries(ctx)

    def titles(artist):
        return sorted(
            row['title']
            for row in filter_library_entries(entries, artist=artist)
        )

    assert titles('AliasGuest') == ['Harbor Lights']
    assert titles('AliasNorth') == ['Harbor Lights', 'Marmalade']
    # An album's page asks for its album artist.
    assert titles('Various Artists') == ['Marmalade', 'Nature']
