"""WatchHistoryStore on both backends (SQLite file, migrated PostgreSQL)."""

from __future__ import annotations

from downtify.db.config import Dialect
from downtify.db.dialect import insert_returning_id
from downtify.watch_history import (
    OUTCOME_DOWNLOADED,
    OUTCOME_LINKED,
    OUTCOME_UNKNOWN,
    WatchHistoryStore,
)
from tests.db.helpers import execute, query

TRACK_A = '4uLU6hMCjMI75M1A2tKUQC'
TRACK_B = '7ouMYWpwJ422jRcDASZB7P'
CREATED = '2026-01-01T00:00:00+00:00'


def _prepare(db) -> None:
    """Create the parent tables on SQLite (Postgres is migrated)."""
    with db.connect() as conn:
        if conn.dialect is Dialect.SQLITE:
            conn.execute(
                'CREATE TABLE IF NOT EXISTS monitored_playlists ('
                ' id INTEGER PRIMARY KEY AUTOINCREMENT,'
                ' spotify_id TEXT NOT NULL, name TEXT NOT NULL,'
                ' url TEXT NOT NULL, user_id INTEGER NOT NULL DEFAULT 0,'
                ' created_at TEXT NOT NULL)'
            )
            conn.execute(
                'CREATE TABLE IF NOT EXISTS downloaded_tracks ('
                ' id INTEGER PRIMARY KEY AUTOINCREMENT,'
                ' playlist_id INTEGER NOT NULL,'
                ' track_spotify_id TEXT NOT NULL,'
                ' downloaded_at TEXT NOT NULL, filename TEXT)'
            )


def _watch(
    db, key='pl1', name='Road Trip', user_id=0, created_at=CREATED
) -> int:
    """Insert one monitored playlist (a watch) and return its id."""
    _prepare(db)
    with db.connect() as conn:
        return insert_returning_id(
            conn,
            'INSERT INTO monitored_playlists'
            ' (spotify_id, name, url, user_id, created_at)'
            ' VALUES (?,?,?,?,?)',
            (key, name, f'https://example.test/{key}', user_id, created_at),
        )


def _hold(db, playlist_id, track_id, filename, downloaded_at=CREATED):
    execute(
        db,
        'INSERT INTO downloaded_tracks (playlist_id, track_spotify_id,'
        ' downloaded_at, filename) VALUES (?,?,?,?)',
        playlist_id,
        track_id,
        downloaded_at,
        filename,
    )


def _song(track_id, name='Alpha', artists=('Artist',)):
    return {'song_id': track_id, 'name': name, 'artists': artists}


def test_record_added_logs_event_and_clears_failure(backend_db) -> None:
    pl = _watch(backend_db, user_id=7)
    store = WatchHistoryStore(backend_db.connect)
    store.record_failure(pl, _song(TRACK_A), 'boom')

    store.record_added(
        pl,
        TRACK_A,
        'Road Trip/Alpha.mp3',
        outcome=OUTCOME_DOWNLOADED,
        provider='youtube-music',
        initial=True,
    )

    assert store.failures(pl) == []
    [event] = store.events(playlist_id=pl)
    assert (
        event['watch_key'],
        event['watch_name'],
        event['user_id'],
        event['track_id'],
        event['outcome'],
        event['filename'],
        event['provider'],
        int(event['initial']),
    ) == (
        'pl1',
        'Road Trip',
        7,
        TRACK_A,
        OUTCOME_DOWNLOADED,
        'Road Trip/Alpha.mp3',
        'youtube-music',
        1,
    )
    assert event['happened_at']


def test_record_added_defaults_and_unknown_watch(backend_db) -> None:
    pl = _watch(backend_db)
    store = WatchHistoryStore(backend_db.connect)

    store.record_added(pl, TRACK_B, None, outcome=OUTCOME_LINKED)
    store.record_added(999, TRACK_B, 'ghost.mp3', outcome=OUTCOME_LINKED)

    [event] = store.events(playlist_id=pl)
    assert (event['filename'], event['provider']) == (None, '')
    assert int(event['initial']) == 0
    # A watch that does not exist logs nothing.
    assert store.events(playlist_id=999) == []


