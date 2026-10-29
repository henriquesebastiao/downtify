"""UI listings must not wait on a full library walk."""

from __future__ import annotations

import asyncio
import threading
import time
from types import SimpleNamespace

from mutagen.id3 import ID3, TALB, TIT2, TPE1, TPE2

from downtify import api, m3u
from downtify import library_paths_cache as paths_cache
from downtify.downloader import Downloader
from downtify.library_catalog import (
    LibraryContext,
    drop_library_listing_files,
    library_album_index,
    library_artist_index,
    library_home_summary,
    list_library_entries,
    listing_for_request,
    lookup_library_songs,
    merge_library_listing_file,
    refresh_library_listing_files,
)
from downtify.library_paths_cache import (
    invalidate_library_paths_cache,
    listing_lock,
    peek_cached_track_entries,
    set_listing_refresh_fn,
)
from downtify.manual_playlists import (
    create_manual_playlist,
    edit_manual_playlist,
)
from downtify.playlist_listing import list_library_playlists


def test_invalidate_keeps_track_snapshot_for_ui(tmp_path):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'One.mp3').write_bytes(b'1')
    invalidate_library_paths_cache()
    ctx = LibraryContext(download_dir=download_dir)
    list_library_entries(ctx)
    invalidate_library_paths_cache()
    peeked = peek_cached_track_entries(ctx)
    assert peeked is not None
    assert [row['file'] for row in peeked] == ['One.mp3']
    summary = library_home_summary(ctx)
    assert summary['track_count'] == 1


def test_summary_does_not_wait_on_listing_lock(tmp_path):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'One.mp3').write_bytes(b'1')
    invalidate_library_paths_cache()
    ctx = LibraryContext(download_dir=download_dir)
    list_library_entries(ctx)
    started = threading.Event()

    def hold_rebuild() -> None:
        with listing_lock():
            started.set()
            time.sleep(0.8)

    worker = threading.Thread(target=hold_rebuild)
    worker.start()
    assert started.wait(timeout=2)
    t0 = time.perf_counter()
    summary = library_home_summary(ctx)
    elapsed = time.perf_counter() - t0
    worker.join()
    assert summary['track_count'] == 1
    assert elapsed < 0.4


def test_playlists_do_not_walk_audio_files(tmp_path, monkeypatch):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'Song.mp3').write_bytes(b'x')
    invalidate_library_paths_cache()
    ctx = LibraryContext(download_dir=download_dir)
    list_library_entries(ctx)
    create_manual_playlist(ctx, 'Mix')
    edit_manual_playlist(ctx, 'Mix', add=['Song.mp3'])
    set_listing_refresh_fn(lambda: None)
    invalidate_library_paths_cache()

    def boom(_ctx):
        raise AssertionError('playlist listing must not scan audio files')

    monkeypatch.setattr(
        'downtify.library_catalog._scan_library_path_pairs', boom
    )
    listed = list_library_playlists(download_dir)
    mix = next(item for item in listed if item['name'] == 'Mix')
    assert mix['files'] == ['Song.mp3']
    assert mix['count'] == 1


def test_merge_listing_file_shows_new_artist_without_rescan(tmp_path):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'One.mp3').write_bytes(b'1')
    invalidate_library_paths_cache()
    ctx = LibraryContext(download_dir=download_dir)
    list_library_entries(ctx)
    artist_dir = download_dir / 'Murilo Huff'
    artist_dir.mkdir()
    track = artist_dir / 'Murilo Huff - Deixa Eu.mp3'
    track.write_bytes(b'huff')
    tags = ID3()
    tags.add(TIT2(encoding=3, text='Deixa Eu'))
    tags.add(TPE1(encoding=3, text='Murilo Huff'))
    tags.add(TPE2(encoding=3, text='Murilo Huff'))
    tags.add(TALB(encoding=3, text='Acústico'))
    tags.save(str(track), v2_version=3)
    merge_library_listing_file(ctx, 'Murilo Huff/Murilo Huff - Deixa Eu.mp3')
    names = [row['name'] for row in library_artist_index(ctx)]
    assert 'Murilo Huff' in names
    files = [row['file'] for row in listing_for_request(ctx)]
    assert 'Murilo Huff/Murilo Huff - Deixa Eu.mp3' in files


