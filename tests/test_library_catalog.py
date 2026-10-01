"""Library listing includes slskd tree; media paths resolve outside download_dir."""

from __future__ import annotations

from mutagen.id3 import ID3, TALB, TIT2, TPE1, TPE2

from downtify.library_catalog import (
    LibraryContext,
    filter_library_entries,
    library_album_index,
    library_artist_index,
    library_home_summary,
    list_entries_for_stored_paths,
    list_library_entries,
    list_library_paths,
    lookup_library_songs,
    resolve_library_file,
    resolve_library_image,
    song_key,
)
from downtify.library_metadata_cache import LibraryMetadataCache
from downtify.library_paths import library_stored_path
from downtify.library_paths_cache import (
    bind_listing_store,
    drop_listing_memory_caches,
    invalidate_library_paths_cache,
)


def test_list_library_includes_slskd_tree(tmp_path):
    download_dir = tmp_path / 'downloads'
    slskd_dir = tmp_path / 'slskd'
    download_dir.mkdir()
    slskd_dir.mkdir()
    (download_dir / 'YouTube - Song.mp3').write_bytes(b'y')
    slskd_track = slskd_dir / 'peer' / 'Artist - Slskd.mp3'
    slskd_track.parent.mkdir(parents=True)
    slskd_track.write_bytes(b's')

    ctx = LibraryContext(download_dir=download_dir, slskd_dir=slskd_dir)
    paths = list_library_paths(ctx)

    assert 'YouTube - Song.mp3' in paths
    rel = library_stored_path(slskd_track, download_dir, slskd_dir)
    assert rel == 'slskd/peer/Artist - Slskd.mp3'
    assert rel in paths


def test_resolve_library_file_allows_slskd_relative_path(tmp_path):
    download_dir = tmp_path / 'downloads'
    slskd_dir = tmp_path / 'slskd'
    download_dir.mkdir()
    track = slskd_dir / 'Artist - Track.mp3'
    slskd_dir.mkdir()
    track.write_bytes(b'x')

    ctx = LibraryContext(download_dir=download_dir, slskd_dir=slskd_dir)
    stored = library_stored_path(track, download_dir, slskd_dir)
    assert stored == 'slskd/Artist - Track.mp3'
    resolved = resolve_library_file(stored, ctx)
    assert resolved == track.resolve()


def test_list_library_entries_reads_embedded_tags(tmp_path):
    download_dir = tmp_path / 'downloads'
    slskd_dir = tmp_path / 'slskd'
    download_dir.mkdir()
    slskd_dir.mkdir(parents=True, exist_ok=True)
    track = slskd_dir / 'peer' / 'scene-name.mp3'
    track.parent.mkdir(parents=True, exist_ok=True)
    tags = ID3()
    tags.add(TIT2(encoding=3, text='Real Title'))
    tags.add(TPE1(encoding=3, text='Real Artist'))
    tags.save(str(track), v2_version=3)

    cache = LibraryMetadataCache(tmp_path / 'library.db')
    ctx = LibraryContext(
        download_dir=download_dir, slskd_dir=slskd_dir, metadata_cache=cache
    )
    entries = list_library_entries(ctx)
    assert len(entries) == 1
    assert entries[0]['title'] == 'Real Title'
    assert entries[0]['artist'] == 'Real Artist'
    assert entries[0]['file'].startswith('slskd/')


def test_resolve_library_image_finds_a_playlist_cover(tmp_path):
    download_dir = tmp_path / 'downloads'
    cover = download_dir / 'My Playlist' / 'My Playlist.jpg'
    cover.parent.mkdir(parents=True)
    cover.write_bytes(b'\xff\xd8\xff')

    ctx = LibraryContext(download_dir=download_dir)
    stored = library_stored_path(cover, download_dir, None)

    assert stored == 'My Playlist/My Playlist.jpg'
    assert resolve_library_image(stored, ctx) == cover.resolve()


