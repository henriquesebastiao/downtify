"""LibrarySync on both backends: the same ids and feed on SQLite and PostgreSQL."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone

from downtify.db.config import Dialect
from downtify.db.migrations.schema.library_b import DDL
from downtify.library_cache_keys import file_content_key_from_name_and_size
from downtify.library_sync import TOMBSTONE_DAYS, LibrarySync

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _entry(path: str, title: str, size: int = 1000, **extra) -> dict:
    entry = {
        'file': path,
        'title': title,
        'artist': 'Ana',
        'album': 'Sun',
        'duration': 120.0,
        'size': size,
        'track_number': 1,
    }
    entry.update(extra)
    return entry


def _create_optional_tables(db, *names: str) -> None:
    """The optional tables of other stores, from the migration's DDL (a
    no-op on PostgreSQL, where the migration already created them)."""

    statements = [
        stmt
        for stmt in DDL
        if any(f'EXISTS {name} (' in stmt for name in names)
    ]
    with db.connect() as conn:
        for stmt in statements:
            conn.execute(stmt)


def _sync_table_count(db) -> int:
    with db.connect() as conn:
        return conn.execute('SELECT COUNT(*) FROM sync_tracks').fetchone()[0]


def test_empty_library(backend_db) -> None:
    sync = LibrarySync(backend_db)

    assert sync.cursor() == 0
    assert sync.refresh([]) == 0
    assert sync.refresh([], now=NOW) == 0
    assert sync.changes(0) == {
        'cursor': 0,
        'full': True,
        'tracks': [],
        'deleted': [],
    }
    assert sync.changes(5)['full'] is True
    assert sync.touch('') is False
    assert sync.touch('missing.flac') is False
    assert sync.touch_all() == 0
    assert sync.cursor() == 0
    assert sync.ids_for_paths(['missing.flac', '']) == {}
    assert sync.path_for('t0') is None
    assert sync.row_for('t0') is None
    assert sync.rows_for(['t0', 't0']) == {}


def test_populated_library_ids_rows_and_feed(backend_db) -> None:
    sync = LibrarySync(backend_db)
    entries = [
        _entry('a/one.flac', 'One'),
        _entry('a/two.flac', 'Two', explicit=True, playlists=['P']),
    ]

    assert sync.refresh(entries, now=NOW) == 2
    assert sync.cursor() == 2
    # Unchanged rows bump nothing.
    assert sync.refresh(entries, now=NOW) == 2

    ids = sync.ids_for_paths(['a/one.flac', 'a/two.flac', 'missing', ''])
    assert set(ids) == {'a/one.flac', 'a/two.flac'}
    one, two = ids['a/one.flac'], ids['a/two.flac']
    assert one != two

    assert sync.path_for(one) == 'a/one.flac'
    row = sync.row_for(one)
    assert row['id'] == one
    assert row['file'] == 'a/one.flac'
    assert row['title'] == 'One'
    assert row['album_id']
    assert row['artist_id']
    assert 'explicit' not in row

    found = sync.rows_for([one, 'nope', one, two])
    assert set(found) == {one, two}
    assert found[two]['explicit'] is True
    assert found[two]['playlists'] == ['P']

    feed = sync.changes(0)
    assert feed['cursor'] == 2
    assert feed['full'] is True
    assert feed['deleted'] == []
    assert [t['file'] for t in feed['tracks']] == ['a/one.flac', 'a/two.flac']
    assert {t['id'] for t in feed['tracks']} == {one, two}

    incremental = sync.changes(2)
    assert incremental == {
        'cursor': 2,
        'full': False,
        'tracks': [],
        'deleted': [],
    }


def test_edit_move_and_rename_keep_ids(backend_db) -> None:
    sync = LibrarySync(backend_db)
    sync.refresh(
        [_entry('a/one.flac', 'One'), _entry('x/old.mp3', 'Song', size=500)],
        now=NOW,
    )
    ids = sync.ids_for_paths(['a/one.flac', 'x/old.mp3'])
    one, old = ids['a/one.flac'], ids['x/old.mp3']
    before = sync.cursor()

    # A re-tag in place: same path, same id, new content.
    sync.refresh(
        [
            _entry('a/one.flac', 'One (remaster)'),
            _entry('x/old.mp3', 'Song', size=500),
        ],
        now=NOW,
    )
    edited = sync.changes(before)
    assert edited['full'] is False
    assert [t['id'] for t in edited['tracks']] == [one]
    assert edited['tracks'][0]['title'] == 'One (remaster)'
    assert edited['deleted'] == []

    # A move (same file name and size, new folder) keeps the id.
    # A rename (new name and size, same title/artist/album/length) does too.
    sync.refresh(
        [
            _entry('c/one.flac', 'One (remaster)'),
            _entry('x/new.m4a', 'Song', size=700),
        ],
        now=NOW,
    )
    moved = sync.ids_for_paths(['c/one.flac', 'x/new.m4a'])
    assert moved == {'c/one.flac': one, 'x/new.m4a': old}
    assert sync.path_for(one) == 'c/one.flac'
    assert sync.path_for(old) == 'x/new.m4a'
    assert sync.changes(before)['deleted'] == []


def test_removal_leaves_a_tombstone(backend_db) -> None:
    sync = LibrarySync(backend_db)
    sync.refresh([_entry('a/one.flac', 'One'), _entry('b/two.flac', 'Two')])
    ids = sync.ids_for_paths(['a/one.flac', 'b/two.flac'])
    gone, kept = ids['b/two.flac'], ids['a/one.flac']
    before = sync.cursor()

    assert sync.refresh([_entry('a/one.flac', 'One')]) == before + 1
    feed = sync.changes(before)
    assert feed == {
        'cursor': before + 1,
        'full': False,
        'tracks': [],
        'deleted': [gone],
    }
    assert sync.path_for(gone) is None
    assert sync.row_for(gone) is None
    assert sync.rows_for([gone]) == {}
    assert sync.ids_for_paths(['b/two.flac']) == {}
    assert sync.path_for(kept) == 'a/one.flac'

    full = sync.changes(0)
    assert full['full'] is True
    assert [t['id'] for t in full['tracks']] == [kept]
    assert full['deleted'] == []


def test_touch_and_touch_all(backend_db) -> None:
    sync = LibrarySync(backend_db)
    sync.refresh([_entry('a/one.flac', 'One'), _entry('b/two.flac', 'Two')])
    ids = sync.ids_for_paths(['a/one.flac', 'b/two.flac'])

    assert sync.touch('a/one.flac') is True
    assert sync.cursor() == 3
    poked = sync.changes(2)
    assert [t['id'] for t in poked['tracks']] == [ids['a/one.flac']]
    assert poked['deleted'] == []

    assert sync.touch('missing.flac') is False
    assert sync.cursor() == 3

    assert sync.touch_all() == 2
    assert sync.cursor() == 4
    again = sync.changes(3)
    assert {t['id'] for t in again['tracks']} == set(ids.values())


def test_feed_filters_by_allowed_keys(backend_db) -> None:
    sync = LibrarySync(backend_db)
    sync.refresh([_entry('a/one.flac', 'One'), _entry('b/two.flac', 'Two')])
    ids = sync.ids_for_paths(['a/one.flac', 'b/two.flac'])
    key_one = file_content_key_from_name_and_size('a/one.flac', 1000)
    before = sync.cursor()
    sync.touch_all()

    full = sync.changes(0, allowed_keys={key_one})
    assert [t['id'] for t in full['tracks']] == [ids['a/one.flac']]
    assert full['deleted'] == []

    # Rows that fall outside the allowed set leave the client's copy.
    incremental = sync.changes(before, allowed_keys={key_one})
    assert [t['id'] for t in incremental['tracks']] == [ids['a/one.flac']]
    assert incremental['deleted'] == [ids['b/two.flac']]


def test_tombstones_are_purged_after_the_window(backend_db) -> None:
    sync = LibrarySync(backend_db)
    sync.refresh(
        [_entry('a/one.flac', 'One'), _entry('b/two.flac', 'Two')], now=NOW
    )
    gone = sync.ids_for_paths(['b/two.flac'])['b/two.flac']
    sync.refresh([_entry('a/one.flac', 'One')], now=NOW)
    assert sync.cursor() == 3
    assert _sync_table_count(backend_db) == 2

    later = NOW + timedelta(days=TOMBSTONE_DAYS + 1)
    sync.refresh([_entry('a/one.flac', 'One')], now=later)

    assert _sync_table_count(backend_db) == 1
    assert sync.row_for(gone) is None
    # A cursor older than the purge needs a full list.
    assert sync.changes(2)['full'] is True
    assert sync.changes(3)['full'] is False
    assert sync.changes(3)['deleted'] == []


def test_trashed_tombstones_are_kept_until_released(backend_db) -> None:
    _create_optional_tables(backend_db, 'library_trash')
    sync = LibrarySync(backend_db)
    sync.refresh(
        [_entry('a/one.flac', 'One'), _entry('b/two.flac', 'Two')], now=NOW
    )
    gone = sync.ids_for_paths(['b/two.flac'])['b/two.flac']
    with backend_db.connect() as conn:
        conn.execute(
            'INSERT INTO library_trash (id, batch, user_id, root_key, '
            'relative, stored, track_id, row_json, manifest, state, created) '
            "VALUES ('trash1', 'b1', 1, 'music', 'two.flac', 'x', ?, "
            "'{}', '[]', 'trashed', 1.0)",
            (gone,),
        )
    sync.refresh([_entry('a/one.flac', 'One')], now=NOW)

    later = NOW + timedelta(days=TOMBSTONE_DAYS + 1)
    sync.refresh([_entry('a/one.flac', 'One')], now=later)
    assert _sync_table_count(backend_db) == 2

    with backend_db.connect() as conn:
        conn.execute(
            "UPDATE library_trash SET state = 'purged' WHERE id = 'trash1'"
        )
    sync.refresh([_entry('a/one.flac', 'One')], now=later)
    assert _sync_table_count(backend_db) == 1


def test_audio_replacement_aliases_resolve_to_the_new_file(backend_db) -> None:
    _create_optional_tables(
        backend_db,
        'library_audio_replacements',
        'library_audio_sync_aliases',
    )
    sync = LibrarySync(backend_db)
    sync.refresh([_entry('a/one.flac', 'One')], now=NOW)
    track = sync.ids_for_paths(['a/one.flac'])['a/one.flac']
    new_metadata = _entry('a/new.flac', 'One (new file)', size=2000)
    with backend_db.connect() as conn:
        conn.execute(
            'INSERT INTO library_audio_replacements (old_file, run_id, '
            'new_file, old_key, new_key, old_sha, new_sha, new_metadata, '
            'catalog, state, updated_at) VALUES (?, 1, ?, ?, ?, ?, ?, ?, '
            "'{}', 'linked', ?)",
            (
                'a/one.flac',
                'a/new.flac',
                'k1',
                'k2',
                's1',
                's2',
                json.dumps(new_metadata),
                NOW.isoformat(),
            ),
        )
        conn.execute(
            'INSERT INTO library_audio_sync_aliases (track_id, old_file) '
            'VALUES (?, ?)',
            (track, 'a/one.flac'),
        )

    assert sync.path_for(track) == 'a/new.flac'
    row = sync.row_for(track)
    assert row['id'] == track
    assert row['file'] == 'a/new.flac'
    assert row['title'] == 'One (new file)'
    assert sync.rows_for([track])[track]['file'] == 'a/new.flac'

    # Only linked, retained, removed or complete replacements count.
    with backend_db.connect() as conn:
        conn.execute(
            "UPDATE library_audio_replacements SET state = 'prepared'"
        )
    assert sync.path_for(track) == 'a/one.flac'
    assert sync.row_for(track)['file'] == 'a/one.flac'
    assert sync.rows_for([track])[track]['file'] == 'a/one.flac'


def test_constructor_accepts_path_and_database(backend_db, tmp_path) -> None:
    by_db = LibrarySync(backend_db)
    assert by_db.db is backend_db
    if backend_db.dialect is Dialect.SQLITE:
        assert by_db._path == str(backend_db.path)
        by_path = LibrarySync(tmp_path / 'lib.db')
        assert by_path._path == str(tmp_path / 'lib.db')
    else:
        assert by_db._path is None


def _run_threads(targets) -> list[BaseException]:
    """Run each callable in its own thread; return what they raised."""

    errors: list[BaseException] = []

    def wrap(fn):
        def run():
            try:
                fn()
            except BaseException as exc:  # reported by the test
                errors.append(exc)

        return run

    threads = [threading.Thread(target=wrap(fn)) for fn in targets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    return errors


def test_concurrent_touch_stamps_unique_seqs(backend_db) -> None:
    sync = LibrarySync(backend_db)
    paths = [f'c/{i:03}.flac' for i in range(160)]
    sync.refresh(
        [_entry(p, f'Track {i}') for i, p in enumerate(paths)], now=NOW
    )
    start = sync.cursor()

    def touch_chunk(chunk):
        def run():
            for path in chunk:
                assert sync.touch(path) is True

        return run

    errors = _run_threads(
        touch_chunk(paths[i * 20 : (i + 1) * 20]) for i in range(8)
    )
    assert errors == []

    # Every touch got its own number, and no number was skipped or reused.
    assert sync.cursor() == start + 160
    with backend_db.connect() as conn:
        seqs = sorted(
            r[0]
            for r in conn.execute(
                'SELECT seq FROM sync_tracks WHERE deleted_at IS NULL'
            ).fetchall()
        )
    assert seqs == list(range(start + 1, start + 161))

    # The feed returns every row exactly once, from the start and since it.
    full = sync.changes(0)
    assert full['full'] is True
    assert len({t['id'] for t in full['tracks']}) == 160
    assert len(full['tracks']) == 160
    incremental = sync.changes(start)
    assert incremental['full'] is False
    ids = [t['id'] for t in incremental['tracks']]
    assert len(ids) == 160
    assert len(set(ids)) == 160
    assert set(ids) == {t['id'] for t in full['tracks']}


def _two_writer_setup(backend_db):
    writer_a = LibrarySync(backend_db)
    writer_b = LibrarySync(backend_db)
    reader = LibrarySync(backend_db)
    paths = [f'lib/{i:02}.flac' for i in range(20)]

    def entries(tag: str) -> list[dict]:
        return [_entry(p, f'{tag} {p}') for p in paths]

    writer_a.refresh(entries('init'), now=NOW)
    ids = writer_a.ids_for_paths(paths)
    return writer_a, writer_b, reader, paths, entries, ids


def test_two_writers_interleave_without_gaps(backend_db) -> None:
    """Two LibrarySync objects on one database, as two processes would
    have: their writes interleave, and an incremental reader following
    ``since`` gets exactly what each write changed."""

    writer_a, writer_b, reader, paths, entries, ids = _two_writer_setup(
        backend_db
    )
    since = reader.changes(0)['cursor']
    for step in range(9):
        writer = (writer_a, writer_b)[step % 2]
        before = since
        if step % 3:
            assert writer.touch(paths[step]) is True
            expected = {ids[paths[step]]}
        else:
            writer.refresh(entries(f'step{step}'), now=NOW)
            expected = set(ids.values())
        feed = reader.changes(since)
        assert feed['full'] is False
        assert feed['cursor'] > before
        assert feed['cursor'] == writer.cursor()
        assert {t['id'] for t in feed['tracks']} == expected
        assert feed['deleted'] == []
        since = feed['cursor']


def test_threaded_writers_feed_has_no_gaps(backend_db) -> None:
    """Both writers refresh the whole library and touch rows from their
    own threads while a reader follows the feed: the reader ends up with
    exactly the library as it is, and the cursor never goes backwards."""

    writer_a, writer_b, reader, paths, entries, ids = _two_writer_setup(
        backend_db
    )
    seen: dict[str, str] = {}
    cursors: list[int] = []
    refresh_results: list[int] = []
    lock = threading.Lock()
    done = threading.Event()
    state = {'since': 0}

    def follow() -> None:
        while True:
            finished = done.is_set()
            feed = reader.changes(state['since'])
            cursors.append(feed['cursor'])
            if feed['full']:
                seen.clear()
            for track_id in feed['deleted']:
                seen.pop(track_id, None)
            for track in feed['tracks']:
                seen[track['id']] = track['revision']
            state['since'] = feed['cursor']
            if finished:
                return

    def writer(writer_obj, tag: str):
        def run() -> None:
            for i in range(8):
                result = writer_obj.refresh(entries(f'{tag}{i}'), now=NOW)
                with lock:
                    refresh_results.append(result)
                writer_obj.touch(paths[i])

        return run

    reader_thread = threading.Thread(target=follow)
    reader_thread.start()
    errors = _run_threads([writer(writer_a, 'a'), writer(writer_b, 'b')])
    done.set()
    reader_thread.join(timeout=120)
    assert errors == []
    assert not reader_thread.is_alive()

    # Every refresh got its own numbers, and the reader's cursor only grew.
    assert len(set(refresh_results)) == len(refresh_results)
    assert cursors == sorted(cursors)
    assert cursors[-1] == writer_a.cursor()

    # Nothing was missed: what the reader holds is the library as it is.
    final = reader.changes(0)
    assert final['full'] is True
    assert seen == {t['id']: t['revision'] for t in final['tracks']}
    assert set(seen) == set(ids.values())
