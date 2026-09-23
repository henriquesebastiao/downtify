"""Concurrency guarantees: work that used to run sequentially (or on the
event loop thread) now runs in parallel / off the loop.

Where possible these assert the concurrency itself with barriers/events
— a test deadlocks into a timeout, not merely "runs slower", if the code
under test goes back to running things one after another.
"""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

import pytest
from mutagen.id3 import ID3

from downtify import api, library_metadata_cache, spotify
from downtify import downloader as downloader_mod
from downtify.downloader import (
    DOWNLOAD_EXECUTOR,
    MAX_PARALLEL_DOWNLOADS,
    Downloader,
)
from tests.test_downloader_extended import _minimal_mp3

_SONG = {
    'name': 'Song',
    'artists': ['Artist'],
    'youtube_id': 'abc123def45',
    'album_name': 'Album',
    'cover_url': 'https://example.com/cover.jpg',
}


# ── dedicated download thread pool ───────────────────────────────────────────


def test_download_executor_fits_the_parallel_downloads_maximum():
    # asyncio's default executor is min(32, cpu+4) threads — 6 on a 2-core
    # box — which silently capped "Parallel downloads" and starved every
    # asyncio.to_thread() call behind running downloads.
    assert DOWNLOAD_EXECUTOR._max_workers > MAX_PARALLEL_DOWNLOADS
    assert api.MAX_PARALLEL_DOWNLOADS == MAX_PARALLEL_DOWNLOADS


def test_run_download_uses_the_dedicated_executor(monkeypatch):
    seen = []

    class _Downloader:
        @staticmethod
        def download(song, progress, subdir=None):
            seen.append(threading.current_thread().name)
            return 'Artist - Song.mp3'

    async def _noop_broadcast(_msg):
        return None

    monkeypatch.setattr(api.state, 'downloader', _Downloader())
    monkeypatch.setattr(api.state, 'download_semaphore', None)
    monkeypatch.setattr(api.state, 'loop', None)
    monkeypatch.setattr(api.state.connections, 'broadcast', _noop_broadcast)

    result = asyncio.run(api._run_download(dict(_SONG), 'job-1'))

    assert result == 'Artist - Song.mp3'
    assert seen[0].startswith('downtify-download')


# ── async endpoints don't block the event loop ───────────────────────────────


def _loop_running_here() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def test_download_endpoint_resolves_the_song_off_the_event_loop(monkeypatch):
    on_loop = []

    def _resolve(url):
        on_loop.append(_loop_running_here())
        return dict(_SONG)

    async def _fake_run_download(song, song_id, **kwargs):
        return 'Artist - Song.mp3'

    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(api, '_song_for_download', _resolve)
    monkeypatch.setattr(api, '_run_download', _fake_run_download)

    result = asyncio.run(
        api.download_endpoint(
            url='https://open.spotify.com/track/x',
            client_id='',
            client_hints=None,
        )
    )

    assert result == 'Artist - Song.mp3'
    assert on_loop == [False]


def test_download_album_endpoint_resolves_tracks_off_the_event_loop(
    monkeypatch,
):
    on_loop = []

    def _resolve(url):
        on_loop.append(_loop_running_here())
        return []

    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(api, '_songs_for_album_download', _resolve)

    assert asyncio.run(api.download_album_endpoint(url='x')) == {}
    assert on_loop == [False]


# ── WebSocket broadcast ──────────────────────────────────────────────────────


class _WS:
    def __init__(self, delay=0.0, fail=False):
        self.delay = delay
        self.fail = fail
        self.sent: list[str] = []

    async def send_text(self, text):
        await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError('client gone')
        self.sent.append(text)


def test_run_download_announces_downloading_only_inside_the_slot(
    monkeypatch,
):
    """Rows started together must not all broadcast ``downloading``
    before any of them holds the parallel-download semaphore."""
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api.state, 'loop', None)

    release = threading.Event()
    entered = threading.Event()

    class _Downloader:
        overwrite_existing_files = True

        @staticmethod
        def download(song, progress, subdir=None):
            entered.set()
            if not release.wait(timeout=5):
                raise RuntimeError('download was not released')
            return f'{song["song_id"]}.mp3'

    broadcasts: list[dict] = []

    async def fake_broadcast(message):
        broadcasts.append(message)

    async def _noop_record(*_args, **_kwargs):
        return None

    monkeypatch.setattr(api.state, 'downloader', _Downloader())
    monkeypatch.setattr(api.state.connections, 'broadcast', fake_broadcast)
    monkeypatch.setattr(api, '_record_finished_download', _noop_record)

    songs = [{'song_id': str(i), 'name': f'Song {i}'} for i in range(3)]
    previous_sem = api.state.download_semaphore

    async def _scenario():
        api.state.download_semaphore = asyncio.Semaphore(1)
        for song in songs:
            api._register_job(song, status='queued')
        task = asyncio.create_task(
            asyncio.gather(
                *(
                    api._run_download(song, song['song_id'])
                    for song in songs
                )
            )
        )
        try:
            for _ in range(50):
                if entered.is_set():
                    break
                await asyncio.sleep(0.01)
            assert entered.is_set(), 'first download never started'
            # The other two rows are queued on the semaphore. Give them
            # a chance to announce anyway, which is the bug.
            await asyncio.sleep(0.05)
            downloading = [
                message
                for message in broadcasts
                if message.get('status') == 'downloading'
            ]
            assert len(downloading) == 1
            assert not task.done()
        finally:
            release.set()
            await task

    try:
        asyncio.run(_scenario())
    finally:
        api.state.download_semaphore = previous_sem


