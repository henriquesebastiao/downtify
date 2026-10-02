"""Extra library folders: listing, artist match, duplicate skip."""

from __future__ import annotations

from pathlib import Path

from mutagen.id3 import ID3, TALB, TIT2, TPE1, TPE2, USLT

from downtify import external_library as ext
from downtify import lyrics as lyrics_mod
from downtify.cover_cache import CoverArtCache
from downtify.external_library import (
    artist_match_key,
    enrich_imported_track,
    extra_dirs_from_settings,
    finish_library_entries,
    match_artist,
    partition_extra_entries,
    sanitize_external_folders,
    sync_external_library,
)
from downtify.external_sync import ExternalSyncJob, unmap_extra_folder
from downtify.library_catalog import (
    LibraryContext,
    library_context_from_state,
    list_library_entries,
    list_library_paths,
    resolve_library_file,
)
from downtify.library_metadata_cache import LibraryMetadataCache
from downtify.library_paths import (
    EXTERNAL_LIBRARY_PREFIX,
    extra_dir_id,
    library_file_root,
    library_stored_path,
)
from downtify.library_paths_cache import invalidate_library_paths_cache
from downtify.library_upgrade import _Artwork
from downtify.lyrics import Lyrics, lrc_sidecar_path, read_track_lyrics


def _write_mp3(
    path: Path,
    *,
    title: str,
    artist: str,
    album: str = '',
    album_artist: str = '',
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tags = ID3()
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text=artist))
    if album:
        tags.add(TALB(encoding=3, text=album))
    if album_artist:
        tags.add(TPE2(encoding=3, text=album_artist))
    tags.save(str(path), v2_version=3)


def test_sanitize_drops_relative_and_duplicates(tmp_path):
    abs_one = str(tmp_path / 'one')
    assert sanitize_external_folders([
        'relative/path',
        abs_one,
        abs_one,
        '',
        None,
    ]) == [abs_one]


def test_extra_dirs_skip_download_tree(tmp_path):
    download = tmp_path / 'downloads'
    download.mkdir()
    nested = download / 'ripped'
    nested.mkdir()
    outside = tmp_path / 'collection'
    outside.mkdir()
    settings = {
        'external_library': {
            'folders': [str(nested), str(outside)],
        }
    }
    dirs = extra_dirs_from_settings(settings, download)
    assert dirs == (outside,)


def test_artist_match_strips_the_and_punctuation():
    catalog = ['The Beatles']
    assert match_artist('Beatles', catalog) == 'The Beatles'
    assert match_artist('AC/DC', ['ACDC']) == 'ACDC'
    assert artist_match_key('The Beatles') == artist_match_key('beatles')
    assert match_artist('Radiohead', catalog) is None


def test_list_library_includes_extra_folder(tmp_path):
    download = tmp_path / 'downloads'
    extra = tmp_path / 'ripped'
    download.mkdir()
    track = extra / 'Band' / 'Song.mp3'
    _write_mp3(track, title='Harbor Lights', artist='Kenji Aoki')

    ctx = LibraryContext(download_dir=download, extra_dirs=(extra,))
    invalidate_library_paths_cache()
    paths = list_library_paths(ctx)
    stored = library_stored_path(track, download, extra_dirs=(extra,))
    assert stored.startswith(EXTERNAL_LIBRARY_PREFIX)
    assert extra_dir_id(extra) in stored
    assert stored in paths
    resolved = resolve_library_file(stored, ctx)
    assert resolved == track.resolve()


