"""LibraryTrash's journal on both backends: the same results on SQLite and
PostgreSQL. Files are real files under ``tmp_path``; the rename that needs
Linux (``renameat2``) is replaced by a plain rename, so the journal logic
runs the same way on macOS."""

from __future__ import annotations

import json
import os

import pytest

from downtify import library_trash
from downtify.db.config import Dialect
from downtify.library_trash import (
    RETENTION_SECONDS,
    LibraryTrash,
    TrashError,
    TrashRoot,
    trash_from_config,
    trash_from_env,
)

AUDIO = b'audio-one'
LYRICS = b'[00:00.00]la'
SIZE = len(AUDIO) + len(LYRICS)
META = {
    'spotify_id': 'sp-1',
    'title': 'Track',
    'artist': 'Artist',
    'album': 'Album',
}


class Clock:
    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


@pytest.fixture(autouse=True)
def plain_rename(monkeypatch):
    monkeypatch.setattr(
        library_trash,
        '_rename_no_replace',
        os.rename,
    )


@pytest.fixture
def music(tmp_path):
    root = tmp_path / 'music'
    (root / 'Artist').mkdir(parents=True)
    (root / 'Artist' / 'track.flac').write_bytes(AUDIO)
    (root / 'Artist' / 'track.lrc').write_bytes(LYRICS)
    return root


def _track(relative='Artist/track.flac', spotify='sp-1', track_id='t-1'):
    return {
        'root_key': 'music',
        'relative': relative,
        'stored': relative,
        'track_id': track_id,
        'metadata': {**META, 'spotify_id': spotify},
    }


def _store(db, music, clock=None):
    return LibraryTrash(
        db, {'music': TrashRoot(music)}, clock=clock or Clock()
    )


def _trash_one(store, track=None) -> str:
    """Preview, confirm and move one track; return its operation id."""
    preview = store.preview(1, [track or _track()])
    store.confirm(1, preview['confirmation'])
    [result] = store.process(authorized=lambda uid: True)
    assert result == {'id': preview['items'][0]['id'], 'ok': True}
    return result['id']


def test_constructor_takes_a_path_or_a_database(backend_db, tmp_path, music):
    store = _store(backend_db, music)
    assert store.db is backend_db
    assert store.revision() == 0
    assert store.exclusions() == []
    if backend_db.dialect is Dialect.SQLITE:
        assert store._path == backend_db.path
    else:
        assert store._path is None

    # Seeding the revision row again must not change it.
    _store(backend_db, music)
    assert store.revision() == 0

    by_path = LibraryTrash(
        tmp_path / 'nested' / 'library.db', {'music': TrashRoot(music)}
    )
    assert by_path.db.dialect is Dialect.SQLITE
    assert by_path._path == tmp_path / 'nested' / 'library.db'
    assert by_path.revision() == 0


def test_unknown_worker_mode_is_refused(backend_db, music):
    with pytest.raises(TrashError, match='unsupported_configuration'):
        LibraryTrash(backend_db, {'music': TrashRoot(music)}, worker='x')


def test_preview_then_confirm_then_process_trashes_the_track(
    backend_db, music
):
    store = _store(backend_db, music)

    preview = store.preview(1, [_track()])
    batch = preview['confirmation']
    (item,) = preview['items']
    assert item['state'] == 'preview'
    assert item['file'] == 'Artist/track.flac'
    assert item['size'] == SIZE
    assert item['metadata']['spotify_id'] == 'sp-1'
    # Previews are not part of the list yet.
    assert store.list()['total'] == 0
    assert store.confirmation_files(1, batch) == ['Artist/track.flac']
    assert store.confirmation_files(2, batch) == []

    assert store.confirm(1, batch) == [item['id']]
    assert store.revision() == 1
    # A repeat of a confirmed batch changes nothing.
    assert store.confirm(1, batch) == [item['id']]
    assert store.revision() == 1
    assert store.blocked(META) is True
    assert store.blocked({'spotify_id': 'other'}) is False
    assert store.hidden_paths() == frozenset({'Artist/track.flac'})
    assert str(music / 'Artist' / 'track.flac') in store.hidden_resolved()
    assert store.has_work() is True
    assert store.work_files() == {item['id']: 'Artist/track.flac'}

    assert store.process(authorized=lambda uid: True) == [
        {'id': item['id'], 'ok': True}
    ]
    assert not (music / 'Artist' / 'track.flac').exists()
    assert not (music / 'Artist' / 'track.lrc').exists()
    assert store.has_work() is False
    assert store.work_files() == {}

    listed = store.list()
    assert listed['total'] == 1
    assert listed['size'] == SIZE
    assert [row['state'] for row in listed['items']] == ['trashed']
    assert store.list(search='TRACK')['total'] == 1
    assert store.list(search='nothing')['total'] == 0
    assert store.list(offset=1)['items'] == []
    # Trashed, not purged: still hidden, not yet an exclusion.
    assert store.exclusions() == []
    assert store.hidden_paths() == frozenset({'Artist/track.flac'})


def test_preview_refuses_bad_selections(backend_db, music):
    store = _store(backend_db, music)

    with pytest.raises(TrashError, match='invalid_selection'):
        store.preview(0, [_track()])
    with pytest.raises(TrashError, match='invalid_selection'):
        store.preview(1, [])
    with pytest.raises(TrashError, match='invalid_path'):
        store.preview(1, [_track(relative='../escape.flac')])
    no_identity = {**_track(), 'metadata': {}}
    with pytest.raises(TrashError, match='identity_uncertain'):
        store.preview(1, [no_identity])
    assert store.list()['total'] == 0


