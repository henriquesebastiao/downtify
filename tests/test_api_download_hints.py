"""Tests for client hint merge on per-URL downloads."""

from __future__ import annotations

from downtify.api import _merge_client_track_hints


def test_merge_applies_track_index_and_dates():
    base: dict = {'song_id': 'spotify:id', 'url': 'https://open.spotify.com/track/x'}
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
    _merge_client_track_hints(base, {'track_number': 'x', 'album_track_total': 0})
    assert 'track_number' not in base
    assert 'album_track_total' not in base
