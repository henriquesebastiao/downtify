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
    assert stub['spotify_url'] == (
        'https://open.spotify.com/search/Daft%20Punk%20One%20More%20Time'
    )


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