def test_extra_track_matches_existing_artist(tmp_path):
    download = tmp_path / 'downloads'
    extra = tmp_path / 'ripped'
    download.mkdir()
    _write_mp3(
        download / 'The Beatles - Help.mp3',
        title='Help!',
        artist='The Beatles',
        album_artist='The Beatles',
    )
    _write_mp3(
        extra / 'yesterday.mp3',
        title='Yesterday',
        artist='Beatles',
        album='Help!',
        album_artist='Beatles',
    )
    ctx = LibraryContext(download_dir=download, extra_dirs=(extra,))
    invalidate_library_paths_cache()
    entries = list_library_entries(ctx)
    extra_row = next(
        item
        for item in entries
        if str(item['file']).startswith(EXTERNAL_LIBRARY_PREFIX)
    )
    assert extra_row['album_artist'] == 'The Beatles'
    assert extra_row['title'] == 'Yesterday'


def test_duplicate_song_in_extra_folder_is_skipped(tmp_path):
    download = tmp_path / 'downloads'
    extra = tmp_path / 'ripped'
    download.mkdir()
    _write_mp3(
        download / 'Kenji Aoki - Harbor Lights.mp3',
        title='Harbor Lights',
        artist='Kenji Aoki',
        album_artist='Kenji Aoki',
    )
    _write_mp3(
        extra / 'copy.mp3',
        title='Harbor Lights',
        artist='Kenji Aoki',
        album_artist='Kenji Aoki',
    )
    ctx = LibraryContext(download_dir=download, extra_dirs=(extra,))
    invalidate_library_paths_cache()
    entries = list_library_entries(ctx)
    files = [item['file'] for item in entries]
    assert any(not f.startswith(EXTERNAL_LIBRARY_PREFIX) for f in files)
    assert not any(f.startswith(EXTERNAL_LIBRARY_PREFIX) for f in files)


def test_library_file_root_points_at_the_extra_folder(tmp_path):
    download = tmp_path / 'downloads'
    extra = tmp_path / 'ripped'
    download.mkdir()
    track = extra / 'Band' / 'Song.mp3'
    _write_mp3(track, title='Harbor Lights', artist='Kenji Aoki')
    stored = library_stored_path(track, download, extra_dirs=(extra,))
    root, rel = library_file_root(stored, download, extra_dirs=(extra,))
    assert root == extra.resolve()
    assert rel == 'Band/Song.mp3'
    assert (root / rel).is_file()


def test_library_context_from_settings(tmp_path):
    download = tmp_path / 'downloads'
    extra = tmp_path / 'ripped'
    download.mkdir()
    extra.mkdir()
    ctx = library_context_from_state(
        download,
        {'external_library': {'folders': [str(extra)]}},
    )
    assert ctx.extra_dirs == (extra,)


def test_finish_merges_catalog_artist():
    owned = [
        {
            'file': 'a.mp3',
            'title': 'One',
            'artist': 'The Beatles',
            'album_artist': 'The Beatles',
            'duration': 0,
        }
    ]
    extra = [
        {
            'file': 'ext/abc123/two.mp3',
            'title': 'Two',
            'artist': 'Beatles',
            'album_artist': 'Beatles',
            'duration': 0,
        }
    ]
    merged = finish_library_entries(owned + extra)
    extra_row = next(
        item for item in merged if item['file'].startswith('ext/')
    )
    assert extra_row['album_artist'] == 'The Beatles'


def test_partition_reports_duplicate_for_the_log():
    owned = [
        {
            'file': 'a.mp3',
            'title': 'Harbor Lights',
            'artist': 'Kenji Aoki',
            'album_artist': 'Kenji Aoki',
            'duration': 0,
        }
    ]
    extra = [
        {
            'file': 'ext/abc123/copy.mp3',
            'title': 'Harbor Lights',
            'artist': 'Kenji Aoki',
            'album_artist': 'Kenji Aoki',
            'duration': 0,
        },
        {
            'file': 'ext/abc123/other.mp3',
            'title': 'Undertow',
            'artist': 'Kenji Aoki',
            'album_artist': 'Kenji Aoki',
            'duration': 0,
        },
    ]
    _owned, kept, skipped = partition_extra_entries(owned + extra)
    assert [item['title'] for item in kept] == ['Undertow']
    assert skipped[0][1] == 'duplicate'
    assert skipped[0][0]['title'] == 'Harbor Lights'


