"""Tests for the saved Spotify top songs (downtify/artist_top_songs.py) and
the endpoint that serves them - offline: Spotify is always mocked."""

from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from downtify import api, artist_profile, artist_top_songs
from downtify.downloader import Downloader

ARTIST_ID = '6XyY86QOPPrYVGvF9ch6wz'


def _songs(count=5):
    return [
        {
            'song_id': f'{i}' * 22,
            'name': f'Song {i}',
            'artists': ['Linkin Park'],
            'album_name': 'Album',
            'cover_url': f'https://img.test/{i}.jpg',
            'duration': 200 + i,
            'play_count': 1000 * (10 - i),
            'source': 'spotify',
            'url': f'https://open.spotify.com/track/{i}',
        }
        for i in range(1, count + 1)
    ]


def _fetcher(calls=None, songs=None, name='Linkin Park'):
    def fake(artist_id, limit=None):
        if calls is not None:
            calls.append((artist_id, limit))
        return name, 'https://img.test/artist.jpg', songs or _songs()

    return fake


def _age(download_dir, name, days):
    """Make the saved file look *days* old."""

    path = artist_top_songs.path_for(download_dir, name)
    data = json.loads(path.read_text(encoding='utf-8'))
    then = datetime.now(timezone.utc) - timedelta(days=days)
    data['fetched_at'] = then.isoformat(timespec='seconds')
    path.write_text(json.dumps(data), encoding='utf-8')


@pytest.fixture
def no_thread_leaks(monkeypatch):
    """Runs nothing in the background unless a test asks for it."""

    started = []

    class _Thread:
        def __init__(self, target, name=None, daemon=None):
            self.target = target

        def start(self):
            started.append(self.target)

    monkeypatch.setattr(artist_top_songs.threading, 'Thread', _Thread)
    return started


# ── file basics ────────────────────────────────────────────────────────


def test_path_is_a_sidecar_next_to_the_other_artist_files(tmp_path):
    assert artist_top_songs.path_for(tmp_path, 'Linkin/Park') == (
        tmp_path / 'Metadata/ArtistTopSongs/LinkinPark.json'
    )


def test_load_of_a_missing_or_broken_file_is_none(tmp_path):
    assert artist_top_songs.load(tmp_path, 'Nobody') is None
    path = artist_top_songs.path_for(tmp_path, 'Nobody')
    path.parent.mkdir(parents=True)
    path.write_text('{not json', encoding='utf-8')
    assert artist_top_songs.load(tmp_path, 'Nobody') is None
    path.write_text('[1, 2]', encoding='utf-8')
    assert artist_top_songs.load(tmp_path, 'Nobody') is None
    path.write_text('{"songs": "nope"}', encoding='utf-8')
    assert artist_top_songs.load(tmp_path, 'Nobody') is None


# ── ensure_top_songs ───────────────────────────────────────────────────


def test_first_call_fetches_five_songs_and_saves_the_file(tmp_path):
    calls: list = []
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher(calls)
    ):
        data = artist_top_songs.ensure_top_songs(
            tmp_path, 'Linkin Park', ARTIST_ID
        )
    assert calls == [(ARTIST_ID, 5)]
    assert [s['name'] for s in data['songs']] == [
        f'Song {i}' for i in range(1, 6)
    ]
    saved = json.loads(
        artist_top_songs.path_for(tmp_path, 'Linkin Park').read_text(
            encoding='utf-8'
        )
    )
    assert saved['artist_id'] == ARTIST_ID
    assert saved['source'] == 'spotify'
    assert saved['name'] == 'Linkin Park'
    assert saved['cover_url'] == 'https://img.test/artist.jpg'
    assert saved['songs'] == data['songs']
    assert datetime.fromisoformat(saved['fetched_at']).tzinfo is not None


