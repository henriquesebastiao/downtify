"""Editing a watch: interval/enabled, and changing its URL."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from downtify import api, monitor
from downtify.monitor import KIND_ARTIST, KIND_PLAYLIST, PlaylistMonitorDB

PLAYLIST_A = '37i9dQZF1DXcBWIGoYBM5M'
PLAYLIST_B = '37i9dQZF1DX0XUsuxWHRQd'
URL_A = f'https://open.spotify.com/playlist/{PLAYLIST_A}'
URL_B = f'https://open.spotify.com/playlist/{PLAYLIST_B}'
CHANNEL = 'UCabcdefghijklmnopqrstuv'


class _Req:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


@pytest.fixture
def db(monkeypatch, tmp_path):
    store = PlaylistMonitorDB(tmp_path / 'monitor.db')
    monkeypatch.setattr(api.state, 'monitor_db', store)
    monkeypatch.setattr(api.state, 'downloader', None)
    return store


@pytest.fixture
def resolve(monkeypatch):
    """Resolve URLs from a table instead of the network."""
    targets = {
        URL_A: (KIND_PLAYLIST, PLAYLIST_A, 'Today’s Top Hits'),
        f'{URL_A}?si=abc': (KIND_PLAYLIST, PLAYLIST_A, 'Today’s Top Hits'),
        URL_B: (KIND_PLAYLIST, PLAYLIST_B, 'Rap Caviar'),
        f'https://music.youtube.com/channel/{CHANNEL}': (
            KIND_ARTIST,
            CHANNEL,
            'Some Artist',
        ),
    }

    async def _resolve(url):
        if url not in targets:
            raise HTTPException(status_code=400, detail='bad url')
        return targets[url]

    monkeypatch.setattr(api, '_resolve_watch_target', _resolve)
    return targets


def _patch(watch_id, payload):
    return asyncio.run(api.update_monitor_playlist(watch_id, _Req(payload)))


def _with_history(db):
    watch = db.add_playlist(PLAYLIST_A, 'Today’s Top Hits', URL_A, 360)
    db.mark_track_downloaded(watch.id, 'track1', 'Today’s Top Hits/one.mp3')
    db.update_playlist(
        watch.id, last_checked='2026-01-01T00:00:00', last_track_count=50
    )
    return watch


def test_interval_and_enabled_still_update(db, resolve):
    watch = _with_history(db)
    out = _patch(watch.id, {'interval_minutes': 60, 'enabled': False})
    assert out['interval_minutes'] == 60
    assert out['enabled'] is False
    assert out['url'] == URL_A


def test_same_playlist_link_only_replaces_the_url(db, resolve):
    watch = _with_history(db)
    out = _patch(watch.id, {'url': f'{URL_A}?si=abc'})
    assert out['url'] == f'{URL_A}?si=abc'
    assert out['spotify_id'] == PLAYLIST_A
    assert out['last_track_count'] == 50
    assert db.get_track_filenames(watch.id)


def test_unchanged_url_is_not_resolved(db, monkeypatch):
    watch = _with_history(db)

    async def _fail(url):
        raise AssertionError('should not resolve')

    monkeypatch.setattr(api, '_resolve_watch_target', _fail)
    assert _patch(watch.id, {'url': URL_A, 'enabled': False})['url'] == URL_A


def test_other_playlist_retargets_and_starts_over(db, resolve):
    watch = _with_history(db)
    out = _patch(watch.id, {'url': URL_B, 'interval_minutes': 720})
    assert out['id'] == watch.id
    assert out['spotify_id'] == PLAYLIST_B
    assert out['name'] == 'Rap Caviar'
    assert out['url'] == URL_B
    assert out['interval_minutes'] == 720
    assert out['last_checked'] is None
    assert out['last_track_count'] == 0
    assert db.get_track_filenames(watch.id) == {}
    assert db.get_by_spotify_id(PLAYLIST_A) is None


def test_retarget_starts_a_check_when_enabled(db, resolve, monkeypatch):
    watch = _with_history(db)
    started = []
    monkeypatch.setattr(
        api, '_start_initial_check', lambda pl, _db: started.append(pl.id)
    )
    _patch(watch.id, {'url': URL_B})
    assert started == [watch.id]

    started.clear()
    _patch(watch.id, {'enabled': False, 'url': URL_A})
    assert started == []


def test_cannot_switch_kind(db, resolve):
    watch = _with_history(db)
    with pytest.raises(HTTPException) as exc:
        _patch(
            watch.id, {'url': f'https://music.youtube.com/channel/{CHANNEL}'}
        )
    assert exc.value.status_code == 400
    assert db.get_playlist(watch.id).url == URL_A


def test_cannot_retarget_onto_another_watch(db, resolve):
    watch = _with_history(db)
    db.add_playlist(PLAYLIST_B, 'Rap Caviar', URL_B)
    with pytest.raises(HTTPException) as exc:
        _patch(watch.id, {'url': URL_B})
    assert exc.value.status_code == 409
    assert db.get_playlist(watch.id).spotify_id == PLAYLIST_A


def test_invalid_url_leaves_the_watch_alone(db, resolve):
    watch = _with_history(db)
    with pytest.raises(HTTPException) as exc:
        _patch(watch.id, {'url': 'https://example.com/x', 'enabled': False})
    assert exc.value.status_code == 400
    assert db.get_playlist(watch.id).enabled is True


def test_missing_watch_is_404(db, resolve):
    with pytest.raises(HTTPException) as exc:
        _patch(999, {'enabled': False})
    assert exc.value.status_code == 404


def test_retarget_drops_seen_releases(tmp_path):
    store = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = store.add_playlist(
        CHANNEL, 'Some Artist', 'https://x', kind=monitor.KIND_ARTIST
    )
    store.mark_album_seen(watch.id, 'MPREb_1', 'Album')
    assert store.get_seen_album_ids(watch.id)
    store.retarget_playlist(watch.id, 'UCother', 'Other', 'https://y')
    assert store.get_seen_album_ids(watch.id) == set()
    assert store.retarget_playlist(12345, 'a', 'b', 'c') is None
