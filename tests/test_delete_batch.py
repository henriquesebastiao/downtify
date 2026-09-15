"""Tests for bulk deletion: ``main._delete_track_file`` (factored out of
``DELETE /delete``, unchanged behavior) and ``main._delete_tracks_batch``
(``DELETE /delete/batch``).

Powers the Library page's multi-select — deleting many tracks matching
the active filter used to mean one request per file, which is
impractical for anything beyond a handful. Each file in a batch is
still deleted independently through the same path as a single delete
(sidecars, orphaned cover, empty-folder pruning all included), so one
bad path or an already-gone file never stops the rest.

``DELETE /delete`` and ``DELETE /delete/batch`` live inside
``main.build_app()`` alongside the other file-management routes, none
of which have route-level tests in this suite (no TestClient fixture).
Both underlying functions are plain
module-level functions, so they're tested directly here.
"""

from __future__ import annotations

import asyncio

import pytest

import main
from downtify import api
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex


def _track(base, name: str, content: bytes = b'audio') -> None:
    path = base / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


# ── _delete_track_file (still the single-file behavior) ─────────────────────


def test_delete_track_file_removes_the_file(tmp_path):
    _track(tmp_path, 'Song.mp3')

    result = main._delete_track_file('Song.mp3', tmp_path)

    assert result == {'deleted': True}
    assert not (tmp_path / 'Song.mp3').exists()


def test_delete_track_file_missing_file(tmp_path):
    result = main._delete_track_file('Nope.mp3', tmp_path)
    assert result == {'deleted': False, 'error': 'File not found'}


def test_delete_track_file_rejects_path_traversal(tmp_path):
    result = main._delete_track_file('../outside.mp3', tmp_path)
    assert result == {'deleted': False, 'error': 'Invalid path'}


def test_delete_track_file_also_prunes_sidecars_and_empty_folder(tmp_path):
    # Full path: sidecar + cover + folder pruning all still apply per file.
    _track(tmp_path, 'Some Album/Song.mp3')
    (tmp_path / 'Some Album' / 'Song.lrc').write_text('x', encoding='utf-8')
    (tmp_path / 'Some Album' / 'cover.jpg').write_bytes(b'jpeg')

    result = main._delete_track_file('Some Album/Song.mp3', tmp_path)

    assert result == {'deleted': True}
    assert not (tmp_path / 'Some Album').exists()


# ── _delete_tracks_batch ─────────────────────────────────────────────────────


def test_batch_deletes_every_file(tmp_path):
    _track(tmp_path, 'A.mp3')
    _track(tmp_path, 'B.mp3')
    _track(tmp_path, 'C.mp3')

    result = main._delete_tracks_batch(['A.mp3', 'B.mp3', 'C.mp3'], tmp_path)

    assert result['deleted_count'] == 3
    assert result['failed_count'] == 0
    assert all(r['deleted'] for r in result['results'].values())
    assert not any(tmp_path.iterdir())


def test_batch_continues_past_a_missing_file(tmp_path):
    _track(tmp_path, 'A.mp3')
    _track(tmp_path, 'C.mp3')

    result = main._delete_tracks_batch(['A.mp3', 'B.mp3', 'C.mp3'], tmp_path)

    assert result['deleted_count'] == 2
    assert result['failed_count'] == 1
    assert result['results']['A.mp3'] == {'deleted': True}
    assert result['results']['B.mp3'] == {
        'deleted': False,
        'error': 'File not found',
    }
    assert result['results']['C.mp3'] == {'deleted': True}


def test_batch_deletes_an_entire_album_folder(tmp_path):
    # Selecting "this album" in the UI sends every track in it.
    _track(tmp_path, 'My Album/Track 1.mp3')
    _track(tmp_path, 'My Album/Track 2.mp3')
    (tmp_path / 'My Album' / 'cover.jpg').write_bytes(b'jpeg')

    result = main._delete_tracks_batch(
        ['My Album/Track 1.mp3', 'My Album/Track 2.mp3'], tmp_path
    )

    assert result['deleted_count'] == 2
    # Cover survives after the first track (second still needs it) and
    # the whole now-empty album folder is pruned once the second is gone.
    assert not (tmp_path / 'My Album').exists()


