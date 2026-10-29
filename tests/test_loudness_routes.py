import asyncio
import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse

from downtify import api, mobile_routes
from downtify.library_catalog import LibraryContext
from downtify.loudness import LoudnessAnalyzer


def request():
    return Request({'type': 'http', 'headers': [], 'query_string': b''})


def test_clients_cannot_control_or_read_analysis_progress(monkeypatch):
    monkeypatch.setattr(api, 'request_is_admin', lambda req: False)
    for operation in [
        api.control_loudness(request(), 'start'),
        api.loudness_status(request()),
    ]:
        with pytest.raises(HTTPException) as error:
            asyncio.run(operation)
        assert error.value.status_code == 403


def test_hidden_track_measurement_is_not_exposed(monkeypatch):
    monkeypatch.setattr(api, 'request_user_id', lambda req: 2)
    monkeypatch.setattr(api, 'filter_paths_for_request', lambda files, req: [])
    with pytest.raises(HTTPException) as error:
        asyncio.run(api.track_loudness(request(), 'private.mp3'))
    assert error.value.status_code == 404


def test_unknown_measurement_does_not_start_analysis(tmp_path, monkeypatch):
    audio = tmp_path / 'available.mp3'
    audio.write_bytes(b'fixture')
    monkeypatch.setattr(api, 'request_user_id', lambda req: 2)
    monkeypatch.setattr(
        api, 'filter_paths_for_request', lambda files, req: files
    )
    monkeypatch.setattr(
        api, 'library_context', lambda: LibraryContext(download_dir=tmp_path)
    )
    monkeypatch.setattr(
        api.state,
        'loudness_analyzer',
        SimpleNamespace(info=lambda *args: None),
    )
    assert asyncio.run(api.track_loudness(request(), audio.name)) == {
        'state': 'unanalysed',
        'gain_db': 0.0,
    }


def test_measured_profile_carries_the_original_download_etag(
    tmp_path, monkeypatch
):
    # The apps bind an offline copy to a measurement only when the ETag of
    # their download (a plain FileResponse of the original) matches.
    root = tmp_path / 'music'
    root.mkdir()
    audio = root / 'song.flac'
    audio.write_bytes(b'original audio')
    ctx = LibraryContext(download_dir=root)
    runner = LoudnessAnalyzer(tmp_path / 'library.db', lambda: ctx)
    monkeypatch.setattr(
        runner,
        '_measure',
        lambda path: {
            'state': 'ready',
            'gain_db': 6.0,
            'integrated_lufs': -24.0,
            'true_peak_dbtp': -10.0,
            'algorithm_version': 1,
        },
    )
    runner.start(['song.flac'])
    deadline = time.monotonic() + 5
    while runner.status()['active']:
        assert time.monotonic() < deadline
        time.sleep(0.01)
    monkeypatch.setattr(api.state, 'loudness_analyzer', runner)
    monkeypatch.setattr(api, 'library_context', lambda: ctx)
    monkeypatch.setattr(api, 'request_user_id', lambda req: 2)
    monkeypatch.setattr(
        api, 'filter_paths_for_request', lambda files, req: files
    )
    monkeypatch.setattr(
        mobile_routes,
        '_track_path',
        lambda track_id: ({'file': 'song.flac'}, audio),
    )

    profile = asyncio.run(mobile_routes.track_loudness('t1', request()))

    response = FileResponse(audio, stat_result=audio.stat())
    assert profile['state'] == 'ready'
    assert profile['gain_db'] == pytest.approx(6.0)
    assert profile['source_etag'] == response.headers['etag']
    assert profile['source_size'] == len(b'original audio')
    runner.close()
