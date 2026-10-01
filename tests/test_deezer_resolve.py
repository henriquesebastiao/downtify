"""Tests for resolving a pasted Deezer track/album/playlist/artist link
into downloadable song rows or release summaries (no network) - the
Deezer counterpart to downtify.spotify's/downtify.providers' URL
resolvers, wired into downtify.api's _deezer_details et al."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from downtify.deezer import (
    album_from_id,
    artist_page_from_id,
    artist_top_songs_from_id,
    parse_deezer_url,
    playlist_cover_url_from_id,
    playlist_info_and_tracks,
    track_from_id,
)


def _mock_response(payload):
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.json = lambda: payload
    return resp


def _sequenced_responses(*payloads):
    """``side_effect`` list for calls expected in this exact order - the
    only reliable way to tell two calls to the same paginated endpoint
    (a first page vs. its ``next`` URL) apart, since both contain the
    same path."""

    return [_mock_response(payload) for payload in payloads]


# ── parse_deezer_url ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ('url', 'expected'),
    [
        ('https://www.deezer.com/track/123', ('track', '123')),
        ('https://deezer.com/album/456', ('album', '456')),
        ('https://www.deezer.com/br/playlist/789', ('playlist', '789')),
        ('http://www.deezer.com/us/artist/321', ('artist', '321')),
        (
            'Check this out: https://www.deezer.com/track/999 nice song',
            ('track', '999'),
        ),
    ],
)
def test_parse_deezer_url_matches_every_kind(url, expected):
    assert parse_deezer_url(url) == expected


@pytest.mark.parametrize(
    'url',
    [
        '',
        'https://open.spotify.com/track/123',
        'https://music.youtube.com/watch?v=abc',
        'https://deezer.page.link/abc123',
        'not a url at all',
    ],
)
def test_parse_deezer_url_rejects_non_deezer_links(url):
    assert parse_deezer_url(url) is None


# ── track_from_id ────────────────────────────────────────────────────────


_TRACK_PAYLOAD = {
    'id': 111,
    'title': 'Track Title',
    'link': 'https://www.deezer.com/track/111',
    'duration': 200,
    'track_position': 3,
    'release_date': '2024-05-01',
    'explicit_lyrics': True,
    'preview': 'https://cdnt-preview.dzcdn.net/track111.mp3',
    'artist': {'name': 'Main Artist'},
    'contributors': [{'name': 'Main Artist'}, {'name': 'Featured Artist'}],
    'album': {
        'title': 'Track Album',
        'cover_xl': 'https://example.com/cover-xl.jpg',
    },
}


def test_track_from_id_maps_full_track():
    with patch(
        'downtify.deezer.httpx.get',
        return_value=_mock_response(_TRACK_PAYLOAD),
    ):
        song = track_from_id('111')
    assert song == {
        'song_id': 'deezer-111',
        'name': 'Track Title',
        'artists': ['Main Artist', 'Featured Artist'],
        'album_name': 'Track Album',
        'cover_url': 'https://example.com/cover-xl.jpg',
        'duration': 200,
        'url': 'https://www.deezer.com/track/111',
        'preview_url': 'https://cdnt-preview.dzcdn.net/track111.mp3',
        'explicit': True,
        'year': '2024',
        'release_date': '2024-05-01',
        'source': 'deezer',
        'track_number': 3,
    }


def test_track_from_id_raises_on_missing_track():
    payload = {'error': {'type': 'DataException', 'message': 'no data'}}
    with patch(
        'downtify.deezer.httpx.get', return_value=_mock_response(payload)
    ):
        with pytest.raises(ValueError, match='Deezer refused'):
            track_from_id('does-not-exist')


def test_track_from_id_raises_on_request_failure():
    with patch('downtify.deezer.httpx.get', side_effect=Exception('boom')):
        with pytest.raises(ValueError, match='Could not reach Deezer'):
            track_from_id('111')


# ── album_from_id ────────────────────────────────────────────────────────


def _album_track_row(track_id, title, artist='Album Artist'):
    return {
        'id': track_id,
        'title': title,
        'link': f'https://www.deezer.com/track/{track_id}',
        'duration': 180,
        'explicit_lyrics': False,
        'preview': f'https://cdnt-preview.dzcdn.net/{track_id}.mp3',
        'artist': {'name': artist},
        'album': {
            'title': 'The Album',
            'cover_xl': 'https://example.com/album-xl.jpg',
        },
    }


def test_album_from_id_numbers_tracks_in_order():
    payload = {
        'title': 'The Album',
        'release_date': '2023-01-15',
        'tracks': {
            'data': [
                _album_track_row(1, 'First'),
                _album_track_row(2, 'Second'),
            ]
        },
    }
    with patch(
        'downtify.deezer.httpx.get', return_value=_mock_response(payload)
    ):
        songs = album_from_id('999')
    assert [s['name'] for s in songs] == ['First', 'Second']
    assert [s['track_number'] for s in songs] == [1, 2]
    assert all(s['album_track_total'] == 2 for s in songs)
    # The album's own release date fills in every track's, since the
    # per-track rows embedded here don't carry one.
    assert all(s['year'] == '2023' for s in songs)


def test_album_from_id_follows_pagination():
    first = {
        'title': 'Big Album',
        'release_date': '',
        'tracks': {
            'data': [_album_track_row(1, 'Track 1')],
            'next': 'https://api.deezer.com/album/999/tracks?index=1',
        },
    }
    second_page = {'data': [_album_track_row(2, 'Track 2')]}
    with patch(
        'downtify.deezer.httpx.get',
        side_effect=_sequenced_responses(first, second_page),
    ):
        songs = album_from_id('999')
    assert [s['name'] for s in songs] == ['Track 1', 'Track 2']
    assert [s['track_number'] for s in songs] == [1, 2]
    assert all(s['album_track_total'] == 2 for s in songs)


def test_album_from_id_skips_rows_without_artist():
    payload = {
        'title': 'The Album',
        'release_date': '',
        'tracks': {'data': [{'id': 1, 'title': 'No Artist'}]},
    }
    with patch(
        'downtify.deezer.httpx.get', return_value=_mock_response(payload)
    ):
        assert album_from_id('999') == []


# ── playlist_info_and_tracks ─────────────────────────────────────────────


def _playlist_track_row(track_id, title):
    return {
        'id': track_id,
        'title': title,
        'link': f'https://www.deezer.com/track/{track_id}',
        'duration': 210,
        'explicit_lyrics': False,
        'preview': f'https://cdnt-preview.dzcdn.net/{track_id}.mp3',
        'artist': {'name': f'Artist {track_id}'},
        # A playlist row's album sub-object carries no release_date,
        # unlike track_from_id's/album_from_id's.
        'album': {
            'title': f'Album {track_id}',
            'cover_xl': f'https://example.com/{track_id}.jpg',
        },
    }


def test_playlist_info_and_tracks_does_not_number_tracks():
    payload = {
        'title': 'My Playlist',
        'tracks': {
            'data': [
                _playlist_track_row(1, 'Song One'),
                _playlist_track_row(2, 'Song Two'),
            ]
        },
    }
    with patch(
        'downtify.deezer.httpx.get', return_value=_mock_response(payload)
    ):
        name, songs = playlist_info_and_tracks('555')
    assert name == 'My Playlist'
    assert [s['name'] for s in songs] == ['Song One', 'Song Two']
    # A playlist position is never a track's real album track number.
    assert all('track_number' not in s for s in songs)
    assert all('album_track_total' not in s for s in songs)
    assert all(not s['year'] for s in songs)


def test_playlist_info_and_tracks_follows_pagination():
    first = {
        'title': 'Long Playlist',
        'tracks': {
            'data': [_playlist_track_row(1, 'Track 1')],
            'next': 'https://api.deezer.com/playlist/555/tracks?index=1',
        },
    }
    second_page = {'data': [_playlist_track_row(2, 'Track 2')]}
    with patch(
        'downtify.deezer.httpx.get',
        side_effect=_sequenced_responses(first, second_page),
    ):
        name, songs = playlist_info_and_tracks('555')
    assert name == 'Long Playlist'
    assert [s['name'] for s in songs] == ['Track 1', 'Track 2']


def test_playlist_cover_url_from_id_uses_picture_fields():
    payload = {
        'title': 'My Playlist',
        'picture_xl': 'https://example.com/playlist-xl.jpg',
        'picture_big': 'https://example.com/playlist-big.jpg',
    }
    with patch(
        'downtify.deezer.httpx.get', return_value=_mock_response(payload)
    ):
        assert (
            playlist_cover_url_from_id('555')
            == 'https://example.com/playlist-xl.jpg'
        )


# ── artist_page_from_id ──────────────────────────────────────────────────


def test_artist_page_from_id_fills_in_the_artist_name():
    artist_payload = {
        'name': 'The Artist',
        'picture_xl': 'https://example.com/artist-xl.jpg',
    }
    albums_payload = {
        'data': [
            {
                'id': 1,
                'title': 'Album One',
                'cover_xl': 'https://example.com/album1-xl.jpg',
                'release_date': '2022-06-01',
                'record_type': 'album',
                'link': 'https://www.deezer.com/album/1',
            },
            {
                'id': 2,
                'title': 'Single One',
                'cover_xl': 'https://example.com/album2-xl.jpg',
                'release_date': '2021-01-01',
                'record_type': 'single',
                'link': 'https://www.deezer.com/album/2',
            },
        ]
    }
    with patch(
        'downtify.deezer.httpx.get',
        side_effect=_sequenced_responses(artist_payload, albums_payload),
    ):
        name, cover, releases = artist_page_from_id('42')
    assert name == 'The Artist'
    assert cover == 'https://example.com/artist-xl.jpg'
    assert releases == [
        {
            'album_id': '1',
            'name': 'Album One',
            'artist': 'The Artist',
            'cover_url': 'https://example.com/album1-xl.jpg',
            'year': '2022',
            'explicit': False,
            'url': 'https://www.deezer.com/album/1',
            'source': 'deezer',
            'release_type': 'Album',
        },
        {
            'album_id': '2',
            'name': 'Single One',
            'artist': 'The Artist',
            'cover_url': 'https://example.com/album2-xl.jpg',
            'year': '2021',
            'explicit': False,
            'url': 'https://www.deezer.com/album/2',
            'source': 'deezer',
            'release_type': 'Single',
        },
    ]


def test_artist_page_from_id_follows_album_pagination():
    artist_payload = {'name': 'Prolific Artist'}
    first = {
        'data': [{'id': 1, 'title': 'A1', 'link': 'https://x/1'}],
        'next': 'https://api.deezer.com/artist/7/albums?index=100',
    }
    second_page = {'data': [{'id': 2, 'title': 'A2', 'link': 'https://x/2'}]}
    with patch(
        'downtify.deezer.httpx.get',
        side_effect=_sequenced_responses(artist_payload, first, second_page),
    ):
        _name, _cover, releases = artist_page_from_id('7')
    assert [r['name'] for r in releases] == ['A1', 'A2']


# ── artist_top_songs_from_id ─────────────────────────────────────────────


def test_artist_top_songs_from_id_maps_ranked_tracks():
    artist_payload = {
        'name': 'The Artist',
        'picture_xl': 'https://example.com/artist-xl.jpg',
    }
    top_payload = {
        'data': [
            _album_track_row(1, 'Hit Song', artist='The Artist'),
            _album_track_row(2, 'Another Hit', artist='The Artist'),
        ]
    }
    with patch(
        'downtify.deezer.httpx.get',
        side_effect=_sequenced_responses(artist_payload, top_payload),
    ):
        name, cover, songs = artist_top_songs_from_id('42')
    assert name == 'The Artist'
    assert cover == 'https://example.com/artist-xl.jpg'
    assert [s['name'] for s in songs] == ['Hit Song', 'Another Hit']
