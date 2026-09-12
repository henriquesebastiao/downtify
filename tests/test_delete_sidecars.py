"""Tests for the cleanup ``DELETE /delete`` does after removing a track:
``main._delete_lrc_sidecar``, ``main._delete_album_cover_if_orphaned``
and ``main._prune_empty_parent_dirs``.

Deleting a track through the Library page used to only remove the audio
file, leaving things behind:

* the ``.lrc`` lyrics sidecar (see ``downtify/downloader.py:embed_lyrics``),
  sharing the audio file's basename;
* under *Organize by album*, the album's shared ``cover.jpg`` (see
  ``Downloader._save_album_cover``) — but only once no other track in
  that same folder still needs it;
* the (now possibly empty) per-playlist/artist/album folder itself, and
  any of its ancestors that are also now empty, up to but not including
  the downloads directory root.

``DELETE /delete`` itself lives inside ``main.build_app()`` alongside
the other file-management routes, none of which have route-level tests
in this suite (no TestClient/build_app fixture yet — see
test_main_tracks.py). All three cleanup functions are plain
module-level functions, so they're tested directly here.
"""

from __future__ import annotations

from pathlib import Path

import main

# ── _delete_lrc_sidecar ──────────────────────────────────────────────────────


def test_delete_lrc_sidecar_removes_matching_lrc(tmp_path):
    audio = tmp_path / 'Artist - Song.mp3'
    audio.write_bytes(b'audio')
    lrc = tmp_path / 'Artist - Song.lrc'
    lrc.write_text('[00:00.00]La la la', encoding='utf-8')

    main._delete_lrc_sidecar(audio)

    assert not lrc.exists()


def test_delete_lrc_sidecar_no_op_when_no_lyrics(tmp_path):
    audio = tmp_path / 'Artist - Song.mp3'
    audio.write_bytes(b'audio')

    # Must not raise just because there was never a .lrc to begin with.
    main._delete_lrc_sidecar(audio)


def test_delete_lrc_sidecar_does_not_touch_other_files(tmp_path):
    audio = tmp_path / 'Artist - Song.mp3'
    audio.write_bytes(b'audio')
    other_lrc = tmp_path / 'Other Song.lrc'
    other_lrc.write_text('unrelated', encoding='utf-8')

    main._delete_lrc_sidecar(audio)

    assert other_lrc.exists()


def test_delete_lrc_sidecar_survives_unremovable_file(tmp_path, monkeypatch):
    audio = tmp_path / 'Artist - Song.mp3'
    audio.write_bytes(b'audio')
    lrc = tmp_path / 'Artist - Song.lrc'
    lrc.write_text('lyrics', encoding='utf-8')

    def _raise(*_a, **_kw):
        raise OSError('permission denied')

    monkeypatch.setattr(Path, 'unlink', _raise)

    # Must not propagate — the audio file's own deletion already
    # succeeded by the time this runs.
    main._delete_lrc_sidecar(audio)


# ── _delete_album_cover_if_orphaned ──────────────────────────────────────────


def _album_folder(tmp_path, *track_names: str) -> Path:
    folder = tmp_path / 'Some Album'
    folder.mkdir()
    for name in track_names:
        (folder / name).write_bytes(b'audio')
    return folder


def test_cover_deleted_when_last_track_in_folder_is_gone(tmp_path):
    folder = _album_folder(tmp_path, 'Track 1.mp3')
    cover = folder / 'cover.jpg'
    cover.write_bytes(b'jpeg data')
    deleted_track = folder / 'Track 1.mp3'

    # Mirrors what delete_download does: audio file is unlinked first...
    deleted_track.unlink()
    # ...then cleanup runs.
    main._delete_album_cover_if_orphaned(deleted_track)

    assert not cover.exists()


def test_cover_kept_when_another_track_remains(tmp_path):
    folder = _album_folder(tmp_path, 'Track 1.mp3', 'Track 2.mp3')
    cover = folder / 'cover.jpg'
    cover.write_bytes(b'jpeg data')
    deleted_track = folder / 'Track 1.mp3'

    deleted_track.unlink()
    main._delete_album_cover_if_orphaned(deleted_track)

    assert cover.exists()
    assert (folder / 'Track 2.mp3').exists()


