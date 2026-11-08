import asyncio
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from downtify import api, trash_routes
from downtify.auth import Principal
from downtify.deemix_upgrade_store import AudioReplacementStore
from downtify.library_catalog import (
    LibraryContext,
    _walk_audio_files,
    resolve_library_file,
)
from downtify.library_sync import LibrarySync
from downtify.library_trash import TRASH_DIR, LibraryTrash, TrashRoot
from downtify.monitor import PlaylistMonitorDB


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'music'
        self.root.mkdir()
        self.audio = self.root / 'song.flac'
        self.audio.write_bytes(b'synthetic audio')
        db = Path(self.temp.name) / 'library.db'
        self.store = LibraryTrash(db, {'music': TrashRoot(self.root)})
        AudioReplacementStore(db)
        self.sync = LibrarySync(db)
        self.entry = {
            'file': 'song.flac',
            'title': 'Song',
            'artist': 'Artist',
            'album': 'Album',
            'duration': 123,
            'size': self.audio.stat().st_size,
        }
        self.sync.refresh([self.entry])
        self.track_id = self.sync.ids_for_paths(['song.flac'])['song.flac']
        state = SimpleNamespace(
            library_trash=self.store,
            library_sync=self.sync,
            auth=SimpleNamespace(
                users=SimpleNamespace(
                    get=lambda id: {
                        'id': id,
                        'role': 'admin' if id in {1, 3} else 'user',
                    }
                )
            ),
            now_playing=SimpleNamespace(active=lambda: []),
            track_index=None,
            library_visibility=None,
            loop=None,
            settings={},
            monitor_db=PlaylistMonitorDB(Path(self.temp.name) / 'monitor.db'),
            background_tasks=set(),
        )
        self.state = state
        self.addCleanup(patch.stopall)
        patch.object(api, 'state', state).start()
        patch.object(api, 'library_context', self.context).start()
        patch.object(api, 'log_activity', AsyncMock()).start()
        patch.object(api, 'announce_playlists_changed', AsyncMock()).start()
        patch.object(api, 'announce_library_changed').start()
        patch.object(trash_routes, '_previews', {}).start()
        patch.object(
            trash_routes, '_preview_slots', asyncio.Semaphore(1)
        ).start()
        patch.object(trash_routes, '_revision', None).start()
        patch.object(
            trash_routes,
            'list_library_entries',
            lambda ctx: (
                [self.entry]
                if self.audio.exists() and 'song.flac' not in ctx.hidden_files
                else []
            ),
        ).start()
        app = FastAPI()

        @app.middleware('http')
        async def principal(request, next):
            mode = request.headers.get('x-test-principal', '')
            values = {
                'admin': Principal(
                    'session', 'admin', user_id=1, role='admin'
                ),
                'device-admin': Principal(
                    'device', 'client', user_id=1, role='admin'
                ),
                'other-admin': Principal(
                    'session', 'admin', user_id=3, role='admin'
                ),
                'user': Principal('session', 'user', user_id=2, role='user'),
                'device-user': Principal(
                    'device', 'client', user_id=2, role='user'
                ),
                'signed': Principal(
                    'signed', 'client', user_id=1, role='admin'
                ),
            }
            request.state.principal = values.get(mode)
            return await next(request)

        app.include_router(trash_routes.router)
        self.client = self.enterContext(TestClient(app))

    def context(self):
        return LibraryContext(
            self.root,
            hidden_files=frozenset(self.store.hidden_paths()),
            hidden_resolved=frozenset(self.store.hidden_resolved()),
        )

    def post(self, path, data, role='admin'):
        return self.client.post(
            '/api/v1/library/trash/' + path,
            json=data,
            headers={'x-test-principal': role},
        )

    def preview(self, role='admin'):
        started = self.post('preview', {'track_ids': [self.track_id]}, role)
        if started.status_code != 202:
            return started
        token = started.json()['request_id']
        for _ in range(300):
            result = self.client.get(
                '/api/v1/library/trash/preview/' + token,
                headers={'x-test-principal': role},
            )
            if result.status_code != 200 or result.json()['state'] == 'ready':
                return result
            time.sleep(0.01)
        self.fail('preview timed out')

    def test_all_operations_refuse_non_admin_and_signed_url(self):
        for role in ('user', 'device-user', 'signed', ''):
            with self.subTest(role=role):
                assert self.preview(role).status_code == 403
                assert (
                    self.post(
                        'confirm', {'confirmation': 'x' * 30}, role
                    ).status_code
                    == 403
                )
                assert (
                    self.post('restore', {'ids': ['id']}, role).status_code
                    == 403
                )
                assert (
                    self.post(
                        'allow-download', {'ids': ['id']}, role
                    ).status_code
                    == 403
                )
                assert (
                    self.client.get(
                        '/api/v1/library/trash',
                        headers={'x-test-principal': role},
                    ).status_code
                    == 403
                )
        assert self.audio.exists()

    def test_admin_browser_and_paired_admin_can_preview(self):
        for role in ('admin', 'device-admin'):
            with self.subTest(role=role):
                response = self.preview(role)
                assert response.status_code == 200, response.text
                assert (
                    response.json()['preview']['items'][0]['track_id']
                    == self.track_id
                )
        assert self.audio.exists()

    def test_admin_role_is_rechecked_against_current_account(self):
        self.state.auth.users.get = lambda id: {'role': 'user'}
        assert self.preview().status_code == 403

    def test_move_restore_retains_mobile_id(self):
        preview = self.preview().json()['preview']
        response = self.post(
            'confirm', {'confirmation': preview['confirmation']}
        )
        assert response.status_code == 202, response.text
        assert self.sync.row_for(self.track_id) is None
        self.store.process(authorized=lambda id: True)
        asyncio.run(trash_routes.publish_changes())
        assert self.sync.row_for(self.track_id) is None
        response = self.post('restore', {'ids': [preview['items'][0]['id']]})
        assert response.status_code == 202, response.text
        self.store.process(authorized=lambda id: True)
        asyncio.run(trash_routes.publish_changes())
        assert (
            self.sync.ids_for_paths(['song.flac'])['song.flac']
            == self.track_id
        )
        assert self.audio.read_bytes() == b'synthetic audio'

    def test_active_playback_refuses_preview(self):
        self.state.now_playing.active = lambda: [
            {'track': {'file': 'song.flac'}, 'paused': False}
        ]
        response = self.preview()
        assert response.status_code == 409
        assert response.json()['detail']['code'] == 'track_is_playing'

    def test_trash_never_resolves_as_audio_and_is_not_scanned(self):
        preview = self.preview().json()['preview']
        self.post('confirm', {'confirmation': preview['confirmation']})
        self.store.process(authorized=lambda id: True)
        trashed = next((self.root / TRASH_DIR).rglob('*.flac'))
        assert (
            resolve_library_file(
                trashed.relative_to(self.root).as_posix(), self.context()
            )
            is None
        )
        assert list(_walk_audio_files(self.root)) == []
        alias = self.root / 'alias.flac'
        alias.symlink_to(trashed)
        assert resolve_library_file('alias.flac', self.context()) is None

    def test_exclusion_persists_until_explicit_unblock(self):
        preview = self.preview().json()['preview']
        self.post('confirm', {'confirmation': preview['confirmation']})
        self.store.process(authorized=lambda id: True)
        assert self.store.blocked(self.entry)
        response = self.post(
            'allow-download', {'ids': [preview['items'][0]['id']]}
        )
        assert response.status_code == 200, response.text
        assert not self.store.blocked(self.entry)

    def test_capabilities_are_account_specific(self):
        for role, expected in [
            ('admin', True),
            ('device-admin', True),
            ('user', False),
            ('signed', False),
        ]:
            response = self.client.get(
                '/api/v1/library/trash/capabilities',
                headers={'x-test-principal': role},
            )
            assert response.json()['can_manage'] == expected

    def test_confirmation_rechecks_current_playback(self):
        preview = self.preview().json()['preview']
        self.state.now_playing.active = lambda: [
            {'track': {'file': 'song.flac'}, 'paused': False}
        ]
        response = self.post(
            'confirm', {'confirmation': preview['confirmation']}
        )
        assert response.status_code == 409
        assert self.audio.exists()

    def test_preview_is_background_and_bound_to_requesting_admin(self):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        original = self.store.preview

        def slow_preview(*args):
            entered.set()
            release.wait(5)
            return original(*args)

        with patch.object(self.store, 'preview', side_effect=slow_preview):
            started = self.post('preview', {'track_ids': [self.track_id]})
            assert started.status_code == 202
            assert entered.wait(2)
            path = (
                '/api/v1/library/trash/preview/' + started.json()['request_id']
            )
            assert (
                self.client.get(
                    path, headers={'x-test-principal': 'admin'}
                ).json()['state']
                == 'preparing'
            )
            assert (
                self.client.get(
                    path, headers={'x-test-principal': 'other-admin'}
                ).status_code
                == 404
            )
            release.set()
            for _ in range(300):
                response = self.client.get(
                    path, headers={'x-test-principal': 'admin'}
                )
                if response.json().get('state') == 'ready':
                    token = response.json()['preview']['confirmation']
                    assert (
                        self.post(
                            'confirm', {'confirmation': token}, 'other-admin'
                        ).status_code
                        == 409
                    )
                    break
                time.sleep(0.01)
            else:
                self.fail('preview did not finish')


if __name__ == '__main__':
    unittest.main()
