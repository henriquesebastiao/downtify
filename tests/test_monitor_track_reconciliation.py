"""Tests for the "trust the DB, not the filesystem" Playlist Monitor
dedup fix (downtify/monitor.py):

* ``check_playlist`` must not re-download a track it already recorded
  in ``downloaded_tracks`` just because its file isn't at the stored
  path anymore (e.g. the user moved it elsewhere on disk).
* A separate hourly sweep (``reconcile_downloaded_tracks`` /
  ``reconcile_loop``) is what still notices a track whose file is
  genuinely gone and forgets it, making it eligible for re-download.

All offline — uses a real (tmp_path) ``PlaylistMonitorDB`` plus a fake
downloader, no network.
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest

from downtify import monitor
from downtify.library_paths import extra_dir_id


class _FakeDownloader:
    organize_by_artist = False
    organize_by_album = False

    def __init__(self, tmp_path, *, fail=False):
        self.download_dir = tmp_path
        self.fail = fail
        self.calls: list[str] = []

    def download(self, song, progress_cb=None, subdir=None):
        if self.fail:
            raise RuntimeError('should not be called')
        self.calls.append(song['song_id'])
        return f'{song["song_id"]}.mp3'


def _db(tmp_path) -> monitor.PlaylistMonitorDB:
    return monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')


async def _noop_broadcast(_msg):
    return None


def _playlist(tmp_path):
    db = _db(tmp_path)
    pl = db.add_playlist('pl1', 'My Playlist', 'url', 60)
    return db, pl


# ── check_playlist trusts the DB over the filesystem ─────────────────────────


def test_check_playlist_does_not_redownload_when_file_moved_away(
    monkeypatch, tmp_path
):
    db, pl = _playlist(tmp_path)
    # Recorded as downloaded in an earlier sweep, but the file is no
    # longer under the downloads directory (moved elsewhere on disk).
    db.mark_track_downloaded(pl.id, 'a', 'a.mp3')

    tracks = [{'song_id': 'a', 'name': 'A', 'artists': ['Artist']}]
    monkeypatch.setattr(
        monitor.spotify, 'playlist_tracks_from_id', lambda spotify_id: tracks
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda tid: {})

    downloader = _FakeDownloader(tmp_path, fail=True)

    async def _scenario():
        return await monitor.check_playlist(
            pl,
            db,
            downloader,
            _noop_broadcast,
            asyncio.get_running_loop(),
            settings={'generate_m3u': False},
        )

    downloaded = asyncio.run(_scenario())

    assert downloaded == 0
    assert downloader.calls == []


def test_check_playlist_still_downloads_genuinely_new_tracks(
    monkeypatch, tmp_path
):
    db, pl = _playlist(tmp_path)
    db.mark_track_downloaded(pl.id, 'a', 'a.mp3')  # known, file missing

    tracks = [
        {'song_id': 'a', 'name': 'A', 'artists': ['Artist']},
        {'song_id': 'b', 'name': 'B', 'artists': ['Artist']},
    ]
    monkeypatch.setattr(
        monitor.spotify, 'playlist_tracks_from_id', lambda spotify_id: tracks
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda tid: {})

    downloader = _FakeDownloader(tmp_path)

    async def _scenario():
        return await monitor.check_playlist(
            pl,
            db,
            downloader,
            _noop_broadcast,
            asyncio.get_running_loop(),
            settings={'generate_m3u': False},
        )

    downloaded = asyncio.run(_scenario())

    assert downloaded == 1
    assert downloader.calls == ['b']


# ── PlaylistMonitorDB: list/remove downloaded tracks ─────────────────────────


def test_list_all_downloaded_tracks_only_returns_rows_with_a_filename(
    tmp_path,
):
    db, pl = _playlist(tmp_path)
    db.mark_track_downloaded(pl.id, 'a', 'a.mp3')
    db.mark_track_downloaded(pl.id, 'b', None)

    rows = db.list_all_downloaded_tracks()

    assert rows == [
        {'playlist_id': pl.id, 'track_spotify_id': 'a', 'filename': 'a.mp3'}
    ]


def test_remove_downloaded_tracks_deletes_only_given_pairs(tmp_path):
    db, pl = _playlist(tmp_path)
    db.mark_track_downloaded(pl.id, 'a', 'a.mp3')
    db.mark_track_downloaded(pl.id, 'b', 'b.mp3')

    removed = db.remove_downloaded_tracks([(pl.id, 'a')])

    assert removed == 1
    remaining = db.get_track_filenames(pl.id)
    assert remaining == {'b': 'b.mp3'}


def test_remove_downloaded_tracks_no_op_for_empty_list(tmp_path):
    db, pl = _playlist(tmp_path)
    db.mark_track_downloaded(pl.id, 'a', 'a.mp3')

    assert db.remove_downloaded_tracks([]) == 0
    assert db.get_track_filenames(pl.id) == {'a': 'a.mp3'}


# ── reconcile_downloaded_tracks ──────────────────────────────────────────────


def test_reconcile_removes_rows_whose_file_is_gone(tmp_path):
    db, pl = _playlist(tmp_path)
    (tmp_path / 'present.mp3').write_bytes(b'')
    db.mark_track_downloaded(pl.id, 'present', 'present.mp3')
    db.mark_track_downloaded(pl.id, 'missing', 'missing.mp3')

    downloader = _FakeDownloader(tmp_path)
    removed = asyncio.run(monitor.reconcile_downloaded_tracks(db, downloader))

    assert removed == 1
    assert db.get_track_filenames(pl.id) == {'present': 'present.mp3'}


def test_reconcile_keeps_slskd_leave_in_place_tracks(tmp_path):
    slskd_dir = tmp_path / 'slskd_source'
    slskd_dir.mkdir()
    (slskd_dir / 'AM (2013)').mkdir()
    (slskd_dir / 'AM (2013)' / 'Mad Sounds.mp3').write_bytes(b'')

    db, pl = _playlist(tmp_path)
    db.mark_track_downloaded(pl.id, 'mad', 'slskd/AM (2013)/Mad Sounds.mp3')

    downloader = _FakeDownloader(tmp_path)
    downloader.slskd_settings = {'source_dir': str(slskd_dir)}
    removed = asyncio.run(monitor.reconcile_downloaded_tracks(db, downloader))

    assert removed == 0
    assert db.get_track_filenames(pl.id) == {
        'mad': 'slskd/AM (2013)/Mad Sounds.mp3'
    }


def test_reconcile_is_a_no_op_when_all_files_present(tmp_path):
    db, pl = _playlist(tmp_path)
    (tmp_path / 'a.mp3').write_bytes(b'')
    db.mark_track_downloaded(pl.id, 'a', 'a.mp3')

    downloader = _FakeDownloader(tmp_path)
    removed = asyncio.run(monitor.reconcile_downloaded_tracks(db, downloader))

    assert removed == 0
    assert db.get_track_filenames(pl.id) == {'a': 'a.mp3'}


@pytest.mark.parametrize('reverse_folders', [False, True])
def test_reconcile_keeps_external_tracks_and_prevents_redownload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    reverse_folders: bool,
) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    external = tmp_path / 'collection'
    external.mkdir()
    audio = external / 'a.mp3'
    audio.write_bytes(b'audio')
    other = tmp_path / 'other-collection'
    other.mkdir()
    folders = [str(external), str(other)]
    if reverse_folders:
        folders.reverse()
    settings = {
        'external_library': {'folders': folders},
        'generate_m3u': False,
    }
    db, pl = _playlist(tmp_path)
    stored = f'ext/{extra_dir_id(external)}/a.mp3'
    db.mark_track_downloaded(pl.id, 'a', stored)
    downloader = _FakeDownloader(downloads, fail=True)

    removed = asyncio.run(
        monitor.reconcile_downloaded_tracks(db, downloader, settings=settings)
    )

    assert removed == 0
    assert db.get_track_filenames(pl.id) == {'a': stored}
    monkeypatch.setattr(
        monitor.spotify,
        'playlist_tracks_from_id',
        lambda _id: [{'song_id': 'a', 'name': 'A', 'artists': ['Artist']}],
    )

    async def _scenario() -> int:
        return await monitor.check_playlist(
            pl,
            db,
            downloader,
            _noop_broadcast,
            asyncio.get_running_loop(),
            settings=settings,
        )

    assert asyncio.run(_scenario()) == 0
    assert downloader.calls == []
    assert audio.read_bytes() == b'audio'


def test_reconcile_prunes_only_missing_files_across_library_roots(
    tmp_path: Path,
) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    (downloads / 'local.mp3').write_bytes(b'local')
    external = tmp_path / 'collection'
    external.mkdir()
    (external / 'a.mp3').write_bytes(b'external')
    slskd = tmp_path / 'slskd'
    slskd.mkdir()
    (slskd / 'soulseek.mp3').write_bytes(b'slskd')
    stored = f'ext/{extra_dir_id(external)}/a.mp3'
    missing = f'ext/{extra_dir_id(external)}/missing.mp3'
    settings = {'external_library': {'folders': [str(external)]}}
    db, pl = _playlist(tmp_path)
    filenames = {
        'local': 'local.mp3',
        'external': stored,
        'slskd': 'slskd/soulseek.mp3',
        'missing-external': missing,
        'missing-local': 'missing.mp3',
    }
    for tid, filename in filenames.items():
        db.mark_track_downloaded(pl.id, tid, filename)
    downloader = _FakeDownloader(downloads)
    downloader.slskd_settings = {'source_dir': str(slskd)}

    removed = asyncio.run(
        monitor.reconcile_downloaded_tracks(db, downloader, settings=settings)
    )

    assert removed == 2
    assert db.get_track_filenames(pl.id) == {
        'local': 'local.mp3',
        'external': stored,
        'slskd': 'slskd/soulseek.mp3',
    }


def test_reconcile_forgets_external_tracks_after_folder_is_unmapped(
    tmp_path: Path,
) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    external = tmp_path / 'collection'
    external.mkdir()
    audio = external / 'a.mp3'
    audio.write_bytes(b'audio')
    db, pl = _playlist(tmp_path)
    db.mark_track_downloaded(pl.id, 'a', f'ext/{extra_dir_id(external)}/a.mp3')

    removed = asyncio.run(
        monitor.reconcile_downloaded_tracks(
            db,
            _FakeDownloader(downloads),
            settings={'external_library': {'folders': []}},
        )
    )

    assert removed == 1
    assert db.get_track_filenames(pl.id) == {}
    assert audio.read_bytes() == b'audio'


def test_reconcile_resolves_external_roots_off_the_event_loop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    db, pl = _playlist(tmp_path)
    (tmp_path / 'a.mp3').write_bytes(b'audio')
    db.mark_track_downloaded(pl.id, 'a', 'a.mp3')
    event_thread = threading.get_ident()
    resolve = monitor.extra_dirs_from_settings
    locate = monitor.locate_library_file
    calls: list[str] = []

    def _resolve(
        settings: dict, download_dir: Path, slskd_dir: Path | None
    ) -> tuple[Path, ...]:
        assert threading.get_ident() != event_thread
        calls.append('roots')
        return resolve(settings, download_dir, slskd_dir)

    def _locate(
        stored: str,
        download_dir: Path,
        slskd_dir: Path | None,
        extra_dirs: tuple[Path, ...],
    ) -> Path | None:
        assert threading.get_ident() != event_thread
        calls.append('file')
        return locate(stored, download_dir, slskd_dir, extra_dirs)

    monkeypatch.setattr(monitor, 'extra_dirs_from_settings', _resolve)
    monkeypatch.setattr(monitor, 'locate_library_file', _locate)

    assert (
        asyncio.run(
            monitor.reconcile_downloaded_tracks(
                db, _FakeDownloader(tmp_path), settings={}
            )
        )
        == 0
    )
    assert calls == ['roots', 'file']


# ── reconcile_loop ────────────────────────────────────────────────────────────


class _Stop(Exception):
    pass


def test_reconcile_loop_sweeps_then_sleeps_the_configured_interval(
    monkeypatch, tmp_path
):
    db, pl = _playlist(tmp_path)
    db.mark_track_downloaded(pl.id, 'missing', 'missing.mp3')
    downloader = _FakeDownloader(tmp_path)

    sleeps: list[float] = []

    async def _stop(seconds):
        sleeps.append(seconds)
        raise _Stop

    monkeypatch.setattr(monitor.asyncio, 'sleep', _stop)

    async def _scenario():
        try:
            await monitor.reconcile_loop(
                db, lambda: downloader, interval_seconds=123
            )
        except _Stop:
            pass

    asyncio.run(_scenario())

    assert sleeps == [123]
    # The one missing-file row was pruned during the sweep before sleeping.
    assert db.get_track_filenames(pl.id) == {}


def test_reconcile_loop_tolerates_no_downloader_yet(monkeypatch, tmp_path):
    db, pl = _playlist(tmp_path)
    db.mark_track_downloaded(pl.id, 'a', 'a.mp3')

    async def _stop(_seconds):
        raise _Stop

    monkeypatch.setattr(monitor.asyncio, 'sleep', _stop)

    async def _scenario():
        try:
            await monitor.reconcile_loop(db, lambda: None)
        except _Stop:
            pass

    asyncio.run(_scenario())  # must not raise

    # No downloader available yet -> nothing was reconciled.
    assert db.get_track_filenames(pl.id) == {'a': 'a.mp3'}


def test_reconcile_loop_uses_current_external_folder_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    external = tmp_path / 'collection'
    external.mkdir()
    (external / 'a.mp3').write_bytes(b'audio')
    stored = f'ext/{extra_dir_id(external)}/a.mp3'
    db, pl = _playlist(tmp_path)
    db.mark_track_downloaded(pl.id, 'a', stored)
    settings = {'external_library': {'folders': [str(external)]}}
    downloader = _FakeDownloader(downloads)
    sleeps: list[float] = []

    async def _sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 1:
            assert db.get_track_filenames(pl.id) == {'a': stored}
            settings['external_library'] = {'folders': []}
        else:
            raise _Stop

    monkeypatch.setattr(monitor.asyncio, 'sleep', _sleep)

    async def _scenario() -> None:
        try:
            await monitor.reconcile_loop(
                db,
                lambda: downloader,
                interval_seconds=123,
                settings=settings,
            )
        except _Stop:
            pass

    asyncio.run(_scenario())

    assert sleeps == [123, 123]
    assert db.get_track_filenames(pl.id) == {}
