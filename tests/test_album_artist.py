"""Tests for the album-artist / compilation rule (``downtify/album_artist.py``).

Aliases only - no real artist names.
"""

from __future__ import annotations

import pytest

from downtify.album_artist import (
    PLAYLIST_ALBUM,
    VARIOUS_ARTISTS,
    album_artist_fields,
    as_playlist_album,
    filing_artist,
    is_act_of,
    is_various_artists,
)

# One artist whose own name holds a comma and an ampersand.
_COMMA_BAND = 'Coast, Hill & Vale'


@pytest.mark.parametrize(
    ('names', 'act', 'expected'),
    [
        (['Mica', 'Tomas'], 'Mica & Tomas', True),
        (['Tomas', 'Mica'], 'Mica & Tomas', True),
        (['Mica', 'Tomas'], 'mica e tomas', True),
        (['Mica', 'Tomas'], 'Mica, Tomas', True),
        (['Coast', 'Hill', 'Vale'], _COMMA_BAND, True),
        (['Mica', 'Tomas', 'Solenne'], 'Mica & Tomas', False),
        (['Mica', 'Tomas'], 'Mica', False),
        (['Mica', 'Tomas'], 'Mica & Tomasz', False),
        (['Mica'], 'Mica & Tomas', False),
        (['Mica', 'Tomas'], '', False),
        # "x" joins a collaboration, not an act.
        (['Mica', 'Tomas'], 'Mica x Tomas', False),
    ],
)
def test_is_act_of(names, act, expected):
    assert is_act_of(names, act) is expected


@pytest.mark.parametrize(
    'name',
    [
        'Various Artists',
        'various artists',
        '  Various   Artists ',
        'Various',
        'Vários intérpretes',
        'Varios artistas',
    ],
)
def test_is_various_artists_by_name(name):
    assert is_various_artists(name)


@pytest.mark.parametrize(
    'name', [_COMMA_BAND, 'Artists', 'Alias & Guest', '', None]
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
        # A playlist saved as one album keeps its tracks together.
        (
            {
                'artists': ['AliasNorth'],
                'album_artist': VARIOUS_ARTISTS,
                'compilation': True,
                PLAYLIST_ALBUM: True,
            },
            VARIOUS_ARTISTS,
        ),
    ],
)
def test_filing_artist(song, expected):
    assert filing_artist(song) == expected


def test_as_playlist_album_makes_one_compilation_in_playlist_order():
    # Issue #531: a playlist saved as an album, not spread over the
    # artists' own album folders.
    songs = [
        {'name': 'Third', 'artists': ['AliasC'], 'downtify_track_order': 7},
        {
            'name': 'First',
            'artists': ['AliasA'],
            'album_name': 'Their Album',
            'album_artist': 'AliasA',
            'track_number': 4,
            'year': '2001',
            'downtify_track_order': 0,
        },
        {'name': 'Second', 'artists': ['AliasB'], 'downtify_track_order': 3},
    ]
    as_playlist_album(songs, 'Road Trip', 'https://img/playlist.jpg')

    by_name = {song['name']: song for song in songs}
    assert [
        by_name[n]['track_number'] for n in ('First', 'Second', 'Third')
    ] == [
        1,
        2,
        3,
    ]
    for song in songs:
        assert song['album_name'] == 'Road Trip'
        assert song['album_artist'] == VARIOUS_ARTISTS
        assert song['compilation'] is True
        assert song[PLAYLIST_ALBUM] is True
        assert song['album_track_total'] == 3
        assert song['cover_url'] == 'https://img/playlist.jpg'
    # Each track keeps its own artist and year.
    assert by_name['First']['artists'] == ['AliasA']
    assert by_name['First']['year'] == '2001'


def test_as_playlist_album_keeps_track_covers_without_a_playlist_cover():
    songs = [{'name': 'One', 'cover_url': 'https://img/one.jpg'}]
    as_playlist_album(songs, 'Road Trip')
    assert songs[0]['cover_url'] == 'https://img/one.jpg'
    assert songs[0]['track_number'] == 1


def test_as_playlist_album_needs_a_name():
    songs = [{'name': 'One'}]
    as_playlist_album(songs, '  ')
    assert songs == [{'name': 'One'}]