def test_resolve_library_image_rejects_audio_and_escapes(tmp_path):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'Track.mp3').write_bytes(b'x')
    outside = tmp_path / 'secret.jpg'
    outside.write_bytes(b'\xff\xd8\xff')

    ctx = LibraryContext(download_dir=download_dir)

    # Only images, and only inside the library.
    assert resolve_library_image('Track.mp3', ctx) is None
    assert resolve_library_image('../secret.jpg', ctx) is None
    assert resolve_library_image('/etc/hosts', ctx) is None
    assert resolve_library_image('', ctx) is None
    # And the audio resolver still refuses an image.
    assert resolve_library_file('My Playlist/My Playlist.jpg', ctx) is None


def test_resolve_library_file_legacy_dotdot_slskd_path(tmp_path):
    download_dir = tmp_path / 'downloads'
    slskd_dir = tmp_path / 'slskd'
    download_dir.mkdir()
    track = slskd_dir / 'Legacy.mp3'
    slskd_dir.mkdir()
    track.write_bytes(b'x')

    ctx = LibraryContext(download_dir=download_dir, slskd_dir=slskd_dir)
    legacy = '../slskd/Legacy.mp3'
    resolved = resolve_library_file(legacy, ctx)
    assert resolved == track.resolve()


def test_list_library_entries_does_not_re_resolve_each_file(
    tmp_path, monkeypatch
):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'Song.mp3').write_bytes(b'x')
    invalidate_library_paths_cache()
    ctx = LibraryContext(download_dir=download_dir)
    calls = {'n': 0}
    real = resolve_library_file

    def counting(stored, library_ctx):
        calls['n'] += 1
        return real(stored, library_ctx)

    monkeypatch.setattr(
        'downtify.library_catalog.resolve_library_file', counting
    )
    entries = list_library_entries(ctx)
    assert [item['file'] for item in entries] == ['Song.mp3']
    assert calls['n'] == 0


def test_list_library_entries_reuses_in_memory_rows(tmp_path, monkeypatch):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'Song.mp3').write_bytes(b'x')
    invalidate_library_paths_cache()
    ctx = LibraryContext(download_dir=download_dir)
    first = list_library_entries(ctx)
    assert first[0]['file'] == 'Song.mp3'

    def boom(_ctx):
        raise AssertionError('disk scan should be cached')

    monkeypatch.setattr(
        'downtify.library_catalog._scan_library_path_pairs', boom
    )
    second = list_library_entries(ctx)
    assert [item['file'] for item in second] == ['Song.mp3']


def test_library_home_summary_does_not_list_every_track(tmp_path):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'One.mp3').write_bytes(b'1')
    (download_dir / 'Two.mp3').write_bytes(b'2')
    invalidate_library_paths_cache()
    ctx = LibraryContext(download_dir=download_dir)
    summary = library_home_summary(ctx)
    assert summary['track_count'] == 2
    assert summary['size'] > 0


def test_list_entries_for_stored_paths_skips_unknown_files(tmp_path):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'Keep.mp3').write_bytes(b'k')
    invalidate_library_paths_cache()
    ctx = LibraryContext(download_dir=download_dir)
    rows = list_entries_for_stored_paths(
        ctx, ['Keep.mp3', 'Missing.mp3', 'Keep.mp3']
    )
    assert [item['file'] for item in rows] == ['Keep.mp3']


def test_list_library_entries_sees_a_new_file_without_invalidate(tmp_path):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'One.mp3').write_bytes(b'1')
    invalidate_library_paths_cache()
    ctx = LibraryContext(download_dir=download_dir)
    first = list_library_entries(ctx)
    assert [item['file'] for item in first] == ['One.mp3']
    (download_dir / 'Two.mp3').write_bytes(b'2')
    second = list_library_entries(ctx)
    assert sorted(item['file'] for item in second) == ['One.mp3', 'Two.mp3']