def test_sync_log_lists_imported_and_duplicates(tmp_path, monkeypatch):
    download = tmp_path / 'downloads'
    extra = tmp_path / 'ripped'
    download.mkdir()
    _write_mp3(
        download / 'Kenji Aoki - Harbor Lights.mp3',
        title='Harbor Lights',
        artist='Kenji Aoki',
        album_artist='Kenji Aoki',
    )
    _write_mp3(
        extra / 'copy.mp3',
        title='Harbor Lights',
        artist='Kenji Aoki',
        album_artist='Kenji Aoki',
    )
    _write_mp3(
        extra / 'new.mp3',
        title='Undertow',
        artist='Kenji Aoki',
        album_artist='Kenji Aoki',
    )

    monkeypatch.setattr(
        'downtify.lyrics.fetch',
        lambda *_a, **_k: Lyrics(plain='The tide comes in'),
    )
    monkeypatch.setattr('downtify.itunes.fetch_genre', lambda _song: '')

    ctx = LibraryContext(download_dir=download, extra_dirs=(extra,))
    invalidate_library_paths_cache()
    result = sync_external_library(
        ctx,
        download_dir=download,
        settings={
            'download_cover_art': False,
            'download_lyrics': True,
            'lyrics_providers': ['lrclib'],
        },
    )
    statuses = {item['title']: item['status'] for item in result['log']}
    assert statuses['Undertow'] == 'imported'
    assert statuses['Harbor Lights'] == 'duplicate'
    imported = next(
        item for item in result['log'] if item['status'] == 'imported'
    )
    assert imported['lyrics'] is True
    assert result['added'] == 1
    assert result['skipped_duplicates'] == 1


def test_enrich_embeds_lyrics_like_a_download(tmp_path, monkeypatch):
    download = tmp_path / 'downloads'
    extra = tmp_path / 'ripped'
    download.mkdir()
    track = extra / 'Song.mp3'
    _write_mp3(track, title='Harbor Lights', artist='Kenji Aoki')

    monkeypatch.setattr(
        'downtify.lyrics.fetch',
        lambda *_a, **_k: Lyrics(
            plain='The tide comes in',
            synced='[00:01.00]The tide comes in',
        ),
    )
    monkeypatch.setattr('downtify.itunes.fetch_genre', lambda _song: '')

    ctx = LibraryContext(download_dir=download, extra_dirs=(extra,))
    invalidate_library_paths_cache()
    stored = library_stored_path(track, download, extra_dirs=(extra,))
    result = enrich_imported_track(
        stored,
        ctx,
        settings={
            'download_cover_art': False,
            'download_lyrics': True,
            'lyrics_providers': ['lrclib'],
        },
    )
    assert result['lyrics'] is True
    found = read_track_lyrics(track)
    assert 'tide' in found['plain']
    assert found['synced'].startswith('[00:01.00]')
    assert track.with_suffix('.lrc').is_file()


def test_enrich_skips_lyrics_when_disabled(tmp_path, monkeypatch):
    download = tmp_path / 'downloads'
    extra = tmp_path / 'ripped'
    download.mkdir()
    track = extra / 'Song.mp3'
    _write_mp3(track, title='Harbor Lights', artist='Kenji Aoki')

    def _no_fetch(*_a, **_k):
        raise AssertionError('lyrics must not be fetched when disabled')

    monkeypatch.setattr('downtify.lyrics.fetch', _no_fetch)
    monkeypatch.setattr('downtify.itunes.fetch_genre', lambda _song: '')

    ctx = LibraryContext(download_dir=download, extra_dirs=(extra,))
    invalidate_library_paths_cache()
    stored = library_stored_path(track, download, extra_dirs=(extra,))
    result = enrich_imported_track(
        stored,
        ctx,
        settings={
            'download_cover_art': False,
            'download_lyrics': False,
            'lyrics_providers': ['lrclib'],
        },
    )
    assert result['lyrics'] is False
    found = read_track_lyrics(track)
    assert not found['plain']
    assert not found['synced']


