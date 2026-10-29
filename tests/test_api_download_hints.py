"""Tests for client hint merge on per-URL downloads."""

from __future__ import annotations

from downtify.api import _merge_client_track_hints


def test_merge_applies_track_index_and_dates():
    base: dict = {
        'song_id': 'spotify:id',
        'url': 'https://open.spotify.com/track/x',
    }
    _merge_client_track_hints(
        base,
        {
            'track_number': 4,
            'album_track_total': 14,
            'release_date': '2022-03-01',
            'year': '2022',
            'noise': 'ignored',
        },
    )
    assert base['track_number'] == 4
    assert base['album_track_total'] == 14
    assert base['release_date'] == '2022-03-01'
    assert base['year'] == '2022'
    assert 'noise' not in base


def test_merge_ignores_invalid_track_number():
    base: dict = {'song_id': 'a'}
    _merge_client_track_hints(
        base, {'track_number': 'x', 'album_track_total': 0}
    )
    assert 'track_number' not in base
    assert 'album_track_total' not in base


def test_merge_applies_youtube_id_override():
    base: dict = {
        'song_id': 'spotify:id',
        'url': 'https://open.spotify.com/track/x',
    }
    _merge_client_track_hints(base, {'youtube_id': ' dQw4w9WgXcQ '})
    assert base['youtube_id'] == 'dQw4w9WgXcQ'
    assert base['youtube_id_override'] is True


def test_merge_applies_soundcloud_track_url_override():
    base = {
        'song_id': 'spotify:id',
        'name': 'Spotify track',
        'album_name': 'Spotify album',
        'source': 'spotify',
    }

    _merge_client_track_hints(
        base,
        {'soundcloud_url': 'https://soundcloud.com/artist/track'},
    )

    assert base['soundcloud_url'] == 'https://soundcloud.com/artist/track'
    assert base['soundcloud_url_override'] is True
    assert base['name'] == 'Spotify track'
    assert base['album_name'] == 'Spotify album'
    assert base['source'] == 'spotify'


def test_merge_ignores_non_soundcloud_override_url():
    base = {'song_id': 'spotify:id'}

    _merge_client_track_hints(
        base,
        {'soundcloud_url': 'https://example.com/redirect'},
    )

    assert 'soundcloud_url' not in base


def test_soundcloud_override_drops_the_known_video():
    base = {'song_id': 'yt1', 'youtube_id': 'dQw4w9WgXcQ'}

    _merge_client_track_hints(
        base,
        {
            'youtube_id': 'dQw4w9WgXcQ',
            'soundcloud_url': 'https://soundcloud.com/artist/track?si=x',
        },
    )

    assert base['soundcloud_url'] == 'https://soundcloud.com/artist/track'
    assert 'youtube_id' not in base


def test_youtube_override_drops_a_stale_soundcloud_track():
    base = {
        'song_id': 'spotify:id',
        'soundcloud_url': 'https://soundcloud.com/artist/track',
    }

    _merge_client_track_hints(base, {'youtube_id': 'dQw4w9WgXcQ'})

    assert base['youtube_id'] == 'dQw4w9WgXcQ'
    assert 'soundcloud_url' not in base
