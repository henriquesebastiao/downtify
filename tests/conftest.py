from __future__ import annotations

import pytest

from downtify import downloader as downloader_mod


@pytest.fixture(autouse=True)
def _offline_metadata_lookups(monkeypatch):
    """Keep tests off the network: ``Downloader.download()`` starts the
    iTunes genre and cover-art lookups alongside yt-dlp, so even a test
    whose fake YoutubeDL aborts the download would otherwise fire real
    HTTP requests (and ``embed_metadata`` fetches the cover too). Tests
    that exercise these lookups override them with their own fakes."""

    monkeypatch.setattr(downloader_mod, '_fetch_itunes_genre', lambda s: '')
    monkeypatch.setattr(downloader_mod, '_download_cover', lambda url: None)
