"""Tests for GET /api/health, the Docker HEALTHCHECK liveness probe."""

from __future__ import annotations

from downtify import api
from downtify.api import get_health


def test_health_returns_ok_status():
    result = get_health()
    assert result['status'] == 'ok'


def test_health_reports_current_version(monkeypatch):
    monkeypatch.setattr(api.state, 'version', '9.9.9')
    result = get_health()
    assert result['version'] == '9.9.9'


def test_health_does_not_require_downloader(monkeypatch):
    # A liveness probe must answer during the brief startup window before
    # main.py's startup hook has set up the downloader/monitor DB — it
    # should never depend on state that isn't ready yet.
    monkeypatch.setattr(api.state, 'downloader', None)
    monkeypatch.setattr(api.state, 'monitor_db', None)
    result = get_health()
    assert result['status'] == 'ok'