def test_batch_dedupes_repeated_paths(tmp_path):
    _track(tmp_path, 'A.mp3')

    result = main._delete_tracks_batch(['A.mp3', 'A.mp3'], tmp_path)

    # One real deletion, not a spurious "File not found" on the repeat.
    assert result['deleted_count'] == 1
    assert result['failed_count'] == 0
    assert len(result['results']) == 1


def test_batch_rejects_path_traversal_per_file(tmp_path):
    _track(tmp_path, 'A.mp3')

    result = main._delete_tracks_batch(['A.mp3', '../evil.mp3'], tmp_path)

    assert result['deleted_count'] == 1
    assert result['results']['../evil.mp3'] == {
        'deleted': False,
        'error': 'Invalid path',
    }


def test_batch_empty_list_is_a_no_op(tmp_path):
    result = main._delete_tracks_batch([], tmp_path)
    assert result == {'deleted_count': 0, 'failed_count': 0, 'results': {}}


def test_batch_over_the_limit_raises_value_error(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'MAX_BATCH_DELETE', 3)
    with pytest.raises(ValueError, match='Cannot delete more than 3'):
        main._delete_tracks_batch(['a', 'b', 'c', 'd'], tmp_path)


def test_batch_at_exactly_the_limit_is_allowed(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'MAX_BATCH_DELETE', 3)
    result = main._delete_tracks_batch(['a', 'b', 'c'], tmp_path)
    assert result['failed_count'] == 3  # none of them exist, but no raise


# ── slskd downloads left in place (PR #182) ────────────────────────────────


def test_delete_track_file_resolves_slskd_paths_against_slskd_dir(tmp_path):
    base = tmp_path / 'downloads'
    slskd = tmp_path / 'slskd'
    base.mkdir()
    _track(slskd, 'peer/Album/01 - Song.mp3')
    _track(slskd, 'peer/Album/01 - Song.lrc', b'[00:01.00]la')

    result = main._delete_track_file(
        'slskd/peer/Album/01 - Song.mp3', base.resolve(), slskd
    )

    assert result == {'deleted': True}
    assert not (slskd / 'peer').exists()
    # Pruning stops at the slskd folder itself.
    assert slskd.is_dir()


def test_delete_track_file_rejects_traversal_out_of_slskd_dir(tmp_path):
    base = tmp_path / 'downloads'
    slskd = tmp_path / 'slskd'
    base.mkdir()
    slskd.mkdir()
    _track(tmp_path, 'secret.mp3')

    result = main._delete_track_file(
        'slskd/../secret.mp3', base.resolve(), slskd
    )

    assert result == {'deleted': False, 'error': 'Invalid path'}
    assert (tmp_path / 'secret.mp3').exists()


def test_slskd_paths_without_slskd_dir_stay_under_downloads(tmp_path):
    _track(tmp_path, 'slskd/local.mp3')

    result = main._delete_track_file('slskd/local.mp3', tmp_path)

    assert result == {'deleted': True}


def test_after_library_delete_forgets_files_and_reports_playlists(
    tmp_path, monkeypatch
):
    track = tmp_path / 'Mix' / 'Artist - Song.mp3'
    _track(tmp_path, 'Mix/Artist - Song.mp3')
    song = {
        'song_id': '4uLU6hMCjMI75M1A2tKUQC',
        'name': 'Song',
        'artists': ['Artist'],
    }
    db = tmp_path / 'library.db'
    catalog = PlaylistCatalog(db)
    catalog.ensure_playlist('Mix')
    catalog.upsert_track('Mix', song, 'Mix/Artist - Song.mp3', track)
    index = TrackIndex(db)
    index.register_song(song, 'Mix/Artist - Song.mp3', full_path=track)
    monkeypatch.setattr(api.state, 'playlist_catalog', catalog)
    monkeypatch.setattr(api.state, 'track_index', index)
    monkeypatch.setattr(api.state, 'navidrome_index', None)
    monkeypatch.setattr(api.state, 'metadata_cache', None)
    monkeypatch.setattr(api.state, 'cover_cache', None)
    track.unlink()

    response = asyncio.run(
        api.after_library_delete(
            {'Mix/Artist - Song.mp3': {'deleted': True}}, {'deleted': True}
        )
    )

    assert response == {'deleted': True, 'playlists_affected': ['Mix']}
    assert catalog.list_tracks('Mix') == []
    assert index.lookup('4uLU6hMCjMI75M1A2tKUQC') is None