def test_enrich_writes_sidecar_when_tags_already_have_lyrics(
    tmp_path, monkeypatch
):
    download = tmp_path / 'downloads'
    extra = tmp_path / 'ripped'
    download.mkdir()
    track = extra / 'Song.mp3'
    _write_mp3(track, title='Harbor Lights', artist='Kenji Aoki')
    tags = ID3(str(track))
    tags.add(USLT(encoding=3, lang='eng', desc='', text='The tide comes in'))
    tags.save(v2_version=3)

    monkeypatch.setattr(
        'downtify.lyrics.fetch',
        lambda *_a, **_k: Lyrics(
            plain='The tide comes in',
            synced='[00:01.00]The tide comes in',
        ),
    )
    monkeypatch.setattr('downtify.itunes.fetch_genre', lambda _song: '')

    ctx = LibraryContext(download_dir=download, extra_dirs=(extra,))
    invalidate_library_paths_cache()
    stored = library_stored_path(track, download, extra_dirs=(extra,))
    result = enrich_imported_track(
        stored,
        ctx,
        settings={
            'download_cover_art': False,
            'download_lyrics': True,
            'lyrics_providers': ['lrclib'],
        },
    )
    assert result['lyrics'] is True
    assert track.with_suffix('.lrc').is_file()
    assert '[00:01.00]' in track.with_suffix('.lrc').read_text(
        encoding='utf-8'
    )


def test_enrich_writes_lrc_to_dedicated_folder(tmp_path, monkeypatch):
    download = tmp_path / 'downloads'
    extra = tmp_path / 'ripped'
    lyrics_root = tmp_path / 'lrc'
    download.mkdir()
    extra.mkdir()
    track = extra / 'Song.mp3'
    _write_mp3(track, title='Harbor Lights', artist='Kenji Aoki')

    monkeypatch.setattr(
        'downtify.lyrics.fetch',
        lambda *_a, **_k: Lyrics(
            plain='The tide comes in',
            synced='[00:01.00]The tide comes in',
        ),
    )
    monkeypatch.setattr('downtify.itunes.fetch_genre', lambda _song: '')

    settings = {
        'download_cover_art': False,
        'download_lyrics': True,
        'lyrics_providers': ['lrclib'],
        'lyrics_lrc_beside': False,
        'lyrics_lrc_dir': str(lyrics_root),
    }

    def _resolve(audio):
        return lrc_sidecar_path(
            audio,
            settings=settings,
            download_dir=download,
            extra_dirs=(extra,),
        )

    lyrics_mod.set_lrc_resolver(_resolve, tree_root=lambda: lyrics_root)
    try:
        ctx = LibraryContext(download_dir=download, extra_dirs=(extra,))
        invalidate_library_paths_cache()
        stored = library_stored_path(track, download, extra_dirs=(extra,))
        result = enrich_imported_track(stored, ctx, settings=settings)
        dest = (
            lyrics_root
            / f'{EXTERNAL_LIBRARY_PREFIX}{extra_dir_id(extra)}'
            / 'Song.lrc'
        )
        assert result['lyrics'] is True
        assert dest.is_file()
        assert not track.with_suffix('.lrc').exists()
    finally:
        lyrics_mod.set_lrc_resolver(None)


