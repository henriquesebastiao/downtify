"""PlaylistHiddenSongs on both backends: the same results on SQLite and PostgreSQL."""

from __future__ import annotations

from downtify.playlist_hidden import PlaylistHiddenSongs, hidden_key


def test_hide_songs_counts_and_show_again(backend_db) -> None:
    store = PlaylistHiddenSongs(backend_db)

    assert store.hide(
        'Road Trip', track_id='t1', content_key='k1', path='a.mp3'
    )
    assert not store.hide('road trip', track_id='t1', path='a.mp3')
    assert store.hide('Road Trip', content_key='k2', path='b.mp3')
    assert store.hide('Road Trip', path='c.mp3', label='C', position=2)
    assert not store.hide('Road Trip')
    assert not store.hide('', track_id='t9')
    assert not store.hide('Road Trip', path='   ')

    songs = store.songs('ROAD TRIP')
    assert bool(songs)
    assert songs.track_ids == frozenset({'t1'})
    assert songs.content_keys == frozenset({'k1', 'k2'})
    assert songs.files == frozenset({'a.mp3', 'b.mp3', 'c.mp3'})
    assert not store.songs('Nothing')
    assert store.counts() == {hidden_key('Road Trip'): 3}

    removed = store.show('Road Trip', ['t1', 'key:k2', 'missing', 't1'])
    assert [row['key'] for row in removed] == ['t1', 'key:k2']
    assert removed[0]['track_id'] == 't1'
    assert removed[0]['file'] == 'a.mp3'
    assert removed[0]['content_key'] == 'k1'
    assert removed[1]['content_key'] == 'k2'
    assert store.show('Road Trip', []) == []
    assert store.show('', ['c.mp3']) == []
    assert store.counts() == {hidden_key('Road Trip'): 1}
    assert [row['key'] for row in store.show('Road Trip', ['file:c.mp3'])] == [
        'file:c.mp3'
    ]
    assert store.counts() == {}


def test_items_list_most_recent_first_and_row_shape(backend_db) -> None:
    store = PlaylistHiddenSongs(backend_db)
    store.hide('Mix', track_id='a', path='a.mp3', label='A', extinf='E1')
    store.hide('Mix', content_key='kb', path='b.mp3', position=4)
    store.hide('Mix', path='c.mp3')
    store.hide('Other', track_id='z', path='z.mp3')

    items = store.items('mix')
    assert [item['file'] for item in items] == ['c.mp3', 'b.mp3', 'a.mp3']
    assert items[2] == {
        'key': 'a',
        'track_id': 'a',
        'content_key': '',
        'file': 'a.mp3',
        'label': 'A',
        'extinf': 'E1',
        'position': -1,
        'hidden_at': items[2]['hidden_at'],
    }
    assert items[1]['key'] == 'key:kb'
    assert items[1]['position'] == 4
    assert isinstance(items[1]['position'], int)
    assert store.items('Nobody') == []


def test_forget_drops_a_playlist(backend_db) -> None:
    store = PlaylistHiddenSongs(backend_db)
    store.hide('Gone', track_id='g1', path='g1.mp3')
    store.hide('Gone', track_id='g2', path='g2.mp3')
    store.hide('Kept', track_id='k1', path='k1.mp3')

    assert store.forget('gone') == 2
    assert store.forget('gone') == 0
    assert not store.songs('Gone')
    assert store.counts() == {hidden_key('Kept'): 1}


def test_rekey_follows_a_rewritten_file(backend_db) -> None:
    store = PlaylistHiddenSongs(backend_db)
    store.hide('Mix', track_id='t1', content_key='old', path='x/old.mp3')
    store.hide('Mix', track_id='t2', content_key='keep', path='x/keep.mp3')

    assert store.rekey('', 'new') == 0
    assert store.rekey('old', 'old') == 0
    assert store.rekey('old', 'new', 'x\\new.mp3') == 1
    assert store.rekey('gone', 'new2') == 0

    songs = store.songs('Mix')
    assert songs.content_keys == frozenset({'new', 'keep'})
    assert songs.files == frozenset({'x/new.mp3', 'x/keep.mp3'})

    store.hide('Other', content_key='c2', path='y/z.mp3')
    assert store.rekey('c2', 'c3') == 1
    assert store.songs('Other').content_keys == frozenset({'c3'})
    assert store.songs('Other').files == frozenset({'y/z.mp3'})


def test_hidden_songs_match_source_rows_and_files(backend_db) -> None:
    store = PlaylistHiddenSongs(backend_db)
    store.hide('Mix', track_id='abc123', content_key='ck', path='m/a.mp3')
    songs = store.songs('Mix')

    assert songs.hides_song({'song_id': 'abc123'})
    assert not songs.hides_song({'song_id': 'other'})
    assert songs.hides_file('m\\a.mp3')
    assert songs.hides_file('zz.mp3', 'ck')
    assert not songs.hides_file('zz.mp3', '')


def test_store_opened_on_a_database_keeps_its_path_attribute(
    sqlite_db,
) -> None:
    store = PlaylistHiddenSongs(sqlite_db)
    assert store.db is sqlite_db
    assert store._path == str(sqlite_db.path)