def test_drop_listing_files_hides_deleted_album_without_rescan(tmp_path):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    keep = download_dir / 'Keep.mp3'
    keep.write_bytes(b'k')
    album_dir = download_dir / 'Oruam' / 'Oh Garota'
    album_dir.mkdir(parents=True)
    gone = album_dir / 'Oruam - Track.mp3'
    gone.write_bytes(b'o')
    tags = ID3()
    tags.add(TIT2(encoding=3, text='Track'))
    tags.add(TPE1(encoding=3, text='Oruam'))
    tags.add(TPE2(encoding=3, text='Oruam'))
    tags.add(TALB(encoding=3, text='Oh Garota Eu Quero Você Só Pra Mim'))
    tags.save(str(gone), v2_version=3)
    invalidate_library_paths_cache()
    ctx = LibraryContext(download_dir=download_dir)
    list_library_entries(ctx)
    titles = {row['title'] for row in library_album_index(ctx)}
    assert 'Oh Garota Eu Quero Você Só Pra Mim' in titles
    gone.unlink()
    drop_library_listing_files(ctx, ['Oruam/Oh Garota/Oruam - Track.mp3'])
    titles = {row['title'] for row in library_album_index(ctx)}
    assert 'Oh Garota Eu Quero Você Só Pra Mim' not in titles
    files = [row['file'] for row in listing_for_request(ctx)]
    assert 'Oruam/Oh Garota/Oruam - Track.mp3' not in files
    assert 'Keep.mp3' in files


def _tag(path, title, album_artist):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'x')
    tags = ID3()
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text='AliasNorth'))
    tags.add(TPE2(encoding=3, text=album_artist))
    tags.add(TALB(encoding=3, text='Glass Harbor'))
    tags.save(str(path), v2_version=3)


def test_refresh_listing_files_reads_a_retag_in_place(tmp_path):
    download_dir = tmp_path / 'downloads'
    first = download_dir / 'AliasNorth' / 'a.mp3'
    _tag(first, 'Harbor Lights', 'AliasNorth')
    invalidate_library_paths_cache()
    ctx = LibraryContext(download_dir=download_dir)
    list_library_entries(ctx)
    # Marked as a compilation: same path, new album artist.
    _tag(first, 'Harbor Lights', 'Various Artists')
    refresh_library_listing_files(ctx, ['AliasNorth/a.mp3'])
    # A download finishing before the rescan stores the snapshot again
    # under the tree's new fingerprint; the retag must survive it.
    _tag(download_dir / 'AliasWest' / 'b.mp3', 'Tide Line', 'Various Artists')
    merge_library_listing_file(ctx, 'AliasWest/b.mp3')
    rows = {row['file']: row for row in listing_for_request(ctx)}
    assert rows['AliasNorth/a.mp3']['album_artist'] == 'Various Artists'
    albums = [
        row
        for row in library_album_index(ctx)
        if row['title'] == 'Glass Harbor'
    ]
    assert len(albums) == 1
    assert albums[0]['track_count'] == 2


def test_a_delete_removes_the_search_downloaded_badge(tmp_path, monkeypatch):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'Ryder Spot - Pursuit.mp3').write_bytes(b'p')
    set_listing_refresh_fn(lambda: None)
    invalidate_library_paths_cache(drop_entries=True)
    monkeypatch.setattr(
        api.state,
        'downloader',
        Downloader(download_dir=download_dir, audio_format='mp3'),
    )
    ctx = api.library_context()
    list_library_entries(ctx)
    wanted = [{'artist': 'Ryder Spot', 'title': 'Pursuit'}]
    assert [row['file'] for row in lookup_library_songs(ctx, wanted)] == [
        'Ryder Spot - Pursuit.mp3'
    ]

    (download_dir / 'Ryder Spot - Pursuit.mp3').unlink()
    asyncio.run(
        api.after_library_delete(
            {'Ryder Spot - Pursuit.mp3': {'deleted': True}}, {}
        )
    )

    assert lookup_library_songs(ctx, wanted) == []
    assert listing_for_request(ctx) == []


def _count_m3u_walks(monkeypatch):
    calls = []
    real = paths_cache.playlist_listing_fingerprint

    def counting(download_dir):
        calls.append(download_dir)
        return real(download_dir)

    monkeypatch.setattr(paths_cache, 'playlist_listing_fingerprint', counting)
    return calls


