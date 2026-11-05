import zlib

from downtify import api
from downtify.providers import (
    _parse_text_search_query,
    song_stub_from_text_query,
    spotify_open_url,
)


def test_parse_artist_dash_title():
    artists, title = _parse_text_search_query('Daft Punk - One More Time')
    assert artists == ['Daft Punk']
    assert title == 'One More Time'


def test_song_stub_from_text_query():
    stub = song_stub_from_text_query('Daft Punk - One More Time')
    assert stub is not None
    assert stub['name'] == 'One More Time'
    assert stub['artists'] == ['Daft Punk']
    assert stub['source'] == 'text_search'
    # The id keys the download queue, so it must not change between runs.
    assert stub['song_id'] == 'search-%08x' % zlib.crc32(
        b'Daft Punk - One More Time'
    )
    assert stub['spotify_url'] == (
        'https://open.spotify.com/search/Daft%20Punk%20One%20More%20Time'
    )


def test_search_results_are_downloaded_by_metadata(monkeypatch):
    row = {
        'song_id': 'video1234567',
        'name': 'One More Time',
        'artists': ['Daft Punk'],
        'duration': 320,
        'source': 'youtube',
    }
    monkeypatch.setattr(api.library_only, 'enabled', lambda settings: False)
    monkeypatch.setattr(
        api.providers, 'search_songs', lambda query, limit: [row]
    )

    result = api.search_endpoint(query='Daft Punk - One More Time')

    assert result == [{**row, 'download_by_metadata': True}]


def test_search_download_keeps_result_metadata(monkeypatch):
    def unexpected_resolve(url):
        raise AssertionError('a search result must not be re-resolved by URL')

    monkeypatch.setattr(api, '_song_for_download', unexpected_resolve)
    hints = {
        'song_id': 'video1234567',
        'name': 'One More Time',
        'artists': ['Daft Punk'],
        'duration': 320,
        'source': 'youtube',
        'url': 'https://music.youtube.com/watch?v=video1234567',
        'download_by_metadata': True,
    }

    song = api._song_from_download_request(hints['url'], hints)

    assert song['name'] == 'One More Time'
    assert song['artists'] == ['Daft Punk']
    assert song['duration'] == 320
    assert song['_match_by_metadata'] is True
    assert 'download_by_metadata' not in song


def test_spotify_open_url_uses_existing_spotify_link():
    song = {
        'name': 'Track',
        'artists': ['A'],
        'url': 'https://open.spotify.com/track/abc123',
    }
    assert spotify_open_url(song) == 'https://open.spotify.com/track/abc123'


def test_spotify_open_url_builds_search_for_youtube_rows():
    song = {
        'name': 'One More Time',
        'artists': ['Daft Punk'],
        'url': 'https://music.youtube.com/watch?v=xyz',
    }
    assert spotify_open_url(song) == (
        'https://open.spotify.com/search/Daft%20Punk%20One%20More%20Time'
    )