def test_a_fresh_file_is_read_without_touching_spotify(tmp_path):
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher()
    ):
        artist_top_songs.ensure_top_songs(tmp_path, 'Linkin Park', ARTIST_ID)

    def boom(*a, **k):
        raise AssertionError('Spotify must not be asked')

    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', boom
    ):
        again = artist_top_songs.ensure_top_songs(
            tmp_path, 'Linkin Park', ARTIST_ID
        )
    assert len(again['songs']) == 5


def test_a_file_just_inside_seven_days_is_still_fresh(tmp_path):
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher()
    ):
        artist_top_songs.ensure_top_songs(tmp_path, 'Linkin Park', ARTIST_ID)
    _age(tmp_path, 'Linkin Park', 6.9)
    _, fresh = artist_top_songs.cached(tmp_path, 'Linkin Park', ARTIST_ID)
    assert fresh


def test_a_file_older_than_seven_days_is_fetched_again(tmp_path):
    calls: list = []
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher(calls)
    ):
        artist_top_songs.ensure_top_songs(tmp_path, 'Linkin Park', ARTIST_ID)
        _age(tmp_path, 'Linkin Park', 7.1)
        _, fresh = artist_top_songs.cached(tmp_path, 'Linkin Park', ARTIST_ID)
        assert not fresh
        artist_top_songs.ensure_top_songs(tmp_path, 'Linkin Park', ARTIST_ID)
    assert len(calls) == 2
    # ...and the rewrite made it fresh again.
    _, fresh = artist_top_songs.cached(tmp_path, 'Linkin Park', ARTIST_ID)
    assert fresh


def test_a_file_for_another_spotify_artist_is_not_served(tmp_path):
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher()
    ):
        artist_top_songs.ensure_top_songs(tmp_path, 'Linkin Park', 'oldid')
    _, fresh = artist_top_songs.cached(tmp_path, 'Linkin Park', ARTIST_ID)
    assert not fresh


@pytest.mark.parametrize('stamp', [None, '', 'yesterday', 12345])
def test_a_file_without_a_usable_timestamp_counts_as_stale(stamp):
    data = {'artist_id': ARTIST_ID, 'songs': [], 'fetched_at': stamp}
    assert not artist_top_songs.is_fresh(data, ARTIST_ID)


def test_a_naive_timestamp_is_read_as_utc():
    naive = (datetime.now(timezone.utc) - timedelta(days=1)).replace(
        tzinfo=None
    )
    data = {
        'artist_id': ARTIST_ID,
        'songs': [],
        'fetched_at': naive.isoformat(),
    }
    assert artist_top_songs.is_fresh(data, ARTIST_ID)


def test_a_failed_refresh_serves_the_stale_file(tmp_path):
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher()
    ):
        artist_top_songs.ensure_top_songs(tmp_path, 'Linkin Park', ARTIST_ID)
    _age(tmp_path, 'Linkin Park', 30)

    def down(*a, **k):
        raise RuntimeError('spotify down')

    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', down
    ):
        data = artist_top_songs.ensure_top_songs(
            tmp_path, 'Linkin Park', ARTIST_ID
        )
    assert len(data['songs']) == 5


def test_a_failed_first_fetch_propagates_and_saves_nothing(tmp_path):
    def down(*a, **k):
        raise RuntimeError('spotify down')

    with (
        patch.object(
            artist_top_songs.spotify, 'artist_top_songs_from_id', down
        ),
        pytest.raises(RuntimeError, match='spotify down'),
    ):
        artist_top_songs.ensure_top_songs(tmp_path, 'Linkin Park', ARTIST_ID)
    assert not artist_top_songs.path_for(tmp_path, 'Linkin Park').exists()


def test_a_stale_file_of_another_artist_is_not_a_fallback(tmp_path):
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher()
    ):
        artist_top_songs.ensure_top_songs(tmp_path, 'Linkin Park', 'oldid')

    def down(*a, **k):
        raise RuntimeError('spotify down')

    with (
        patch.object(
            artist_top_songs.spotify, 'artist_top_songs_from_id', down
        ),
        pytest.raises(RuntimeError),
    ):
        artist_top_songs.ensure_top_songs(tmp_path, 'Linkin Park', ARTIST_ID)


