"""Start-up backfills write in a few short transactions, not one per row."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from downtify.db import batching
from downtify.db.config import Dialect
from downtify.db.core import Database
from downtify.monitor import PlaylistMonitorDB
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex

_ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'


def _track_id(n: int) -> str:
    text = ''
    for _ in range(22):
        text += _ALPHABET[n % 62]
        n //= 62
    return text


def _table(db: Database) -> None:
    with db.connect() as conn:
        conn.execute('CREATE TABLE t (n INTEGER PRIMARY KEY)')


def _rows(db: Database) -> list[int]:
    with db.connect() as conn:
        return [r['n'] for r in conn.execute('SELECT n FROM t ORDER BY n')]


def _insert(db: Database, n: int) -> None:
    # What a store method does: its own ``with connect()`` block.
    with db.connect() as conn:
        conn.execute('INSERT INTO t (n) VALUES (?)', (n,))


def test_rows_commit_in_batches_visible_to_other_connections(tmp_path):
    db = Database.sqlite(tmp_path / 'x.db')
    _table(db)
    reader = Database.sqlite(tmp_path / 'x.db')
    seen = []
    for n in batching.in_short_transactions(
        db, range(7), max_rows=3, max_seconds=60
    ):
        # Before row n is written: only whole earlier batches are visible.
        seen.append(len(_rows(reader)))
        _insert(db, n)
    assert seen == [0, 0, 0, 3, 3, 3, 6]
    assert _rows(reader) == list(range(7))


def test_a_failure_rolls_back_only_the_current_batch(tmp_path):
    db = Database.sqlite(tmp_path / 'x.db')
    _table(db)

    def write_until_six() -> None:
        for n in batching.in_short_transactions(
            db, range(10), max_rows=4, max_seconds=60
        ):
            if n == 6:
                raise RuntimeError('boom')
            _insert(db, n)

    with pytest.raises(RuntimeError):
        write_until_six()
    # Rows 0-3 were committed; 4 and 5 shared the failed transaction.
    assert _rows(db) == [0, 1, 2, 3]
    # The connection was released: the database is usable again.
    _insert(db, 99)
    assert _rows(db) == [0, 1, 2, 3, 99]


def test_a_slow_loop_commits_on_time_not_just_on_count(tmp_path):
    db = Database.sqlite(tmp_path / 'x.db')
    _table(db)
    reader = Database.sqlite(tmp_path / 'x.db')
    seen = []
    for n in batching.in_short_transactions(
        db, range(3), max_rows=1000, max_seconds=0
    ):
        seen.append(len(_rows(reader)))
        _insert(db, n)
    assert seen == [0, 1, 2]


def test_another_writer_waits_for_the_batch_instead_of_failing(tmp_path):
    db = Database.sqlite(tmp_path / 'x.db')
    _table(db)
    other = Database.sqlite(tmp_path / 'x.db')
    errors: list[BaseException] = []

    def write_elsewhere() -> None:
        try:
            _insert(other, 1000)
        except BaseException as error:  # noqa: BLE001  # reported below
            errors.append(error)

    writer = threading.Thread(target=write_elsewhere)
    for n in batching.in_short_transactions(
        db, range(5), max_rows=100, max_seconds=60
    ):
        if n == 0:
            # Read first, like the backfills' lookups, and let another
            # writer commit in the middle of the batch: the batch's own
            # writes must still go through.
            _rows(db)
            writer.start()
            writer.join(timeout=1)
        _insert(db, n)
    writer.join(timeout=30)
    assert not errors
    assert _rows(db) == [0, 1, 2, 3, 4, 1000]


def test_empty_input_writes_nothing(tmp_path):
    db = Database.sqlite(tmp_path / 'x.db')
    _table(db)
    assert list(batching.in_short_transactions(db, [])) == []
    assert _rows(db) == []


def _history(backend_db, download_dir: Path, count: int) -> None:
    monitor = PlaylistMonitorDB(backend_db)
    # One transaction, so building a big history stays quick.
    with backend_db.connect():
        watches = [
            monitor.add_playlist(f'pl{n:026d}', f'Mix {n}', f'http://x/{n}')
            for n in range(3)
        ]
        for n in range(count):
            name = f'Artist {n % 7} - Song {n}.mp3'
            (download_dir / name).write_bytes(b'a' * (n % 50 + 1))
            monitor.mark_track_downloaded(
                watches[n % 3].id, _track_id(n + 1), name
            )
        # A song in two playlists, and a row whose file is gone.
        monitor.mark_track_downloaded(
            watches[1].id, _track_id(1), 'Artist 0 - Song 0.mp3'
        )
        monitor.mark_track_downloaded(
            watches[2].id, _track_id(10**6), 'gone.mp3'
        )


def _snapshot(db: Database) -> dict:
    with db.connect() as conn:
        return {
            'tracks': sorted(
                (r['spotify_track_id'], r['filename'], r['content_key'])
                for r in conn.execute('SELECT * FROM library_tracks')
            ),
            'playlists': sorted(
                (r['name'], r['spotify_id'])
                for r in conn.execute('SELECT * FROM playlists')
            ),
            'members': sorted(
                (
                    r['playlist_name'],
                    r['track_spotify_id'],
                    r['content_key'],
                    r['filename'],
                    r['track_order'],
                )
                for r in conn.execute('SELECT * FROM playlist_tracks')
            ),
        }


@pytest.mark.parametrize('rows', [0, 1, 40])
def test_batched_backfill_matches_the_one_row_at_a_time_result(
    backend_db, tmp_path, monkeypatch, rows
):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    _history(backend_db, download_dir, rows)

    def run(batch: int, label: str):
        with monkeypatch.context() as m:
            m.setattr(
                batching.in_short_transactions,
                '__kwdefaults__',
                {'max_rows': batch, 'max_seconds': 60},
            )
            return _snapshot_after(backend_db, download_dir, tmp_path, label)

    # One transaction per row is the old behaviour; 7 puts batch ends
    # in the middle of a playlist and of the duplicate song's rows.
    assert run(7, 'batched') == run(1, 'one-by-one')


def _snapshot_after(backend_db, download_dir, tmp_path, label):
    """Backfill a fresh library store from *backend_db*'s history."""

    if backend_db.dialect is Dialect.SQLITE:
        library = Database.sqlite(tmp_path / f'library-{label}.db')
    else:
        # PostgreSQL: one schema per test, so wipe the library tables.
        library = backend_db
        with library.connect() as conn:
            for table in ('playlist_tracks', 'playlists', 'library_tracks'):
                conn.execute(f'DELETE FROM {table}')
    TrackIndex(library)
    PlaylistCatalog(library)
    imported = TrackIndex(library).backfill_from_monitor_db(backend_db)
    linked = PlaylistCatalog(library).backfill_from_monitor_db(
        backend_db, download_dir=download_dir
    )
    # Running again (the next start) must change nothing.
    again = _snapshot(library)
    TrackIndex(library).backfill_from_monitor_db(backend_db)
    PlaylistCatalog(library).backfill_from_monitor_db(
        backend_db, download_dir=download_dir
    )
    assert _snapshot(library) == again
    return imported, linked, again


def test_backfill_opens_a_handful_of_connections_not_one_per_row(
    sqlite_db, tmp_path, monkeypatch
):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    _history(sqlite_db, download_dir, 1203)
    library = Database.sqlite(tmp_path / 'library.db')
    TrackIndex(library)
    PlaylistCatalog(library)

    opened = []
    real = Database._acquire

    def counting(self):
        if self is library:
            opened.append(1)
        return real(self)

    monkeypatch.setattr(Database, '_acquire', counting)
    imported, linked = _run_backfills_into(library, sqlite_db, download_dir)
    # The index records the missing file too (it never checks the disk).
    assert imported == 1204
    assert linked == 1204  # the song in two playlists counts twice
    # Was about 5 per row (over 6,000); now a few per 500 rows.
    assert len(opened) < 20


def _run_backfills_into(library, monitor, download_dir):
    imported = TrackIndex(library).backfill_from_monitor_db(monitor)
    linked = PlaylistCatalog(library).backfill_from_monitor_db(
        monitor, download_dir=download_dir
    )
    return imported, linked