def test_rename_file_points_matching_events_at_the_new_file(
    backend_db,
) -> None:
    pl = _watch(backend_db)
    store = WatchHistoryStore(backend_db.connect)
    store.record_added(pl, TRACK_A, 'old/Alpha.mp3', outcome=OUTCOME_LINKED)
    store.record_added(pl, TRACK_A, None, outcome=OUTCOME_LINKED)
    store.record_added(pl, TRACK_B, 'old/Beta.mp3', outcome=OUTCOME_LINKED)

    store.rename_file(TRACK_A, 'new/Alpha.mp3')
    store.rename_file(TRACK_A, 'new/Alpha.mp3')

    files = [
        (e['track_id'], e['filename']) for e in store.events(playlist_id=pl)
    ]
    assert files == [
        (TRACK_A, 'new/Alpha.mp3'),
        (TRACK_A, 'new/Alpha.mp3'),
        (TRACK_B, 'old/Beta.mp3'),
    ]


def test_events_filters(backend_db) -> None:
    pl = _watch(backend_db)
    other = _watch(backend_db, key='pl2', name='Other')
    store = WatchHistoryStore(backend_db.connect)
    store.record_added(pl, TRACK_A, 'a.mp3', outcome=OUTCOME_DOWNLOADED)
    store.record_added(pl, TRACK_B, 'b.mp3', outcome=OUTCOME_DOWNLOADED)
    store.record_added(other, TRACK_B, 'c.mp3', outcome=OUTCOME_LINKED)

    def ids(events):
        return [(e['watch_key'], e['track_id']) for e in events]

    assert ids(store.events()) == [
        ('pl1', TRACK_A),
        ('pl1', TRACK_B),
        ('pl2', TRACK_B),
    ]
    assert ids(store.events(playlist_id=other)) == [('pl2', TRACK_B)]
    assert ids(store.events(filename='a.mp3')) == [('pl1', TRACK_A)]
    assert ids(store.events(track_ids={TRACK_B})) == [
        ('pl1', TRACK_B),
        ('pl2', TRACK_B),
    ]
    assert ids(store.events(filename='a.mp3', track_ids={TRACK_B})) == [
        ('pl1', TRACK_A),
        ('pl1', TRACK_B),
        ('pl2', TRACK_B),
    ]
    assert store.events(track_ids={'nope'}) == []
    # The watch id wins over the other filters.
    assert ids(
        store.events(playlist_id=other, filename='a.mp3', track_ids={TRACK_A})
    ) == [('pl2', TRACK_B)]


def test_holdings_by_file_and_track(backend_db) -> None:
    pl = _watch(backend_db)
    other = _watch(backend_db, key='pl2', name='Other')
    _hold(backend_db, pl, TRACK_A, 'shared.mp3')
    _hold(backend_db, other, TRACK_A, 'shared.mp3')
    _hold(backend_db, pl, TRACK_B, 'beta.mp3')
    store = WatchHistoryStore(backend_db.connect)

    held = store.holdings('shared.mp3')
    assert sorted(
        (h['playlist_id'], h['track_spotify_id'], h['filename']) for h in held
    ) == [(pl, TRACK_A, 'shared.mp3'), (other, TRACK_A, 'shared.mp3')]
    assert store.holdings('missing.mp3') == []
    by_track = store.holdings('moved.mp3', {TRACK_B})
    assert [(h['playlist_id'], h['track_spotify_id']) for h in by_track] == [
        (pl, TRACK_B)
    ]
    assert store.holdings('moved.mp3', set()) == []