def test_broadcast_sends_to_clients_concurrently():
    manager = api.ConnectionManager()
    slow_a, slow_b = _WS(delay=0.3), _WS(delay=0.3)
    manager._clients = {'a': slow_a, 'b': slow_b}

    started = time.perf_counter()
    asyncio.run(manager.broadcast({'progress': 50}))
    elapsed = time.perf_counter() - started

    assert slow_a.sent == slow_b.sent == ['{"progress": 50}']
    # Sequential sends would take ~0.6 s.
    assert elapsed < 0.5


def test_broadcast_drops_failed_clients_only():
    manager = api.ConnectionManager()
    good, bad = _WS(), _WS(fail=True)
    manager._clients = {'good': good, 'bad': bad}

    asyncio.run(manager.broadcast({'x': 1}))

    assert list(manager._clients) == ['good']
    assert good.sent == ['{"x": 1}']


def test_broadcast_keeps_a_client_that_reconnected_mid_send():
    manager = api.ConnectionManager()
    replacement = _WS()

    class _FailsAfterReconnect:
        @staticmethod
        async def send_text(text):
            manager._clients['c'] = replacement
            raise RuntimeError('old socket closed')

    manager._clients = {'c': _FailsAfterReconnect()}

    asyncio.run(manager.broadcast({'x': 1}))

    assert manager._clients == {'c': replacement}


# ── Downloader: metadata lookups alongside yt-dlp ────────────────────────────


def _fake_youtube_dl(on_download):
    class _YoutubeDL:
        def __init__(self, opts):
            self.opts = opts
            self.params = opts

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def add_post_processor(self, pp, when='post_process'):
            pass

        def download(self, urls):
            on_download(self.opts)
            _minimal_mp3(Path(self.opts['outtmpl'].replace('%(ext)s', 'mp3')))

    return _YoutubeDL


def test_metadata_lookups_run_while_yt_dlp_downloads(tmp_path, monkeypatch):
    started = {
        'genre': threading.Event(),
        'cover': threading.Event(),
        'lyrics': threading.Event(),
    }

    def _genre(song):
        started['genre'].set()
        return 'Rock'

    def _cover(url):
        started['cover'].set()

    def _lyrics(song, providers, cache=None):
        started['lyrics'].set()

    def _download(opts):
        # Sequential lookups (after the download) would never start while
        # we wait here.
        for name, event in started.items():
            assert event.wait(timeout=5), f'{name} lookup did not start'

    monkeypatch.setattr(downloader_mod, '_fetch_itunes_genre', _genre)
    monkeypatch.setattr(downloader_mod, '_download_cover', _cover)
    monkeypatch.setattr(downloader_mod.lyrics_mod, 'fetch', _lyrics)
    monkeypatch.setattr(
        downloader_mod.yt_dlp, 'YoutubeDL', _fake_youtube_dl(_download)
    )
    d = Downloader(tmp_path, lyrics_providers=['lrclib'])

    name = d.download(dict(_SONG))

    tags = ID3(tmp_path / name)
    assert str(tags.getall('TCON')[0]) == 'Rock'


def test_failed_download_does_not_wait_for_lookups(tmp_path, monkeypatch):
    release = threading.Event()

    def _slow_lyrics(song, providers):
        release.wait(timeout=10)

    def _download(opts):
        raise RuntimeError('yt-dlp failed')

    monkeypatch.setattr(downloader_mod.lyrics_mod, 'fetch', _slow_lyrics)
    monkeypatch.setattr(
        downloader_mod.yt_dlp, 'YoutubeDL', _fake_youtube_dl(_download)
    )
    d = Downloader(tmp_path, lyrics_providers=['lrclib'])

    started = time.perf_counter()
    try:
        with pytest.raises(Exception, match='yt-dlp failed'):
            d.download(dict(_SONG))
        assert time.perf_counter() - started < 5
    finally:
        release.set()


def test_cover_is_downloaded_once_for_tags_and_cover_jpg(
    tmp_path, monkeypatch
):
    calls = []

    def _cover(url):
        calls.append(url)
        return b'IMG-BYTES'

    monkeypatch.setattr(downloader_mod, '_download_cover', _cover)
    monkeypatch.setattr(
        downloader_mod.yt_dlp, 'YoutubeDL', _fake_youtube_dl(lambda o: None)
    )
    d = Downloader(tmp_path, organize_by_album=True)

    d.download(dict(_SONG))

    assert calls == ['https://example.com/cover.jpg']
    [cover_jpg] = list(tmp_path.rglob('cover.jpg'))
    assert cover_jpg.read_bytes() == b'IMG-BYTES'


