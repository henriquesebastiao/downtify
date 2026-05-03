"""Tests for parse_spotify_url() — pure URL parsing, no network calls."""

from __future__ import annotations

import pytest

from downtify.spotify import parse_spotify_url

# ── valid URLs ────────────────────────────────────────────────────────────────


def test_parse_track_url():
    result = parse_spotify_url(
        'https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT'
    )
    assert result == ('track', '4cOdK2wGLETKBW3PvgPWqT')


def test_parse_album_url():
    result = parse_spotify_url(
        'https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3'
    )
    assert result == ('album', '1DFixLWuPkv3KT3TnV35m3')


def test_parse_playlist_url():
    result = parse_spotify_url(
        'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M'
    )
    assert result == ('playlist', '37i9dQZF1DXcBWIGoYBM5M')


def test_parse_intl_localized_url():
    result = parse_spotify_url(
        'https://open.spotify.com/intl-pt/track/4cOdK2wGLETKBW3PvgPWqT'
    )
    assert result == ('track', '4cOdK2wGLETKBW3PvgPWqT')


def test_parse_intl_es_localized_url():
    result = parse_spotify_url(
        'https://open.spotify.com/intl-es/album/1DFixLWuPkv3KT3TnV35m3'
    )
    assert result == ('album', '1DFixLWuPkv3KT3TnV35m3')


def test_parse_url_without_scheme():
    result = parse_spotify_url('open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT')
    assert result == ('track', '4cOdK2wGLETKBW3PvgPWqT')


def test_parse_http_scheme():
    result = parse_spotify_url(
        'http://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT'
    )
    assert result == ('track', '4cOdK2wGLETKBW3PvgPWqT')


# ── URI format ────────────────────────────────────────────────────────────────


def test_parse_uri_track():
    result = parse_spotify_url('spotify:track:4cOdK2wGLETKBW3PvgPWqT')
    assert result == ('track', '4cOdK2wGLETKBW3PvgPWqT')


def test_parse_uri_playlist():
    result = parse_spotify_url('spotify:playlist:37i9dQZF1DXcBWIGoYBM5M')
    assert result == ('playlist', '37i9dQZF1DXcBWIGoYBM5M')


def test_parse_uri_album():
    result = parse_spotify_url('spotify:album:1DFixLWuPkv3KT3TnV35m3')
    assert result == ('album', '1DFixLWuPkv3KT3TnV35m3')


def test_parse_uri_malformed_returns_none():
    assert parse_spotify_url('spotify:onlyone') is None


# ── invalid / non-Spotify ─────────────────────────────────────────────────────


def test_parse_empty_string_returns_none():
    assert parse_spotify_url('') is None


def test_parse_youtube_url_returns_none():
    assert (
        parse_spotify_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        is None
    )


def test_parse_random_text_returns_none():
    assert parse_spotify_url('not a url at all') is None


@pytest.mark.parametrize(
    'url',
    [
        'https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT',
        'https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3',
        'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M',
        'spotify:track:4cOdK2wGLETKBW3PvgPWqT',
    ],
)
def test_parse_returns_two_tuple(url):
    result = parse_spotify_url(url)
    assert result is not None
    assert len(result) == 2


@pytest.mark.parametrize(
    'url',
    [
        'https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT',
        'https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3',
        'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M',
    ],
)
def test_parse_id_is_alphanumeric(url):
    result = parse_spotify_url(url)
    assert result is not None
    kind, sid = result
    assert sid.isalnum()
