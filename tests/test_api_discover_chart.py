"""Tests for the Deezer-chart discovery endpoint and the download-request
bypass its tracks rely on (a Deezer track link isn't a URL this app can
resolve, so a ``source: 'deezer'`` row is taken from the request body
as-is - the same escape hatch a slskd text-search stub uses)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from downtify import api

# ── discover_chart_endpoint ─────────────────────────────────────────────


def test_discover_chart_endpoint_returns_deezer_data(monkeypatch):
    chart = {'tracks': [{'song_id': 'deezer-1'}], 'albums': [], 'artists': []}
    monkeypatch.setattr(api.deezer, 'fetch_chart', lambda limit: chart)
    assert api.discover_chart_endpoint(limit=25) == chart


def test_discover_chart_endpoint_translates_value_error(monkeypatch):
    def boom(limit):
        raise ValueError('Could not reach Deezer')

    monkeypatch.setattr(api.deezer, 'fetch_chart', boom)
    with pytest.raises(HTTPException) as exc_info:
        api.discover_chart_endpoint(limit=25)
    assert exc_info.value.status_code == 502


# ── _song_from_download_request ─────────────────────────────────────────


def test_song_from_download_request_uses_deezer_hints_as_is(monkeypatch):
    def unexpected_resolve(url):
        raise AssertionError('a Deezer row must not go through URL parsing')

    monkeypatch.setattr(api, '_song_for_download', unexpected_resolve)

    hints = {
        'song_id': 'deezer-111',
        'name': 'Chart Track',
        'artists': ['Main Artist'],
        'url': 'https://www.deezer.com/track/111',
        'source': 'deezer',
    }
    assert api._song_from_download_request(hints['url'], hints) == hints


def test_song_from_download_request_still_resolves_other_sources(
    monkeypatch,
):
    resolved = {'song_id': 'abc', 'name': 'Resolved'}
    monkeypatch.setattr(api, '_song_for_download', lambda url: dict(resolved))

    result = api._song_from_download_request(
        'https://open.spotify.com/track/abc', None
    )
    assert result == resolved
