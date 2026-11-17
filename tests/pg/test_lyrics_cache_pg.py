"""LyricsLookupCache on both backends: the same results on SQLite and PostgreSQL."""

from __future__ import annotations

from downtify.lyrics_cache import LyricsLookupCache, song_key


def test_miss_is_remembered_per_provider(backend_db) -> None:
    cache = LyricsLookupCache(backend_db)
    key = song_key({'song_id': 'abc'})

    assert cache.should_skip(key, 'lrclib') is False
    cache.record(key, 'lrclib', found=False)
    assert cache.should_skip(key, 'lrclib') is True
    assert cache.should_skip(key, 'netease') is False


def test_hit_is_recorded_but_never_skipped(backend_db) -> None:
    cache = LyricsLookupCache(backend_db)
    key = song_key({'song_id': 'hit'})

    cache.record(key, 'lrclib', found=True)
    assert cache.should_skip(key, 'lrclib') is False


def test_record_overwrites_an_earlier_answer(backend_db) -> None:
    cache = LyricsLookupCache(backend_db)
    key = song_key({'song_id': 'flip'})

    cache.record(key, 'lrclib', found=False)
    cache.record(key, 'lrclib', found=True)
    assert cache.should_skip(key, 'lrclib') is False
    cache.record(key, 'lrclib', found=False)
    assert cache.should_skip(key, 'lrclib') is True


def test_expired_miss_is_retried(backend_db) -> None:
    cache = LyricsLookupCache(backend_db, miss_ttl_days=0)
    key = song_key({'song_id': 'ttl'})

    cache.record(key, 'lrclib', found=False)
    assert cache.should_skip(key, 'lrclib') is False


def test_empty_key_is_ignored(backend_db) -> None:
    cache = LyricsLookupCache(backend_db)

    cache.record('', 'lrclib', found=False)
    assert cache.should_skip('', 'lrclib') is False
    assert cache.forget('') == 0


def test_forget_drops_every_provider_for_one_song(backend_db) -> None:
    cache = LyricsLookupCache(backend_db)
    gone = song_key({'song_id': 'gone'})
    kept = song_key({'song_id': 'kept'})

    cache.record(gone, 'lrclib', found=False)
    cache.record(gone, 'netease', found=False)
    cache.record(kept, 'lrclib', found=False)

    assert cache.forget(gone) == 2
    assert cache.should_skip(gone, 'lrclib') is False
    assert cache.should_skip(kept, 'lrclib') is True


def test_clear_empties_the_table(backend_db) -> None:
    cache = LyricsLookupCache(backend_db)
    cache.record(song_key({'song_id': 'a'}), 'lrclib', found=False)
    cache.record(song_key({'song_id': 'b'}), 'lrclib', found=True)

    assert cache.clear() == 2
    assert cache.clear() == 0
    assert cache.should_skip(song_key({'song_id': 'a'}), 'lrclib') is False


def test_song_key_prefers_the_spotify_id() -> None:
    assert song_key({'song_id': ' 42 ', 'name': 'x'}) == 'id:42'
    assert (
        song_key({'artists': ['Zed', 'Other'], 'name': ' Song '})
        == 'text:zed|song'
    )
    assert song_key({'artist': 'A', 'title': 'T'}) == 'text:a|t'
    assert not song_key({'artist': 'A'})


def test_store_on_a_shared_database_object(backend_db) -> None:
    cache = LyricsLookupCache(backend_db)
    other = LyricsLookupCache(backend_db)
    key = song_key({'song_id': 'shared'})

    cache.record(key, 'lrclib', found=False)
    assert other.should_skip(key, 'lrclib') is True