def test_enrich_moves_sidecar_when_location_changes(tmp_path, monkeypatch):
    download = tmp_path / 'downloads'
    extra = tmp_path / 'ripped'
    lyrics_root = tmp_path / 'lrc'
    download.mkdir()
    extra.mkdir()
    track = extra / 'Song.mp3'
    _write_mp3(track, title='Harbor Lights', artist='Kenji Aoki')
    track.with_suffix('.lrc').write_text(
        '[00:01.00]The tide comes in', encoding='utf-8'
    )

    def _no_fetch(*_a, **_k):
        raise AssertionError('must copy existing sidecar, not fetch')

    monkeypatch.setattr('downtify.lyrics.fetch', _no_fetch)
    monkeypatch.setattr('downtify.itunes.fetch_genre', lambda _song: '')

    settings = {
        'download_cover_art': False,
        'download_lyrics': True,
        'lyrics_providers': ['lrclib'],
        'lyrics_lrc_beside': False,
        'lyrics_lrc_dir': str(lyrics_root),
    }

    def _resolve(audio):
        return lrc_sidecar_path(
            audio,
            settings=settings,
            download_dir=download,
            extra_dirs=(extra,),
        )

    lyrics_mod.set_lrc_resolver(_resolve, tree_root=lambda: lyrics_root)
    try:
        ctx = LibraryContext(download_dir=download, extra_dirs=(extra,))
        invalidate_library_paths_cache()
        stored = library_stored_path(track, download, extra_dirs=(extra,))
        result = enrich_imported_track(stored, ctx, settings=settings)
        dest = (
            lyrics_root
            / f'{EXTERNAL_LIBRARY_PREFIX}{extra_dir_id(extra)}'
            / 'Song.lrc'
        )
        assert result['lyrics'] is True
        assert dest.is_file()
        assert not track.with_suffix('.lrc').exists()
    finally:
        lyrics_mod.set_lrc_resolver(None)


def test_enrich_read_only_stores_cover_and_genre_off_the_file(
    tmp_path, monkeypatch
):
    download = tmp_path / 'downloads'
    extra = tmp_path / 'ripped'
    lyrics_root = tmp_path / 'lrc'
    download.mkdir()
    extra.mkdir()
    track = extra / 'Song.mp3'
    _write_mp3(track, title='Harbor Lights', artist='Kenji Aoki')
    tags_before = track.read_bytes()

    monkeypatch.setattr(lyrics_mod, 'can_mutate_audio', lambda _path: False)
    monkeypatch.setattr(
        'downtify.lyrics.fetch',
        lambda *_a, **_k: Lyrics(
            plain='The tide comes in',
            synced='[00:01.00]The tide comes in',
        ),
    )
    monkeypatch.setattr(
        'downtify.external_library.fetch_genre', lambda _song: 'Pop'
    )
    monkeypatch.setattr(
        'downtify.external_library._pick_artwork',
        lambda *_a, **_k: _Artwork(
            data=b'jpeg-bytes', px=300, source='itunes'
        ),
    )

    settings = {
        'download_cover_art': True,
        'download_lyrics': True,
        'lyrics_providers': ['lrclib'],
        'lyrics_lrc_beside': False,
        'lyrics_lrc_dir': str(lyrics_root),
    }

    def _resolve(audio: Path) -> Path:
        return lrc_sidecar_path(
            audio,
            settings=settings,
            download_dir=download,
            extra_dirs=(extra,),
        )

    covers = CoverArtCache(tmp_path / 'covers')
    meta = LibraryMetadataCache(tmp_path / 'meta.db')
    lyrics_mod.set_lrc_resolver(_resolve, tree_root=lambda: lyrics_root)
    try:
        ctx = LibraryContext(
            download_dir=download,
            extra_dirs=(extra,),
            metadata_cache=meta,
        )
        invalidate_library_paths_cache()
        stored = library_stored_path(track, download, extra_dirs=(extra,))
        result = enrich_imported_track(
            stored, ctx, settings=settings, cover_cache=covers
        )
        dest = (
            lyrics_root
            / f'{EXTERNAL_LIBRARY_PREFIX}{extra_dir_id(extra)}'
            / 'Song.lrc'
        )
        assert result['lyrics'] is True
        assert not result['error']
        assert result['artwork'] is True
        assert result['genre'] is True
        assert dest.is_file()
        assert track.read_bytes() == tags_before
        hit = covers.lookup(stored, track)
        assert hit is not None
        assert hit[0] == b'jpeg-bytes'
        row = meta.get_entry(stored, track)
        assert row['has_cover'] is True
        assert row['genre'] == 'Pop'
    finally:
        lyrics_mod.set_lrc_resolver(None)


