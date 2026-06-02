"""Tests for Navidrome song ID SQLite cache."""

from pathlib import Path

from downtify.navidrome_index import NavidromeIndex


def _touch(path: Path, payload: bytes = b'x') -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def test_store_and_lookup_by_filename(tmp_path: Path) -> None:
    db = tmp_path / 'library.db'
    index = NavidromeIndex(db)
    track = _touch(tmp_path / 'Artist/Track.mp3')
    index.store('Artist/Track.mp3', 'nd-1', spotify_track_id='sp-1', full_path=track)
    assert index.lookup_filename('Artist/Track.mp3') == 'nd-1'
    assert index.lookup_file(track) == 'nd-1'


def test_lookup_spotify_and_song(tmp_path: Path) -> None:
    spotify_id = '4uLU6hMCjMI75M1A2tKUQC'
    db = tmp_path / 'library.db'
    index = NavidromeIndex(db)
    track = _touch(tmp_path / 'a.mp3')
    index.store(
        'a.mp3',
        'nd-2',
        spotify_track_id=f'spotify:track:{spotify_id}',
        full_path=track,
    )
    assert index.lookup_spotify(f'spotify:track:{spotify_id}') == 'nd-2'
    assert (
        index.lookup_song(
            {
                'filename': 'missing.mp3',
                'song_id': f'spotify:track:{spotify_id}',
            },
            full_path=track,
        )
        == 'nd-2'
    )


def test_store_updates_existing_filename(tmp_path: Path) -> None:
    db = tmp_path / 'library.db'
    index = NavidromeIndex(db)
    track = _touch(tmp_path / 't.mp3')
    index.store('t.mp3', 'old', full_path=track)
    index.store('t.mp3', 'new', full_path=track)
    assert index.lookup_filename('t.mp3') == 'new'


def test_lookup_file_after_path_change(tmp_path: Path) -> None:
    db = tmp_path / 'library.db'
    index = NavidromeIndex(db)
    data = b'same'
    old = _touch(tmp_path / 'pl' / 't.mp3', data)
    index.store('pl/t.mp3', 'nd-move', full_path=old)
    new = _touch(tmp_path / 't.mp3', data)
    assert index.lookup_file(new) == 'nd-move'


def test_forget_filename(tmp_path: Path) -> None:
    db = tmp_path / 'library.db'
    index = NavidromeIndex(db)
    track = _touch(tmp_path / 'gone.mp3')
    index.store('gone.mp3', 'nd-x', full_path=track)
    index.forget_filename('gone.mp3', full_path=track)
    assert index.lookup_filename('gone.mp3') is None
    assert index.lookup_file(track) is None
