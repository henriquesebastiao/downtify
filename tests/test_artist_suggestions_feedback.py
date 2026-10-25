from datetime import datetime, timezone

from downtify import api
from downtify.artist_suggestions import artist_candidates, artist_suggestions
from tests.test_artist_suggestions import request


def test_various_artists_is_not_a_followable_suggestion():
    now = datetime.now(timezone.utc)
    result = artist_suggestions(
        [{'name': 'Various Artists', 'track_count': 100, 'album_count': 10}],
        [
            {
                'name': 'Various Artists',
                'plays': 100,
                'last_played': now.isoformat(),
            }
        ],
        [],
        now=now,
    )
    assert result['listening']['total'] == result['library']['total'] == 0


def test_spotify_homonyms_require_explicit_choice():
    rows = [{'name': 'Artist', 'artist_id': n * 22} for n in ('a', 'b')]
    result = artist_candidates('Artist', rows, source='spotify')
    assert result['url'] is None
    assert len(result['candidates']) == 2
    assert all(
        r['url'].startswith('https://open.spotify.com/artist/')
        for r in result['candidates']
    )


def test_resolution_prefers_spotify_when_requested(monkeypatch):
    monkeypatch.setattr(
        api.spotify, '_search_suggestion_items', lambda name: []
    )
    monkeypatch.setattr(
        api.spotify,
        'search_results',
        lambda items: {'artists': [{'id': 'a' * 22, 'name': 'Artist'}]},
    )
    monkeypatch.setattr(
        api.providers,
        'search_artists',
        lambda *a, **k: [{'name': 'Artist', 'artist_id': 'UC' + 'a' * 22}],
    )
    assert (
        api.resolve_monitor_artist_suggestion(request(), 'Artist', 'spotify')[
            'url'
        ]
        == 'https://open.spotify.com/artist/' + 'a' * 22
    )


def test_spotify_unavailable_has_explicit_youtube_fallback(monkeypatch):
    monkeypatch.setattr(
        api.spotify,
        '_search_suggestion_items',
        lambda name: (_ for _ in ()).throw(ValueError('Unavailable')),
    )
    monkeypatch.setattr(
        api.providers,
        'search_artists',
        lambda *a, **k: [{'name': 'Artist', 'artist_id': 'UC' + 'a' * 22}],
    )
    assert api.resolve_monitor_artist_suggestion(
        request(), 'Artist', 'spotify'
    )['url'].startswith('https://music.youtube.com/channel/')


def test_ambiguous_spotify_channel_mapping_is_offered_before_submit(
    monkeypatch,
):
    monkeypatch.setattr(
        api.spotify, '_search_suggestion_items', lambda name: []
    )
    monkeypatch.setattr(
        api.spotify,
        'search_results',
        lambda items: {'artists': [{'id': 'a' * 22, 'name': 'Artist'}]},
    )
    monkeypatch.setattr(
        api.providers,
        'search_artists',
        lambda *a, **k: [
            {'name': 'Artist', 'artist_id': 'UC' + c * 22} for c in ('a', 'b')
        ],
    )
    result = api.resolve_monitor_artist_suggestion(
        request(), 'Artist', 'spotify'
    )
    assert result['url'] is None
    assert len(result['candidates']) == 2
    assert all(
        r['url'].startswith('https://music.youtube.com/channel/')
        for r in result['candidates']
    )
