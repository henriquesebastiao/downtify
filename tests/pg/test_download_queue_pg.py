"""PendingDownloads on both backends (SQLite file, migrated PostgreSQL)."""

from __future__ import annotations

import threading

from downtify.download_queue import PendingDownload, PendingDownloads


def _job(song_id: str, users=(), **options) -> PendingDownload:
    return PendingDownload(
        song_id=song_id,
        song={'song_id': song_id, 'name': song_id.upper()},
        options=options,
        user_ids=list(users),
    )


def _ids(store: PendingDownloads) -> list[str]:
    return [row.song_id for row in store.rows()]


def test_add_keeps_queue_order_and_round_trips_fields(backend_db):
    store = PendingDownloads(backend_db)
    store.add([
        _job('a', [2, 1], subdir='x', delay_seconds=3),
        _job('b'),
        _job('c', [0, 5]),
    ])

    rows = store.rows()

    assert [r.song_id for r in rows] == ['a', 'b', 'c']
    assert rows[0].song == {'song_id': 'a', 'name': 'A'}
    assert rows[0].options == {'subdir': 'x', 'delay_seconds': 3}
    assert rows[0].user_ids == [1, 2]
    assert rows[2].user_ids == [5]


def test_add_existing_song_keeps_place_and_options_merges_users(backend_db):
    store = PendingDownloads(backend_db)
    store.add([_job('a', [1], subdir='first'), _job('b')])
    store.add([_job('a', [3, 1], subdir='second'), _job('c', [4])])

    rows = {r.song_id: r for r in store.rows()}

    assert _ids(store) == ['a', 'b', 'c']
    assert rows['a'].options == {'subdir': 'first'}
    assert rows['a'].user_ids == [1, 3]
    assert rows['c'].user_ids == [4]


def test_add_empty_is_a_no_op(backend_db):
    store = PendingDownloads(backend_db)
    store.add([])
    assert store.rows() == []


def test_add_concurrently_with_overlapping_songs(backend_db):
    store = PendingDownloads(backend_db)
    errors: list[BaseException] = []

    def worker(n: int) -> None:
        try:
            store.add([_job(f's{i}', [n]) for i in range(10)])
        except BaseException as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    rows = {r.song_id: r for r in store.rows()}
    assert sorted(rows) == sorted(f's{i}' for i in range(10))
    assert all(r.user_ids == list(range(1, 8)) for r in rows.values())


def test_forget_removes_listed_songs_and_ignores_unknown(backend_db):
    store = PendingDownloads(backend_db)
    store.add([_job('a'), _job('b'), _job('c')])

    store.forget(['b', 'missing', '', 'b'])
    assert _ids(store) == ['a', 'c']

    store.forget([])
    assert _ids(store) == ['a', 'c']


def test_forget_handles_more_ids_than_one_chunk(backend_db):
    store = PendingDownloads(backend_db)
    ids = [f'song-{i}' for i in range(1200)]
    store.add([_job(sid) for sid in ids])

    store.forget(ids[:1100])

    assert _ids(store) == ids[1100:]


def test_clear_empties_the_queue(backend_db):
    store = PendingDownloads(backend_db)
    store.add([_job('a'), _job('b')])
    store.clear()
    assert store.rows() == []


def test_rows_skips_unreadable_and_non_object_rows(backend_db):
    store = PendingDownloads(backend_db)
    store.add([_job('good')])
    store.add([_job('ok')])
    with store.db.connect() as conn:
        conn.execute(
            'INSERT INTO pending_downloads (song_id, song, options, user_ids)'
            " VALUES ('bad', 'not json', '{}', '[]')"
        )
        conn.execute(
            'INSERT INTO pending_downloads (song_id, song, options, user_ids)'
            " VALUES ('list', '[1, 2]', '{}', '[]')"
        )
        conn.execute(
            'INSERT INTO pending_downloads (song_id, song, options, user_ids)'
            " VALUES ('badopts', '{\"a\": 1}', '[]', '[]')"
        )

    rows = {r.song_id: r for r in store.rows()}

    assert set(rows) == {'good', 'ok', 'badopts'}
    assert rows['badopts'].options == {}


def test_rows_normalises_user_ids(backend_db):
    store = PendingDownloads(backend_db)
    store.add([_job('a')])
    with store.db.connect() as conn:
        conn.execute(
            'UPDATE pending_downloads SET user_ids = \'[3, "4", 0, "x", 3]\''
            " WHERE song_id = 'a'"
        )
    assert store.rows()[0].user_ids == [3, 4]


def test_paused_defaults_false_and_round_trips(backend_db):
    store = PendingDownloads(backend_db)
    assert store.paused() is False

    store.set_paused(True)
    assert store.paused() is True

    store.set_paused(False)
    assert store.paused() is False


def test_store_built_from_path_keeps_path_attribute(tmp_path):
    store = PendingDownloads(tmp_path / 'queue.db')
    assert store._path == str(tmp_path / 'queue.db')
    store.add([_job('a')])
    assert _ids(store) == ['a']
