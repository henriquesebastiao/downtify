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


def _assert_scoped_csv_ids(ids: list[str]) -> str:
    """Ids are ``csv:{token}:{index}`` for one import, indexes from 0."""
    assert ids
    _csv, token, _index = ids[0].split(':')
    assert len(token) == 12
    assert all(c in '0123456789abcdef' for c in token)
    assert ids == [f'csv:{token}:{i}' for i in range(len(ids))]
    return token


def test_download_csv_queues_every_row(monkeypatch):
    csv_text = 'Title,Artist\nSong A,Artist A\nSong B,Artist B\n'
    result, batches = _run(monkeypatch, {'csv': csv_text})
    assert result['count'] == 2
    assert len(result['job_ids']) == 2
    assert len(batches) == 1
    songs = batches[0]['songs']
    assert [s['name'] for s in songs] == ['Song A', 'Song B']
    assert [s['artists'] for s in songs] == [['Artist A'], ['Artist B']]
    ids = [s['song_id'] for s in songs]
    assert ids == result['job_ids']
    _assert_scoped_csv_ids(ids)


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


def test_download_csv_broadcasts_one_queue_reload(monkeypatch):
    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(api.state, 'download_jobs', {})
    sent = []

    async def fake_broadcast(message):
        sent.append(message)

    async def fake_process_batch(*_args, **_kwargs):
        return None

    monkeypatch.setattr(api.state.connections, 'broadcast', fake_broadcast)
    monkeypatch.setattr(api, '_process_batch', fake_process_batch)

    rows = ''.join(f'Song {i},Artist {i}\n' for i in range(20))

    async def _invoke():
        result = await api.download_csv_endpoint(
            _FakeRequest({'csv': f'Title,Artist\n{rows}'})
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return result

    result = asyncio.run(_invoke())
    assert result['count'] == 20
    assert sent == [{'type': 'queue_reload'}]
    for job_id in result['job_ids']:
        assert api.state.download_jobs[job_id]['status'] == 'queued'


def test_download_csv_registers_jobs_for_every_row(monkeypatch):
    csv_text = 'Title,Artist\nSong A,Artist A\nSong B,Artist B\n'
    result, _ = _run(monkeypatch, {'csv': csv_text})
    for job_id in result['job_ids']:
        assert job_id in api.state.download_jobs
        assert api.state.download_jobs[job_id]['status'] == 'queued'


def test_download_csv_second_import_keeps_the_first_jobs(monkeypatch):
    """Two files both start at csv:0 in the parser. Queue keys must not."""
    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(api.state, 'download_jobs', {})

    async def fake_process_batch(*_args, **_kwargs):
        return None

    monkeypatch.setattr(api, '_process_batch', fake_process_batch)

    async def _import(csv_text: str) -> dict:
        result = await api.download_csv_endpoint(
            _FakeRequest({'csv': csv_text, 'playlist_name': 'Imported'})
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return result

    async def _both():
        first = await _import('Title,Artist\nA1,Artist\nA2,Artist\n')
        second = await _import(
            'Title,Artist\nB1,Artist\nB2,Artist\nB3,Artist\n'
        )
        return first, second

    first, second = asyncio.run(_both())
    assert len(first['job_ids']) == 2
    assert len(second['job_ids']) == 3
    assert len(api.state.download_jobs) == 5
    assert set(first['job_ids']).isdisjoint(second['job_ids'])
    assert _assert_scoped_csv_ids(first['job_ids']) != _assert_scoped_csv_ids(
        second['job_ids']
    )
    assert api.state.download_jobs[first['job_ids'][0]]['song']['name'] == 'A1'
    assert (
        api.state.download_jobs[second['job_ids'][0]]['song']['name'] == 'B1'
    )
    for job_id in (*first['job_ids'], *second['job_ids']):
        assert api.state.download_jobs[job_id]['status'] == 'queued'


# ── _process_batch with an explicit playlist_name (no Spotify URL) ─────────


def test_process_batch_writes_m3u_under_explicit_playlist_name(monkeypatch):
    """CSV imports have no Spotify playlist_url to resolve a name from;
    _process_batch must accept an explicit playlist_name instead and
    still group tracks into that playlist's subfolder / M3U."""
    monkeypatch.setattr(api.state, 'downloader', _StubDownloader())
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api, '_organize_enabled', lambda: False)

    async def fake_run_download(
        song, song_id, subdir=None, delay_seconds=0, **_kwargs
    ):
        return f'{song["name"]}.mp3'

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    written = {}

    def fake_write_m3u(
        download_dir,
        playlist_name,
        entries,
        *,
        playlist_subdir=None,
        slskd_dir=None,
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

    async def fake_run_download(
        song, song_id, subdir=None, delay_seconds=0, **_kwargs
    ):
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
