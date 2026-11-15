import time
from datetime import datetime

from ai_test_support import opted_in_store

from downtify.music_ai.playlists import PARIS
from downtify.music_ai.scheduler import refresh_due
from downtify.music_ai.store import MOODS, Store


def test_catchup_is_user_scoped_and_does_not_repeat(tmp_path):
    store = opted_in_store(tmp_path / 'derived.db')
    for owner in (1, 2):
        store.ensure_user(owner)

    def rows(prefix, start, count):
        genres = ('rap', 'rock', 'electro', 'Pop')
        return [
            {
                'id': f'{prefix}-{i}',
                'artist': f'{prefix}-{i}',
                'genre': genres[i % len(genres)],
                'fingerprint': f'{prefix}-{i}',
            }
            for i in range(start, start + count)
        ]

    catalog = rows('u', 0, 60) + rows('v', 0, 60)
    store.observe([{**row, 'id': row['id']} for row in catalog])
    for row in catalog:
        store.put_analysis(row['id'], row['fingerprint'], 'm', [1] + [0] * 511)
    with store.connect() as db:
        for mood in MOODS:
            db.execute(
                'INSERT INTO mood_vectors VALUES (?,?,?)',
                (mood, 'm', Store.pack([1] + [0] * 511)),
            )
    store.set_preferences(2, {'daily': False})
    calls = []

    def visible(owner):
        calls.append(owner)
        return rows('u', 0, 60) if owner == 1 else rows('v', 0, 60)

    now = datetime(2026, 11, 5, 13, tzinfo=PARIS)
    assert refresh_due(store, 'm', lambda uid: True, visible, now=now) == 26
    assert sorted(calls) == [1, 2]
    calls.clear()
    assert refresh_due(store, 'm', lambda uid: True, visible, now=now) == 0
    assert not calls
    with store.connect() as db:
        assert (
            db.execute(
                "SELECT count(*) FROM playlists WHERE owner=2 AND cadence='daily'"
            ).fetchone()[0]
            == 0
        )


def test_initial_partial_analysis_is_not_frozen_as_empty(tmp_path):
    store = opted_in_store(tmp_path / 'derived.db')
    store.ensure_user(1)
    rows = [
        {'id': str(i), 'artist': str(i), 'fingerprint': str(i)}
        for i in range(60)
    ]
    store.observe(rows)
    store.put_analysis('0', '0', 'm', [1] + [0] * 511)
    with store.connect() as db:
        for mood in MOODS:
            db.execute(
                'INSERT INTO mood_vectors VALUES (?,?,?)',
                (mood, 'm', Store.pack([1] + [0] * 511)),
            )
    assert refresh_due(store, 'm', lambda uid: True, lambda uid: rows) == 0
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM playlists').fetchone()[0] == 0


def test_generation_yields_before_ranking_when_dj_requests_compute(tmp_path):
    store = opted_in_store(tmp_path / 'derived.db')
    assert (
        refresh_due(
            store,
            'm',
            lambda uid: True,
            lambda uid: [{'id': 'one'}],
            checkpoint=lambda: False,
        )
        == 0
    )
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM playlists').fetchone()[0] == 0


def _sweep(tmp_path, monkeypatch, lease_kind=None):
    from types import SimpleNamespace

    from downtify import api
    from downtify.music_ai import routes

    database = opted_in_store(tmp_path / 'derived.db')
    database.set_metadata('model', {'id': 'm', 'ready': True})
    rows = [
        {'id': str(i), 'artist': str(i), 'fingerprint': str(i)}
        for i in range(60)
    ]
    database.observe(rows)
    for row in rows:
        database.put_analysis(
            row['id'], row['fingerprint'], 'm', [1] + [0] * 511
        )
    with database.connect() as db:
        for mood in MOODS:
            db.execute(
                'INSERT INTO mood_vectors VALUES (?,?,?)',
                (mood, 'm', Store.pack([1] + [0] * 511)),
            )
        if lease_kind is not None:
            db.execute(
                'INSERT OR REPLACE INTO compute_lease VALUES (1,?,?,?)',
                ('token', lease_kind, time.time() + 45),
            )
    monkeypatch.setattr(routes, 'store', lambda: database)
    monkeypatch.setattr(
        api.state,
        'auth',
        SimpleNamespace(
            users=SimpleNamespace(
                get=lambda uid: {'role': 'admin', 'username': 'x'}
            )
        ),
    )
    return database, rows


def test_native_sweep_does_not_read_catalog_for_a_dj_request(
    tmp_path, monkeypatch
):
    from downtify.music_ai import routes, scheduler

    database, _ = _sweep(tmp_path, monkeypatch, lease_kind='dj')
    monkeypatch.setattr(
        routes,
        'catalog',
        lambda *args: (_ for _ in ()).throw(
            AssertionError('No catalog read while DJ owns compute')
        ),
    )
    scheduler.native_sweep()
    with database.connect() as db:
        assert db.execute('SELECT count(*) FROM playlists').fetchone()[0] == 0


def test_native_sweep_generates_while_analysis_holds_the_lease(
    tmp_path, monkeypatch
):
    from downtify.music_ai import routes, scheduler

    database, rows = _sweep(tmp_path, monkeypatch, lease_kind='analysis')
    monkeypatch.setattr(routes, 'catalog', lambda *args: rows)
    scheduler.native_sweep()
    with database.connect() as db:
        assert db.execute('SELECT count(*) FROM playlists').fetchone()[0] == 24
