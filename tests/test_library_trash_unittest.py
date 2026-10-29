import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

from downtify import library_trash
from downtify.library_trash import (
    PREVIEW_SECONDS,
    RETENTION_SECONDS,
    TRASH_DIR,
    LibraryTrash,
    TrashError,
    TrashRoot,
    worker_lock,
)


class _TrashFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'music'
        self.root.mkdir()
        (self.root / '.nas').write_text('expected')
        self.now = 1000.0
        self.db = Path(self.temp.name) / 'library.db'
        self.store = LibraryTrash(
            self.db,
            {'music': TrashRoot(self.root, '.nas', 'expected')},
            clock=lambda: self.now,
        )
        self.audio = self.root / 'Artist' / 'track.flac'
        self.audio.parent.mkdir()
        self.audio.write_bytes(b'original audio')
        self.track = {
            'stored': 'Artist/track.flac',
            'root_key': 'music',
            'relative': 'Artist/track.flac',
            'track_id': 'stable-id',
            'metadata': {
                'title': 'Track',
                'artist': 'Artist',
                'album': 'Album',
            },
        }

    def confirm(self):
        preview = self.store.preview(1, [self.track])
        self.store.confirm(1, preview['confirmation'])
        return preview['items'][0]['id']

    def process(self):
        return self.store.process(authorized=lambda user: user == 1)


class TrashTests(_TrashFixture):
    def test_preview_is_not_a_deletion(self):
        self.store.preview(1, [self.track])
        assert self.audio.exists()
        assert self.store.hidden_paths() == set()
        assert self.store.list()['total'] == 0

    def test_uncertain_identity_is_not_falsely_claimed_as_blocked(self):
        self.track['metadata'] = {'title': 'Unknown track'}
        with pytest.raises(TrashError, match='identity_uncertain'):
            self.store.preview(1, [self.track])
        assert self.audio.exists()

    def test_confirmation_belongs_to_admin(self):
        preview = self.store.preview(1, [self.track])
        with pytest.raises(TrashError, match='confirmation_invalid'):
            self.store.confirm(2, preview['confirmation'])

    def test_confirmation_expires(self):
        preview = self.store.preview(1, [self.track])
        self.now += PREVIEW_SECONDS + 1
        with pytest.raises(TrashError, match='confirmation_expired'):
            self.store.confirm(1, preview['confirmation'])

    def test_changed_audio_rejected_before_confirmation(self):
        preview = self.store.preview(1, [self.track])
        self.audio.write_bytes(b'new audio')
        with pytest.raises(TrashError, match='file_changed'):
            self.store.confirm(1, preview['confirmation'])
        assert self.store.hidden_paths() == set()

    def test_changed_audio_rejected_by_worker(self):
        self.confirm()
        self.audio.write_bytes(b'changed after confirmation')
        assert not self.process()[0]['ok']
        assert self.audio.exists()

    def test_move_and_restore_after_worker_restart(self):
        item = self.confirm()
        assert self.process()[0]['ok']
        assert not self.audio.exists()
        current = self.store.list()['items'][0]
        assert current['state'] == 'trashed'
        assert current['expires_at'] == self.now + RETENTION_SECONDS
        self.store = LibraryTrash(
            self.db, self.store.roots, clock=lambda: self.now
        )
        self.store.request_restore([item])
        assert self.process()[0]['ok']
        assert self.audio.read_bytes() == b'original audio'
        assert self.store.hidden_paths() == set()

    def test_catalogue_revision_changes_only_when_visibility_changes(self):
        before = self.store.revision()
        item = self.confirm()
        hidden = self.store.revision()
        assert hidden == before + 1
        self.process()
        assert self.store.revision() == hidden
        self.store.request_restore([item])
        assert self.store.revision() == hidden
        self.process()
        assert self.store.revision() == hidden + 1

    def test_expiration_starts_when_move_finishes(self):
        self.confirm()
        self.now += 3600
        self.process()
        assert (
            self.store.list()['items'][0]['expires_at']
            == self.now + RETENTION_SECONDS
        )

    def test_no_purge_before_30_days_then_purges(self):
        self.confirm()
        self.process()
        self.now += RETENTION_SECONDS - 1
        assert self.process() == []
        self.now += 1
        assert self.process()[0]['ok']
        assert self.store.list()['total'] == 0
        assert self.track['stored'] in self.store.hidden_paths()
        assert list((self.root / TRASH_DIR).rglob('*.flac')) == []

    def test_restore_never_overwrites_a_recreated_file(self):
        item = self.confirm()
        self.process()
        self.audio.write_bytes(b'a different file')
        self.store.request_restore([item])
        assert not self.process()[0]['ok']
        assert self.audio.read_bytes() == b'a different file'
        assert len(list((self.root / TRASH_DIR).rglob('*.flac'))) == 1

    def test_modified_trash_never_purged(self):
        self.confirm()
        self.process()
        trash = next((self.root / TRASH_DIR).rglob('*.flac'))
        trash.write_bytes(b'changed trash')
        self.now += RETENTION_SECONDS
        assert not self.process()[0]['ok']
        assert trash.exists()

    def test_nas_marker_loss_keeps_source(self):
        self.confirm()
        (self.root / '.nas').unlink()
        assert not self.process()[0]['ok']
        assert self.audio.exists()

    def test_admin_revoked_before_move(self):
        self.confirm()
        result = self.store.process(authorized=lambda user: False)
        assert result[0]['error'] == 'admin_access_revoked'
        assert self.audio.exists()


