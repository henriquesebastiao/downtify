"""Tests for how the downloader files and tags songs with several artists,
and various-artists compilations.

* ``{artist}`` is the first credited artist, ``{artists}`` all of them.
* The album-artist tag is the album artist the source declares, else the
  first artist - never "Various Artists" just because a track has guests.
* A compilation (``compilation: True``, only ever set from the source) is
  tagged as one, and filed by the folder settings and the template like
  any other song - with "Organize by artist", under its own first artist,
  never a "Various Artists" folder.

Aliases only - no real artist names.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from mutagen.flac import FLAC
from mutagen.id3 import ID3
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

from downtify.downloader import (
    Downloader,
    _album_artist_for_tags,
    embed_metadata,
)

_GUESTS = ['AliasNorth', 'AliasSouth', 'AliasEast']
_COMMA_BAND = 'Coast, Hill & Vale'


def _song(**overrides):
    song = {
        'name': 'Harbor Lights',
        'artists': list(_GUESTS),
        'album_name': 'Glass Harbor',
        'track_number': 2,
        'year': '2001',
    }
    song.update(overrides)
    return song


def _compilation(**overrides):
    return _song(album_artist='Various Artists', compilation=True, **overrides)


def _path(dl: Downloader, song, subdir=None) -> str:
    """The download-dir-relative path (no extension) ``song`` is saved to."""

    parts = dl._format_output_parts(song)
    folder = dl._effective_subdir(song, subdir)
    return '/'.join([folder, *parts] if folder else parts)


# ── {artist} / {artists} ──────────────────────────────────────────────────


def test_artist_token_is_the_first_artist_only(tmp_path):
    dl = Downloader(tmp_path, output_template='{artist} - {title}')
    assert _path(dl, _song()) == 'AliasNorth - Harbor Lights'


def test_artists_token_is_every_artist(tmp_path):
    dl = Downloader(tmp_path, output_template='{artists} - {title}')
    assert (
        _path(dl, _song())
        == 'AliasNorth, AliasSouth, AliasEast - Harbor Lights'
    )


def test_artist_token_keeps_a_name_with_a_comma_whole(tmp_path):
    dl = Downloader(tmp_path, output_template='{artist}/{title}')
    song = _song(artists=[_COMMA_BAND, 'AliasGuest'])
    assert _path(dl, song) == f'{_COMMA_BAND}/Harbor Lights'


# ── Folders ───────────────────────────────────────────────────────────────


def test_regular_album_with_guests_goes_to_the_first_artist(tmp_path):
    dl = Downloader(tmp_path, organize_by_artist=True, organize_by_album=True)
    assert _path(dl, _song()) == (
        'AliasNorth/Glass Harbor/AliasNorth, AliasSouth, AliasEast'
        ' - Harbor Lights'
    )


def test_regular_album_follows_the_declared_album_artist(tmp_path):
    dl = Downloader(tmp_path, organize_by_artist=True)
    song = _song(artists=['AliasGuest', 'AliasSolo'], album_artist='AliasSolo')
    assert _path(dl, song).startswith('AliasSolo/')


def test_compilation_track_goes_to_its_first_artist_folder(tmp_path):
    dl = Downloader(tmp_path, organize_by_artist=True, organize_by_album=True)
    assert _path(dl, _compilation(), subdir='My Playlist') == (
        'AliasNorth/Glass Harbor/AliasNorth, AliasSouth, AliasEast'
        ' - Harbor Lights'
    )


def test_various_artists_album_artist_alone_never_names_a_folder(tmp_path):
    dl = Downloader(tmp_path, organize_by_artist=True)
    song = _song(album_artist='Various Artists')
    assert _path(dl, song).startswith('AliasNorth/')


def test_compilation_keeps_the_playlist_folder_without_organize(tmp_path):
    dl = Downloader(tmp_path)
    assert _path(dl, _compilation(), subdir='My Playlist') == (
        'My Playlist/AliasNorth, AliasSouth, AliasEast - Harbor Lights'
    )


def test_compilation_keeps_the_template_folders(tmp_path):
    dl = Downloader(
        tmp_path, output_template='{artist}/{album}/{tracknumber} - {title}'
    )
    assert _path(dl, _compilation()) == (
        'AliasNorth/Glass Harbor/02 - Harbor Lights'
    )


def test_compilation_saves_no_cover_jpg_without_organize_by_album(tmp_path):
    dl = Downloader(tmp_path)
    dl._save_album_cover(tmp_path, _compilation(), cover_bytes=b'IMG')
    assert not (tmp_path / 'cover.jpg').exists()


# ── Album-artist tag ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ('song', 'expected'),
    [
        # Guests on a track never make it "Various Artists".
        (_song(), 'AliasNorth'),
        (_song(album_artist='AliasSolo'), 'AliasSolo'),
        (_song(artists=[_COMMA_BAND]), _COMMA_BAND),
        (_song(artists=['Alias & Guest']), 'Alias & Guest'),
        (_compilation(), 'Various Artists'),
        (_song(artists=[]), None),
    ],
)
def test_album_artist_for_tags(song, expected):
    assert _album_artist_for_tags(song) == expected


# ── Tags written to each format ───────────────────────────────────────────

_CODECS = {
    'mp3': ['-c:a', 'libmp3lame', '-b:a', '64k'],
    'flac': ['-c:a', 'flac'],
    'm4a': ['-c:a', 'aac', '-b:a', '64k'],
    'opus': ['-c:a', 'libopus', '-b:a', '32k'],
    'ogg': ['-c:a', 'libvorbis', '-q:a', '1'],
}

needs_ffmpeg = pytest.mark.skipif(
    shutil.which('ffmpeg') is None, reason='no ffmpeg'
)


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


def _read_tags(path: Path) -> dict:
    """``{artists, album_artist, compilation}`` as each format stores them."""

    suffix = path.suffix.lstrip('.')
    if suffix == 'mp3':
        tags = ID3(path)
        artists = tags.get('TXXX:ARTISTS')
        album_artist = tags.get('TPE2')
        return {
            'artists': list(artists.text) if artists else [],
            'album_artist': str(album_artist.text[0]) if album_artist else '',
            'compilation': str(tags['TCMP'].text[0]) == '1'
            if 'TCMP' in tags
            else False,
        }
    if suffix == 'm4a':
        tags = MP4(path).tags
        return {
            'artists': [
                bytes(v).decode()
                for v in tags.get('----:com.apple.iTunes:ARTISTS', [])
            ],
            'album_artist': (tags.get('aART') or [''])[0],
            'compilation': bool(tags.get('cpil')),
        }
    reader = {'flac': FLAC, 'ogg': OggVorbis, 'opus': OggOpus}[suffix]
    tags = reader(path)
    return {
        'artists': list(tags.get('artists') or []),
        'album_artist': (tags.get('albumartist') or [''])[0],
        'compilation': (tags.get('compilation') or [''])[0] == '1',
    }


@needs_ffmpeg
@pytest.mark.parametrize('fmt', sorted(_CODECS))
def test_compilation_tags_round_trip(tmp_path, fmt):
    path = _audio(tmp_path / f'song.{fmt}')
    song = _compilation(artists=[_COMMA_BAND, 'AliasGuest'])
    embed_metadata(path, song, download_cover=False)
    assert _read_tags(path) == {
        'artists': [_COMMA_BAND, 'AliasGuest'],
        'album_artist': 'Various Artists',
        'compilation': True,
    }


@needs_ffmpeg
@pytest.mark.parametrize('fmt', sorted(_CODECS))
def test_track_with_guests_is_not_tagged_as_a_compilation(tmp_path, fmt):
    path = _audio(tmp_path / f'song.{fmt}')
    embed_metadata(path, _song(), download_cover=False)
    assert _read_tags(path) == {
        'artists': list(_GUESTS),
        'album_artist': 'AliasNorth',
        'compilation': False,
    }
