"""Liking songs, and the playlist that lists the liked ones."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException

from downtify import api, likes, m3u
from downtify.downloader import Downloader
from downtify.library_catalog import LibraryContext
from downtify.likes import (
    LIKED_PLAYLIST_NAME,
    LikedTracks,
    is_liked_playlist,
    remap_moved,
    sync_liked_playlist,
)
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex

# ── helpers ────────────────────────────────────────────────────────────


def _track(base: Path, name: str, content: bytes = b'audio') -> Path:
    path = base / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _store(tmp_path: Path) -> LikedTracks:
    return LikedTracks(tmp_path / 'lib.db')


def _liked_m3u(download_dir: Path) -> Path:
    return download_dir / 'Playlists' / f'{LIKED_PLAYLIST_NAME}.m3u'


class _Body:
    def __init__(self, payload: Any = None):
        self._payload = payload

    async def json(self) -> Any:
        return self._payload


@pytest.fixture
def app_state(monkeypatch, tmp_path):
    """The bits of ``api.state`` liking touches, pointed at ``tmp_path``."""

    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    monkeypatch.setattr(
        api.state,
        'downloader',
        Downloader(download_dir=downloads, audio_format='mp3'),
    )
    monkeypatch.setattr(api.state, 'settings', {})
    monkeypatch.setattr(api.state, 'likes', LikedTracks(tmp_path / 'lib.db'))
    monkeypatch.setattr(api.state, 'loop', None)
    return downloads


def _like(file: str, liked: bool = True) -> dict[str, Any]:
    return asyncio.run(api.set_like(_Body({'file': file, 'liked': liked})))


# ── the store ──────────────────────────────────────────────────────────


def test_a_like_is_kept_and_counted(tmp_path):
    store = _store(tmp_path)

    assert store.like('a.mp3', title='A', artist='X', duration=200) is True

    assert store.count() == 1
    assert store.paths() == ['a.mp3']
    row = store.rows()[0]
    assert (row['title'], row['artist'], row['duration']) == ('A', 'X', 200.0)


def test_the_newest_like_comes_first(tmp_path):
    store = _store(tmp_path)
    for name in ('a.mp3', 'b.mp3', 'c.mp3'):
        store.like(name)

    assert store.paths() == ['c.mp3', 'b.mp3', 'a.mp3']


def test_liking_twice_keeps_the_original_place(tmp_path):
    store = _store(tmp_path)
    store.like('a.mp3')
    store.like('b.mp3')

    # A double tap must not move the song to the top.
    assert store.like('a.mp3') is False

    assert store.paths() == ['b.mp3', 'a.mp3']
    assert store.count() == 2


def test_unliking_reports_whether_there_was_a_like(tmp_path):
    store = _store(tmp_path)
    store.like('a.mp3')

    assert store.unlike('a.mp3') is True
    assert store.unlike('a.mp3') is False
    assert store.count() == 0


def test_backslashes_in_a_path_are_the_same_song(tmp_path):
    store = _store(tmp_path)
    store.like('Album\\a.mp3')

    assert store.paths() == ['Album/a.mp3']
    assert store.unlike('Album/a.mp3') is True


def test_clearing_removes_every_like(tmp_path):
    store = _store(tmp_path)
    store.like('a.mp3')
    store.like('b.mp3')

    assert store.clear() == 2
    assert store.count() == 0


def test_likes_survive_reopening_the_database(tmp_path):
    _store(tmp_path).like('a.mp3', title='A')

    assert _store(tmp_path).paths() == ['a.mp3']


def test_repointing_a_like_keeps_its_place(tmp_path):
    store = _store(tmp_path)
    store.like('old.mp3')
    store.like('other.mp3')

    assert store.update_path('old.mp3', 'new/old.mp3') is True

    assert store.paths() == ['other.mp3', 'new/old.mp3']


def test_repointing_onto_an_already_liked_path_drops_the_duplicate(tmp_path):
    store = _store(tmp_path)
    store.like('old.mp3')
    store.like('new.mp3')

    assert store.update_path('old.mp3', 'new.mp3') is True

    assert store.paths() == ['new.mp3']


def test_the_reserved_name_is_recognised_however_it_is_written():
    assert is_liked_playlist(LIKED_PLAYLIST_NAME)
    assert is_liked_playlist(f'  {LIKED_PLAYLIST_NAME.upper()} ')
    assert not is_liked_playlist('Liked songs')
    assert not is_liked_playlist('')
    assert not is_liked_playlist(None)


# ── the playlist file ──────────────────────────────────────────────────


def test_the_playlist_lists_the_liked_songs_newest_first(tmp_path):
    downloads = tmp_path / 'downloads'
    _track(downloads, 'Old Artist - Old.mp3')
    _track(downloads, 'New Artist - New.mp3')
    store = _store(tmp_path)
    store.like(
        'Old Artist - Old.mp3', title='Old', artist='Old Artist', duration=200
    )
    store.like(
        'New Artist - New.mp3', title='New', artist='New Artist', duration=180
    )

    path = sync_liked_playlist(store, downloads)

    assert path == _liked_m3u(downloads)
    lines = path.read_text(encoding='utf-8').splitlines()
    assert lines == [
        '#EXTM3U',
        '#EXTINF:180,New Artist - New',
        '../New Artist - New.mp3',
        '#EXTINF:200,Old Artist - Old',
        '../Old Artist - Old.mp3',
    ]


def test_there_is_no_playlist_until_something_is_liked(tmp_path):
    downloads = tmp_path / 'downloads'
    downloads.mkdir()

    assert sync_liked_playlist(_store(tmp_path), downloads) is None
    assert not _liked_m3u(downloads).exists()


def test_the_playlist_appears_with_the_first_like_and_goes_with_the_last(
    tmp_path,
):
    downloads = tmp_path / 'downloads'
    _track(downloads, 'a.mp3')
    store = _store(tmp_path)

    store.like('a.mp3', title='A')
    sync_liked_playlist(store, downloads)
    assert _liked_m3u(downloads).is_file()

    store.unlike('a.mp3')
    assert sync_liked_playlist(store, downloads) is None
    # Removed, not left behind stale: the writer won't write an empty one.
    assert not _liked_m3u(downloads).exists()


def test_a_song_that_went_missing_is_skipped_but_stays_liked(tmp_path):
    downloads = tmp_path / 'downloads'
    _track(downloads, 'here.mp3')
    store = _store(tmp_path)
    store.like('gone.mp3', title='Gone')
    store.like('here.mp3', title='Here')

    sync_liked_playlist(store, downloads)

    text = _liked_m3u(downloads).read_text(encoding='utf-8')
    assert '../here.mp3' in text
    assert 'gone.mp3' not in text
    # An unmounted drive shouldn't cost anyone their hearts.
    assert store.paths() == ['here.mp3', 'gone.mp3']


def test_when_every_liked_file_is_missing_the_playlist_is_removed(tmp_path):
    downloads = tmp_path / 'downloads'
    _track(downloads, 'a.mp3')
    store = _store(tmp_path)
    store.like('a.mp3', title='A')
    sync_liked_playlist(store, downloads)
    (downloads / 'a.mp3').unlink()

    assert sync_liked_playlist(store, downloads) is None

    assert not _liked_m3u(downloads).exists()
    assert store.count() == 1  # still liked; back when the file is


def test_slskd_files_left_in_place_are_listed_too(tmp_path):
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    slskd = tmp_path / 'slskd'
    _track(slskd, 'peer/Song.mp3')
    store = _store(tmp_path)
    store.like('slskd/peer/Song.mp3', title='Song')

    path = sync_liked_playlist(store, downloads, slskd)

    assert path is not None
    assert 'Song.mp3' in path.read_text(encoding='utf-8')


def test_a_downloaded_playlist_with_a_similar_name_is_not_overwritten(
    tmp_path,
):
    # Spotify playlists called "Liked songs" are everywhere; the reserved
    # name means neither can write over the other's file.
    downloads = tmp_path / 'downloads'
    _track(downloads, 'a.mp3')
    _track(downloads, 'b.mp3')
    store = _store(tmp_path)
    store.like('a.mp3', title='A')
    sync_liked_playlist(store, downloads)

    m3u.write_m3u(
        downloads,
        'Liked songs',
        [{'filename': 'b.mp3', 'title': 'B'}],
    )

    liked = _liked_m3u(downloads).read_text(encoding='utf-8')
    assert 'a.mp3' in liked
    assert 'b.mp3' not in liked
    assert (downloads / 'Playlists' / 'Liked songs.m3u').is_file()


# ── following moved files ──────────────────────────────────────────────


def _ctx(tmp_path: Path) -> LibraryContext:
    return LibraryContext(download_dir=tmp_path / 'downloads')


def test_a_like_follows_its_file_when_it_is_moved(tmp_path):
    downloads = tmp_path / 'downloads'
    original = _track(downloads, 'Song.mp3', b'same bytes')
    store = _store(tmp_path)
    store.like(
        'Song.mp3', content_key=likes.content_key_for(original), title='Song'
    )
    moved = downloads / 'Sorted' / 'Song.mp3'
    moved.parent.mkdir()
    original.rename(moved)

    assert remap_moved(store, _ctx(tmp_path)) == 1

    assert store.paths() == ['Sorted/Song.mp3']


def test_a_like_stays_put_while_its_file_is_still_there(tmp_path):
    downloads = tmp_path / 'downloads'
    original = _track(downloads, 'Song.mp3', b'same bytes')
    store = _store(tmp_path)
    store.like('Song.mp3', content_key=likes.content_key_for(original))
    # A same-named, same-sized twin elsewhere shares the content key.
    _track(downloads, 'Copy/Song.mp3', b'same bytes')

    assert remap_moved(store, _ctx(tmp_path)) == 0

    assert store.paths() == ['Song.mp3']


def test_a_like_without_a_content_key_is_left_alone(tmp_path):
    store = _store(tmp_path)
    store.like('a.mp3')
    (tmp_path / 'downloads').mkdir()

    assert remap_moved(store, _ctx(tmp_path)) == 0


# ── the endpoints ──────────────────────────────────────────────────────


def test_liking_a_library_song_creates_the_playlist(app_state):
    _track(app_state, 'Artist - Song.mp3')

    result = _like('Artist - Song.mp3')

    assert result == {'file': 'Artist - Song.mp3', 'liked': True, 'count': 1}
    assert _liked_m3u(app_state).is_file()
    assert api.get_likes()['files'] == ['Artist - Song.mp3']


def test_unliking_the_only_song_removes_the_playlist(app_state):
    _track(app_state, 'a.mp3')
    _like('a.mp3')

    result = _like('a.mp3', liked=False)

    assert result['count'] == 0
    assert not _liked_m3u(app_state).exists()


def test_the_same_request_twice_changes_nothing(app_state):
    _track(app_state, 'a.mp3')

    first = _like('a.mp3')
    second = _like('a.mp3')

    assert first == second
    assert api.get_likes()['count'] == 1
    assert _like('a.mp3', liked=False)['count'] == 0
    assert _like('a.mp3', liked=False)['count'] == 0


def test_only_songs_in_the_library_can_be_liked(app_state, tmp_path):
    (tmp_path / 'secret.mp3').write_bytes(b'x')
    _track(app_state, 'notes.txt')

    for bad in ('missing.mp3', '../secret.mp3', 'notes.txt', '/etc/hosts'):
        with pytest.raises(HTTPException) as exc:
            _like(bad)
        assert exc.value.status_code == 404, bad

    assert api.get_likes()['count'] == 0


def test_a_like_needs_a_file(app_state):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.set_like(_Body({'liked': True})))

    assert exc.value.status_code == 400


def test_a_like_on_a_file_that_vanished_can_still_be_cleared(app_state):
    _track(app_state, 'a.mp3')
    _like('a.mp3')
    (app_state / 'a.mp3').unlink()

    assert _like('a.mp3', liked=False)['count'] == 0


def test_the_snapshot_taken_at_like_time_labels_the_playlist(app_state):
    _track(app_state, 'Some Artist - Some Song.mp3')

    _like('Some Artist - Some Song.mp3')

    # No readable tags on this stand-in file, so the file name stands in.
    assert 'Some Artist - Some Song' in _liked_m3u(app_state).read_text(
        encoding='utf-8'
    )


def test_clearing_unlikes_everything_and_removes_the_playlist(app_state):
    for name in ('a.mp3', 'b.mp3'):
        _track(app_state, name)
        _like(name)

    result = asyncio.run(api.clear_likes_endpoint())

    assert result == {'cleared': 2, 'count': 0}
    assert api.get_likes()['count'] == 0
    assert not _liked_m3u(app_state).exists()
    # Only the hearts went: no song was deleted.
    assert (app_state / 'a.mp3').is_file()
    assert (app_state / 'b.mp3').is_file()


def test_liking_before_the_store_is_ready_is_an_error(monkeypatch):
    monkeypatch.setattr(api.state, 'likes', None)

    with pytest.raises(HTTPException) as exc:
        api.get_likes()

    assert exc.value.status_code == 500


# ── deleting must never delete music ───────────────────────────────────


def test_deleting_the_liked_playlist_only_unlikes_never_deletes_audio(
    app_state, monkeypatch, tmp_path
):
    # With the real delete machinery in place, so that without the guard
    # this test really reaches the folder sweep and deletes files, rather
    # than stopping early for lack of a catalog.
    monkeypatch.setattr(
        api.state, 'playlist_catalog', PlaylistCatalog(tmp_path / 'lib.db')
    )
    monkeypatch.setattr(
        api.state, 'track_index', TrackIndex(tmp_path / 'lib.db')
    )
    # A folder named exactly like the playlist is what a normal playlist
    # delete sweeps as "the playlist's tracks".
    lookalike = _track(app_state, f'{LIKED_PLAYLIST_NAME}/Kept.mp3')
    elsewhere = _track(app_state, 'Artist - Song.mp3')
    _like('Artist - Song.mp3')
    _like(f'{LIKED_PLAYLIST_NAME}/Kept.mp3')

    result = asyncio.run(
        api.delete_library_playlist_endpoint(playlist_name=LIKED_PLAYLIST_NAME)
    )

    assert result['ok'] is True
    assert result['files'] == []
    assert result['deleted_count'] == 0
    assert lookalike.is_file()
    assert elsewhere.is_file()
    assert api.get_likes()['count'] == 0
    assert not _liked_m3u(app_state).exists()


def test_the_guard_ignores_case_and_padding(app_state):
    kept = _track(app_state, 'a.mp3')
    _like('a.mp3')

    asyncio.run(
        api.delete_library_playlist_endpoint(
            playlist_name=f' {LIKED_PLAYLIST_NAME.lower()} '
        )
    )

    assert kept.is_file()
    assert api.get_likes()['count'] == 0


def test_other_playlists_still_go_through_the_normal_delete(
    monkeypatch, app_state
):
    seen: list[str] = []

    def fake_delete(name, download_dir, settings, state):
        seen.append(name)
        return {'ok': True, 'playlist': name, 'files': ['x.mp3']}

    monkeypatch.setattr(api, 'delete_playlist_from_library', fake_delete)

    result = asyncio.run(
        api.delete_library_playlist_endpoint(playlist_name='Road Trip')
    )

    assert seen == ['Road Trip']
    assert result['files'] == ['x.mp3']


# ── other things that change the library ───────────────────────────────


def test_deleting_a_liked_track_unlikes_it_and_rewrites_the_playlist(
    app_state,
):
    _track(app_state, 'a.mp3')
    _track(app_state, 'b.mp3')
    _like('a.mp3')
    _like('b.mp3')
    (app_state / 'a.mp3').unlink()

    asyncio.run(api.after_library_delete({'a.mp3': {'deleted': True}}, {}))

    assert api.get_likes()['files'] == ['b.mp3']
    text = _liked_m3u(app_state).read_text(encoding='utf-8')
    assert 'b.mp3' in text
    assert 'a.mp3' not in text


def test_deleting_the_last_liked_track_takes_the_playlist_with_it(app_state):
    _track(app_state, 'a.mp3')
    _like('a.mp3')
    (app_state / 'a.mp3').unlink()

    asyncio.run(api.after_library_delete({'a.mp3': {'deleted': True}}, {}))

    assert api.get_likes()['count'] == 0
    assert not _liked_m3u(app_state).exists()


def test_deleting_a_song_that_was_not_liked_leaves_the_playlist_alone(
    app_state,
):
    _track(app_state, 'liked.mp3')
    _track(app_state, 'other.mp3')
    _like('liked.mp3')
    before = _liked_m3u(app_state).stat().st_mtime_ns
    (app_state / 'other.mp3').unlink()

    asyncio.run(api.after_library_delete({'other.mp3': {'deleted': True}}, {}))

    assert api.get_likes()['files'] == ['liked.mp3']
    assert _liked_m3u(app_state).stat().st_mtime_ns == before


def test_the_playlist_is_rewritten_at_startup_if_the_file_was_removed(
    app_state,
):
    _track(app_state, 'a.mp3')
    _like('a.mp3')
    _liked_m3u(app_state).unlink()

    api._sync_liked_playlist()

    assert _liked_m3u(app_state).is_file()