def test_an_empty_shelf_is_returned_but_not_saved(tmp_path):
    fetch = _fetcher(songs=[])

    def empty(artist_id, limit=None):
        return 'Linkin Park', '', []

    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', empty
    ):
        data = artist_top_songs.ensure_top_songs(
            tmp_path, 'Linkin Park', ARTIST_ID
        )
    assert data['songs'] == []
    assert not artist_top_songs.path_for(tmp_path, 'Linkin Park').exists()
    assert fetch  # (helper unused on purpose: shelf returned empty above)


def test_no_spotify_id_is_an_error(tmp_path):
    with pytest.raises(ValueError, match='No Spotify artist id'):
        artist_top_songs.ensure_top_songs(tmp_path, 'Linkin Park', '')


def test_the_write_is_atomic_and_leaves_no_temp_files(tmp_path):
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher()
    ):
        artist_top_songs.ensure_top_songs(tmp_path, 'Linkin Park', ARTIST_ID)
    folder = tmp_path / 'Metadata/ArtistTopSongs'
    assert [p.name for p in folder.iterdir()] == ['Linkin Park.json']


def test_a_failed_write_keeps_the_previous_file_and_cleans_up(
    tmp_path, monkeypatch
):
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher()
    ):
        artist_top_songs.ensure_top_songs(tmp_path, 'Linkin Park', ARTIST_ID)
    before = artist_top_songs.path_for(tmp_path, 'Linkin Park').read_bytes()

    def broken_replace(src, dst):
        raise OSError('disk full')

    monkeypatch.setattr(artist_top_songs.os, 'replace', broken_replace)
    with pytest.raises(OSError, match='disk full'):
        artist_top_songs._write(
            tmp_path, 'Linkin Park', {'songs': [], 'artist_id': 'x'}
        )
    assert artist_top_songs.path_for(tmp_path, 'Linkin Park').read_bytes() == (
        before
    )
    folder = tmp_path / 'Metadata/ArtistTopSongs'
    assert [p.name for p in folder.iterdir()] == ['Linkin Park.json']


def test_two_simultaneous_requests_fetch_once(tmp_path):
    calls: list = []
    release = threading.Event()

    def slow(artist_id, limit=None):
        calls.append(artist_id)
        release.wait(2)
        return 'Linkin Park', '', _songs()

    results: list[Any] = []
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', slow
    ):
        threads = [
            threading.Thread(
                target=lambda: results.append(
                    artist_top_songs.ensure_top_songs(
                        tmp_path, 'Linkin Park', ARTIST_ID
                    )
                )
            )
            for _ in range(2)
        ]
        for t in threads:
            t.start()
        release.set()
        for t in threads:
            t.join(5)
    assert len(calls) == 1
    assert len(results) == 2
    assert results[0]['songs'] == results[1]['songs']


def test_songs_are_saved_without_any_library_state(tmp_path):
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher()
    ):
        data = artist_top_songs.ensure_top_songs(
            tmp_path, 'Linkin Park', ARTIST_ID
        )
    for song in data['songs']:
        assert not {'status', 'in_library', 'queued'} & set(song)


# ── refresh_in_background ──────────────────────────────────────────────


def test_background_refresh_starts_when_the_file_is_missing(
    tmp_path, no_thread_leaks
):
    assert artist_top_songs.refresh_in_background(
        tmp_path, 'Linkin Park', ARTIST_ID
    )
    assert len(no_thread_leaks) == 1


def test_background_refresh_does_nothing_for_a_fresh_file(
    tmp_path, no_thread_leaks
):
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher()
    ):
        artist_top_songs.ensure_top_songs(tmp_path, 'Linkin Park', ARTIST_ID)
    assert not artist_top_songs.refresh_in_background(
        tmp_path, 'Linkin Park', ARTIST_ID
    )
    assert no_thread_leaks == []


