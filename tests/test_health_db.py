"""GET /api/health answers 503 when the PostgreSQL server is unreachable."""

from __future__ import annotations

import json

import pytest

from downtify import api


def _body(response) -> dict:
    return json.loads(response.body)


@pytest.mark.parametrize('db_state', [True, None])
def test_health_ok_when_database_reachable_or_sqlite(monkeypatch, db_state):
    monkeypatch.setattr(api.db_runtime, 'healthcheck', lambda: db_state)
    result = api.get_health()
    assert result['status'] == 'ok'
    assert 'version' in result


def test_health_503_when_database_unreachable(monkeypatch):
    monkeypatch.setattr(api.db_runtime, 'healthcheck', lambda: False)
    response = api.get_health()
    assert response.status_code == 503
    assert _body(response) == {'status': 'database_unavailable'}


def test_health_503_when_healthcheck_raises(monkeypatch):
    def boom():
        raise OSError('connection refused')

    monkeypatch.setattr(api.db_runtime, 'healthcheck', boom)
    response = api.get_health()
    assert response.status_code == 503
    assert _body(response) == {'status': 'database_unavailable'}