def test_progress_is_reported_once_per_whole_percent(tmp_path, monkeypatch):
    def _download(opts):
        hook = opts['progress_hooks'][0]
        total = 10_000
        for downloaded in range(0, total + 1, 8):
            hook({
                'status': 'downloading',
                'total_bytes': total,
                'downloaded_bytes': downloaded,
            })

    monkeypatch.setattr(
        downloader_mod.yt_dlp, 'YoutubeDL', _fake_youtube_dl(_download)
    )
    reports = []
    d = Downloader(tmp_path)

    d.download(
        dict(_SONG),
        lambda pct, msg, provider=None: reports.append((pct, msg)),
    )

    downloading = [int(p) for p, m in reports if m == 'Downloading']
    # 1,251 chunk callbacks collapse to one report per percent (0..95).
    assert len(downloading) == 96
    assert downloading == sorted(set(downloading))
    assert reports[-1] == (100.0, 'Done')


# ── Spotify playlist pages ───────────────────────────────────────────────────


def _fake_pages(monkeypatch, total, page_sizes, barrier=None):
    """Serve ``total`` numbered items; ``page_sizes`` maps an offset to how
    many items that request returns (default: up to 100)."""

    requested = []

    def _fetch(playlist_id, token, offset, limit=100):
        requested.append(offset)
        if barrier is not None and offset > 0:
            barrier.wait(timeout=5)
        size = page_sizes.get(offset, limit)
        return {
            'name': 'List',
            'content': {
                'totalCount': total,
                'items': list(range(offset, min(total, offset + size))),
            },
        }

    monkeypatch.setattr(spotify, '_graphql_fetch_page', _fetch)
    monkeypatch.setattr(
        spotify, '_track_dict_from_graphql_item', lambda item: {'n': item}
    )
    return requested


def test_graphql_pages_after_the_first_are_fetched_concurrently(monkeypatch):
    # Offsets 100, 200 and 300 each wait for the other two: only
    # concurrent requests get past the barrier.
    barrier = threading.Barrier(3)
    _fake_pages(monkeypatch, total=350, page_sizes={}, barrier=barrier)

    name, songs = spotify._graphql_all_tracks('pl', 'token')

    assert name == 'List'
    assert [s['n'] for s in songs] == list(range(350))


def test_graphql_single_page_makes_one_request(monkeypatch):
    requested = _fake_pages(monkeypatch, total=42, page_sizes={})

    _, songs = spotify._graphql_all_tracks('pl', 'token')

    assert requested == [0]
    assert len(songs) == 42


def test_graphql_short_middle_page_falls_back_to_sequential(monkeypatch):
    # Offset 100 only returns 60 items: fixed 100-item offsets would skip
    # items 160–199, so the rest must be walked by actual page lengths.
    requested = _fake_pages(monkeypatch, total=300, page_sizes={100: 60})

    _, songs = spotify._graphql_all_tracks('pl', 'token')

    assert [s['n'] for s in songs] == list(range(300))
    assert 160 in requested


# ── /tracks tag cache (LibraryMetadataCache) ─────────────────────────────


def _entry(stored, full):
    return {
        'file': stored,
        'title': full.stem,
        'artist': 'Artist',
        'album': '',
        'album_artist': '',
        'track_number': 0,
        'year': '',
        'duration': 0.0,
        'has_cover': False,
        'cover_px': 0,
        'added': int(full.stat().st_mtime),
        'size': full.stat().st_size,
    }


def test_library_tags_are_cached_until_the_file_changes(tmp_path, monkeypatch):
    reads = []

    def _read(stored, full):
        reads.append(full.name)
        return _entry(stored, full)

    monkeypatch.setattr(
        library_metadata_cache, 'library_entry_for_file', _read
    )
    cache = library_metadata_cache.LibraryMetadataCache(tmp_path / 'lib.db')
    a, b = tmp_path / 'a.mp3', tmp_path / 'b.mp3'
    a.write_bytes(b'1')
    b.write_bytes(b'2')
    items = [('a.mp3', a), ('b.mp3', b)]

    first = cache.get_entries_batch(items)
    second = cache.get_entries_batch(items)

    assert [e['title'] for e in first] == ['a', 'b']
    assert second == first
    assert sorted(reads) == ['a.mp3', 'b.mp3']

    b.write_bytes(b'retagged, different size')
    cache.get_entries_batch(items)
    assert sorted(reads) == ['a.mp3', 'b.mp3', 'b.mp3']


def test_library_tags_are_read_on_multiple_threads(tmp_path, monkeypatch):
    barrier = threading.Barrier(4)

    def _read(stored, full):
        barrier.wait(timeout=5)
        return _entry(stored, full)

    monkeypatch.setattr(
        library_metadata_cache, 'library_entry_for_file', _read
    )
    cache = library_metadata_cache.LibraryMetadataCache(tmp_path / 'lib.db')
    items = []
    for i in range(4):
        path = tmp_path / f'{i}.mp3'
        path.write_bytes(b'x')
        items.append((f'{i}.mp3', path))

    entries = cache.get_entries_batch(items)

    assert [e['title'] for e in entries] == ['0', '1', '2', '3']
