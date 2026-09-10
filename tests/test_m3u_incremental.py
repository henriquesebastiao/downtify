"""End-to-end tests that the M3U lands on disk *before* a batch finishes.

These deliberately use the real `m3u.write_m3u`, the real
`Downloader.existing_filename_for` path resolution and real files in a
tmp dir — mocking `_regenerate_m3u` / `write_m3u` would only prove the
call happens, not that a playable file actually appears while a slow
track is still downloading, which is the whole point of the feature.
"""

from __future__ import annotations

import asyncio
import threading

from downtify import api, monitor
from downtify.downloader import Downloader

PLAYLIST_NAME = 'My Playlist'


def _make_downloader(tmp_path) -> Downloader:
    return Downloader(download_dir=tmp_path, audio_format='mp3')


def _write_track_file(dl: Downloader, song: dict, subdir: str) -> str:
    """Create the file exactly where the downloader would have put it.

    Uses the downloader's own path resolution so the test exercises the
    real `existing_filename_for` lookup instead of a guessed layout.
    """
    parts = dl._format_output_parts(song)
    basename = parts[-1]
    target_dir, prefix = dl._resolve_target_dir(
        dl._effective_subdir(song, subdir)
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / f'{basename}.{dl.audio_format}').write_bytes(b'audio')
    return f'{prefix}{basename}.{dl.audio_format}'


async def _wait_for(predicate, timeout=5.0):
    """Poll until *predicate* is true (or give up), yielding to the loop."""
    waited = 0.0
    while waited < timeout:
        if predicate():
            return True
        await asyncio.sleep(0.01)
        waited += 0.01
    return False


# ── manual playlist / CSV batch downloads (api._process_batch) ──────────────


def test_process_batch_writes_m3u_before_slow_track_finishes(
    monkeypatch, tmp_path
):
    songs = [
        {'song_id': 'a', 'name': 'Song A', 'artists': ['Artist A']},
        {'song_id': 'b', 'name': 'Song B', 'artists': ['Artist B']},
    ]
    dl = _make_downloader(tmp_path)
    monkeypatch.setattr(api.state, 'downloader', dl)
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api.state, 'download_semaphore', None)

    release_slow = asyncio.Event()

    async def fake_run_download(song, song_id, subdir=None, delay_seconds=0):
        if song['song_id'] == 'b':
            await release_slow.wait()
        return _write_track_file(dl, song, subdir)

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    m3u_path = tmp_path / PLAYLIST_NAME / f'{PLAYLIST_NAME}.m3u'

    async def _scenario():
        task = asyncio.create_task(
            api._process_batch(
                songs,
                ['job-a', 'job-b'],
                playlist_url='',
                generate_m3u=True,
                playlist_name=PLAYLIST_NAME,
            )
        )

        appeared = await _wait_for(m3u_path.exists)
        assert appeared, 'M3U was not written before the slow track finished'
        early = m3u_path.read_text(encoding='utf-8')
        assert not task.done(), 'batch finished before the assertion ran'

        release_slow.set()
        await task
        return early, m3u_path.read_text(encoding='utf-8')

    early, final = asyncio.run(_scenario())

    # Early file is playable and holds only the track that finished.
    assert early.startswith('#EXTM3U')
    assert 'Song A' in early
    assert 'Song B' not in early
    # Final rewrite picks up the slow track too, in playlist order.
    assert 'Song A' in final
    assert 'Song B' in final
    assert final.index('Song A') < final.index('Song B')


def test_process_batch_skips_m3u_when_generation_disabled(
    monkeypatch, tmp_path
):
    songs = [{'song_id': 'a', 'name': 'Song A', 'artists': ['Artist A']}]
    dl = _make_downloader(tmp_path)
    monkeypatch.setattr(api.state, 'downloader', dl)
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api.state, 'download_semaphore', None)

    async def fake_run_download(song, song_id, subdir=None, delay_seconds=0):
        return _write_track_file(dl, song, subdir)

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    asyncio.run(
        api._process_batch(
            songs,
            ['job-a'],
            playlist_url='',
            generate_m3u=False,
            playlist_name=PLAYLIST_NAME,
        )
    )

    assert not (tmp_path / PLAYLIST_NAME / f'{PLAYLIST_NAME}.m3u').exists()


