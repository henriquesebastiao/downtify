"""Tests for YouTube Music provider helpers."""

from __future__ import annotations

from downtify.providers import enrich_from_match


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