def test_cover_kept_when_a_different_audio_extension_remains(tmp_path):
    # A FLAC re-download of the same track counts as "still needs it".
    folder = _album_folder(tmp_path, 'Track 1.mp3', 'Track 1.flac')
    cover = folder / 'cover.jpg'
    cover.write_bytes(b'jpeg data')
    deleted_track = folder / 'Track 1.mp3'

    deleted_track.unlink()
    main._delete_album_cover_if_orphaned(deleted_track)

    assert cover.exists()


def test_no_op_when_there_is_no_cover(tmp_path):
    folder = _album_folder(tmp_path, 'Track 1.mp3')
    deleted_track = folder / 'Track 1.mp3'
    deleted_track.unlink()

    # Must not raise just because organize-by-album was never on.
    main._delete_album_cover_if_orphaned(deleted_track)


def test_cover_ignores_lrc_and_m3u_siblings(tmp_path):
    # A leftover .lrc or .m3u must not count as a reason to keep the cover.
    folder = _album_folder(tmp_path, 'Track 1.mp3')
    cover = folder / 'cover.jpg'
    cover.write_bytes(b'jpeg data')
    (folder / 'Track 1.lrc').write_text('lyrics', encoding='utf-8')
    (folder / 'Some Album.m3u').write_text('#EXTM3U\n', encoding='utf-8')
    deleted_track = folder / 'Track 1.mp3'

    deleted_track.unlink()
    main._delete_album_cover_if_orphaned(deleted_track)

    assert not cover.exists()


def test_cover_survives_unremovable_file(tmp_path, monkeypatch):
    folder = _album_folder(tmp_path, 'Track 1.mp3')
    cover = folder / 'cover.jpg'
    cover.write_bytes(b'jpeg data')
    deleted_track = folder / 'Track 1.mp3'
    deleted_track.unlink()

    def _raise(*_a, **_kw):
        raise OSError('permission denied')

    monkeypatch.setattr(Path, 'unlink', _raise)

    # Must not propagate.
    main._delete_album_cover_if_orphaned(deleted_track)


# ── _prune_empty_parent_dirs ─────────────────────────────────────────────────


def test_prune_removes_single_empty_folder(tmp_path):
    root = tmp_path
    playlist_dir = root / 'My Playlist'
    playlist_dir.mkdir()

    main._prune_empty_parent_dirs(playlist_dir, root)

    assert not playlist_dir.exists()
    assert root.exists()


def test_prune_climbs_nested_empty_folders_up_to_root(tmp_path):
    root = tmp_path
    album_dir = root / 'Some Artist' / 'Some Album'
    album_dir.mkdir(parents=True)

    main._prune_empty_parent_dirs(album_dir, root)

    assert not album_dir.exists()
    assert not (root / 'Some Artist').exists()
    assert root.exists()


def test_prune_stops_at_first_non_empty_ancestor(tmp_path):
    root = tmp_path
    artist_dir = root / 'Some Artist'
    album_dir = artist_dir / 'Album A'
    other_album_dir = artist_dir / 'Album B'
    album_dir.mkdir(parents=True)
    other_album_dir.mkdir(parents=True)

    main._prune_empty_parent_dirs(album_dir, root)

    # Album A is gone, but Artist still holds Album B, so it must stay.
    assert not album_dir.exists()
    assert artist_dir.exists()
    assert other_album_dir.exists()


def test_prune_never_removes_root_even_if_empty(tmp_path):
    root = tmp_path

    main._prune_empty_parent_dirs(root, root)

    assert root.exists()


def test_prune_leaves_folder_with_a_leftover_file(tmp_path):
    # e.g. a playlist's .m3u is still there even though its last track
    # was just deleted — the folder isn't actually empty.
    root = tmp_path
    playlist_dir = root / 'My Playlist'
    playlist_dir.mkdir()
    (playlist_dir / 'My Playlist.m3u').write_text(
        '#EXTM3U\n', encoding='utf-8'
    )

    main._prune_empty_parent_dirs(playlist_dir, root)

    assert playlist_dir.exists()


def test_prune_no_op_when_folder_already_gone(tmp_path):
    root = tmp_path
    already_gone = root / 'Nonexistent'

    # Must not raise — nothing to prune, the caller's own folder may
    # already not exist in edge cases.
    main._prune_empty_parent_dirs(already_gone, root)


def test_prune_refuses_to_climb_outside_root(tmp_path):
    root = tmp_path / 'downloads'
    root.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()

    main._prune_empty_parent_dirs(outside, root)

    # `outside` isn't under `root` at all — must be left untouched.
    assert outside.exists()
