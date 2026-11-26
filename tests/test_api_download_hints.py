"""Tests for client hint merge on per-URL downloads."""

from __future__ import annotations

from downtify import api, providers
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


def test_merge_applies_the_album_artist_of_the_listed_album():
    base: dict = {'song_id': 'a'}
    _merge_client_track_hints(
        base, {'album_artist': ' Various Artists ', 'compilation': True}
    )
    assert base['album_artist'] == 'Various Artists'
    assert base['compilation'] is True


def test_merge_keeps_the_album_artist_the_url_resolved():
    base: dict = {'song_id': 'a', 'album_artist': 'AliasSolo'}
    _merge_client_track_hints(
        base, {'album_artist': 'Various Artists', 'compilation': True}
    )
    assert base['album_artist'] == 'AliasSolo'
    assert 'compilation' not in base


def test_merge_applies_the_album_of_the_listed_release():
    base: dict = {'song_id': 'v', 'album_name': ''}
    _merge_client_track_hints(base, {'album_name': ' The Lay of Thrym '})
    assert base['album_name'] == 'The Lay of Thrym'


def test_merge_keeps_the_album_the_url_resolved():
    base: dict = {'song_id': 'v', 'album_name': 'Resolved'}
    _merge_client_track_hints(base, {'album_name': 'Listed'})
    assert base['album_name'] == 'Resolved'


def test_a_retried_watch_song_keeps_its_album(monkeypatch):
    """Retry on a failed artist-watch song in the queue sends the song as
    the body; the video alone names no album, so without the body's the
    file went to ``<artist>/unknown/`` untagged."""

    monkeypatch.setattr(
        providers,
        'song_from_video_id',
        lambda video_id: {
            'song_id': video_id,
            'name': 'Flames Of The Free',
            'artists': ['Tyr'],
            'album_name': '',
            'url': f'https://music.youtube.com/watch?v={video_id}',
        },
    )
    watch_row = {
        'song_id': '6Lef-CitRnI',
        'name': 'Flames of the Free',
        'artists': ['Tyr'],
        'album_name': 'The Lay of Thrym',
        'track_number': 1,
        'url': 'https://music.youtube.com/watch?v=6Lef-CitRnI',
        '_monitor_release': 'MPREb_R7OrKkU35LS',
    }

    song = api._song_from_download_request(watch_row['url'], watch_row)

    assert song['album_name'] == 'The Lay of Thrym'
    assert song['track_number'] == 1


def test_merge_never_takes_a_compilation_flag_on_its_own():
    base: dict = {'song_id': 'a'}
    _merge_client_track_hints(base, {'compilation': True})
    assert 'compilation' not in base


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