def test_list_library_entries_survives_restart_via_sqlite(
    tmp_path, monkeypatch
):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'Song.mp3').write_bytes(b'x')
    bind_listing_store(tmp_path / 'listing.db')
    try:
        invalidate_library_paths_cache()
        ctx = LibraryContext(download_dir=download_dir)
        first = list_library_entries(ctx)
        assert first[0]['file'] == 'Song.mp3'
        drop_listing_memory_caches()

        def boom(_ctx):
            raise AssertionError('disk scan should use the sqlite snapshot')

        monkeypatch.setattr(
            'downtify.library_catalog._scan_library_path_pairs', boom
        )
        second = list_library_entries(ctx)
        assert [item['file'] for item in second] == ['Song.mp3']
    finally:
        bind_listing_store(None)


def test_song_key_matches_frontend_rules():
    assert song_key(
        'Kenji Aoki, Mira Kovač', 'Harbor Lights (Remastered)'
    ) == song_key('kenji aoki', 'Harbor  Lights')
    assert song_key('Ana Luz', 'Blue Hour feat. Someone') == song_key(
        'Ana Luz', 'Blue Hour'
    )
    assert song_key('Ana Luz', 'Blue Hour (Cake Mix)') != song_key(
        'Ana Luz', 'Blue Hour'
    )


def test_filter_library_entries_artist_album_q_and_limit():
    rows = [
        {
            'file': 'a.mp3',
            'title': 'Undertow',
            'artist': 'Kenji Aoki',
            'album': 'Glass Harbor',
            'album_artist': 'Kenji Aoki',
        },
        {
            'file': 'b.mp3',
            'title': 'Blue Hour',
            'artist': 'Ana Luz',
            'album': 'Night',
            'album_artist': 'Ana Luz',
        },
        {
            'file': 'c.mp3',
            'title': 'Harbor Lights',
            'artist': 'Kenji Aoki',
            'album': 'Glass Harbor',
            'album_artist': 'Kenji Aoki',
        },
    ]
    assert [
        item['file']
        for item in filter_library_entries(rows, artist='Kenji Aoki')
    ] == ['a.mp3', 'c.mp3']
    assert [
        item['file']
        for item in filter_library_entries(
            rows, artist='Kenji Aoki', album='Glass Harbor', q='lights'
        )
    ] == ['c.mp3']
    assert [
        item['file'] for item in filter_library_entries(rows, q='kovac harbor')
    ] == []
    assert [
        item['file'] for item in filter_library_entries(rows, q='harbor kenji')
    ] == ['a.mp3', 'c.mp3']
    assert len(filter_library_entries(rows, limit=1)) == 1


def test_library_indexes_omit_track_rows(tmp_path):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()

    def write(name, title, artist, album):
        path = download_dir / name
        tags = ID3()
        tags.add(TIT2(encoding=3, text=title))
        tags.add(TPE1(encoding=3, text=artist))
        tags.add(TPE2(encoding=3, text=artist))
        tags.add(TALB(encoding=3, text=album))
        tags.save(str(path), v2_version=3)

    write('one.mp3', 'Undertow', 'Kenji Aoki', 'Glass Harbor')
    write('two.mp3', 'Harbor Lights', 'Kenji Aoki', 'Glass Harbor')
    write('three.mp3', 'Blue Hour', 'Ana Luz', 'Night')
    invalidate_library_paths_cache()
    cache = LibraryMetadataCache(tmp_path / 'library.db')
    ctx = LibraryContext(download_dir=download_dir, metadata_cache=cache)
    albums = library_album_index(ctx)
    assert 'tracks' not in albums[0]
    harbor = next(row for row in albums if row['title'] == 'Glass Harbor')
    assert harbor['track_count'] == 2
    assert harbor['artist'] == 'Kenji Aoki'
    artists = library_artist_index(ctx, {'one.mp3'})
    kenji = next(row for row in artists if row['name'] == 'Kenji Aoki')
    assert kenji['track_count'] == 2
    assert kenji['album_count'] == 1
    assert kenji['liked_count'] == 1
    found = lookup_library_songs(
        ctx,
        [{'artists': ['Kenji Aoki'], 'name': 'Undertow (Remastered)'}],
    )
    assert [item['title'] for item in found] == ['Undertow']
