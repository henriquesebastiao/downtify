from downtify.providers import (
    _parse_text_search_query,
    song_stub_from_text_query,
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
