"""Tests for _resolve_url's YouTube artist-channel branch."""

from __future__ import annotations

from downtify import api


def test_resolve_url_artist_channel_returns_albums(monkeypatch):
    monkeypatch.setattr(
        api.providers,
        'artist_albums_from_channel_id',
        lambda channel_id: [{'album_id': f'{channel_id}-album'}],
    )
    result = api._resolve_url(
        'https://music.youtube.com/channel/UCAjidy3vxRkgGVNIFqZMl_Q'
    )
    assert result == [{'album_id': 'UCAjidy3vxRkgGVNIFqZMl_Q-album'}]