def test_process_batch_m3u_keeps_playlist_order_not_completion_order(
    monkeypatch, tmp_path
):
    # The second song finishes first; the M3U must still list them in
    # playlist order.
    songs = [
        {'song_id': 'a', 'name': 'Song A', 'artists': ['Artist A']},
        {'song_id': 'b', 'name': 'Song B', 'artists': ['Artist B']},
    ]
    dl = _make_downloader(tmp_path)
    monkeypatch.setattr(api.state, 'downloader', dl)
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api.state, 'download_semaphore', None)

    b_done = asyncio.Event()

    async def fake_run_download(song, song_id, subdir=None, delay_seconds=0):
        if song['song_id'] == 'a':
            await b_done.wait()
        filename = _write_track_file(dl, song, subdir)
        if song['song_id'] == 'b':
            b_done.set()
        return filename

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    asyncio.run(
        api._process_batch(
            songs,
            ['job-a', 'job-b'],
            playlist_url='',
            generate_m3u=True,
            playlist_name=PLAYLIST_NAME,
        )
    )

    final = (tmp_path / PLAYLIST_NAME / f'{PLAYLIST_NAME}.m3u').read_text(
        encoding='utf-8'
    )
    assert final.index('Song A') < final.index('Song B')


# ── Playlist Monitor sweeps (monitor.check_playlist) ────────────────────────


class _FakeMonitorDB:
    @staticmethod
    def get_track_filenames(playlist_id):
        return {}

    @staticmethod
    def mark_track_downloaded(playlist_id, track_id, filename):
        pass

    @staticmethod
    def update_playlist(playlist_id, **kwargs):
        pass


def _monitored_playlist():
    return monitor.MonitoredPlaylist(
        id=1,
        spotify_id='pl123',
        name=PLAYLIST_NAME,
        url='https://open.spotify.com/playlist/pl123',
        interval_minutes=60,
        enabled=True,
        last_checked=None,
        last_track_count=0,
        created_at='2026-01-01T00:00:00+00:00',
    )


def test_check_playlist_writes_m3u_before_slow_track_finishes(
    monkeypatch, tmp_path
):
    tracks = [
        {'song_id': 'a', 'name': 'Song A', 'artists': ['Artist A']},
        {'song_id': 'b', 'name': 'Song B', 'artists': ['Artist B']},
    ]
    dl = _make_downloader(tmp_path)

    monkeypatch.setattr(
        monitor.spotify, 'playlist_tracks_from_id', lambda spotify_id: tracks
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda track_id: {})

    # download() runs in a worker thread, so the slow track blocks on a
    # threading primitive rather than an asyncio one.
    release_slow = threading.Event()

    def fake_download(song, cb, subdir=None):
        if song['song_id'] == 'b':
            release_slow.wait(timeout=5)
        return _write_track_file(dl, song, subdir)

    monkeypatch.setattr(dl, 'download', fake_download)

    m3u_path = tmp_path / PLAYLIST_NAME / f'{PLAYLIST_NAME}.m3u'

    async def fake_broadcast(_msg):
        return None

    async def _scenario():
        task = asyncio.create_task(
            monitor.check_playlist(
                _monitored_playlist(),
                _FakeMonitorDB(),
                dl,
                fake_broadcast,
                asyncio.get_running_loop(),
                settings={'generate_m3u': True},
            )
        )

        appeared = await _wait_for(m3u_path.exists)
        assert appeared, 'M3U was not written before the slow track finished'
        early = m3u_path.read_text(encoding='utf-8')
        assert not task.done(), 'sweep finished before the assertion ran'

        release_slow.set()
        downloaded = await task
        return early, m3u_path.read_text(encoding='utf-8'), downloaded

    early, final, downloaded = asyncio.run(_scenario())

    assert downloaded == 2
    assert early.startswith('#EXTM3U')
    assert 'Song A' in early
    assert 'Song B' not in early
    assert 'Song A' in final
    assert 'Song B' in final


def test_check_playlist_skips_m3u_when_generation_disabled(
    monkeypatch, tmp_path
):
    tracks = [{'song_id': 'a', 'name': 'Song A', 'artists': ['Artist A']}]
    dl = _make_downloader(tmp_path)

    monkeypatch.setattr(
        monitor.spotify, 'playlist_tracks_from_id', lambda spotify_id: tracks
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda track_id: {})
    monkeypatch.setattr(
        dl,
        'download',
        lambda song, cb, subdir=None: _write_track_file(dl, song, subdir),
    )

    async def fake_broadcast(_msg):
        return None

    async def _scenario():
        return await monitor.check_playlist(
            _monitored_playlist(),
            _FakeMonitorDB(),
            dl,
            fake_broadcast,
            asyncio.get_running_loop(),
            settings={'generate_m3u': False},
        )

    assert asyncio.run(_scenario()) == 1
    assert not (tmp_path / PLAYLIST_NAME / f'{PLAYLIST_NAME}.m3u').exists()