def test_background_refresh_starts_for_a_stale_file(tmp_path, no_thread_leaks):
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher()
    ):
        artist_top_songs.ensure_top_songs(tmp_path, 'Linkin Park', ARTIST_ID)
    _age(tmp_path, 'Linkin Park', 8)
    assert artist_top_songs.refresh_in_background(
        tmp_path, 'Linkin Park', ARTIST_ID
    )


def test_background_refresh_skips_when_someone_is_already_fetching(
    tmp_path, no_thread_leaks
):
    with artist_top_songs._lock_for(tmp_path, 'Linkin Park'):
        assert not artist_top_songs.refresh_in_background(
            tmp_path, 'Linkin Park', ARTIST_ID
        )
    assert no_thread_leaks == []


def test_background_refresh_without_an_id_does_nothing(
    tmp_path, no_thread_leaks
):
    assert not artist_top_songs.refresh_in_background(
        tmp_path, 'Linkin Park', ''
    )
    assert no_thread_leaks == []


def test_the_background_thread_creates_the_file_and_swallows_errors(tmp_path):
    done = threading.Event()

    def fake(artist_id, limit=None):
        done.set()
        return 'Linkin Park', '', _songs()

    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', fake
    ):
        assert artist_top_songs.refresh_in_background(
            tmp_path, 'Linkin Park', ARTIST_ID
        )
        assert done.wait(3)
        for _ in range(60):
            if artist_top_songs.path_for(tmp_path, 'Linkin Park').exists():
                break
            threading.Event().wait(0.05)
    assert artist_top_songs.path_for(tmp_path, 'Linkin Park').exists()

    def down(*a, **k):
        raise RuntimeError('spotify down')

    other = tmp_path / 'other'
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', down
    ):
        assert artist_top_songs.refresh_in_background(
            other, 'Linkin Park', ARTIST_ID
        )
        threading.Event().wait(0.2)  # must not raise anywhere


# ── GET /api/artists/top_songs/spotify ─────────────────────────────────


@pytest.fixture
def app_state(monkeypatch, tmp_path):
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    monkeypatch.setattr(
        api.state,
        'downloader',
        Downloader(download_dir=downloads, audio_format='mp3'),
    )
    monkeypatch.setattr(api.state, 'settings', {})
    monkeypatch.setattr(api.state, 'track_index', None)
    return downloads


def _with_spotify_id(downloads, name='Linkin Park', spotify_id=ARTIST_ID):
    profile = artist_profile.load_profile(downloads, name)
    profile['platforms_id']['spotify'] = spotify_id
    artist_profile._save_profile(downloads, name, profile)


def _get(name):
    return asyncio.run(api.artist_top_songs_saved_endpoint(name=name))


def test_endpoint_blank_name_is_400(app_state):
    with pytest.raises(HTTPException) as exc:
        _get('   ')
    assert exc.value.status_code == 400


def test_endpoint_without_a_saved_spotify_id_is_404(app_state):
    with pytest.raises(HTTPException) as exc:
        _get('Linkin Park')
    assert exc.value.status_code == 404


def test_endpoint_fetches_and_saves_when_there_is_no_file(app_state):
    _with_spotify_id(app_state)
    calls: list = []
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher(calls)
    ):
        result = _get('Linkin Park')
    assert calls == [(ARTIST_ID, 5)]
    assert result['stale'] is False
    assert result['name'] == 'Linkin Park'
    assert result['artist_id'] == ARTIST_ID
    assert len(result['songs']) == 5
    assert artist_top_songs.path_for(app_state, 'Linkin Park').is_file()


def test_endpoint_serves_a_fresh_file_without_touching_spotify(app_state):
    _with_spotify_id(app_state)
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher()
    ):
        _get('Linkin Park')

    def boom(*a, **k):
        raise AssertionError('Spotify must not be asked')

    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', boom
    ):
        result = _get('Linkin Park')
    assert result['stale'] is False
    assert len(result['songs']) == 5


