"""The music trash's simple switch, its embedded worker, and recovery."""

import ctypes
import json
import platform
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from downtify import api, library_trash, trash_routes
from downtify.download_policy import DownloadPolicyBlocked
from downtify.downloader import Downloader
from downtify.library_trash import (
    TRASH_DIR,
    LibraryTrash,
    TrashError,
    TrashRoot,
    trash_from_config,
    trash_from_env,
)

TRACK = {
    'stored': 'Artist/track.flac',
    'root_key': 'music',
    'relative': 'Artist/track.flac',
    'track_id': 'stable-id',
    'metadata': {'title': 'Track', 'artist': 'Artist', 'album': 'Album'},
}


@pytest.fixture
def music(tmp_path):
    root = tmp_path / 'music'
    audio = root / 'Artist' / 'track.flac'
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b'original audio')
    return root


def _confirm(store: LibraryTrash, track=TRACK) -> str:
    preview = store.preview(1, [track])
    store.confirm(1, preview['confirmation'])
    return preview['items'][0]['id']


def _admin(user_id: int) -> bool:
    return user_id == 1


# Turning it on


def test_nothing_set_leaves_the_trash_off(tmp_path):
    assert trash_from_env(tmp_path, tmp_path / 'library.db', env={}) is None
    assert (
        trash_from_env(
            tmp_path, tmp_path / 'library.db', env={'DOWNTIFY_TRASH': 'no'}
        )
        is None
    )


def test_switch_covers_the_download_folder_with_the_embedded_worker(
    tmp_path,
):
    store = trash_from_env(
        tmp_path, tmp_path / 'library.db', env={'DOWNTIFY_TRASH': 'true'}
    )
    assert store is not None
    assert store.worker == 'embedded'
    assert list(store.roots) == ['downloads']
    assert store.roots['downloads'].path == tmp_path.absolute()


def test_configuration_file_wins_and_names_the_worker(tmp_path, music):
    config = tmp_path / 'trash.json'
    config.write_text(
        json.dumps({
            'version': 1,
            'worker': 'external',
            'roots': {'music': {'path': str(music)}},
        })
    )
    store = trash_from_env(
        tmp_path,
        tmp_path / 'library.db',
        env={'DOWNTIFY_TRASH_CONFIG': str(config), 'DOWNTIFY_TRASH': '1'},
    )
    assert store.worker == 'external'
    assert list(store.roots) == ['music']


@pytest.mark.parametrize(
    'config',
    [
        {'version': 1, 'worker': 'cron', 'roots': {'m': {'path': '/m'}}},
        {'version': 1, 'roots': {}},
        {'version': 1, 'roots': {'m': {'path': 'relative'}}},
        {'version': 2, 'roots': {'m': {'path': '/m'}}},
    ],
)
def test_unusable_configuration_is_refused(tmp_path, config):
    path = tmp_path / 'trash.json'
    path.write_text(json.dumps(config))
    with pytest.raises(TrashError):
        trash_from_config(path, tmp_path / 'library.db')


# Recovery


def test_a_move_stopped_before_anything_moved_can_be_restored(music):
    store = LibraryTrash(
        music.parent / 'library.db', {'music': TrashRoot(music)}
    )
    item = _confirm(store)
    audio = music / 'Artist' / 'track.flac'
    # Retagged between the confirmation and the worker: the move stops.
    audio.write_bytes(b'retagged audio')
    [result] = store.process(authorized=_admin)
    assert result == {'id': item, 'ok': False, 'error': 'file_changed'}
    assert 'Artist/track.flac' in store.hidden_paths()

    store.request_restore([item], user_id=1)
    [result] = store.process(authorized=_admin)
    assert result['ok']
    assert audio.read_bytes() == b'retagged audio'
    assert store.hidden_paths() == frozenset()
    assert not store.blocked(TRACK['metadata'])


def test_root_below_a_linked_folder_moves_and_restores(tmp_path, music):
    link = tmp_path / 'linked'
    link.symlink_to(tmp_path)
    store = LibraryTrash(
        tmp_path / 'library.db', {'music': TrashRoot(link / 'music')}
    )
    item = _confirm(store)
    assert str((music / 'Artist' / 'track.flac').resolve()) in (
        store.hidden_resolved()
    )
    assert store.process(authorized=_admin)[0]['ok']
    assert not (music / 'Artist' / 'track.flac').exists()
    assert any((music / TRASH_DIR / item).iterdir())

    store.request_restore([item], user_id=1)
    assert store.process(authorized=_admin)[0]['ok']
    assert (music / 'Artist' / 'track.flac').read_bytes() == b'original audio'


def test_hidden_paths_follow_a_separate_worker(music, monkeypatch):
    db = music.parent / 'library.db'
    app = LibraryTrash(db, {'music': TrashRoot(music)})
    worker = LibraryTrash(db, {'music': TrashRoot(music)})
    item = _confirm(app)
    assert 'Artist/track.flac' in app.hidden_paths()
    assert worker.process(authorized=_admin)[0]['ok']
    worker.request_restore([item], user_id=1)
    assert worker.process(authorized=_admin)[0]['ok']

    # Trusted for a moment, then read again.
    assert 'Artist/track.flac' in app.hidden_paths()
    monkeypatch.setattr(library_trash, 'HIDDEN_RECHECK_SECONDS', 0)
    assert app.hidden_paths() == frozenset()


