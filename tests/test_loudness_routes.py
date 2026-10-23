import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from downtify import api
from downtify.library_catalog import LibraryContext


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
