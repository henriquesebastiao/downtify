"""Tests for the Finder page's Deezer helpers - free-text search, an
artist's profile and discography, album track counts and one album's
details - and the endpoints wrapping them (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from downtify import api, deezer
from downtify.deezer import (
    album_track_counts,
    finder_album,
    finder_artist,
    finder_artist_albums,
    finder_search,
)

_PLACEHOLDER = (
    'https://cdn-images.dzcdn.net/images/artist/'
    'd41d8cd98f00b204e9800998ecf8427e/1000x1000.jpg'
)


def _mock_response(payload):
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.json = lambda: payload
    return resp


def _routes(table):
    """``httpx.get`` stand-in answering by exact URL, since the Finder
    fetches several endpoints at once (from worker threads), in no fixed
    order. A URL mapped to an exception raises it instead."""

    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append((url, params))
        answer = table[url]
        if isinstance(answer, Exception):
            raise answer
        return _mock_response(answer)

    fake_get.calls = calls
    return fake_get


@pytest.fixture(autouse=True)
def _fresh_track_counts():
    deezer._ALBUM_TRACK_COUNTS.clear()
    yield
    deezer._ALBUM_TRACK_COUNTS.clear()


def _track_row(track_id, title, artist_id=7, album_id=70):
    return {
        'id': track_id,
        'title': title,
        'link': f'https://www.deezer.com/track/{track_id}',
        'duration': 200,
        'explicit_lyrics': False,
        'preview': f'https://cdnt-preview.dzcdn.net/{track_id}.mp3',
        'artist': {'id': artist_id, 'name': 'The Artist'},
        'album': {
            'id': album_id,
            'title': 'The Album',
            'cover_xl': 'https://example.com/album-xl.jpg',
        },
    }


# ── finder_search ────────────────────────────────────────────────────────


_SEARCH_TABLE = {
    'https://api.deezer.com/search': {'data': [_track_row(1, 'Song')]},
    'https://api.deezer.com/search/album': {
        'data': [
            {
                'id': 70,
                'title': 'The Album',
                'cover_xl': 'https://example.com/album-xl.jpg',
                'nb_tracks': 12,
                'record_type': 'single',
                'link': 'https://www.deezer.com/album/70',
                'artist': {'id': 7, 'name': 'The Artist'},
            }
        ]
    },
    'https://api.deezer.com/search/artist': {
        'data': [
            {
                'id': 7,
                'name': 'The Artist',
                'picture_xl': 'https://example.com/artist-xl.jpg',
                'nb_fan': 1234,
                'nb_album': 9,
                'link': 'https://www.deezer.com/artist/7',
            },
            {'id': 8, 'name': 'Nobody', 'picture_xl': _PLACEHOLDER},
        ]
    },
}


def test_finder_search_maps_every_section():
    with patch('downtify.deezer.httpx.get', _routes(_SEARCH_TABLE)):
        result = finder_search('the artist')

    song = result['songs'][0]
    assert song['name'] == 'Song'
    assert song['source'] == 'deezer'
    assert song['deezer_artist_id'] == '7'
    assert song['deezer_album_id'] == '70'

    assert result['albums'] == [
        {
            'album_id': '70',
            'name': 'The Album',
            'artist': 'The Artist',
            'cover_url': 'https://example.com/album-xl.jpg',
            'year': '',
            'explicit': False,
            'url': 'https://www.deezer.com/album/70',
            'source': 'deezer',
            'release_type': 'Single',
            'artist_id': '7',
            'release_date': '',
            'track_count': 12,
            'fans': 0,
        }
    ]

    artist, nobody = result['artists']
    assert artist['artist_id'] == '7'
    assert artist['fans'] == 1234
    assert artist['album_count'] == 9
    assert artist['cover_url'] == 'https://example.com/artist-xl.jpg'
    # Deezer's grey placeholder face is not a photo.
    assert not nobody['cover_url']


def test_finder_search_remembers_album_track_counts():
    fake = _routes(_SEARCH_TABLE)
    with patch('downtify.deezer.httpx.get', fake):
        finder_search('the artist')
        # Known from the search row - no request needed.
        assert album_track_counts(['70']) == {'70': 12}
    assert len(fake.calls) == 3


def test_finder_search_blank_query_makes_no_request():
    with patch('downtify.deezer.httpx.get') as mock_get:
        assert finder_search('   ') == {
            'songs': [],
            'albums': [],
            'artists': [],
        }
    mock_get.assert_not_called()


def test_finder_search_keeps_songs_when_the_extras_fail():
    table = dict(_SEARCH_TABLE)
    table['https://api.deezer.com/search/album'] = Exception('boom')
    table['https://api.deezer.com/search/artist'] = {
        'error': {'code': 4, 'message': 'Quota limit exceeded'}
    }
    with patch('downtify.deezer.httpx.get', _routes(table)):
        result = finder_search('the artist')
    assert [s['name'] for s in result['songs']] == ['Song']
    assert result['albums'] == []
    assert result['artists'] == []


def test_finder_search_raises_when_the_song_search_fails():
    table = dict(_SEARCH_TABLE)
    table['https://api.deezer.com/search'] = Exception('boom')
    with patch('downtify.deezer.httpx.get', _routes(table)):
        with pytest.raises(ValueError, match='Could not reach Deezer'):
            finder_search('the artist')


# ── finder_artist ────────────────────────────────────────────────────────


_ARTIST_TABLE = {
    'https://api.deezer.com/artist/7': {
        'id': 7,
        'name': 'The Artist',
        'picture_xl': 'https://example.com/artist-xl.jpg',
        'nb_fan': 5000,
        'nb_album': 12,
        'link': 'https://www.deezer.com/artist/7',
    },
    'https://api.deezer.com/artist/7/related': {
        'data': [
            {
                'id': 8,
                'name': 'Friend',
                'picture_xl': 'https://example.com/friend-xl.jpg',
                'nb_fan': 10,
                'nb_album': 2,
            }
        ]
    },
    'https://api.deezer.com/artist/7/top': {
        'data': [_track_row(1, 'Hit'), _track_row(2, 'Other Hit')]
    },
}

_FULL = {
    'bio_html': '<p>Born somewhere.</p>',
    'social': {'twitter': 'https://twitter.com/artist'},
    'related_artist_names': [],
}


def test_finder_artist_maps_profile_related_and_top_songs():
    with (
        patch('downtify.deezer.httpx.get', _routes(_ARTIST_TABLE)),
        patch('downtify.deezer.fetch_artist_full', return_value=_FULL) as full,
    ):
        artist = finder_artist('7', 'pt-BR')
    full.assert_called_once_with('7', 'pt-BR')
    assert artist['name'] == 'The Artist'
    assert artist['fans'] == 5000
    assert artist['album_count'] == 12
    assert artist['cover_url'] == 'https://example.com/artist-xl.jpg'
    assert artist['bio_html'] == '<p>Born somewhere.</p>'
    assert artist['social'] == {'twitter': 'https://twitter.com/artist'}
    assert [r['name'] for r in artist['related']] == ['Friend']
    assert artist['related'][0]['fans'] == 10
    assert [s['name'] for s in artist['top_songs']] == ['Hit', 'Other Hit']


def test_finder_artist_extras_fail_quietly():
    table = dict(_ARTIST_TABLE)
    table['https://api.deezer.com/artist/7/related'] = Exception('boom')
    table['https://api.deezer.com/artist/7/top'] = Exception('boom')
    with (
        patch('downtify.deezer.httpx.get', _routes(table)),
        patch(
            'downtify.deezer.fetch_artist_full',
            side_effect=ValueError('no bio'),
        ),
    ):
        artist = finder_artist('7')
    assert artist['name'] == 'The Artist'
    assert not artist['bio_html']
    assert artist['social'] == {}
    assert artist['related'] == []
    assert artist['top_songs'] == []


def test_finder_artist_raises_when_the_artist_does_not_resolve():
    table = dict(_ARTIST_TABLE)
    table['https://api.deezer.com/artist/7'] = {'error': {'code': 800}}
    with (
        patch('downtify.deezer.httpx.get', _routes(table)),
        patch('downtify.deezer.fetch_artist_full', return_value=None),
    ):
        with pytest.raises(ValueError, match='Deezer refused'):
            finder_artist('7')


# ── finder_artist_albums / album_track_counts ────────────────────────────


def test_finder_artist_albums_leaves_unknown_track_counts_empty():
    table = {
        'https://api.deezer.com/artist/7/albums': {
            'data': [
                {
                    'id': 70,
                    'title': 'Newest',
                    'release_date': '2024-02-03',
                    'record_type': 'ep',
                    'fans': 42,
                },
                {'id': 71, 'title': 'Older', 'release_date': '2019-01-01'},
            ]
        }
    }
    deezer._ALBUM_TRACK_COUNTS['71'] = 10
    with patch('downtify.deezer.httpx.get', _routes(table)):
        albums = finder_artist_albums('7')
    newest, older = albums
    assert newest['name'] == 'Newest'
    assert newest['artist_id'] == '7'
    assert newest['release_date'] == '2024-02-03'
    assert newest['year'] == '2024'
    assert newest['release_type'] == 'EP'
    assert newest['fans'] == 42
    # An artist's albums listing carries no track count.
    assert newest['track_count'] is None
    assert older['track_count'] == 10


def test_album_track_counts_reads_the_tracklist_total_once():
    table = {
        'https://api.deezer.com/album/70/tracks': {'data': [], 'total': 11},
        'https://api.deezer.com/album/71/tracks': Exception('boom'),
    }
    fake = _routes(table)
    with patch('downtify.deezer.httpx.get', fake):
        assert album_track_counts(['70', '71', 'x', '70']) == {'70': 11}
        # Remembered: asking again makes no new request for it.
        assert album_track_counts(['70']) == {'70': 11}
    urls = [url for url, _params in fake.calls]
    assert urls.count('https://api.deezer.com/album/70/tracks') == 1
    assert all(params == {'limit': 1} for _url, params in fake.calls)


def test_album_track_counts_ignores_non_numeric_ids():
    with patch('downtify.deezer.httpx.get') as mock_get:
        assert album_track_counts(['', 'abc', '../1']) == {}
    mock_get.assert_not_called()


# ── finder_album ─────────────────────────────────────────────────────────


def test_finder_album_maps_details_and_tracks():
    bare_row = _track_row(2, 'Second')
    bare_row.pop('album')
    table = {
        'https://api.deezer.com/album/70': {
            'id': 70,
            'title': 'The Album',
            'upc': '0123',
            'link': 'https://www.deezer.com/album/70',
            'cover_xl': 'https://example.com/album-xl.jpg',
            'genres': {'data': [{'name': 'Electro'}, {'name': 'Pop'}]},
            'label': 'Label Ltd.',
            'nb_tracks': 2,
            'duration': 400,
            'fans': 99,
            'release_date': '2001-03-07',
            'record_type': 'album',
            'explicit_lyrics': True,
            'contributors': [{'id': 7, 'name': 'The Artist', 'role': 'Main'}],
            'artist': {'id': 7, 'name': 'The Artist'},
            'tracks': {'data': [_track_row(1, 'First'), bare_row]},
        }
    }
    with patch('downtify.deezer.httpx.get', _routes(table)):
        album = finder_album('70')
    tracks = album.pop('tracks')
    assert album == {
        'album_id': '70',
        'name': 'The Album',
        'artist': 'The Artist',
        'artist_id': '7',
        'cover_url': 'https://example.com/album-xl.jpg',
        'release_date': '2001-03-07',
        'year': '2001',
        'label': 'Label Ltd.',
        'genres': ['Electro', 'Pop'],
        'duration': 400,
        'track_count': 2,
        'fans': 99,
        'release_type': 'Album',
        'explicit': True,
        'upc': '0123',
        'url': 'https://www.deezer.com/album/70',
        'contributors': [
            {'artist_id': '7', 'name': 'The Artist', 'role': 'Main'}
        ],
        'source': 'deezer',
    }
    assert [t['track_number'] for t in tracks] == [1, 2]
    # A row without its own album reference borrows the album's.
    assert tracks[1]['cover_url'] == 'https://example.com/album-xl.jpg'
    assert tracks[1]['album_name'] == 'The Album'
    assert deezer._ALBUM_TRACK_COUNTS['70'] == 2


# ── endpoints ────────────────────────────────────────────────────────────


def test_finder_artist_endpoint_returns_plain_text_bio(monkeypatch):
    monkeypatch.setattr(
        api.deezer,
        'finder_artist',
        lambda artist_id, lang: {
            'name': 'The Artist',
            'bio_html': '<p>First.</p><p>Second &amp; last.</p>',
        },
    )
    artist = api.finder_artist_endpoint(artist_id='7', lang='en')
    assert 'bio_html' not in artist
    assert artist['bio'] == 'First.\n\nSecond & last.'


def test_finder_endpoints_turn_deezer_failures_into_502(monkeypatch):
    def fail(*_args, **_kwargs):
        raise ValueError('Could not reach Deezer')

    monkeypatch.setattr(api.deezer, 'finder_album', fail)
    with pytest.raises(HTTPException) as exc:
        api.finder_album_endpoint(album_id='70')
    assert exc.value.status_code == 502
