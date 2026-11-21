"""ExternalPlaylistImports on both backends (SQLite file, migrated PostgreSQL)."""

from __future__ import annotations

import pytest

from downtify.db.config import Dialect
from downtify.external_playlists import (
    ExternalPlaylistImports,
    discover_external_playlists,
    read_external_playlist,
)
from downtify.library_catalog import LibraryContext
from tests.db.helpers import execute, query


@pytest.fixture
def collection(tmp_path):
    downloads = tmp_path / 'downloads'
    external = tmp_path / 'external'
    downloads.mkdir()
    external.mkdir()
    for name in ('one.mp3', 'two.flac'):
        (external / name).write_bytes(b'audio fixture')
    ctx = LibraryContext(download_dir=downloads, extra_dirs=(external,))
    return ctx, external


def _seed(db, user_id, source_id, name, revision='rev'):
    execute(
        db,
        'INSERT INTO external_playlist_imports VALUES (?, ?, ?, ?)',
        user_id,
        source_id,
        name,
        revision,
    )


def _rows(db):
    return [
        tuple(row)
        for row in query(
            db,
            'SELECT user_id, source_id, playlist_name, revision '
            'FROM external_playlist_imports ORDER BY user_id, source_id',
        )
    ]


def test_imported_rename_and_forget(backend_db):
    store = ExternalPlaylistImports(backend_db)
    assert store.imported(7) == {}

    _seed(backend_db, 7, 'src-a', 'Mix')
    _seed(backend_db, 7, 'src-b', 'Other')
    _seed(backend_db, 8, 'src-a', 'Mix (2)')

    assert store.imported(7) == {'src-a': 'Mix', 'src-b': 'Other'}
    assert store.imported(8) == {'src-a': 'Mix (2)'}
    assert all(isinstance(v, str) for v in store.imported(7).values())

    store.rename('Mix', 'Renamed')
    assert store.imported(7) == {'src-a': 'Renamed', 'src-b': 'Other'}
    assert store.imported(8) == {'src-a': 'Mix (2)'}

    store.forget('Renamed')
    assert store.imported(7) == {'src-b': 'Other'}
    store.forget('missing')
    assert store.imported(8) == {'src-a': 'Mix (2)'}


def test_construct_from_path_or_database_shares_the_table(
    backend_db, tmp_path
):
    store = ExternalPlaylistImports(backend_db)
    _seed(backend_db, 3, 'src-x', 'Shared')
    assert store.imported(3) == {'src-x': 'Shared'}
    assert store.lock is not None
    if backend_db.dialect is Dialect.SQLITE:
        assert store.path == str(backend_db.path)
        assert ExternalPlaylistImports(backend_db.path).imported(3) == {
            'src-x': 'Shared'
        }


def test_snapshot_import_is_idempotent_and_per_account(
    backend_db, collection, tmp_path
):
    ctx, root = collection
    source = root / 'Mix.m3u'
    source.write_text('#EXTM3U\none.mp3\ntwo.flac\n')
    found, warnings, truncated = discover_external_playlists(ctx)
    assert not warnings
    assert not truncated
    item = next(c for c in found if c.name == 'Mix')

    store = ExternalPlaylistImports(backend_db)
    result = store.import_snapshot(ctx, 7, item, list(item.files))
    assert result['status'] == 'added'
    assert result['files'] == list(item.files)
    assert store.imported(7) == {item.source_id: result['name']}
    again = store.import_snapshot(ctx, 7, item, list(item.files))
    assert again['status'] == 'already_present'
    assert again['name'] == result['name']

    other = store.import_snapshot(ctx, 8, item, list(item.files))
    assert other['name'] != result['name']
    assert store.imported(8) == {item.source_id: other['name']}
    assert len(_rows(backend_db)) == 2


def test_read_external_playlist_is_backend_independent(collection):
    ctx, root = collection
    source = root / 'Mix.m3u'
    source.write_text('one.mp3\none.mp3\n')
    item = read_external_playlist(source, root, ctx)
    assert item.name == 'Mix'
    assert item.duplicates == 1
    assert len(item.files) == 1