def test_confirm_refuses_changed_files_and_pending_duplicates(
    backend_db, music
):
    store = _store(backend_db, music)
    with pytest.raises(TrashError, match='confirmation_invalid'):
        store.confirm(1, 'no-such-batch')

    changed = store.preview(1, [_track()])
    (music / 'Artist' / 'track.flac').write_bytes(b'edited after preview')
    with pytest.raises(TrashError, match='file_changed'):
        store.confirm(1, changed['confirmation'])

    (music / 'Artist' / 'track.flac').write_bytes(AUDIO)
    first = store.preview(1, [_track()])
    second = store.preview(1, [_track(track_id='t-2')])
    store.confirm(1, first['confirmation'])
    with pytest.raises(TrashError, match='operation_already_pending'):
        store.confirm(1, second['confirmation'])


def test_restore_brings_the_track_back_and_unblocks_it(backend_db, music):
    store = _store(backend_db, music)
    item = _trash_one(store)
    before = store.revision()

    store.request_restore([item], user_id=7)
    store.request_restore([item], user_id=7)  # a second request is a no-op
    with pytest.raises(TrashError, match='item_not_found'):
        store.request_restore(['no-such-item'], user_id=7)
    with pytest.raises(TrashError, match='invalid_selection'):
        store.request_restore([], user_id=7)
    (row,) = store.list()['items']
    assert row['state'] == 'restore_pending'

    assert store.process(authorized=lambda uid: uid == 7) == [
        {'id': item, 'ok': True}
    ]
    assert (music / 'Artist' / 'track.flac').read_bytes() == AUDIO
    assert (music / 'Artist' / 'track.lrc').read_bytes() == LYRICS
    assert store.blocked(META) is False
    assert store.hidden_paths() == frozenset()
    assert store.revision() > before
    assert store.list()['total'] == 0
    # A restored item can be requested again without error.
    store.request_restore([item], user_id=7)


def test_failed_restore_is_an_error_that_retry_puts_back(backend_db, music):
    store = _store(backend_db, music)
    item = _trash_one(store)
    store.request_restore([item], user_id=7)

    assert store.process(authorized=lambda uid: False) == [
        {'id': item, 'ok': False, 'error': 'admin_access_revoked'}
    ]
    (row,) = store.list()['items']
    assert row['state'] == 'error'
    assert row['error'] == 'admin_access_revoked'
    assert not (music / 'Artist' / 'track.flac').exists()

    with pytest.raises(TrashError, match='invalid_selection'):
        store.retry([], user_id=9)
    store.retry([item], user_id=9)
    (row,) = store.list()['items']
    assert row['state'] == 'restore_pending'
    with pytest.raises(TrashError, match='operation_not_complete'):
        store.retry([item], user_id=9)

    store.process(authorized=lambda uid: True)
    assert (music / 'Artist' / 'track.flac').read_bytes() == AUDIO
    assert store.list()['total'] == 0


def test_allow_download_releases_the_block(backend_db, music):
    store = _store(backend_db, music)
    preview = store.preview(1, [_track()])
    with pytest.raises(TrashError, match='operation_not_complete'):
        store.allow_download([preview['items'][0]['id']])
    with pytest.raises(TrashError, match='invalid_selection'):
        store.allow_download([])
    store.confirm(1, preview['confirmation'])
    store.process(authorized=lambda uid: True)
    assert store.blocked(META) is True

    store.allow_download([preview['items'][0]['id']])
    assert store.blocked(META) is False
    assert store.hidden_paths() == frozenset()


def test_expired_track_is_purged_and_stays_excluded(backend_db, music):
    clock = Clock()
    store = _store(backend_db, music, clock)
    item = _trash_one(store)
    assert store.has_work() is False

    clock.now += RETENTION_SECONDS + 1
    assert store.has_work() is True
    assert store.process(authorized=lambda uid: True) == [
        {'id': item, 'ok': True}
    ]

    (excluded,) = store.exclusions()
    assert excluded['id'] == item
    assert excluded['state'] == 'purged'
    assert store.list()['total'] == 0
    assert store.blocked(META) is True
    assert list((music / '.downtify-trash').rglob('*.flac')) == []
    with pytest.raises(TrashError, match='retention_expired'):
        store.request_restore([item], user_id=7)


def test_worker_skips_ids_and_honours_the_limit(backend_db, music):
    (music / 'Artist' / 'two.flac').write_bytes(b'second track')
    store = _store(backend_db, music)
    preview = store.preview(
        1,
        [
            _track(),
            _track(relative='Artist/two.flac', spotify='sp-2', track_id='t-2'),
        ],
    )
    first, second = (row['id'] for row in preview['items'])
    store.confirm(1, preview['confirmation'])

    assert store.process(
        limit=5,
        authorized=lambda uid: True,
        skip_ids=frozenset({first}),
    ) == [{'id': second, 'ok': True}]
    assert store.process(limit=1, authorized=lambda uid: True) == [
        {'id': first, 'ok': True}
    ]
    assert store.process(authorized=lambda uid: True) == []


def test_config_and_environment_accept_a_database(backend_db, music, tmp_path):
    config = tmp_path / 'trash.json'
    config.write_text(
        json.dumps({
            'version': 1,
            'roots': {'music': {'path': str(music)}},
        }),
        encoding='utf-8',
    )
    from_config = trash_from_config(config, backend_db)
    assert from_config.db is backend_db
    assert from_config.worker == 'embedded'

    from_env = trash_from_env(music, backend_db, env={'DOWNTIFY_TRASH': 'on'})
    assert from_env is not None
    assert from_env.db is backend_db
    assert trash_from_env(music, backend_db, env={}) is None