def test_enrich_delay_sleeps_between_tracks(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(ext.time, 'sleep', slept.append)
    monkeypatch.setattr(
        ext,
        'enrich_imported_track',
        lambda *_a, **_k: {
            'lyrics': False,
            'artwork': False,
            'genre': False,
            'error': '',
            'lyrics_missing': False,
        },
    )
    entries = [{'file': 'a'}, {'file': 'b'}, {'file': 'c'}]
    ext._enrich_imported_tracks(
        entries,
        None,
        settings={'max_parallel_downloads': 1},
        delay_seconds=2,
    )
    assert slept == [2, 2]


def test_enrich_delay_sleeps_between_parallel_batches(monkeypatch):
    slept: list[float] = []
    started: list[str] = []
    monkeypatch.setattr(ext.time, 'sleep', slept.append)

    def _fake(_stored, _ctx, **_k):
        started.append(_stored)
        return {
            'lyrics': False,
            'artwork': False,
            'genre': False,
            'error': '',
            'lyrics_missing': False,
        }

    monkeypatch.setattr(ext, 'enrich_imported_track', _fake)
    entries = [{'file': str(index)} for index in range(7)]
    ext._enrich_imported_tracks(
        entries,
        None,
        settings={'max_parallel_downloads': 3},
        delay_seconds=5,
    )
    assert slept == [5, 5]
    assert set(started) == {str(index) for index in range(7)}


def test_enrich_delay_skips_wait_when_one_batch(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(ext.time, 'sleep', slept.append)
    monkeypatch.setattr(
        ext,
        'enrich_imported_track',
        lambda *_a, **_k: {
            'lyrics': False,
            'artwork': False,
            'genre': False,
            'error': '',
            'lyrics_missing': False,
        },
    )
    entries = [{'file': 'a'}, {'file': 'b'}, {'file': 'c'}]
    ext._enrich_imported_tracks(
        entries,
        None,
        settings={'max_parallel_downloads': 3},
        delay_seconds=5,
    )
    assert slept == []


def test_unmap_keeps_audio_drops_sidecar_and_listing(tmp_path):
    download = tmp_path / 'downloads'
    extra = tmp_path / 'ripped'
    download.mkdir()
    track = extra / 'Song.mp3'
    _write_mp3(track, title='Harbor Lights', artist='Kenji Aoki')
    sidecar = extra / 'Song.lrc'
    sidecar.write_text('[00:00.00]Hi', encoding='utf-8')
    ctx = LibraryContext(download_dir=download, extra_dirs=(extra,))
    invalidate_library_paths_cache()
    assert any(
        item.startswith(EXTERNAL_LIBRARY_PREFIX)
        for item in list_library_paths(ctx)
    )

    unmap_extra_folder(extra, download_dir=download, extra_dirs=(extra,))
    assert track.is_file()
    assert not sidecar.exists()
    gone = LibraryContext(download_dir=download, extra_dirs=())
    invalidate_library_paths_cache()
    assert not any(
        item.startswith(EXTERNAL_LIBRARY_PREFIX)
        for item in list_library_paths(gone)
    )


def test_sync_job_keeps_last_result_across_restart(tmp_path):
    path = tmp_path / 'external_sync.json'
    job = ExternalSyncJob(path)
    assert job.try_begin()
    job.finish(result={'added': 3, 'log': []})
    job.try_begin()
    restarted = ExternalSyncJob(path)
    snap = restarted.snapshot()
    assert snap['state'] == 'error'
    assert snap['error'] == 'interrupted'
    assert snap['result']['added'] == 3
