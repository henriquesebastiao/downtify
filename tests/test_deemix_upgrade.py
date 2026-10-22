"""Replacement safety across playlists, references and interrupted cleanup."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from downtify import deemix_upgrade as module
from downtify.deemix_upgrade import DeemixLibraryUpgrade, alias_file
from downtify.deemix_upgrade_playlists import digest, rewrite_playlists
from downtify.deemix_upgrade_store import AudioReplacementStore
from downtify.library_catalog import LibraryContext
from downtify.library_paths import library_stored_path
from downtify.library_sync import LibrarySync
from downtify.library_upgrade import (
    LibraryUpgradeRunner,
    UpgradeDeps,
    UpgradeOptions,
    options_from,
)
from downtify.library_upgrade_db import LibraryUpgradeDB
from downtify.library_visibility import LibraryVisibility
from downtify.likes import LikedTracks
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex
from downtify.track_owners import TrackOwners


@pytest.fixture
def setup(tmp_path: Path) -> SimpleNamespace:
    downloads = tmp_path / 'Downtify'
    external = tmp_path / 'Download'
    downloads.mkdir()
    external.mkdir()
    old = downloads / 'old.mp3'
    new = external / 'new.mp3'
    old.write_bytes(b'original recording')
    new.write_bytes(b'catalog recording')
    db = tmp_path / 'library.db'
    for cls in (
        TrackIndex,
        PlaylistCatalog,
        LikedTracks,
        TrackOwners,
        LibraryVisibility,
        LibrarySync,
    ):
        cls(db)
    store = AudioReplacementStore(db)
    ctx = LibraryContext(downloads, extra_dirs=(external,))
    new_file = library_stored_path(new, downloads, extra_dirs=(external,))
    receipt = {
        'old_file': 'old.mp3',
        'run_id': 1,
        'new_file': new_file,
        'old_key': 'old-key',
        'new_key': 'new-key',
        'old_sha': digest(old),
        'new_sha': digest(new),
        'new_metadata': {
            'file': new_file,
            'title': 'Song',
            'artist': 'Artist',
            'album': 'Album',
            'duration': 173,
        },
        'catalog': {'id': 42, 'duration': 173},
        'delete_original': 1,
    }
    settings = {
        'deemix': {
            'enabled': True,
            'source_dir': str(external),
            'base_url': 'http://deemix:6595',
        }
    }
    published = []
    service = DeemixLibraryUpgrade(
        store,
        lambda: ctx,
        lambda: settings,
        set,
        lambda: published.append(True),
    )
    return SimpleNamespace(**locals())


def save(s: SimpleNamespace) -> None:
    s.store.save_prepared(s.receipt)


@pytest.mark.parametrize('same_key', [False, True])
def test_relink_preserves_every_reference_and_user(
    setup: SimpleNamespace, same_key: bool
) -> None:
    s = setup
    if same_key:
        s.receipt['new_key'] = s.receipt['old_key']
    save(s)
    with s.store.connect() as db:
        db.execute(
            "INSERT INTO library_tracks VALUES ('spotify', 'old.mp3', 'old-key', 'now')"
        )
        db.execute(
            "INSERT INTO playlists(name,updated_at) VALUES ('manual','now')"
        )
        db.execute(
            "INSERT INTO playlist_tracks VALUES ('manual','spotify','old-key','old.mp3',3)"
        )
        for user in (1, 2):
            db.execute(
                "INSERT INTO track_owners VALUES ('old-key',?,'now','old.mp3')",
                (user,),
            )
            db.execute(
                "INSERT INTO liked_tracks VALUES ('old.mp3',?,'old-key','Song','Artist',190,'now')",
                (user,),
            )
        db.execute(
            "INSERT INTO hidden_library_items VALUES ('track','old-key','old.mp3','hidden','reason','now')"
        )
    s.store.relink(s.store.for_run(1))
    s.store.assert_relinked(s.store.for_run(1))
    with s.store.connect() as db:
        assert (
            db.execute('SELECT filename FROM library_tracks').fetchone()[0]
            == s.new_file
        )
        assert db.execute(
            'SELECT filename,track_order FROM playlist_tracks'
        ).fetchone()[:] == (s.new_file, 3)
        assert [
            r[0]
            for r in db.execute(
                'SELECT user_id FROM track_owners ORDER BY user_id'
            )
        ] == [1, 2]
        assert [
            r[0]
            for r in db.execute(
                'SELECT user_id FROM liked_tracks ORDER BY user_id'
            )
        ] == [1, 2]
        assert (
            db.execute(
                'SELECT item_path FROM hidden_library_items'
            ).fetchone()[0]
            == s.new_file
        )
    assert s.old.exists()


def test_existing_new_like_and_owner_are_merged(
    setup: SimpleNamespace,
) -> None:
    s = setup
    save(s)
    with s.store.connect() as db:
        db.executemany(
            'INSERT INTO track_owners VALUES (?,?,?,?)',
            [
                ('old-key', 1, 'now', 'old.mp3'),
                ('new-key', 1, 'before', s.new_file),
            ],
        )
        db.executemany(
            'INSERT INTO liked_tracks VALUES (?,?,?,?,?,?,?)',
            [
                ('old.mp3', 1, 'old-key', 'Song', 'Artist', 190, '2020'),
                (s.new_file, 1, 'new-key', 'Song', 'Artist', 173, '2021'),
            ],
        )
    s.store.relink(s.store.for_run(1))
    s.store.relink(s.store.for_run(1))
    with s.store.connect() as db:
        assert (
            db.execute('SELECT count(*) FROM track_owners').fetchone()[0] == 1
        )
        assert (
            db.execute('SELECT count(*) FROM liked_tracks').fetchone()[0] == 1
        )
        assert (
            db.execute('SELECT liked_at FROM liked_tracks').fetchone()[0]
            == '2020'
        )


def test_m3u_preserves_order_markers_and_updates_duration(
    setup: SimpleNamespace,
) -> None:
    s = setup
    p = s.downloads / 'manual.m3u'
    p.write_text(
        '#EXTM3U\n#DOWNTIFY:manual\n#EXTINF:190,Artist - Song\nold.mp3\n#note\nuntouched.mp3\n',
        encoding='utf-8',
    )
    save(s)
    s.service.finalize(1, lambda: False)
    assert (
        p.read_text(encoding='utf-8')
        == '#EXTM3U\n#DOWNTIFY:manual\n#EXTINF:173,Artist - Song\n../Download/new.mp3\n#note\nuntouched.mp3\n'
    )
    assert not s.old.exists()
    assert s.new.exists()
    assert s.store.path_alias('old.mp3') == s.new_file
    assert alias_file('old.mp3', s.store, s.ctx) == s.new
    assert s.store.summary(1)['removed'] == 1


@pytest.mark.parametrize('changed', ['original', 'target'])
def test_changed_audio_blocks_cleanup(
    setup: SimpleNamespace, changed: str
) -> None:
    s = setup
    save(s)
    (s.old if changed == 'original' else s.new).write_bytes(
        b'changed after verification'
    )
    with pytest.raises(ValueError, match='changed'):
        s.service.finalize(1, lambda: False)
    assert s.old.exists()


def test_manual_deemix_files_and_sidecars_never_removed(
    setup: SimpleNamespace,
) -> None:
    s = setup
    sidecar = s.old.with_suffix('.lrc')
    sidecar.write_text('[00:01]old', encoding='utf-8')
    manual = s.external / 'manual.mp3'
    manual.write_bytes(b'manual')
    save(s)
    s.service.finalize(1, lambda: False)
    assert sidecar.exists()
    assert manual.read_bytes() == b'manual'
    with pytest.raises(ValueError, match='External'):
        s.service._source(s.new_file)


def test_readonly_playlist_reference_retains_original(
    setup: SimpleNamespace,
) -> None:
    s = setup
    p = s.external / 'manual.m3u'
    p.write_text('../Downtify/old.mp3\n', encoding='utf-8')
    save(s)
    with pytest.raises(ValueError, match='external playlist'):
        s.service.finalize(1, lambda: False)
    assert s.old.exists()
    assert s.store.get('old.mp3')['state'] == 'prepared'


def test_publish_failure_keeps_audio_and_retries_without_download(
    setup: SimpleNamespace,
) -> None:
    s = setup
    save(s)

    def fail() -> None:
        raise OSError('catalog unavailable')

    s.service.publish_catalog = fail
    with pytest.raises(OSError, match='catalog unavailable'):
        s.service.finalize(1, lambda: False)
    assert s.old.exists()
    assert s.store.path_alias('old.mp3') == s.new_file
    s.service.publish_catalog = lambda: None
    s.service.finalize(1, lambda: False)
    assert not s.old.exists()


def test_restart_after_unlink_before_receipt_recovers(
    setup: SimpleNamespace,
) -> None:
    s = setup
    save(s)
    s.store.relink(s.store.for_run(1))
    s.old.unlink()
    s.service.finalize(1, lambda: False)
    assert s.store.summary(1)['removed'] == 1
    assert s.new.exists()


def test_pause_and_playback_block_deletion(setup: SimpleNamespace) -> None:
    s = setup
    save(s)
    with pytest.raises(InterruptedError):
        s.service.finalize(1, lambda: True)
    s.service.playing = lambda: {'old.mp3'}
    with pytest.raises(ValueError, match='playing'):
        s.service.finalize(1, lambda: False)
    assert s.old.exists()


def test_cleanup_is_optional(setup: SimpleNamespace) -> None:
    s = setup
    s.receipt['delete_original'] = 0
    save(s)
    s.service.finalize(1, lambda: False)
    assert s.old.exists()
    assert s.store.summary(1)['retained'] == 1


@pytest.mark.parametrize('already_tombstoned', [False, True])
def test_mobile_old_id_resolves_replacement_even_if_new_has_id(
    setup: SimpleNamespace,
    already_tombstoned: bool,
) -> None:
    s = setup
    sync = LibrarySync(s.db)
    sync.refresh([
        {'file': 'old.mp3', 'title': 'Song', 'artist': 'Artist', 'size': 10},
        s.receipt['new_metadata'],
    ])
    old_id = sync.ids_for_paths(['old.mp3'])['old.mp3']
    with s.store.connect() as db:
        s.receipt['old_key'] = db.execute(
            'SELECT content_key FROM sync_tracks WHERE track_id=?', (old_id,)
        ).fetchone()[0]
    if already_tombstoned:
        sync.refresh([s.receipt['new_metadata']])
    save(s)
    s.store.relink(s.store.for_run(1))
    sync.refresh([s.receipt['new_metadata']])
    assert sync.path_for(old_id) == s.new_file
    assert sync.row_for(old_id)['duration'] == 173


def test_mount_marker_failure_retains_original(
    setup: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    s = setup
    save(s)
    monkeypatch.setenv(
        'DOWNTIFY_LIBRARY_READY_MARKERS', '{"/does-not-exist-marker":"ready"}'
    )
    with pytest.raises(FileNotFoundError):
        s.service.finalize(1, lambda: False)
    assert s.old.exists()


def test_default_options_do_not_change_existing_upgrade() -> None:
    assert not options_from({}).replace_audio_deemix
    assert 'replace_audio_deemix' not in options_from({}).as_dict()
    assert options_from({
        'replace_audio_deemix': True,
        'delete_replaced_audio': True,
    }).delete_replaced_audio


def test_scan_includes_unfolded_old_audio_and_scope(
    setup: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    s = setup

    def entries(ctx: LibraryContext, *, fold_extra: bool = True) -> list[dict]:
        assert not fold_extra
        return [
            {'file': 'old.mp3', 'size': 20},
            {'file': s.new_file, 'size': 20},
            {'file': 'other.mp3', 'size': 20},
        ]

    monkeypatch.setattr(
        'downtify.library_upgrade.list_library_entries', entries
    )
    runner = LibraryUpgradeRunner(
        LibraryUpgradeDB(s.db),
        UpgradeDeps(
            context=lambda: s.ctx,
            settings=lambda: s.settings,
            audio_replacement=s.service,
        ),
    )
    options = UpgradeOptions(replace_audio_deemix=True, files=('old.mp3',))
    run_id = runner.db.create_run(['audio'], options.as_dict())
    runner._scan(run_id, options)
    jobs = runner.db.jobs(run_id)
    assert [j['file'] for j in jobs] == ['old.mp3']
    assert jobs[0]['categories'] == ['audio']


def test_missing_lyrics_does_not_overwrite_native(
    setup: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    s = setup
    monkeypatch.setattr(
        module.lyrics_mod,
        'read_track_lyrics',
        lambda _: {'synced': '[00:01]native'},
    )
    monkeypatch.setattr(
        module.lyrics_mod,
        'fetch',
        lambda *args: pytest.fail('Must not fetch existing lyrics'),
    )
    s.service._missing_lyrics(s.new, {})


def test_m3u_interruption_is_safe_and_repeatable(
    setup: SimpleNamespace,
) -> None:
    s = setup
    p = s.downloads / 'test.m3u'
    p.write_text('old.mp3\n', encoding='utf-8')
    mapping = {s.old: (s.new, 173)}
    with pytest.raises(InterruptedError):
        rewrite_playlists(
            [s.downloads], s.downloads, mapping, stopped=lambda: True
        )
    assert p.read_text(encoding='utf-8') == 'old.mp3\n'
    rewrite_playlists(
        [s.downloads], s.downloads, mapping, stopped=lambda: False
    )
    rewrite_playlists(
        [s.downloads], s.downloads, mapping, stopped=lambda: False
    )
    assert p.read_text(encoding='utf-8') == '../Download/new.mp3\n'


@pytest.fixture
def prepare_mocks(
    setup: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> dict:
    s = setup
    row = {
        'id': 42,
        'title': 'Song',
        'artist': {'name': 'Artist'},
        'album': {'title': 'Album'},
        'duration': 173,
    }
    monkeypatch.setattr(
        module,
        'DeemixClient',
        lambda cfg: SimpleNamespace(connect=lambda: None, close=lambda: None),
    )
    monkeypatch.setattr(module, '_catalog_track', lambda client, song: row)
    monkeypatch.setattr(
        module, 'download_from_deemix', lambda song, cfg: s.new
    )
    monkeypatch.setattr(module, 'verified_audio', lambda *args: True)
    monkeypatch.setattr(module.subprocess, 'run', lambda *args, **kwargs: None)

    def metadata(stored: str, path: Path) -> dict:
        return {
            'file': stored,
            'title': 'Song',
            'artist': 'Artist',
            'album': 'Album',
            'duration': 190 if path == s.old else 173,
            'codec': 'mp3',
            'bitrate': 320000,
        }

    monkeypatch.setattr(module, 'library_entry_for_file', metadata)
    return row


def test_prepare_uses_catalog_duration_not_old_youtube_clip(
    setup: SimpleNamespace, prepare_mocks: dict
) -> None:
    s = setup
    outcome = s.service.prepare(
        'old.mp3',
        UpgradeOptions(replace_audio_deemix=True, delete_replaced_audio=True),
        1,
        lambda _: None,
    )
    assert outcome.status == 'done'
    assert s.old.exists()
    assert s.store.get('old.mp3')['new_metadata']['duration'] == 173
    assert s.store.get('old.mp3')['state'] == 'prepared'


def test_prepare_ambiguous_catalog_never_downloads(
    setup: SimpleNamespace,
    prepare_mocks: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = setup
    monkeypatch.setattr(module, '_catalog_track', lambda *args: None)
    monkeypatch.setattr(
        module,
        'download_from_deemix',
        lambda *args: pytest.fail('No ambiguous downloads'),
    )
    assert (
        s.service.prepare(
            'old.mp3', UpgradeOptions(), 1, lambda _: None
        ).status
        == 'skipped'
    )
    assert s.old.exists()


def test_prepare_rejects_wrong_album_in_downloaded_tags(
    setup: SimpleNamespace,
    prepare_mocks: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = setup
    previous = module.library_entry_for_file

    def metadata(stored: str, path: Path) -> dict:
        row = previous(stored, path)
        if path == s.new:
            row['album'] = 'Single release'
        return row

    monkeypatch.setattr(module, 'library_entry_for_file', metadata)
    with pytest.raises(ValueError, match='album tags'):
        s.service.prepare('old.mp3', UpgradeOptions(), 1, lambda _: None)
    assert s.old.exists()
    assert s.store.get('old.mp3') is None


def test_sql_failure_rolls_back_all_references(setup: SimpleNamespace) -> None:
    s = setup
    save(s)
    with s.store.connect() as db:
        db.execute(
            "INSERT INTO library_tracks VALUES ('spotify','old.mp3','old-key','now')"
        )
        db.execute(
            "CREATE TRIGGER reject_link BEFORE UPDATE ON library_audio_replacements BEGIN SELECT RAISE(ABORT,'simulated interruption'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match='simulated interruption'):
        s.store.relink(s.store.for_run(1))
    with s.store.connect() as db:
        assert (
            db.execute('SELECT filename FROM library_tracks').fetchone()[0]
            == 'old.mp3'
        )
    assert s.old.exists()


def test_lyrics_fallback_is_sidecar_only_and_no_overwrite(
    setup: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    s = setup
    dest = s.tmp_path / 'lyrics' / 'new.lrc'
    s.settings['lyrics_providers'] = ['lrclib']
    monkeypatch.setattr(
        module.lyrics_mod, 'read_track_lyrics', lambda path: {}
    )
    monkeypatch.setattr(
        module.lyrics_mod,
        'fetch',
        lambda *args: module.lyrics_mod.Lyrics(synced='[00:01]new lyrics'),
    )
    monkeypatch.setattr(module.lyrics_mod, 'lrc_path_for', lambda path: dest)
    before = digest(s.new)
    s.service._missing_lyrics(s.new, {})
    assert dest.read_text(encoding='utf-8') == '[00:01]new lyrics'
    dest.write_text('[00:02]owner edit', encoding='utf-8')
    s.service._missing_lyrics(s.new, {})
    assert dest.read_text(encoding='utf-8') == '[00:02]owner edit'
    assert digest(s.new) == before


def test_runner_finalization_failure_pauses_and_resumes(
    setup: SimpleNamespace,
) -> None:
    s = setup
    save(s)
    runner = LibraryUpgradeRunner(
        LibraryUpgradeDB(s.db),
        UpgradeDeps(
            context=lambda: s.ctx,
            settings=lambda: s.settings,
            audio_replacement=s.service,
        ),
    )
    run_id = runner.db.create_run(
        ['audio'], UpgradeOptions(replace_audio_deemix=True).as_dict()
    )
    assert run_id == 1
    runner.db.add_jobs(
        run_id,
        [
            {
                'file': 'old.mp3',
                'categories': ['audio'],
                'size': 10,
                'title': 'Song',
                'artist': 'Artist',
            }
        ],
    )
    runner.db.finish_job(
        run_id, 'old.mp3', 'done', detail='Publication pending'
    )
    s.service.playing = lambda: {'old.mp3'}
    runner._run(
        run_id,
        UpgradeOptions(categories=('audio',), replace_audio_deemix=True),
    )
    assert runner.status()['state'] == 'paused'
    assert 'playing' in runner.status()['finalization_error']
    s.service.playing = set
    runner._run(
        run_id,
        UpgradeOptions(categories=('audio',), replace_audio_deemix=True),
    )
    assert runner.status()['state'] == 'done'
    assert not s.old.exists()
    assert (
        runner.db.jobs(run_id)[0]['detail']
        == 'Deemix imported; old copy removed'
    )