def test_record_failure_counts_attempts_and_fields(backend_db) -> None:
    pl = _watch(backend_db)
    store = WatchHistoryStore(backend_db.connect)

    store.record_failure(pl, {'song_id': '  ', 'name': 'Nothing'}, 'x')
    store.record_failure(pl, {'name': 'No id'}, 'x')
    assert store.failures(pl) == []

    store.record_failure(pl, _song(TRACK_A, 'Alpha', ('A', 'B')), 'boom')
    store.record_failure(pl, _song(TRACK_B, 'Beta', 'Solo'), 'x' * 600)
    store.record_failure(pl, _song(TRACK_A, 'Alpha again', ('A',)), 'again')

    failures = store.failures(pl)
    # Latest failure first.
    assert [f['track_id'] for f in failures] == [TRACK_A, TRACK_B]
    alpha, beta = failures
    assert (alpha['name'], alpha['artists'], alpha['error']) == (
        'Alpha again',
        'A',
        'again',
    )
    assert alpha['attempts'] == 2
    assert alpha['first_failed_at'] <= alpha['last_failed_at']
    assert (beta['artists'], beta['attempts']) == ('Solo', 1)
    assert len(beta['error']) == 500


def test_failure_counts_per_watch(backend_db) -> None:
    pl = _watch(backend_db)
    other = _watch(backend_db, key='pl2', name='Other')
    store = WatchHistoryStore(backend_db.connect)
    assert store.failure_counts() == {}

    store.record_failure(pl, _song(TRACK_A))
    store.record_failure(pl, _song(TRACK_B))
    store.record_failure(other, _song(TRACK_A))

    assert store.failure_counts() == {pl: 2, other: 1}


def test_forget_failures_except_drops_tracks_that_left(backend_db) -> None:
    pl = _watch(backend_db)
    other = _watch(backend_db, key='pl2', name='Other')
    store = WatchHistoryStore(backend_db.connect)
    store.record_failure(pl, _song(TRACK_A))
    store.record_failure(pl, _song(TRACK_B))
    store.record_failure(other, _song(TRACK_A))

    assert store.forget_failures_except(pl, {TRACK_B}) == 1
    assert [f['track_id'] for f in store.failures(pl)] == [TRACK_B]
    assert [f['track_id'] for f in store.failures(other)] == [TRACK_A]
    assert store.forget_failures_except(pl, {TRACK_B}) == 0
    assert store.forget_failures_except(pl, set()) == 1
    assert store.failures(pl) == []
    assert store.failure_counts() == {other: 1}


def test_record_added_clears_only_that_track_failure(backend_db) -> None:
    pl = _watch(backend_db)
    store = WatchHistoryStore(backend_db.connect)
    store.record_failure(pl, _song(TRACK_A))
    store.record_failure(pl, _song(TRACK_B))

    store.record_added(pl, TRACK_A, 'a.mp3', outcome=OUTCOME_DOWNLOADED)

    assert [f['track_id'] for f in store.failures(pl)] == [TRACK_B]
    assert (
        query(
            backend_db,
            'SELECT COUNT(*) FROM watch_failures WHERE playlist_id = ?',
            pl,
        )[0][0]
        == 1
    )


def test_backfill_turns_old_rows_into_unknown_events(backend_db) -> None:
    pl = _watch(backend_db, user_id=3)
    # A track from the watch's first day, and one from much later.
    _hold(
        backend_db,
        pl,
        TRACK_A,
        'Road Trip/Alpha.mp3',
        '2026-01-01T05:00:00.123456+00:00',
    )
    _hold(
        backend_db,
        pl,
        TRACK_B,
        'Road Trip/Beta.mp3',
        '2026-03-01T00:00:00+00:00',
    )

    # Opening the store on a database whose history is empty backfills it.
    store = WatchHistoryStore(backend_db.connect)
    events = store.events()

    assert [
        (e['track_id'], e['outcome'], int(e['initial']), e['user_id'])
        for e in events
    ] == [
        (TRACK_A, OUTCOME_UNKNOWN, 1, 3),
        (TRACK_B, OUTCOME_UNKNOWN, 0, 3),
    ]
    assert events[0]['filename'] == 'Road Trip/Alpha.mp3'
    assert not events[0]['provider']
    # Only once: opening the store again adds nothing.
    assert len(WatchHistoryStore(backend_db.connect).events()) == 2
