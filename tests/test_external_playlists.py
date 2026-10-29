import pytest

from downtify.external_playlists import (
    ExternalPlaylistImports,
    discover_external_playlists,
    read_external_playlist,
)
from downtify.library_catalog import LibraryContext
from downtify.library_paths import library_stored_path
from downtify.playlist_catalog import ManualPlaylistOwners


@pytest.fixture
def collection(tmp_path):
    downloads = tmp_path / 'downloads'
    external = tmp_path / 'external'
    downloads.mkdir()
    external.mkdir()
    for name in ('one.mp3', 'two.flac'):
        (external / name).write_bytes(b'audio fixture')
    return LibraryContext(
        download_dir=downloads, extra_dirs=(external,)
    ), external


def test_relative_absolute_bom_and_order(collection):
    ctx, root = collection
    source = root / 'Mix.M3U8'
    source.write_text(
        '\ufeff#EXTM3U\ntwo.flac\n'
        + (root / 'one.mp3').as_posix()
        + '\ntwo.flac\n',
        encoding='utf-8',
    )
    before = source.read_bytes()
    item = read_external_playlist(source, root, ctx)
    assert item.files == tuple(
        library_stored_path(
            root / name, ctx.download_dir, extra_dirs=ctx.extra_dirs
        )
        for name in ('two.flac', 'one.mp3')
    )
    assert item.duplicates == 1
    assert item.missing == 0
    assert source.read_bytes() == before


def test_outside_paths_urls_non_audio_and_missing_are_not_imported(
    collection, tmp_path
):
    ctx, root = collection
    (tmp_path / 'outside.mp3').write_bytes(b'private')
    (root / '.env').write_text('not audio')
    source = root / 'unsafe.m3u'
    source.write_text(
        '#EXTM3U\n../outside.mp3\nhttps://example.org/song.mp3\n.env\nmissing.mp3\none.mp3\n'
    )
    item = read_external_playlist(source, root, ctx)
    assert len(item.files) == 1
    assert item.missing == 4


def test_import_is_selected_owned_idempotent_and_keeps_sources(
    collection, tmp_path
):
    ctx, root = collection
    source = root / 'Mix.m3u'
    source.write_text('#EXTM3U\none.mp3\ntwo.flac\n')
    (root / 'Other.m3u').write_text('#EXTM3U\none.mp3\n')
    before = {path.name: path.read_bytes() for path in root.iterdir()}
    found, warnings, truncated = discover_external_playlists(ctx)
    assert len(found) == 2
    assert not warnings
    assert not truncated
    store = ExternalPlaylistImports(tmp_path / 'library.db')
    item = next(candidate for candidate in found if candidate.name == 'Mix')
    result = store.import_snapshot(ctx, 7, item, list(item.files))
    assert result['status'] == 'added'
    assert result['files'] == list(item.files)
    assert (
        ManualPlaylistOwners(tmp_path / 'library.db').owner_map()['mix'] == 7
    )
    assert (
        store.import_snapshot(ctx, 7, item, list(item.files))['status']
        == 'already_present'
    )
    assert len(list(ctx.download_dir.rglob('*.m3u'))) == 1
    assert {path.name: path.read_bytes() for path in root.iterdir()} == before


def test_equal_names_are_not_overwritten_and_imports_are_per_account(
    collection, tmp_path
):
    ctx, root = collection
    source = root / 'Mix.m3u'
    source.write_text('one.mp3\n')
    item = read_external_playlist(source, root, ctx)
    store = ExternalPlaylistImports(tmp_path / 'library.db')
    first = store.import_snapshot(ctx, 7, item, list(item.files))
    second = store.import_snapshot(ctx, 8, item, list(item.files))
    assert first['name'] != second['name']
    store.rename(first['name'], 'Renamed')
    assert store.imported(7)[item.source_id] == 'Renamed'
    store.forget('Renamed')
    assert not store.imported(7)
    assert store.imported(8)


def test_m3u8_invalid_utf8_is_rejected(collection):
    ctx, root = collection
    path = root / 'bad.m3u8'
    path.write_bytes(b'\xffinvalid')
    with pytest.raises(ValueError, match='UTF-8'):
        read_external_playlist(path, root, ctx)


def test_offline_external_folder_is_reported(collection):
    ctx, root = collection
    offline = root / 'absent'
    missing_ctx = LibraryContext(
        download_dir=ctx.download_dir, extra_dirs=(offline,)
    )
    found, warnings, truncated = discover_external_playlists(missing_ctx)
    assert not found
    assert warnings
    assert not truncated


def test_deemix_generic_filename_uses_folder_and_relative_parent_paths(
    collection,
):
    ctx, root = collection
    folder = root / 'Evening mix'
    folder.mkdir()
    source = folder / 'playlist.m3u8'
    source.write_text(
        '#EXTM3U\n../two.flac\n../missing.flac\n', encoding='utf-8'
    )
    item = read_external_playlist(source, root, ctx)
    assert item.name == 'Evening mix'
    assert len(item.files) == 1
    assert item.missing == 1


def test_empty_playlist_can_be_previewed(collection):
    ctx, root = collection
    source = root / 'Empty.m3u8'
    source.write_text('#EXTM3U\n', encoding='utf-8')
    item = read_external_playlist(source, root, ctx)
    assert item.files == ()
    assert item.missing == 0
