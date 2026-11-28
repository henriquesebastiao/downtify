"""Watches whose playlist or artist can't be read (downtify/watch_reads.py)."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from downtify import monitor, notifications, watch_reads
from downtify.watch_reads import ALERT_AFTER, WatchReads


def _reads(tmp_path=None):
    sent = []
    r = WatchReads(emit=lambda *a: sent.append(a))
    if tmp_path is not None:
        r.configure(tmp_path / 'watch_reads.json')
    return r, sent


def test_reason_in_words():
    assert 'deleted or made private' in watch_reads.reason(
        'ValueError: Spotify entity not found in embed payload'
    )
    assert 'deleted or made private' in watch_reads.reason(
        "KeyError: Unable to find 'contents' using path"
    )
    assert 'did not answer' in watch_reads.reason('Read timed out')
    assert 'did not answer' in watch_reads.reason(
        'HTTP 503 Service Unavailable'
    )
    assert 'Spotify changed' in watch_reads.reason('PersistedQueryNotFound')
    assert (
        watch_reads.reason('boom', 'artist') == 'The artist could not be read'
    )


def test_alerts_once_after_failures_in_a_row(tmp_path):
    r, sent = _reads(tmp_path)
    for _ in range(ALERT_AFTER - 1):
        assert r.failed(7, 'Mix', 'entity not found') is False
    assert r.status(7) is None
    assert r.failed(7, 'Mix', 'entity not found') is True
    assert r.failed(7, 'Mix', 'entity not found') is False

    assert len(sent) == 1
    event, title, text = sent[0]
    assert (event, title) == ('watch_failing', "Mix can't be read")
    assert 'deleted or made private' in text
    status = r.status(7)
    assert status['failures'] == ALERT_AFTER + 1
    assert 'deleted' in status['reason']


def test_a_good_read_clears_it_and_says_so(tmp_path):
    r, sent = _reads(tmp_path)
    for _ in range(ALERT_AFTER):
        r.failed(7, 'Mix', 'x')
    assert r.ok(7, 'Mix') is True
    assert r.status(7) is None
    assert sent[-1][1] == 'Mix works again'
    # A watch that never alerted clears quietly.
    r.failed(8, 'Other', 'x')
    assert r.ok(8, 'Other') is False
    assert len(sent) == 2


def test_kept_across_restarts(tmp_path):
    r, _ = _reads(tmp_path)
    for _ in range(ALERT_AFTER):
        r.failed(7, 'Mix', 'x')
    again, sent = _reads(tmp_path)
    assert again.status(7)['failures'] == ALERT_AFTER
    # Already alerted before the restart: not again.
    again.failed(7, 'Mix', 'x')
    assert sent == []
    raw = json.loads((tmp_path / 'watch_reads.json').read_text())
    assert raw['watches']['7']['alerted'] is True


def test_forget():
    r, _ = _reads()
    for _ in range(ALERT_AFTER):
        r.failed(7, 'Mix', 'x')
    r.forget(7)
    assert r.status(7) is None


def test_check_playlist_counts_failed_and_good_reads(monkeypatch):
    seen = []
    monkeypatch.setattr(
        watch_reads, 'note_failure', lambda w, e: seen.append(('fail', w.id))
    )
    monkeypatch.setattr(
        watch_reads, 'note_ok', lambda w: seen.append(('ok', w.id))
    )

    def boom(*_a):
        raise ValueError('Spotify entity not found in embed payload')

    monkeypatch.setattr(monitor, 'fetch_playlist_tracks', boom)
    watch = SimpleNamespace(
        id=5,
        name='Gone',
        spotify_id='abc',
        source='spotify',
        last_checked=None,
        url='https://open.spotify.com/playlist/abc',
    )
    db = SimpleNamespace(update_playlist=lambda *a, **k: None)

    async def broadcast(_m):
        return None

    got = asyncio.run(monitor.check_playlist(watch, db, None, broadcast, None))
    assert got == 0
    assert seen == [('fail', 5)]


def test_check_playlist_notes_a_good_read(monkeypatch):
    seen = []
    monkeypatch.setattr(
        watch_reads, 'note_ok', lambda w: seen.append(('ok', w.id))
    )
    monkeypatch.setattr(
        watch_reads, 'note_failure', lambda w, e: seen.append(('fail', w.id))
    )
    monkeypatch.setattr(monitor, 'fetch_playlist_tracks', lambda *_a: [])

    class Stop(Exception):
        pass

    def stop(*_a, **_k):
        raise Stop

    # The read worked; what comes after it is not this test's business.
    monkeypatch.setattr(monitor, 'LibraryStores', stop)
    watch = SimpleNamespace(
        id=6,
        name='Fine',
        spotify_id='abc',
        source='spotify',
        last_checked=None,
        url='https://open.spotify.com/playlist/abc',
    )

    async def broadcast(_m):
        return None

    try:
        asyncio.run(
            monitor.check_playlist(
                watch, SimpleNamespace(), None, broadcast, None
            )
        )
    except Stop:
        pass
    assert seen == [('ok', 6)]


def test_watch_failing_event_reaches_channels_saved_before_it():
    saved = {'channels': {'discord': {'events': ['download_failed']}}}
    events = notifications.effective(saved)['channels']['discord']['events']
    assert 'watch_failing' in events
