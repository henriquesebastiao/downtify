"""NavidromeIndex on both backends: the same results on SQLite and PostgreSQL."""

from __future__ import annotations

from pathlib import Path

from downtify.library_cache_keys import file_content_key
from downtify.navidrome_index import NavidromeIndex

SPOTIFY_A = '4uLU6hMCjMI75M1A2tKUQC'
SPOTIFY_B = '1x00000000000000000000'


def _touch(path: Path, payload: bytes = b'x') -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _row_count(index: NavidromeIndex) -> int:
    with index.db.connect() as conn:
        return conn.execute(
            'SELECT COUNT(*) FROM navidrome_tracks'
        ).fetchone()[0]


def test_store_lookups_and_upsert(backend_db, tmp_path: Path) -> None:
    index = NavidromeIndex(backend_db)
    track = _touch(tmp_path / 'Artist' / 'Track.mp3')

    assert index.lookup_filename('Artist/Track.mp3') is None
    assert index.lookup_file(track) is None
    assert index.lookup_spotify(SPOTIFY_A) is None

    index.store(
        'Artist\\Track.mp3',
        'nd-1',
        spotify_track_id=SPOTIFY_A,
        full_path=track,
    )
    assert index.lookup_filename('Artist/Track.mp3') == 'nd-1'
    assert index.lookup_file(track) == 'nd-1'
    assert index.lookup_spotify(SPOTIFY_A) == 'nd-1'
    assert _row_count(index) == 1

    # Same content key: the row is replaced, not duplicated.
    index.store(
        'Artist/Renamed.mp3',
        'nd-2',
        spotify_track_id=SPOTIFY_B,
        full_path=track,
    )
    assert _row_count(index) == 1
    assert index.lookup_filename('Artist/Track.mp3') is None
    assert index.lookup_filename('Artist/Renamed.mp3') == 'nd-2'
    assert index.lookup_file(track) == 'nd-2'
    assert index.lookup_spotify(SPOTIFY_A) is None
    assert index.lookup_spotify(SPOTIFY_B) == 'nd-2'


def test_store_ignores_missing_fields(backend_db, tmp_path: Path) -> None:
    index = NavidromeIndex(backend_db)
    track = _touch(tmp_path / 'a.mp3')
    index.store('', 'nd-1', full_path=track)
    index.store('a.mp3', '  ', full_path=track)
    index.store('a.mp3', 'nd-1')  # no full path: no content key
    assert _row_count(index) == 0


def test_lookup_song_touches_filename(backend_db, tmp_path: Path) -> None:
    index = NavidromeIndex(backend_db)
    track = _touch(tmp_path / 'old.mp3')
    index.store('old.mp3', 'nd-9', full_path=track)

    hit = index.lookup_song({'filename': 'new/name.mp3'}, full_path=track)
    assert hit == 'nd-9'
    assert index.lookup_filename('new/name.mp3') == 'nd-9'
    assert index.lookup_filename('old.mp3') is None

    by_spotify = index.lookup_song({'song_id': SPOTIFY_A})
    assert by_spotify is None
    index.store(
        'x.mp3',
        'nd-3',
        spotify_track_id=SPOTIFY_A,
        full_path=_touch(tmp_path / 'x.mp3', b'other'),
    )
    assert index.lookup_song({'song_id': SPOTIFY_A}) == 'nd-3'
    assert index.lookup_song({'filename': 'x.mp3'}) == 'nd-3'
    assert index.lookup_song({'filename': 'missing.mp3'}) is None


def test_matched_files_by_key_and_path(backend_db, tmp_path: Path) -> None:
    index = NavidromeIndex(backend_db)
    track = _touch(tmp_path / 'k.mp3')
    index.store('Lib/k.mp3', 'nd-k', full_path=track)

    assert index.matched_files({}) == set()
    matched = index.matched_files({
        'Lib/k.mp3': '',
        'Other/none.mp3': 'no-such-key',
        '': 'ignored',
    })
    assert matched == {'Lib/k.mp3'}

    key = file_content_key(track)
    assert index.matched_files({'Elsewhere.mp3': key}) == {'Elsewhere.mp3'}


def test_forget_filename(backend_db, tmp_path: Path) -> None:
    index = NavidromeIndex(backend_db)
    track = _touch(tmp_path / 'f.mp3')
    index.store('f.mp3', 'nd-f', spotify_track_id=SPOTIFY_A, full_path=track)
    index.store(
        'g.mp3',
        'nd-g',
        spotify_track_id=SPOTIFY_B,
        full_path=_touch(tmp_path / 'g.mp3', b'gg'),
    )

    index.forget_filename('')  # empty name: no-op
    assert _row_count(index) == 2

    index.forget_filename('f.mp3')
    assert index.lookup_filename('f.mp3') is None
    assert _row_count(index) == 1

    index.forget_filename('renamed.mp3', full_path=track)
    assert _row_count(index) == 1
    assert index.lookup_spotify(SPOTIFY_B) == 'nd-g'


def test_constructor_accepts_path_and_database(
    backend_db, tmp_path: Path
) -> None:
    index = NavidromeIndex(backend_db)
    assert index.db is backend_db
    path_index = NavidromeIndex(tmp_path / 'library.db')
    assert path_index._path == str(tmp_path / 'library.db')
