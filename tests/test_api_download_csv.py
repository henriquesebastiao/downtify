"""Tests for POST /api/download/csv - importing a library-export CSV."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

from downtify import api


class _StubDownloader:
    download_dir = Path('/tmp/downtify-test-downloads')


class _FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def _run(monkeypatch, payload, *, downloader=object()):
    monkeypatch.setattr(api.state, 'downloader', downloader)
    monkeypatch.setattr(api.state, 'download_jobs', {})
    captured_batches = []

    async def fake_process_batch(
        songs, job_ids, playlist_url, generate_m3u, playlist_name=None
    ):
        captured_batches.append({
            'songs': songs,
            'job_ids': job_ids,
            'playlist_url': playlist_url,
            'generate_m3u': generate_m3u,
            'playlist_name': playlist_name,
        })

    monkeypatch.setattr(api, '_process_batch', fake_process_batch)

    async def _invoke():
        result = await api.download_csv_endpoint(_FakeRequest(payload))
        # _process_batch runs as a background task (asyncio.create_task);
        # yield back to the loop so it actually runs before we assert.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return result

    result = asyncio.run(_invoke())
    return result, captured_batches


def test_download_csv_requires_downloader(monkeypatch):
    monkeypatch.setattr(api.state, 'downloader', None)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(api.download_csv_endpoint(_FakeRequest({'csv': 'x'})))
    assert exc_info.value.status_code == 500


def test_download_csv_rejects_missing_csv_field(monkeypatch):
    monkeypatch.setattr(api.state, 'downloader', object())
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(api.download_csv_endpoint(_FakeRequest({})))
    assert exc_info.value.status_code == 400


def test_download_csv_rejects_blank_csv(monkeypatch):
    monkeypatch.setattr(api.state, 'downloader', object())
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(api.download_csv_endpoint(_FakeRequest({'csv': '   '})))
    assert exc_info.value.status_code == 400


def test_download_csv_rejects_unparsable_csv(monkeypatch):
    monkeypatch.setattr(api.state, 'downloader', object())
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            api.download_csv_endpoint(_FakeRequest({'csv': 'Foo,Bar\n1,2\n'}))
        )
    assert exc_info.value.status_code == 400


def test_download_csv_queues_every_row(monkeypatch):
    csv_text = 'Title,Artist\nSong A,Artist A\nSong B,Artist B\n'
    result, batches = _run(monkeypatch, {'csv': csv_text})
    assert result['count'] == 2
    assert len(result['job_ids']) == 2
    assert len(batches) == 1
    songs = batches[0]['songs']
    assert songs == [
        {'song_id': 'csv:0', 'name': 'Song A', 'artists': ['Artist A']},
        {'song_id': 'csv:1', 'name': 'Song B', 'artists': ['Artist B']},
    ]
    # job_ids must track the (unique) song_id per row, not collide.
    assert result['job_ids'] == ['csv:0', 'csv:1']


def test_download_csv_defaults_playlist_name(monkeypatch):
    csv_text = 'Title,Artist\nSong A,Artist A\n'
    result, batches = _run(monkeypatch, {'csv': csv_text})
    assert result['playlist_name'] == 'Imported Library'
    assert batches[0]['playlist_name'] == 'Imported Library'


def test_download_csv_honors_custom_playlist_name(monkeypatch):
    csv_text = 'Title,Artist\nSong A,Artist A\n'
    result, batches = _run(
        monkeypatch, {'csv': csv_text, 'playlist_name': 'My Old Library'}
    )
    assert result['playlist_name'] == 'My Old Library'
    assert batches[0]['playlist_name'] == 'My Old Library'


def test_download_csv_passes_no_spotify_playlist_url(monkeypatch):
    csv_text = 'Title,Artist\nSong A,Artist A\n'
    _, batches = _run(monkeypatch, {'csv': csv_text})
    assert not batches[0]['playlist_url']


def test_download_csv_honors_generate_m3u_flag(monkeypatch):
    csv_text = 'Title,Artist\nSong A,Artist A\n'
    _, batches = _run(monkeypatch, {'csv': csv_text, 'generate_m3u': False})
    assert batches[0]['generate_m3u'] is False


def test_download_csv_registers_jobs_for_every_row(monkeypatch):
    csv_text = 'Title,Artist\nSong A,Artist A\nSong B,Artist B\n'
    result, _ = _run(monkeypatch, {'csv': csv_text})
    for job_id in result['job_ids']:
        assert job_id in api.state.download_jobs
        assert api.state.download_jobs[job_id]['status'] == 'queued'


# ── _process_batch with an explicit playlist_name (no Spotify URL) ─────────


def test_process_batch_writes_m3u_under_explicit_playlist_name(monkeypatch):
    """CSV imports have no Spotify playlist_url to resolve a name from;
    _process_batch must accept an explicit playlist_name instead and
    still group tracks into that playlist's subfolder / M3U."""
    monkeypatch.setattr(api.state, 'downloader', _StubDownloader())
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api, '_organize_enabled', lambda: False)

    async def fake_run_download(song, song_id, subdir=None, delay_seconds=0):
        return f'{song["name"]}.mp3'

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    written = {}

    def fake_write_m3u(
        download_dir, playlist_name, entries, *, playlist_subdir=None
    ):
        written['playlist_name'] = playlist_name
        written['playlist_subdir'] = playlist_subdir
        written['entries'] = list(entries)
        return download_dir / 'Playlists' / f'{playlist_name}.m3u', len(
            written['entries']
        )

    monkeypatch.setattr(api.m3u, 'write_m3u', fake_write_m3u)

    songs = [
        {'name': 'Song A', 'artists': ['Artist A']},
        {'name': 'Song B', 'artists': ['Artist B']},
    ]
    asyncio.run(
        api._process_batch(
            songs,
            ['job-a', 'job-b'],
            playlist_url='',
            generate_m3u=True,
            playlist_name='My Old Library',
        )
    )

    assert written['playlist_name'] == 'My Old Library'
    assert written['playlist_subdir'] == 'My Old Library'
    assert len(written['entries']) == 2


def test_process_batch_skips_m3u_when_playlist_name_missing(monkeypatch):
    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(api.state, 'download_jobs', {})

    async def fake_run_download(song, song_id, subdir=None, delay_seconds=0):
        return f'{song["name"]}.mp3'

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    def fake_write_m3u(*_a, **_kw):
        raise AssertionError('should not write an M3U with no playlist name')

    monkeypatch.setattr(api.m3u, 'write_m3u', fake_write_m3u)

    songs = [{'name': 'Song A', 'artists': ['Artist A']}]
    asyncio.run(
        api._process_batch(
            songs, ['job-a'], playlist_url='', generate_m3u=True
        )
    )
