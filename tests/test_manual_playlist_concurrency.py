"""Playlist maintenance must not overwrite concurrent Library edits."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, get_ident
from typing import Any, Callable

import pytest

from downtify import m3u, manual_playlists
from downtify.library_catalog import LibraryContext
from downtify.library_delete import delete_library_file
from downtify.playlist_mosaic import has_explicit_cover, keep_explicit_cover

TRACKS = ['a.mp3', 'gone.mp3', 'b.mp3', 'a.mp3']
COVER = b'custom playlist cover'


@pytest.fixture
def library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LibraryContext:
    root = tmp_path / 'downloads'
    root.mkdir()
    for name in {*TRACKS, 'new.mp3'}:
        (root / name).write_bytes(b'audio fixture')
    monkeypatch.setattr(
        manual_playlists, 'refresh_manual_playlist_cover', lambda *_: None
    )
    ctx = LibraryContext(download_dir=root)
    manual_playlists.copy_playlist(ctx, TRACKS, 'Mix')
    path = root / 'Playlists' / 'Mix.m3u'
    path.with_suffix('.jpg').write_bytes(COVER)
    keep_explicit_cover(path)
    m3u.write_m3u(root, 'Imported', [{'filename': 'a.mp3'}])
    return ctx


def _overlap(
    monkeypatch: pytest.MonkeyPatch,
    first: Callable[[], Any],
    second: Callable[[], Any],
    *,
    snapshot_owner: Any = manual_playlists,
    snapshot_name: str = '_read_files',
) -> tuple[Any, Any]:
    snapshot_ready = Event()
    release_snapshot = Event()
    second_progress = Event()
    first_ident: int | None = None
    second_ident: int | None = None
    original_lock = manual_playlists._WRITE_LOCK
    original_snapshot = getattr(snapshot_owner, snapshot_name)

    class ObservedLock:
        def __enter__(self) -> None:
            # Release the first snapshot only once the second operation
            # is blocked by the real lock, or has finished without it.
            if not original_lock.acquire(blocking=False):
                if get_ident() == second_ident:
                    second_progress.set()
                original_lock.acquire()

        def __exit__(self, *_exc: Any) -> None:
            original_lock.release()

    def snapshot(*args: Any, **kwargs: Any) -> Any:
        result = original_snapshot(*args, **kwargs)
        if get_ident() == first_ident and not snapshot_ready.is_set():
            snapshot_ready.set()
            if not release_snapshot.wait(timeout=10):
                raise TimeoutError('playlist snapshot was not released')
        return result

    def run_first() -> Any:
        nonlocal first_ident
        first_ident = get_ident()
        return first()

    def run_second() -> Any:
        nonlocal second_ident
        second_ident = get_ident()
        try:
            return second()
        except manual_playlists.ManualPlaylistError as exc:
            return exc

    monkeypatch.setattr(manual_playlists, '_WRITE_LOCK', ObservedLock())
    monkeypatch.setattr(snapshot_owner, snapshot_name, snapshot)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first_task = pool.submit(run_first)
        try:
            assert snapshot_ready.wait(timeout=10)
            second_task = pool.submit(run_second)
            second_task.add_done_callback(lambda _task: second_progress.set())
            assert second_progress.wait(timeout=10)
        finally:
            release_snapshot.set()
        return first_task.result(timeout=10), second_task.result(timeout=10)


@pytest.mark.parametrize('cleanup', ['missing', 'delete'])
@pytest.mark.parametrize(
    'edit', ['add', 'remove', 'rename', 'drop', 'reorder', 'prune']
)
def test_cleanup_does_not_overwrite_concurrent_playlist_edits(
    library: LibraryContext,
    monkeypatch: pytest.MonkeyPatch,
    cleanup: str,
    edit: str,
) -> None:
    root = library.download_dir
    path = root / 'Playlists' / 'Mix.m3u'
    imported = root / 'Playlists' / 'Imported.m3u'
    imported_before = imported.read_bytes()
    audio_before = {
        name: ((root / name).read_bytes(), (root / name).stat().st_mtime_ns)
        for name in ('a.mp3', 'b.mp3', 'new.mp3')
    }
    if cleanup == 'missing':
        (root / 'gone.mp3').unlink()

    def clean() -> Any:
        if cleanup == 'delete':
            return delete_library_file('gone.mp3', library)
        return manual_playlists.prune_files_from_manual_playlists(
            library, ['gone.mp3']
        )

    edits: dict[str, Callable[[], Any]] = {
        'add': lambda: manual_playlists.edit_manual_playlist(
            library, 'Mix', add=['new.mp3']
        ),
        'remove': lambda: manual_playlists.edit_manual_playlist(
            library, 'Mix', remove_entries=[('a.mp3', 0)]
        ),
        'rename': lambda: manual_playlists.rename_manual_playlist(
            library, 'Mix', 'Renamed'
        ),
        'drop': lambda: manual_playlists.drop_manual_playlist(library, 'Mix'),
        'reorder': lambda: manual_playlists.reorder_manual_playlist(
            library, 'Mix', ['b.mp3', 'a.mp3', 'a.mp3', 'gone.mp3']
        ),
        'prune': lambda: manual_playlists.prune_files_from_manual_playlists(
            library, ['b.mp3']
        ),
    }
    cleaned, edited = _overlap(monkeypatch, clean, edits[edit])

    if cleanup == 'delete':
        assert cleaned['deleted'] is True
        assert cleaned['playlists_affected'] == ['Mix']
    else:
        assert cleaned == ['Mix']
    assert not (root / 'gone.mp3').exists()
    assert imported.read_bytes() == imported_before
    assert {
        name: ((root / name).read_bytes(), (root / name).stat().st_mtime_ns)
        for name in audio_before
    } == audio_before

    if edit == 'drop':
        assert not path.exists()
        assert not path.with_suffix('.jpg').exists()
        return
    if edit == 'rename':
        assert not path.exists()
        assert not path.with_suffix('.jpg').exists()
        path = path.with_name('Renamed.m3u')
    if edit == 'reorder':
        assert isinstance(edited, manual_playlists.ManualPlaylistError)
        assert edited.status_code == 409
    else:
        assert not isinstance(edited, manual_playlists.ManualPlaylistError)
    expected = {
        'add': ['a.mp3', 'b.mp3', 'a.mp3', 'new.mp3'],
        'remove': ['b.mp3', 'a.mp3'],
        'rename': ['a.mp3', 'b.mp3', 'a.mp3'],
        'reorder': ['a.mp3', 'b.mp3', 'a.mp3'],
        'prune': ['a.mp3', 'a.mp3'],
    }
    assert manual_playlists._read_files(library, path) == expected[edit]
    assert m3u.is_manual_m3u(path)
    assert has_explicit_cover(path)
    assert path.with_suffix('.jpg').read_bytes() == COVER


def test_concurrent_detach_only_converts_once(
    library: LibraryContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = library.download_dir / 'Playlists' / 'Imported.m3u'
    path.with_suffix('.jpg').write_bytes(COVER)
    before = path.read_text(encoding='utf-8')

    def detach() -> dict[str, Any]:
        return manual_playlists.detach_imported_playlist(library, 'Imported')

    first, second = _overlap(
        monkeypatch,
        detach,
        detach,
        snapshot_owner=m3u,
        snapshot_name='is_manual_m3u',
    )

    assert first['files'] == ['a.mp3']
    assert isinstance(second, manual_playlists.ManualPlaylistError)
    assert second.status_code == 409
    after = path.read_text(encoding='utf-8')
    assert after.count(m3u.MANUAL_M3U_MARKER) == 1
    assert after.replace(m3u.MANUAL_M3U_MARKER + '\n', '') == before
    assert path.with_suffix('.jpg').read_bytes() == COVER


def test_detach_error_releases_the_lock_for_other_editors(
    library: LibraryContext,
) -> None:
    with pytest.raises(manual_playlists.ManualPlaylistError) as caught:
        manual_playlists.detach_imported_playlist(library, 'Missing')
    assert caught.value.status_code == 404

    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(
            manual_playlists.edit_manual_playlist,
            library,
            'Mix',
            add=['new.mp3'],
        ).result(timeout=10)
    assert result['files'] == [*TRACKS, 'new.mp3']


def test_cleanup_can_reenter_the_existing_playlist_lock(
    library: LibraryContext,
) -> None:
    with manual_playlists._WRITE_LOCK:
        affected = manual_playlists.prune_files_from_manual_playlists(
            library, ['gone.mp3']
        )
    assert affected == ['Mix']
    path = library.download_dir / 'Playlists' / 'Mix.m3u'
    assert manual_playlists._read_files(library, path) == [
        'a.mp3',
        'b.mp3',
        'a.mp3',
    ]
