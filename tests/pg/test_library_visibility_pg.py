"""LibraryVisibility on both backends: the same results on SQLite and PostgreSQL."""

from __future__ import annotations

from downtify.library_visibility import (
    KIND_ALBUM,
    KIND_ARTIST,
    KIND_TRACK,
    LibraryVisibility,
    album_key,
    artist_key,
)


def test_hide_and_rules_on_each_kind(backend_db) -> None:
    store = LibraryVisibility(backend_db)

    assert store.hide(KIND_ARTIST, artist_key('Ana'), label='Ana')
    assert not store.hide(KIND_ARTIST, artist_key('ana'), label='Ana')
    assert store.hide(KIND_ALBUM, album_key('Bo', 'Moon'), label='Moon')
    assert store.hide(
        KIND_TRACK, 'one|10', label='One', path='Ana\\Sun\\one.mp3'
    )
    assert not store.hide('bogus', 'x')
    assert not store.hide(KIND_TRACK, '')

    rules = store.rules()
    assert rules
    assert rules.artist_hidden('ANA')
    assert not rules.album_reason('Bo', 'Sun')
    assert rules.album_reason('bo', 'moon') == KIND_ALBUM
    assert rules.album_reason('Ana', 'Sun') == KIND_ARTIST
    assert 'one|10' in rules.track_keys
    assert 'Ana/Sun/one.mp3' in rules.track_paths


def test_nothing_hidden_is_falsy(backend_db) -> None:
    assert not LibraryVisibility(backend_db).rules()


def test_show_and_drop_remove_rules(backend_db) -> None:
    store = LibraryVisibility(backend_db)
    store.hide(KIND_ARTIST, artist_key('Ana'))
    store.hide(KIND_TRACK, 'k1', path='a/b.mp3')
    store.hide(KIND_TRACK, 'k2')

    assert store.show(KIND_ARTIST, artist_key('Ana'))
    assert not store.show(KIND_ARTIST, artist_key('Ana'))
    assert store.show_track_by_path('a\\b.mp3') == 1
    assert store.show_track_by_path('') == 0
    store.drop_track('k2')
    store.drop_track('')

    assert not store.rules()


def test_rekey_track_moves_rule_and_skips_collisions(backend_db) -> None:
    store = LibraryVisibility(backend_db)
    store.hide(KIND_TRACK, 'old', path='x/old.mp3')
    store.hide(KIND_TRACK, 'taken', path='x/taken.mp3')
    store.hide(KIND_TRACK, 'free', path='x/free.mp3')

    assert store.rekey_track('old', 'new', 'x/new.mp3') == 1
    assert store.rekey_track('free', 'taken') == 0
    assert store.rekey_track('same', 'same') == 0

    rules = store.rules()
    assert 'new' in rules.track_keys
    assert 'x/new.mp3' in rules.track_paths
    assert 'old' not in rules.track_keys
    keys = {item['key'] for item in store.items()['tracks']}
    assert keys == {'new', 'taken'}


def test_items_lists_newest_first_per_kind(backend_db) -> None:
    store = LibraryVisibility(backend_db)
    store.hide(KIND_TRACK, 't1', label='One', detail='Ana', path='a.mp3')
    store.hide(KIND_ALBUM, album_key('Ana', 'Sun'), label='Sun', detail='Ana')
    store.hide(KIND_ARTIST, artist_key('Bo'), label='Bo')
    store.hide(KIND_TRACK, 't2', label='Two')

    items = store.items()

    assert [t['key'] for t in items['tracks']] == ['t2', 't1']
    assert items['tracks'][1]['file'] == 'a.mp3'
    assert items['albums'][0]['title'] == 'Sun'
    assert items['albums'][0]['folded'] == ['ana', 'sun']
    assert items['artists'][0]['name'] == 'Bo'


def test_invalidate_reloads_rules(backend_db) -> None:
    store = LibraryVisibility(backend_db)
    assert not store.rules()
    other = LibraryVisibility(backend_db)
    other.hide(KIND_ARTIST, artist_key('Ana'))

    store.invalidate()

    assert store.rules().artist_hidden('Ana')
