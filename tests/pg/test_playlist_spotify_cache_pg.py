"""PlaylistSpotifyCache on both backends (SQLite file, migrated PostgreSQL)."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from downtify import playlist_spotify_cache as mod
from downtify.db.config import Dialect
from downtify.playlist_spotify_cache import PlaylistSpotifyCache
from tests.db.helpers import execute

SID = 'playlist12345678901234'
SID2 = 'playlist22345678901234'
TID = '4uLU6hMCjMI75M1A2tKUQC'
TID2 = '1x00000000000000000000'


def _tracks() -> list[dict]:
    return [
        {'song_id': TID, 'name': 'Song', 'artists': ['Artist']},
        {'song_id': TID2, 'name': 'Other', 'artist': 'Someone'},
    ]


def test_constructor_accepts_path_and_database(backend_db, tmp_path) -> None:
    by_db = PlaylistSpotifyCache(backend_db)
    assert by_db.db is backend_db
    assert by_db.list_playlists() == []
    if backend_db.dialect is Dialect.SQLITE:
        assert by_db._path == str(backend_db.path)
        by_path = PlaylistSpotifyCache(tmp_path / 'lib.db')
        assert by_path.db.dialect is Dialect.SQLITE
        assert by_path._path == str(tmp_path / 'lib.db')
    else:
        assert by_db._path is None


def test_store_then_get_round_trip(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    cache.store(SID, 'My Mix', _tracks())
    hit = cache.get(SID)
    assert hit is not None
    name, rows = hit
    assert name == 'My Mix'
    assert [r['song_id'] for r in rows] == [TID, TID2]
    assert rows[1]['artist'] == 'Someone'
    assert cache.get('') is None
    assert cache.get('missing-playlist-id') is None


def test_store_defaults_name_and_skips_empty_id(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    cache.store(SID, '   ', _tracks())
    assert cache.get(SID)[0] == SID
    cache.store('  ', 'Nope', _tracks())
    rows = cache.list_playlists()
    assert [(r['spotify_playlist_id'], r['playlist_name']) for r in rows] == [
        (SID, SID)
    ]
    assert rows[0]['track_count'] == 2


def test_store_replaces_existing_playlist(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    cache.store(SID, 'Old', _tracks())
    cache.store(SID, 'New', [{'song_id': TID2, 'name': 'Only'}])
    name, rows = cache.get(SID)
    assert name == 'New'
    assert [r['song_id'] for r in rows] == [TID2]
    assert cache.track_count(SID) == 1


def test_get_returns_none_for_corrupt_tracks_json(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    cache.store(SID, 'Mix', _tracks())
    execute(
        backend_db,
        'UPDATE spotify_playlist_cache SET tracks_json = ?'
        ' WHERE spotify_playlist_id = ?',
        '{not json',
        SID,
    )
    assert cache.get(SID) is None
    execute(
        backend_db,
        'UPDATE spotify_playlist_cache SET tracks_json = ?'
        ' WHERE spotify_playlist_id = ?',
        '{"a": 1}',
        SID,
    )
    assert cache.get(SID) is None


def test_list_playlists_orders_bytewise_with_counts(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    cache.store(SID, 'beta', _tracks())
    cache.store(SID2, 'Alpha', [])
    cache.store('playlist32345678901234567890', 'alpha', _tracks()[:1])
    rows = cache.list_playlists()
    assert [r['playlist_name'] for r in rows] == ['Alpha', 'alpha', 'beta']
    assert [r['track_count'] for r in rows] == [0, 1, 2]
    assert set(rows[0]) == {
        'spotify_playlist_id',
        'playlist_name',
        'fetched_at',
        'track_count',
    }
    assert all(isinstance(r['fetched_at'], str) for r in rows)


def test_get_playlist_track_and_find_track(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    cache.store(SID, 'Mix', _tracks())
    cache.store(SID2, 'Other', [{'song_id': TID, 'name': 'Second'}])
    hit = cache.get_playlist_track(SID, TID)
    assert hit == {'song_id': TID, 'name': 'Song', 'artists': ['Artist']}
    assert cache.get_playlist_track(SID, 'nope') is None
    assert cache.get_playlist_track('', TID) is None
    assert cache.get_playlist_track(SID, '') is None
    # find_track_in_playlists returns the lowest track_order match.
    assert cache.find_track_in_playlists(TID)['name'] == 'Song'
    assert cache.find_track_in_playlists('') is None
    assert cache.find_track_in_playlists('nope') is None


def test_find_track_returns_none_for_corrupt_track_json(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    cache.store(SID, 'Mix', _tracks())
    execute(
        backend_db,
        'UPDATE spotify_playlist_tracks SET track_json = ?'
        ' WHERE spotify_playlist_id = ?',
        '[1, 2]',
        SID,
    )
    assert cache.find_track_in_playlists(TID) is None
    assert cache.get_playlist_track(SID, TID) is None


def test_playlists_for_track_is_distinct_and_sorted(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    cache.store(SID2, 'Second', [{'song_id': TID}, {'song_id': TID}])
    cache.store(SID, 'First', [{'song_id': TID}])
    assert cache.playlists_for_track(TID) == [SID, SID2]
    assert cache.playlists_for_track(TID2) == []
    assert cache.playlists_for_track('') == []


def test_store_and_get_cached_track(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    assert cache.get_cached_track(TID) is None
    assert cache.get_cached_track('') is None
    cache.store_track(TID, {'song_id': TID, 'name': 'First'})
    assert cache.get_cached_track(TID)['name'] == 'First'
    cache.store_track(TID, {'song_id': TID, 'name': 'Second'})
    assert cache.get_cached_track(TID)['name'] == 'Second'


def test_store_track_uses_argument_id_when_track_has_none(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    cache.store_track(TID2, {'name': 'No id inside'})
    assert cache.get_cached_track(TID2)['name'] == 'No id inside'
    cache.store_track('', {'name': 'Dropped'})
    assert cache.get_cached_track('') is None


def test_track_count_and_delete_playlist(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    assert cache.track_count('') == 0
    assert cache.track_count(SID) == 0
    cache.store(SID, 'Mix', _tracks())
    cache.store(SID2, 'Keep', [{'song_id': TID}])
    assert cache.track_count(SID) == 2
    cache.delete_playlist('')
    assert cache.track_count(SID) == 2
    cache.delete_playlist(SID)
    assert cache.get(SID) is None
    assert cache.track_count(SID) == 0
    assert cache.playlists_for_track(TID) == [SID2]
    assert [r['spotify_playlist_id'] for r in cache.list_playlists()] == [SID2]
    # Deleting an unknown playlist is a no-op.
    cache.delete_playlist(SID)


def test_store_keeps_duplicate_track_rows(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    dupes = [{'song_id': TID, 'name': 'Song'}, {'song_id': TID}]
    cache.store(SID, 'Dupes', dupes)
    assert cache.track_count(SID) == 2
    assert len(cache.get(SID)[1]) == 2


def test_store_skips_tracks_without_id_in_rows_table(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    cache.store(SID, 'Mixed', [{'name': 'no id'}, {'song_id': TID}])
    # The JSON blob keeps every track; only identified rows are indexed.
    assert len(cache.get(SID)[1]) == 2
    assert cache.track_count(SID) == 1
    assert cache.get_playlist_track(SID, TID) is not None


def test_fetch_playlist_tracks_reads_cache_and_stores(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    cache.store(SID, 'Cached', [{'song_id': TID, 'name': 'Song'}])
    with patch.object(mod.spotify, 'playlist_info_and_tracks') as fetch:
        name, tracks = mod.fetch_playlist_tracks(SID, cache=cache)
        fetch.assert_not_called()
        assert (name, len(tracks)) == ('Cached', 1)
        assert mod.fetch_playlist_tracks('  ') == ('', [])

    fresh = [{'song_id': TID2, 'name': 'New'}]
    with patch.object(
        mod.spotify,
        'playlist_info_and_tracks',
        return_value=('Fresh', fresh),
    ):
        name, tracks = mod.fetch_playlist_tracks(
            SID, cache=cache, refresh=True
        )
    assert (name, tracks) == ('Fresh', fresh)
    assert cache.get(SID)[0] == 'Fresh'
    assert cache.get_playlist_track(SID, TID2) is not None

    with patch.object(
        mod.spotify,
        'playlist_info_and_tracks',
        return_value=('Uncached', []),
    ):
        name, tracks = mod.fetch_playlist_tracks(SID2, cache=None)
    assert name == 'Uncached'
    assert cache.get(SID2) is None


def test_fetch_track_metadata_lookup_order(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    cache.store(SID, 'Mix', [{'song_id': TID, 'name': 'In playlist'}])
    cache.store_track(TID2, {'song_id': TID2, 'name': 'Cached track'})
    with patch.object(mod.spotify, 'track_from_id') as fetch:
        # Playlist row wins when the playlist is given.
        assert (
            mod.fetch_track_metadata(TID, cache=cache, playlist_id=SID)['name']
            == 'In playlist'
        )
        # Track cache next.
        assert mod.fetch_track_metadata(TID2, cache=cache)['name'] == (
            'Cached track'
        )
        # Any playlist row as the last resort.
        assert (
            mod.fetch_track_metadata(TID, cache=cache)['name'] == 'In playlist'
        )
        fetch.assert_not_called()

        with patch.object(
            mod.spotify,
            'track_from_id',
            return_value={'song_id': 'zzzzzzzzzzzzzzzzzzzzzz', 'name': 'Net'},
        ) as net:
            track = mod.fetch_track_metadata(
                'zzzzzzzzzzzzzzzzzzzzzz', cache=cache, refresh=True
            )
            net.assert_called_once()
        assert track['name'] == 'Net'
        assert cache.get_cached_track('zzzzzzzzzzzzzzzzzzzzzz')['name'] == (
            'Net'
        )

    with pytest.raises(ValueError, match='track_spotify_id required'):
        mod.fetch_track_metadata('  ')


def test_warm_uncached_playlists(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    cache.store(SID, 'Already', [])
    fetched = [{'song_id': TID, 'name': 'Warm'}]
    with patch.object(
        mod.spotify,
        'playlist_info_and_tracks',
        return_value=('Warmed', fetched),
    ) as fetch:
        count = asyncio.run(
            mod.warm_uncached_playlists(
                cache,
                [SID, '', SID2, '  '],
                delay_seconds=0,
            )
        )
    assert count == 1
    fetch.assert_called_once_with(SID2)
    assert cache.get(SID2)[0] == 'Warmed'


def test_playlist_cache_loop_stores_missing_playlists(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)

    async def run_once() -> None:
        await asyncio.wait_for(
            mod.playlist_spotify_cache_loop(
                cache,
                lambda: [SID],
                delay_seconds=0,
                idle_seconds=60,
                settings={},
            ),
            timeout=0.5,
        )

    with patch.object(
        mod.spotify,
        'playlist_info_and_tracks',
        return_value=('Looped', [{'song_id': TID}]),
    ):
        try:
            asyncio.run(run_once())
        except TimeoutError:
            pass
    assert cache.get(SID)[0] == 'Looped'


def test_playlist_cache_loop_survives_list_errors(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)

    def broken() -> list[str]:
        raise RuntimeError('lookup failed')

    async def run_once() -> None:
        await asyncio.wait_for(
            mod.playlist_spotify_cache_loop(
                cache, broken, delay_seconds=0, idle_seconds=60
            ),
            timeout=0.3,
        )

    try:
        asyncio.run(run_once())
    except TimeoutError:
        pass
    assert cache.list_playlists() == []


def test_binary_order_matches_sqlite_text_order(backend_db) -> None:
    cache = PlaylistSpotifyCache(backend_db)
    names = ['zeta', 'Éclair', 'apple', 'Apple', 'éé']
    for index, name in enumerate(names):
        cache.store(f'pl{index:0>20}', name, [])
    got = [r['playlist_name'] for r in cache.list_playlists()]
    assert got == sorted(names)
