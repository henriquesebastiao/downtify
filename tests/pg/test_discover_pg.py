"""DiscoverStore on both backends: the same results on SQLite and PostgreSQL.

Every public method runs at least once; timestamps are pinned so the
ordering checks don't depend on the clock.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from downtify import discover
from downtify.discover import DiscoverStore

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(hours=1)
T2 = T0 + timedelta(hours=2)


@pytest.fixture
def store(backend_db) -> DiscoverStore:
    return DiscoverStore(backend_db)


@pytest.fixture
def pinned_now(monkeypatch):
    """Pin the clock the store reads when no ``when`` is given."""
    clock = {'now': T0}
    monkeypatch.setattr(discover, '_now', lambda: clock['now'])
    return clock


def test_listens_count_per_artist_and_keep_the_latest_name(store):
    store.record_listen('Abba', when=T0)
    row = store.record_listen('abba', when=T1)

    assert row == {
        'name': 'abba',
        'plays': 2,
        'last_played': T1.isoformat(),
    }
    assert store.listens() == [
        {'name': 'abba', 'plays': 2, 'last_played': T1.isoformat()}
    ]


def test_a_late_report_never_moves_last_played_back(store):
    store.record_listen('Abba', when=T1)
    row = store.record_listen('Abba', when=T0)

    assert row['plays'] == 2
    assert row['last_played'] == T1.isoformat()


def test_a_repeated_play_id_is_counted_once(store):
    store.record_listen('Abba', when=T0, play_id='p-1')
    row = store.record_listen('Abba', when=T0, play_id='p-1')

    assert row['plays'] == 1
    assert store.record_listen('Abba', when=T0, play_id='p-2')['plays'] == 2


def test_a_name_without_a_key_is_ignored(store):
    assert store.record_listen('   ') is None
    assert store.block('  ') is None
    assert store.listens() == []


def test_listens_sort_by_plays_then_name_in_byte_order(store):
    store.record_listen('Zed', when=T0)
    store.record_listen('Zed', when=T0)
    store.record_listen('Zed', when=T0)
    store.record_listen('apple', when=T0)
    store.record_listen('Banana', when=T0)

    names = [row['name'] for row in store.listens()]
    assert names == ['Zed', 'Banana', 'apple']


def test_listens_filter_by_user_and_clear_per_user(store):
    store.record_listen('Abba', when=T0, user_id=7)
    store.record_listen('Queen', when=T0, user_id=8)

    assert [r['name'] for r in store.listens(user_id=7)] == ['Abba']
    assert [r['name'] for r in store.listens(user_id=8)] == ['Queen']
    assert store.clear_listens(user_id=7) == 1
    assert store.listens(user_id=7) == []
    assert store.clear_listens() == 1
    assert store.listens() == []


def test_reassign_legacy_moves_user_zero_rows_once(store):
    store.record_listen('Abba', when=T0)
    store.block('Queen')

    assert store.reassign_legacy(0) == 0
    assert store.reassign_legacy(5) == 2
    assert store.reassign_legacy(5) == 0
    assert [r['name'] for r in store.listens(user_id=5)] == ['Abba']
    assert [r['name'] for r in store.blocked(user_id=5)] == ['Queen']


def test_remove_user_forgets_listens_and_blocks(store):
    store.record_listen('Abba', when=T0, user_id=3)
    store.block('Queen', user_id=3)
    store.block('Oasis', user_id=4)

    store.remove_user(3)

    assert store.listens(user_id=3) == []
    assert store.blocked(user_id=3) == []
    assert [r['name'] for r in store.blocked(user_id=4)] == ['Oasis']


def test_block_list_round_trip(store, pinned_now):
    pinned_now['now'] = T0
    assert store.block('Queen', user_id=1) == {
        'name': 'Queen',
        'blocked_at': T0.isoformat(),
    }
    pinned_now['now'] = T1
    store.block('Oasis', user_id=1)
    # Blocking twice keeps the first stamp.
    again = store.block('queen', user_id=1)
    assert again == {'name': 'Queen', 'blocked_at': T0.isoformat()}
    store.block('Blur', user_id=2)

    assert [r['name'] for r in store.blocked(user_id=1)] == ['Oasis', 'Queen']
    assert [r['name'] for r in store.blocked()] == ['Blur', 'Oasis', 'Queen']
    assert store.blocked_keys(user_id=1) == {'queen', 'oasis'}
    assert store.blocked_keys() == {'queen', 'oasis', 'blur'}


def test_blocked_names_sort_by_stamp_then_name(store, pinned_now):
    pinned_now['now'] = T0
    store.block('apple')
    store.block('Banana')
    store.block('cherry')

    names = [r['name'] for r in store.blocked()]
    assert names == ['Banana', 'apple', 'cherry']


def test_unblock_for_one_user_or_everyone(store):
    store.block('Queen', user_id=1)
    store.block('Queen', user_id=2)

    assert store.unblock('queen', user_id=1) is True
    assert store.unblock('queen', user_id=1) is False
    assert store.blocked_keys(user_id=2) == {'queen'}
    assert store.unblock('QUEEN') is True
    assert store.blocked_keys() == set()


def test_related_cache_round_trip(store):
    assert store.cached_related('abba') is None

    related = [{'name': 'Queen', 'id': 3}]
    store.save_related('abba', '1234', related, when=T0)
    assert store.cached_related('abba') == {
        'deezer_id': '1234',
        'related': related,
        'fetched_at': T0,
    }

    store.save_related('abba', '', [], when=T1)
    assert store.cached_related('abba') == {
        'deezer_id': '',
        'related': [],
        'fetched_at': T1,
    }


def test_search_cache_round_trip(store):
    assert store.cached_search('abba') is None

    store.save_search('abba', {'albums': [{'id': 'a1'}]}, when=T0)
    assert store.cached_search('abba') == {
        'results': {'albums': [{'id': 'a1'}]},
        'fetched_at': T0,
    }

    store.save_search('abba', {}, when=T1)
    assert store.cached_search('abba') == {'results': {}, 'fetched_at': T1}


def test_deezer_parts_are_cached_on_their_own(store):
    assert store.cached_deezer('abba', 'albums') is None

    store.save_deezer('abba', 'albums', [{'id': 1}], when=T0)
    assert store.cached_deezer('abba', 'albums') == {
        'value': [{'id': 1}],
        'fetched_at': T0,
    }
    assert store.cached_deezer('abba', 'playlist') is None

    store.save_deezer('abba', 'playlist', None, when=T1)
    assert store.cached_deezer('abba', 'playlist') == {
        'value': None,
        'fetched_at': T1,
    }
    assert store.cached_deezer('abba', 'albums')['value'] == [{'id': 1}]


def test_album_match_round_trip_including_misses(store):
    assert store.cached_album_match('sp-1') is None

    store.save_album_match(
        'sp-1',
        {'album_id': 9, 'artist_id': 3, 'cover_url': 'https://c/1.jpg'},
        when=T0,
    )
    assert store.cached_album_match('sp-1') == {
        'deezer_album_id': '9',
        'deezer_artist_id': '3',
        'cover_url': 'https://c/1.jpg',
        'fetched_at': T0,
    }

    store.save_album_match('sp-2', None, when=T1)
    assert store.cached_album_match('sp-2') == {
        'deezer_album_id': '',
        'deezer_artist_id': '',
        'cover_url': '',
        'fetched_at': T1,
    }
