"""Artists to follow on the Monitor page (``downtify.artist_suggestions``
and ``GET /api/monitor/artist-suggestions[/resolve]``)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from downtify import api
from downtify.artist_suggestions import artist_candidates, artist_suggestions
from downtify.auth import Principal

NOW = datetime(2026, 10, 25, tzinfo=timezone.utc)
CHANNEL = 'UC' + 'a' * 22
OTHER = 'UC' + 'b' * 22


def listen(name, plays, days=0):
    return {
        'name': name,
        'plays': plays,
        'last_played': (NOW - timedelta(days=days)).isoformat(),
    }


def rank(library=(), listens=(), watches=(), **kw):
    return artist_suggestions(library, listens, watches, now=NOW, **kw)


def names(page):
    return [row['name'] for row in page['items']]


# ── Ranking ─────────────────────────────────────────────────────────────


def test_listening_ranks_by_recent_plays_not_library_size():
    out = rank(
        [{'name': 'Old', 'track_count': 500}],
        [listen('Old', 100, 180), listen('Recent', 10)],
    )
    assert names(out['listening']) == ['Recent', 'Old']
    assert out['listening']['items'][0]['track_count'] == 0
    assert out['listening']['items'][1]['track_count'] == 500
    assert out['half_life_days'] == 45


def test_plays_halve_every_half_life_and_a_future_time_counts_as_now():
    rows = rank(listens=[listen('A', 20, 45), listen('B', 10, -5)])[
        'listening'
    ]['items']
    assert [row['score'] for row in rows] == [10, 10]


def test_listens_of_one_artist_under_two_spellings_add_up():
    out = rank(listens=[listen('AC/DC', 3, 2), listen('acdc', 4, 1)])
    [row] = out['listening']['items']
    assert row['plays'] == 7
    assert row['last_played'] == (NOW - timedelta(days=1)).isoformat()


def test_library_by_tracks_then_albums_then_name():
    out = rank([
        {'name': 'Z', 'track_count': 10, 'album_count': 2},
        {'name': 'A', 'track_count': 10, 'album_count': 2},
        {'name': 'B', 'track_count': 10, 'album_count': 3},
        {'name': 'C', 'track_count': 11, 'album_count': 1},
        {'name': 'Empty', 'track_count': 0, 'album_count': 0},
    ])
    assert names(out['library']) == ['C', 'B', 'A', 'Z']


def test_watched_artists_are_left_out_even_paused_but_playlists_are_not():
    watches = [
        SimpleNamespace(name='A', kind='artist', enabled=False),
        SimpleNamespace(name='B', kind='playlist'),
    ]
    out = rank(
        [{'name': 'a', 'track_count': 3}],
        [listen('a', 5), listen('B', 2)],
        watches,
    )
    assert names(out['listening']) == ['B']
    assert out['library']['total'] == 0


@pytest.mark.parametrize('name', ['Various Artists', 'various', 'Unknown'])
def test_compilation_placeholders_are_never_suggested(name):
    out = rank(
        [{'name': name, 'track_count': 100, 'album_count': 10}],
        [listen(name, 100)],
    )
    assert out['listening']['total'] == out['library']['total'] == 0


def test_pages_are_independent():
    listens = [listen(str(n), 50 - n) for n in range(45)]
    out = rank(listens=listens, listening_offset=20, limit=20)
    assert len(out['listening']['items']) == 20
    assert out['listening']['next_offset'] == 40
    assert out['library'] == {'items': [], 'total': 0, 'next_offset': None}
    last = rank(listens=listens, listening_offset=40)['listening']
    assert len(last['items']) == 5
    assert last['next_offset'] is None


def test_unusable_listens_are_left_out():
    out = rank(
        listens=[
            listen('', 2),
            listen('A', 0),
            {'name': 'B', 'plays': 3, 'last_played': 'invalid'},
            {'name': 'C', 'plays': 3, 'last_played': None},
        ]
    )
    assert out['listening']['total'] == 0


# ── Picking the YouTube Music artist ────────────────────────────────────


def test_a_single_artist_with_the_name_is_followed_without_asking():
    rows = [
        {'name': 'Artist Tribute', 'artist_id': OTHER},
        {'name': 'ARTIST', 'artist_id': CHANNEL},
    ]
    result = artist_candidates('Artist', rows)
    assert result['url'] == f'https://music.youtube.com/channel/{CHANNEL}'


def test_namesakes_are_a_choice_named_ones_first():
    rows = [
        {'name': 'Someone Else', 'artist_id': 'UC' + 'c' * 22},
        {'name': 'Same', 'artist_id': CHANNEL},
        {'name': 'Same', 'artist_id': OTHER},
        {'name': 'Same', 'artist_id': CHANNEL},
    ]
    result = artist_candidates('Same', rows)
    assert result['url'] is None
    assert [c['artist_id'] for c in result['candidates']] == [
        CHANNEL,
        OTHER,
        'UC' + 'c' * 22,
    ]


def test_at_most_ten_namesakes_are_offered():
    rows = [{'name': 'Same', 'artist_id': f'UC{n:022d}'} for n in range(20)]
    result = artist_candidates('Same', rows)
    assert len(result['candidates']) == 10
    assert result['candidates'][0]['artist_id'] == f'UC{0:022d}'


def test_the_top_result_is_never_followed_on_its_own():
    result = artist_candidates(
        'Wanted', [{'name': 'Other', 'artist_id': CHANNEL}]
    )
    assert result['url'] is None
    assert [c['name'] for c in result['candidates']] == ['Other']


def test_a_row_without_a_valid_channel_id_is_not_offered():
    rows = [
        {'name': 'Wanted', 'artist_id': '../bad'},
        {'name': 'Wanted', 'artist_id': 'UCshort'},
        {'name': 'Wanted', 'artist_id': ''},
    ]
    assert artist_candidates('Wanted', rows) == {
        'candidates': [],
        'url': None,
    }


@pytest.mark.parametrize(
    ('url', 'allowed'),
    [
        ('https://yt3.googleusercontent.com/artist-photo', True),
        ('https://yt3.ggpht.com/artist-photo', True),
        ('https://lh3.googleusercontent.com/artist-photo=w544', True),
        ('http://yt3.ggpht.com/artist-photo', False),
        ('https://untrusted.invalid/artist-photo', False),
        ('https://user:password@yt3.ggpht.com/photo', False),
        ('https://yt3.ggpht.com:8443/photo', False),
        ('https://yt3.ggpht.com:bad/photo', False),
        ('javascript:alert(1)', False),
    ],
)
def test_only_youtube_music_photos_are_shown(url, allowed):
    [candidate] = artist_candidates(
        'Artist', [{'name': 'Artist', 'artist_id': CHANNEL, 'cover_url': url}]
    )['candidates']
    assert candidate['image_url'] == (url if allowed else '')


# ── Endpoints ───────────────────────────────────────────────────────────


def request(uid=7, admin=False):
    principal = Principal(
        'session', 'user', '', uid, 'owner', 'admin' if admin else 'user'
    )
    return Request({
        'type': 'http',
        'state': {'principal': principal},
        'headers': [],
    })


def _stores(monkeypatch, calls, listens, hidden=()):
    monkeypatch.setattr(
        api,
        '_require_discover',
        lambda: SimpleNamespace(
            listens=lambda uid: calls.append(('listens', uid)) or listens
        ),
    )
    monkeypatch.setattr(
        api,
        '_require_monitor_db',
        lambda: SimpleNamespace(
            list_playlists=lambda uid: calls.append(('watches', uid)) or []
        ),
    )
    monkeypatch.setattr(api, 'library_context', lambda: 'context')
    monkeypatch.setattr(api, 'allowed_entry_keys', lambda req: {'visible'})
    monkeypatch.setattr(api, 'admin_hidden_rules', lambda req: None)
    monkeypatch.setattr(
        api,
        'library_artist_index',
        lambda ctx, **kw: calls.append(('library', kw['allowed_keys'])) or [],
    )
    monkeypatch.setattr(
        api,
        'hidden_rules',
        lambda: SimpleNamespace(artist_hidden=lambda name: name in hidden),
    )


@pytest.mark.parametrize('admin', [False, True])
def test_listens_and_watches_are_always_the_users_own(monkeypatch, admin):
    calls = []
    _stores(monkeypatch, calls, [listen('Own', 3)])
    out = api.monitor_artist_suggestions(request(admin=admin), 0, 0, 20)
    assert names(out['listening']) == ['Own']
    assert calls == [
        ('library', {'visible'}),
        ('listens', 7),
        ('watches', 7),
    ]


@pytest.mark.parametrize('admin', [False, True])
def test_artists_hidden_from_users_stay_out_of_their_listens(
    monkeypatch, admin
):
    _stores(
        monkeypatch,
        [],
        [listen('Hidden', 10), listen('Visible', 3)],
        hidden={'Hidden'},
    )
    out = api.monitor_artist_suggestions(request(admin=admin), 0, 0, 20)
    assert names(out['listening']) == (
        ['Hidden', 'Visible'] if admin else ['Visible']
    )


def test_no_user_no_suggestions():
    with pytest.raises(HTTPException) as err:
        api.monitor_artist_suggestions(None, 0, 0, 20)
    assert err.value.status_code == 401


def test_resolving_searches_youtube_music_and_adds_no_watch(monkeypatch):
    searched = []
    monkeypatch.setattr(
        api.providers,
        'search_artists',
        lambda name, limit: (
            searched.append(name) or [{'name': name, 'artist_id': CHANNEL}]
        ),
    )
    monkeypatch.setattr(
        api,
        '_require_monitor_db',
        lambda: pytest.fail('resolving must not add a watch'),
    )
    out = api.resolve_monitor_artist_suggestion(request(), '  Artist ')
    assert out['url'].endswith(CHANNEL)
    assert searched == ['Artist']


def test_resolving_a_blank_name_is_400():
    with pytest.raises(HTTPException) as err:
        api.resolve_monitor_artist_suggestion(request(), '   ')
    assert err.value.status_code == 400