class TrashSafetyTests(_TrashFixture):
    def test_only_selected_audio_and_owned_sidecar(self):
        other = self.audio.with_suffix('.mp3')
        other.write_bytes(b'other format')
        lrc = self.audio.with_suffix('.lrc')
        lrc.write_text('[00:01]shared lyrics')
        cover = self.audio.parent / 'cover.jpg'
        cover.write_bytes(b'cover')
        self.confirm()
        self.process()
        assert other.exists()
        assert lrc.exists()
        assert cover.exists()

    def test_own_sidecar_moves_and_restores(self):
        lrc = self.audio.with_suffix('.lrc')
        lrc.write_text('[00:01]lyrics')
        item = self.confirm()
        self.process()
        assert not lrc.exists()
        self.store.request_restore([item])
        self.process()
        assert lrc.read_text() == '[00:01]lyrics'

    def test_separate_lyrics_volume_moves_and_restores_without_cross_volume_rename(
        self,
    ):
        lyrics_root = Path(self.temp.name) / 'lyrics'
        lyrics_root.mkdir()
        (lyrics_root / 'Artist').mkdir()
        lrc = lyrics_root / 'Artist' / 'track.lrc'
        lrc.write_text('[00:01]lyrics')
        self.store.roots['lyrics'] = TrashRoot(lyrics_root)
        self.track['extra_sidecars'] = [
            {'root_key': 'lyrics', 'relative': 'Artist/track.lrc'}
        ]
        item = self.confirm()
        assert self.process()[0]['ok']
        assert not lrc.exists()
        assert (
            next((lyrics_root / TRASH_DIR).rglob('*.lrc')).read_text()
            == '[00:01]lyrics'
        )
        self.store.request_restore([item])
        assert self.process()[0]['ok']
        assert lrc.read_text() == '[00:01]lyrics'
        assert self.audio.exists()

    def test_path_traversal_rejected(self):
        for relative in (
            '../track.flac',
            '/etc/passwd',
            'C:/track.flac',
            '.downtify-trash/x',
        ):
            with self.subTest(relative=relative):
                with pytest.raises(TrashError):
                    self.store.preview(
                        1, [{**self.track, 'relative': relative}]
                    )

    def test_confirm_is_idempotent(self):
        preview = self.store.preview(1, [self.track])
        first = self.store.confirm(1, preview['confirmation'])
        assert first == self.store.confirm(1, preview['confirmation'])

    def test_native_download_song_shape_is_excluded(self):
        self.track['metadata'] = {
            'title': 'Song',
            'artist': 'Artist',
            'album': 'Album',
        }
        self.confirm()
        assert self.store.blocked({
            'name': 'Song',
            'artists': ['Artist'],
            'album_name': 'Album',
        })
        assert not self.store.blocked({
            'name': 'Song (Live)',
            'artists': ['Artist'],
            'album_name': 'Album',
        })

    def test_restoring_one_copy_does_not_unblock_another_trashed_copy(self):
        metadata = {'title': 'Song', 'artist': 'Artist', 'album': 'Album'}
        self.track['metadata'] = metadata
        first = self.confirm()
        assert self.process()[0]['ok']
        other = self.root / 'Artist' / 'other.mp3'
        other.write_bytes(b'another format')
        second = {
            **self.track,
            'stored': 'Artist/other.mp3',
            'relative': 'Artist/other.mp3',
        }
        preview = self.store.preview(1, [second])
        self.store.confirm(1, preview['confirmation'])
        assert self.process()[0]['ok']
        self.store.request_restore([first])
        assert self.process()[0]['ok']
        assert self.store.blocked({
            'name': 'Song',
            'artists': ['Artist'],
            'album_name': 'Album',
        })

    def test_spotify_provider_ids_are_case_sensitive(self):
        provider_id = 'aBcDef1234567890123456'
        assert len(provider_id) == 22
        self.track['metadata'] = {'spotify_id': provider_id}
        self.confirm()
        assert self.store.blocked({'song_id': provider_id})
        assert not self.store.blocked({'song_id': provider_id.upper()})

    def test_concurrent_workers_do_not_share_operations(self):
        self.confirm()
        with worker_lock(
            self.db.with_suffix('.trash-worker.lock')
        ) as acquired:
            assert acquired
            assert self.process() == []
        assert self.audio.exists()

    def test_worker_skips_active_track_without_starving_other_items(self):
        first = self.confirm()
        other = self.root / 'Artist' / 'another.flac'
        other.write_bytes(b'other song')
        selection = {
            **self.track,
            'stored': 'Artist/another.flac',
            'relative': 'Artist/another.flac',
            'metadata': {
                'title': 'Another',
                'artist': 'Artist',
                'album': 'Album',
            },
        }
        preview = self.store.preview(1, [selection])
        self.store.confirm(1, preview['confirmation'])
        result = self.store.process(
            limit=1, authorized=lambda _: True, skip_ids=frozenset({first})
        )
        assert len(result) == 1
        assert self.audio.exists()
        assert not other.exists()

    def test_partial_move_resumes_without_source_loss(self):
        self.audio.with_suffix('.lrc').write_text('lyrics')
        self.confirm()
        real = library_trash._rename_no_replace
        calls = []

        def interrupted(source, target):
            calls.append(source)
            if len(calls) == 2:
                raise KeyboardInterrupt()
            return real(source, target)

        with patch.object(library_trash, '_rename_no_replace', interrupted):
            with pytest.raises(KeyboardInterrupt):
                self.process()
        self.store = LibraryTrash(
            self.db, self.store.roots, clock=lambda: self.now
        )
        assert self.process()[0]['ok']
        assert self.store.list()['items'][0]['state'] == 'trashed'

    def test_stale_worker_snapshot_does_not_override_cancelled_move(self):
        item = self.confirm()
        with self.store.connect() as conn:
            stale = dict(
                conn.execute(
                    'SELECT * FROM library_trash WHERE id=?', (item,)
                ).fetchone()
            )
        self.store.request_restore([item])
        assert not self.store._process_item(stale)
        assert self.audio.exists()
        assert self.process()[0]['ok']
        assert self.audio.exists()

    def test_restore_is_not_accepted_during_active_move(self):
        item = self.confirm()
        self.store._update(item, state='moving')
        with pytest.raises(TrashError, match='operation_in_progress'):
            self.store.request_restore([item])
        assert self.audio.exists()