def test_ui_playlist_reads_skip_the_m3u_walk_while_fresh(
    tmp_path, monkeypatch
):
    """Walking the downloads folder for M3U files on every page took
    ~300 ms on a NAS: a recently checked listing is served as is."""

    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'Song.mp3').write_bytes(b'x')
    invalidate_library_paths_cache()
    set_listing_refresh_fn(lambda: None)
    walks = _count_m3u_walks(monkeypatch)

    list_library_playlists(download_dir, stale_ok=True)
    list_library_playlists(download_dir, stale_ok=True)
    list_library_playlists(download_dir, stale_ok=True)

    assert len(walks) == 1


def test_writing_an_m3u_shows_up_on_the_next_ui_read(tmp_path):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'Song.mp3').write_bytes(b'x')
    invalidate_library_paths_cache()
    set_listing_refresh_fn(lambda: None)
    assert list_library_playlists(download_dir, stale_ok=True) == []

    m3u.write_m3u(download_dir, 'Road Trip', [{'filename': 'Song.mp3'}])

    names = [
        p['name'] for p in list_library_playlists(download_dir, stale_ok=True)
    ]
    assert names == ['Road Trip']


def test_a_hand_edited_m3u_shows_up_after_the_recheck_window(
    tmp_path, monkeypatch
):
    download_dir = tmp_path / 'downloads'
    (download_dir / 'Playlists').mkdir(parents=True)
    (download_dir / 'Song.mp3').write_bytes(b'x')
    invalidate_library_paths_cache()
    set_listing_refresh_fn(lambda: None)
    assert list_library_playlists(download_dir, stale_ok=True) == []

    (download_dir / 'Playlists' / 'Manual.m3u').write_text(
        '#EXTM3U\n../Song.mp3\n', encoding='utf-8'
    )
    assert list_library_playlists(download_dir, stale_ok=True) == []

    clock = time.monotonic() + paths_cache.PLAYLIST_RECHECK_SECONDS + 1
    monkeypatch.setattr(paths_cache.time, 'monotonic', lambda: clock)
    names = [
        p['name'] for p in list_library_playlists(download_dir, stale_ok=True)
    ]
    assert names == ['Manual']


def test_merging_a_download_neither_walks_nor_rewrites_the_snapshot(
    tmp_path, monkeypatch
):
    """Each downloaded track used to fingerprint every library folder and
    rewrite the whole sqlite snapshot - slow on a NAS, and repeated for
    every track of a playlist. The refresh after the queue stores it."""

    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'One.mp3').write_bytes(b'1')
    invalidate_library_paths_cache()
    set_listing_refresh_fn(lambda: None)
    ctx = LibraryContext(download_dir=download_dir)
    list_library_entries(ctx)
    (download_dir / 'Two.mp3').write_bytes(b'2')

    def no_walk(*_args, **_kwargs):
        raise AssertionError('the library tree was fingerprinted')

    def no_save(*_args, **_kwargs):
        raise AssertionError('the snapshot was rewritten')

    monkeypatch.setattr(paths_cache, 'library_tree_fingerprint', no_walk)
    monkeypatch.setattr(
        paths_cache, '_STORE', SimpleNamespace(save=no_save, load=no_save)
    )
    merge_library_listing_file(ctx, 'Two.mp3')
    drop_library_listing_files(ctx, ['One.mp3'])

    files = [row['file'] for row in listing_for_request(ctx)]
    assert files == ['Two.mp3']


def test_a_patched_listing_is_rebuilt_on_the_next_live_read(tmp_path):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'One.mp3').write_bytes(b'1')
    invalidate_library_paths_cache()
    set_listing_refresh_fn(lambda: None)
    ctx = LibraryContext(download_dir=download_dir)
    list_library_entries(ctx)
    (download_dir / 'Two.mp3').write_bytes(b'2')
    merge_library_listing_file(ctx, 'Two.mp3')
    (download_dir / 'Three.mp3').write_bytes(b'3')

    files = sorted(row['file'] for row in list_library_entries(ctx))
    assert files == ['One.mp3', 'Three.mp3', 'Two.mp3']
