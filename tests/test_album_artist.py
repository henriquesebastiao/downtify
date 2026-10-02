"""Tests for the album-artist / compilation rule (``downtify/album_artist.py``).

Aliases only - no real artist names.
"""

from __future__ import annotations

import pytest

from downtify.album_artist import (
    VARIOUS_ARTISTS,
    album_artist_fields,
    filing_artist,
    is_various_artists,
)

# One artist whose own name holds a comma and an ampersand.
_COMMA_BAND = 'Coast, Hill & Vale'


@pytest.mark.parametrize(
    'name',
    [
        'Various Artists',
        'various artists',
        '  Various   Artists ',
        'Vários intérpretes',
        'Varios artistas',
    ],
)
def test_is_various_artists_by_name(name):
    assert is_various_artists(name)


@pytest.mark.parametrize(
    'name', [_COMMA_BAND, 'Various', 'Artists', 'Alias & Guest', '', None]
)
def test_real_artists_are_not_various_artists(name):
    assert not is_various_artists(name)


def test_is_various_artists_by_id_whatever_the_name():
    # Deezer localizes the name; its id is what counts.
    assert is_various_artists('Localized Placeholder', artist_id='5080')
    assert is_various_artists('', artist_id='0LyfQWJT6nXafLPZqxe9Of')
    assert not is_various_artists('AliasSolo', artist_id='1309')


def test_album_artist_fields_for_a_compilation():
    assert album_artist_fields('Vários intérpretes') == {
        'album_artist': VARIOUS_ARTISTS,
        'compilation': True,
    }


def test_album_artist_fields_for_a_regular_album_keeps_commas():
    assert album_artist_fields(f' {_COMMA_BAND} ') == {
        'album_artist': _COMMA_BAND
    }


@pytest.mark.parametrize('name', ['', '   ', None])
def test_album_artist_fields_blank_means_no_fields(name):
    assert album_artist_fields(name) == {}


@pytest.mark.parametrize(
    ('song', 'expected'),
    [
        (
            {'artists': ['AliasGuest'], 'album_artist': 'AliasSolo'},
            'AliasSolo',
        ),
        ({'artists': [_COMMA_BAND, 'AliasGuest']}, _COMMA_BAND),
        # A compilation's tracks go to their own first artist.
        (
            {
                'artists': ['AliasNorth', 'AliasSouth'],
                'album_artist': VARIOUS_ARTISTS,
                'compilation': True,
            },
            'AliasNorth',
        ),
        (
            {'artists': ['AliasNorth'], 'album_artist': 'Varios artistas'},
            'AliasNorth',
        ),
        ({'artists': []}, ''),
    ],
)
def test_filing_artist(song, expected):
    assert filing_artist(song) == expected
