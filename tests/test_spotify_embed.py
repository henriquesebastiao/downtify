"""Tests for Spotify embed parsing helpers (no network)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from downtify.spotify import (
    _artist_names,
    _artists_from_subtitle,
    _embed_row_track,
    _track_dict,
    album_tracks_from_id,
)

# Aliases only — no real artist / track titles
_AL1 = 'AliasNorth'
_AL2 = 'AliasSouth'
_AL3 = 'AliasEast'
_AL4 = 'AliasWest'
_AL5 = 'AliasSolo'
_AL6 = 'AliasGuest'
_SUB_TWO_NBSP = f'{_AL1},\xa0{_AL2}'
_SUB_FULLWIDTH = f'{_AL3}，{_AL4}'


def test_embed_row_track_merges_wrapper_subtitle_onto_nested_track():
    item = {
        'track': {
            'uri': 'spotify:track:abc123',
            'id': 'abc123',
            'title': 'Test track title',
        },
        'subtitle': _SUB_TWO_NBSP,
    }
    merged = _embed_row_track(item)
    assert merged is not None
    assert merged['subtitle'] == _SUB_TWO_NBSP
    assert merged['id'] == 'abc123'


def test_embed_row_track_does_not_override_inner_subtitle():
    inner_sub = 'InnerSubtitle'
    item = {
        'track': {
            'id': 'x',
            'uri': 'spotify:track:x',
            'subtitle': inner_sub,
        },
        'subtitle': 'WrapperSubtitle',
    }
    merged = _embed_row_track(item)
    assert merged['subtitle'] == inner_sub


def test_embed_row_track_flat_row_returns_same_dict():
    flat = {
        'id': 'z',
        'uri': 'spotify:track:z',
        'subtitle': f'{_AL1}, {_AL2}',
    }
    assert _embed_row_track(flat) is flat


@pytest.mark.parametrize(
    ('subtitle', 'expected'),
    [
        (f'{_AL1}, {_AL2}', [_AL1, _AL2]),
        (_SUB_TWO_NBSP, [_AL1, _AL2]),
        (_SUB_FULLWIDTH, [_AL3, _AL4]),
    ],
)
def test_artists_from_subtitle_splits(subtitle, expected):
    got = [d['name'] for d in _artists_from_subtitle(subtitle)]
    assert got == expected


def test_artist_names_prefers_structured_artists():
    entity = {
        'artists': [
            {'name': _AL1},
            {'name': _AL2},
        ],
        'subtitle': 'SubtitleIgnored',
    }
    assert _artist_names(entity) == [_AL1, _AL2]


def test_artist_names_string_entries_in_artists_list():
    entity = {'artists': [f'  {_AL5}  ', _AL6]}
    assert _artist_names(entity) == [_AL5, _AL6]


def test_artist_names_falls_back_to_subtitle():
    entity = {
        'uri': 'spotify:track:t',
        'title': 'T',
        'subtitle': f'{_AL3}, {_AL4}',
    }
    assert _artist_names(entity) == [_AL3, _AL4]


def test_track_dict_uses_subtitle_when_artists_empty():
    track = _embed_row_track(
        {
            'track': {
                'id': 'tid',
                'uri': 'spotify:track:tid',
                'title': 'TestSong',
            },
            'subtitle': f'{_AL1}, {_AL2}',
        }
    )
    td = _track_dict(track, track_id='tid', fallback_album='TestAlbum')
    assert td['artists'] == [_AL1, _AL2]
    assert td['artist'] == f'{_AL1}, {_AL2}'
    assert td['album_name'] == 'TestAlbum'
    assert td['name'] == 'TestSong'


def test_album_tracks_from_id_merges_row_subtitle():
    entity = {
        'name': 'TestAlbum',
        'trackList': [
            {
                'track': {
                    'id': 't1',
                    'uri': 'spotify:track:t1',
                    'title': 'TestTrackOne',
                },
                'subtitle': f'{_AL1}, {_AL2}',
            },
        ],
    }
    payload = {
        'props': {
            'pageProps': {
                'state': {'data': {'entity': entity}},
            },
        },
    }

    with patch('downtify.spotify._fetch_embed_json', return_value=payload):
        songs = album_tracks_from_id('dummyAlbumId')

    assert len(songs) == 1
    assert songs[0]['song_id'] == 't1'
    assert songs[0]['artists'] == [_AL1, _AL2]
    assert songs[0]['artist'] == f'{_AL1}, {_AL2}'
    assert songs[0]['album_name'] == 'TestAlbum'