# The embedded worker


@pytest.fixture
def app_state(monkeypatch):
    state = SimpleNamespace(
        auth=SimpleNamespace(
            users=SimpleNamespace(
                get=lambda uid: {'role': 'admin' if uid == 1 else 'user'}
            )
        ),
        now_playing=SimpleNamespace(active=list),
        upgrade_runner=None,
    )
    monkeypatch.setattr(api, 'state', state)
    return state


def test_embedded_worker_moves_what_was_confirmed(music, app_state):
    store = LibraryTrash(
        music.parent / 'library.db', {'music': TrashRoot(music)}
    )
    assert trash_routes.run_worker_pass(store) == []
    item = _confirm(store)
    assert store.has_work()
    [done] = trash_routes.run_worker_pass(store)
    assert done == {'id': item, 'ok': True}
    assert not (music / 'Artist' / 'track.flac').exists()
    assert not store.has_work()


def test_embedded_worker_holds_back_a_song_that_is_playing(music, app_state):
    store = LibraryTrash(
        music.parent / 'library.db', {'music': TrashRoot(music)}
    )
    _confirm(store)
    app_state.now_playing.active = lambda: [
        {'track': {'file': 'Artist/track.flac'}, 'paused': False}
    ]
    assert trash_routes.run_worker_pass(store) == []
    assert (music / 'Artist' / 'track.flac').exists()
    app_state.now_playing.active = list
    assert trash_routes.run_worker_pass(store)[0]['ok']


def test_embedded_worker_waits_for_the_library_upgrade(music, app_state):
    store = LibraryTrash(
        music.parent / 'library.db', {'music': TrashRoot(music)}
    )
    _confirm(store)
    app_state.upgrade_runner = SimpleNamespace(
        status=lambda: {'state': 'running'}
    )
    assert trash_routes.run_worker_pass(store) == []
    assert (music / 'Artist' / 'track.flac').exists()


def test_embedded_worker_rechecks_the_admin(music, app_state):
    store = LibraryTrash(
        music.parent / 'library.db', {'music': TrashRoot(music)}
    )
    item = _confirm(store)
    app_state.auth.users.get = lambda uid: {'role': 'user'}
    [done] = trash_routes.run_worker_pass(store)
    assert done == {'id': item, 'ok': False, 'error': 'admin_access_revoked'}
    assert (music / 'Artist' / 'track.flac').exists()


def test_external_worker_mode_leaves_files_alone(music, app_state):
    store = LibraryTrash(
        music.parent / 'library.db',
        {'music': TrashRoot(music)},
        worker='external',
    )
    _confirm(store)
    assert trash_routes.run_worker_pass(store) == []
    assert (music / 'Artist' / 'track.flac').exists()


# Downloads


def test_trashed_song_is_an_exclusion_not_a_failed_attempt():
    downloader = Downloader.__new__(Downloader)
    downloader.trash_store = SimpleNamespace(blocked=lambda song: True)
    with pytest.raises(DownloadPolicyBlocked, match='library_trash_excluded'):
        downloader._download({'name': 'Track'}, None, None)


def test_unknown_worker_mode_is_refused(tmp_path):
    with pytest.raises(TrashError):
        LibraryTrash(tmp_path / 'library.db', {}, worker='cron')


def test_root_path_is_absolute_in_the_simple_switch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = trash_from_env(
        Path('downloads'), tmp_path / 'library.db', env={'DOWNTIFY_TRASH': '1'}
    )
    assert store.roots['downloads'].path.is_absolute()


def test_capabilities_never_offer_a_trash_that_is_off(monkeypatch):
    monkeypatch.setattr(api, 'state', SimpleNamespace(library_trash=None))
    monkeypatch.setattr(trash_routes, 'admin_user', lambda request: 1)
    assert trash_routes.capabilities(None) == {
        'can_manage': False,
        'enabled': False,
        'retention_days': 30,
    }


@pytest.mark.skipif(
    sys.platform != 'linux'
    or platform.machine().lower() not in library_trash._RENAMEAT2_SYSCALL,
    reason='renameat2 syscall number known on Linux only',
)
def test_no_replace_rename_works_without_the_libc_wrapper(tmp_path):
    # musl before 1.2.5 (Alpine images) has no renameat2(): use the syscall.
    (tmp_path / 'a').write_text('a')
    (tmp_path / 'b').write_text('b')
    real = ctypes.CDLL

    class WithoutWrapper:
        def __init__(self, *args, **kwargs):
            self._lib = real(*args, **kwargs)

        def __getattr__(self, name):
            if name == 'renameat2':
                raise AttributeError(name)
            return getattr(self._lib, name)

    with patch.object(library_trash.ctypes, 'CDLL', WithoutWrapper):
        with pytest.raises(TrashError, match='restore_collision'):
            library_trash._rename_no_replace(tmp_path / 'a', tmp_path / 'b')
        library_trash._rename_no_replace(tmp_path / 'a', tmp_path / 'c')
    assert (tmp_path / 'b').read_text() == 'b'
    assert (tmp_path / 'c').read_text() == 'a'
    assert not (tmp_path / 'a').exists()
