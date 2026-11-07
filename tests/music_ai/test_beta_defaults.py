import json
import sqlite3

from downtify.music_ai.store import DEFAULTS, Store


def test_fresh_install_and_new_accounts_have_every_beta_module_off(tmp_path):
    store = Store(tmp_path / 'derived.db')
    store.ensure_user(1)
    assert not any(DEFAULTS.values())
    assert not any(store.preferences(-1).values())
    assert not any(store.preferences(1).values())
    assert not any(store.effective(1).values())
    assert not store.listen(1, 'not-collected', 'one', 10, 'pause')


def test_existing_partial_preferences_keep_their_effective_values(tmp_path):
    path = tmp_path / 'derived.db'
    with sqlite3.connect(path) as db:
        db.execute(
            'CREATE TABLE preferences(owner INTEGER PRIMARY KEY,value TEXT NOT NULL)'
        )
        db.execute(
            'INSERT INTO preferences VALUES (1,?)',
            (json.dumps({'weekly': False}),),
        )
    store = Store(path)
    expected = {
        **DEFAULTS,
        'personalization': True,
        'similarity': True,
        'daily': True,
    }
    assert store.effective(1) == expected
    store.set_preferences(1, {'daily': False})
    reopened = Store(path)
    assert not reopened.effective(1)['daily']
    assert reopened.effective(1)['similarity']
    reopened.ensure_user(2)
    assert not any(reopened.effective(2).values())


def test_explicit_admin_disable_survives_the_migration(tmp_path):
    path = tmp_path / 'derived.db'
    with sqlite3.connect(path) as db:
        db.execute(
            'CREATE TABLE preferences(owner INTEGER PRIMARY KEY,value TEXT NOT NULL)'
        )
        db.executemany(
            'INSERT INTO preferences VALUES (?,?)',
            [
                (-1, json.dumps({'daily': False})),
                (1, json.dumps({'daily': True})),
            ],
        )
    store = Store(path)
    assert not store.effective(1)['daily']
    assert store.preferences(1)['daily']
