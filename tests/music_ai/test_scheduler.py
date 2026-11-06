from datetime import datetime

from ai_test_support import opted_in_store

from downtify.music_ai.playlists import PARIS
from downtify.music_ai.scheduler import refresh_due
from downtify.music_ai.store import MOODS, Store


def test_catchup_is_user_scoped_and_does_not_repeat(tmp_path):
    store = opted_in_store(tmp_path / 'derived.db')
    for owner in (1, 2):
        store.ensure_user(owner)
    rows = [
        {'id': str(i), 'artist': str(i), 'fingerprint': str(i)}
        for i in range(60)
    ]
    store.observe(rows)
    for row in rows:
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
        return rows[:50] if owner == 1 else rows[50:]

    now = datetime(2026, 11, 5, 13, tzinfo=PARIS)
    assert refresh_due(store, 'm', lambda uid: True, visible, now=now) == 18
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
