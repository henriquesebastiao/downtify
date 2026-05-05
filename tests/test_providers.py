"""Tests for YouTube Music provider helpers."""

from __future__ import annotations

import pytest

from downtify.providers import enrich_from_match, youtube_music_track_index_for_match


@pytest.fixture(autouse=True)
def clear_ytm_album_cache():
    """Isolate tests that manipulate the in-memory get_album cache."""
    import downtify.providers as p

    p._album_track_cache.clear()
    p._album_browse_search_cache.clear()
    yield
    p._album_track_cache.clear()
    p._album_browse_search_cache.clear()


def test_enrich_from_match_backfills_artists_when_empty():
    song = {
        'name': 'Test Song',
        'artists': [],
        'source': 'spotify',
        'song_id': 'spotifyTrack1',
    }
    match = {
        'videoId': 'yt123',
        'title': 'Test Song',
        'artists': [{'name': 'AliasFromYT'}],
        'thumbnails': [{'url': 'https://example.com/t.jpg'}],
        'duration_seconds': 180,
    }
    out = enrich_from_match(song, match)
    assert out['artists'] == ['AliasFromYT']
    assert out['artist'] == 'AliasFromYT'


def test_enrich_from_match_does_not_replace_existing_artists():
    song = {
        'name': 'Test Song',
        'artists': ['KeepMe'],
        'source': 'spotify',
    }
    match = {
        'videoId': 'yt123',
        'title': 'Test Song',
        'artists': [{'name': 'Other'}],
    }
    out = enrich_from_match(song, match)
    assert out['artists'] == ['KeepMe']


def test_enrich_from_match_sets_track_index_from_album(monkeypatch):
    import downtify.providers as providers

    def fake_cached(browse_id: str):
        assert browse_id == 'MPREb_test'
        return (
            [
                {'videoId': 'v_one', 'trackNumber': 1},
                {'videoId': 'v_two', 'trackNumber': 2},
            ],
            12,
        )

    monkeypatch.setattr(providers, '_cached_album_tracks_and_count', fake_cached)
    match = {
        'videoId': 'v_two',
        'title': 'B-side',
        'album': {'name': 'Test LP', 'id': 'MPREb_test'},
    }
    out = enrich_from_match({'name': 'B-side', 'source': 'spotify'}, match)
    assert out['track_number'] == 2
    assert out['album_track_total'] == 12


def test_youtube_music_track_number_zero_falls_back_to_list_position(monkeypatch):
    import downtify.providers as providers

    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _browse_id: (
            [{'videoId': 'vidX', 'trackNumber': 0}],
            None,
        ),
    )
    n, total = youtube_music_track_index_for_match(
        {'videoId': 'vidX', 'album': {'name': '', 'id': 'x'}},
        None,
    )
    assert n == 1
    assert total == 1


def test_youtube_music_no_album_id_returns_no_track(monkeypatch):
    import downtify.providers as providers

    monkeypatch.setattr(providers, '_album_browse_id_from_search', lambda *_: '')
    assert youtube_music_track_index_for_match(
        {'videoId': 'solo', 'album': {'name': 'Loose singles only'}},
        None,
    ) == (None, None)


def test_enrich_preserves_preset_track_number(monkeypatch):
    import downtify.providers as providers

    def fake_cached(_browse_id: str):
        return ([{'videoId': 'vin', 'trackNumber': 2}], 9)

    monkeypatch.setattr(providers, '_cached_album_tracks_and_count', fake_cached)
    monkeypatch.setattr(
        providers, '_album_browse_id', lambda *_args, **_kw: 'any'
    )
    out = enrich_from_match(
        {'track_number': 7, 'album_track_total': 11},
        {'videoId': 'vin', 'album': {'id': 'mbid'}},
    )
    assert out['track_number'] == 7
    assert out['album_track_total'] == 11