def test_endpoint_serves_a_stale_file_and_refreshes_in_the_background(
    app_state, monkeypatch
):
    _with_spotify_id(app_state)
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher()
    ):
        _get('Linkin Park')
    _age(app_state, 'Linkin Park', 9)
    refreshed: list = []
    monkeypatch.setattr(
        api.artist_top_songs,
        'refresh_in_background',
        lambda *args: refreshed.append(args) or True,
    )

    def boom(*a, **k):
        raise AssertionError('the request itself must not wait for Spotify')

    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', boom
    ):
        result = _get('Linkin Park')
    assert result['stale'] is True
    assert len(result['songs']) == 5
    assert refreshed == [(app_state, 'Linkin Park', ARTIST_ID)]


def test_endpoint_a_fresh_file_starts_no_refresh(app_state, monkeypatch):
    _with_spotify_id(app_state)
    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', _fetcher()
    ):
        _get('Linkin Park')
    refreshed: list = []
    monkeypatch.setattr(
        api.artist_top_songs,
        'refresh_in_background',
        lambda *args: refreshed.append(args),
    )
    _get('Linkin Park')
    assert refreshed == []


def test_endpoint_spotify_failure_is_502(app_state):
    _with_spotify_id(app_state)

    def down(*a, **k):
        raise RuntimeError('spotify down')

    with (
        patch.object(
            artist_top_songs.spotify, 'artist_top_songs_from_id', down
        ),
        pytest.raises(HTTPException) as exc,
    ):
        _get('Linkin Park')
    assert exc.value.status_code == 502
    assert 'spotify down' in exc.value.detail


def test_endpoint_waits_for_a_fetch_already_in_flight(app_state):
    """The ensure's background fetch and the tab opening must not fetch
    twice: the request queues behind the running fetch, then reads its
    file."""

    _with_spotify_id(app_state)
    calls: list = []
    started = threading.Event()
    release = threading.Event()

    def slow(artist_id, limit=None):
        calls.append(artist_id)
        started.set()
        release.wait(3)
        return 'Linkin Park', '', _songs()

    with patch.object(
        artist_top_songs.spotify, 'artist_top_songs_from_id', slow
    ):
        background = threading.Thread(
            target=artist_top_songs.ensure_top_songs,
            args=(app_state, 'Linkin Park', ARTIST_ID),
        )
        background.start()
        assert started.wait(3)
        timer = threading.Timer(0.2, release.set)
        timer.start()
        result = _get('Linkin Park')
        background.join(5)
    assert len(calls) == 1
    assert len(result['songs']) == 5


# ── the ensure endpoint starts the background fetch ────────────────────


class _JsonRequest:
    def __init__(self, payload: Any):
        self._payload = payload

    async def json(self) -> Any:
        return self._payload


def _ensure(name='Linkin Park'):
    request = _JsonRequest({'name': name, 'lang': 'en'})
    return asyncio.run(api.artist_profile_ensure_endpoint(request))


def test_ensure_endpoint_starts_the_top_songs_fetch_for_its_spotify_id(
    app_state, monkeypatch
):
    started: list = []
    monkeypatch.setattr(
        api.artist_top_songs,
        'refresh_in_background',
        lambda *args: started.append(args),
    )
    monkeypatch.setattr(
        api.artist_profile,
        'ensure_profile',
        lambda *a, **k: {'platforms_id': {'spotify': ARTIST_ID}},
    )
    _ensure()
    assert started == [(app_state, 'Linkin Park', ARTIST_ID)]


def test_ensure_endpoint_without_a_spotify_id_asks_for_nothing(
    app_state, monkeypatch
):
    started: list = []
    monkeypatch.setattr(
        api.artist_top_songs,
        'refresh_in_background',
        lambda *args: started.append(args),
    )
    monkeypatch.setattr(
        api.artist_profile,
        'ensure_profile',
        lambda *a, **k: {'platforms_id': {'spotify': ''}},
    )
    _ensure()
    # Called with an empty id, which refresh_in_background ignores.
    assert started == [(app_state, 'Linkin Park', '')]
    assert not artist_top_songs.refresh_in_background(
        app_state, 'Linkin Park', ''
    )
