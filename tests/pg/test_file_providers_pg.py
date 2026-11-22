"""FileProviders on both backends (SQLite file, migrated PostgreSQL)."""

from __future__ import annotations

from downtify.file_providers import (
    FOLDER,
    FileProviders,
    guess_provider,
    providers_for,
)
from tests.db.helpers import execute, query


def _rows(db) -> list[tuple]:
    return [
        tuple(row)
        for row in query(
            db,
            'SELECT content_key, path, provider, source '
            'FROM file_providers ORDER BY content_key',
        )
    ]


def test_record_and_lookup_by_key_then_path(backend_db):
    store = FileProviders(backend_db)
    store.record('k1', 'Artist/A.mp3', 'youtube', source='')
    store.record('k2', 'Artist/B.mp3', 'slskd', source='/slskd/B.mp3')

    assert store.lookup({'Artist/A.mp3': 'k1'}) == {'Artist/A.mp3': 'youtube'}
    # Moved file: the content key still finds it.
    assert store.lookup({'Moved/A.mp3': 'k1'}) == {'Moved/A.mp3': 'youtube'}
    # Rewritten in place with a new key: the path still finds it.
    assert store.lookup({'Artist/B.mp3': 'other'}) == {'Artist/B.mp3': 'slskd'}
    assert store.lookup({'Nothing.mp3': 'zz'}) == {}


def test_record_replaces_latest_and_ignores_blank_input(backend_db):
    store = FileProviders(backend_db)
    store.record('k1', 'A.mp3', 'youtube')
    store.record('k1', ' B\\C.mp3 ', 'deemix', source='/x/y.mp3')
    store.record('', 'D.mp3', 'youtube')
    store.record('k3', 'E.mp3', '')

    assert _rows(backend_db) == [('k1', 'B/C.mp3', 'deemix', '/x/y.mp3')]


def test_recorded_returns_provider_and_time(backend_db):
    store = FileProviders(backend_db)
    store.record('k1', 'A.mp3', 'youtube')

    found = store.recorded({'A.mp3': 'k1', 'missing.mp3': 'nope', '': 'k1'})

    assert set(found) == {'A.mp3'}
    assert found['A.mp3']['provider'] == 'youtube'
    assert found['A.mp3']['recorded_at']
    assert store.recorded({}) == {}


def test_recorded_chunks_large_lookups(backend_db):
    store = FileProviders(backend_db)
    keys = {f'Music/{i}.mp3': f'key{i}' for i in range(900)}
    for i in range(900):
        store.record(f'key{i}', f'Music/{i}.mp3', 'youtube')

    assert len(store.lookup(keys)) == 900


def test_sources_lists_copied_transfers(backend_db):
    store = FileProviders(backend_db)
    assert store.sources() == []
    store.record('k1', 'A.mp3', 'slskd', source='/slskd/A.mp3')
    store.record('k2', 'B.mp3', 'slskd', source='/slskd/A.mp3')
    store.record('k3', 'C.mp3', 'youtube')

    assert store.sources() == ['/slskd/A.mp3']


def test_rekey_moves_row_and_replaces_existing_target(backend_db):
    store = FileProviders(backend_db)
    store.record('old', 'A.mp3', 'youtube')
    store.record('new', 'Stale.mp3', 'deemix')

    assert store.rekey('old', 'new', 'Renamed.mp3') == 1

    assert _rows(backend_db) == [('new', 'Renamed.mp3', 'youtube', '')]


def test_rekey_keeps_path_when_none_given_and_ignores_noops(backend_db):
    store = FileProviders(backend_db)
    store.record('old', 'A.mp3', 'youtube')

    assert store.rekey('old', 'old') == 0
    assert store.rekey('', 'x') == 0
    assert store.rekey('missing', 'x') == 0
    # The existing row under the new key must survive a no-match rekey.
    store.record('keep', 'K.mp3', 'slskd')
    assert store.rekey('missing', 'keep') == 0
    assert store.rekey('old', 'keep') == 1
    assert _rows(backend_db) == [('keep', 'A.mp3', 'youtube', '')]


def test_drop_forgets_file(backend_db):
    store = FileProviders(backend_db)
    store.record('k1', 'A.mp3', 'youtube')
    store.drop('')
    store.drop('k1')

    assert _rows(backend_db) == []


def test_providers_for_falls_back_to_path_guess(backend_db):
    store = FileProviders(backend_db)
    store.record('k1', 'Rec.mp3', 'deemix')

    found = providers_for(
        store,
        {'Rec.mp3': 'k1', 'slskd/x.mp3': 'z', 'ext/y.mp3': 'w', 'n.mp3': 'q'},
    )

    assert found == {
        'Rec.mp3': 'deemix',
        'slskd/x.mp3': 'slskd',
        'ext/y.mp3': FOLDER,
    }
    assert providers_for(None, {'n.mp3': 'q'}) == {}
    assert not guess_provider('n.mp3')


def test_existing_source_column_is_not_duplicated(backend_db):
    FileProviders(backend_db)
    FileProviders(backend_db)
    execute(
        backend_db,
        'INSERT INTO file_providers (content_key, path, provider, '
        "recorded_at, source) VALUES ('z', 'Z.mp3', 'youtube', 'now', '')",
    )

    assert query(backend_db, 'SELECT count(*) FROM file_providers')[0][0] == 1
