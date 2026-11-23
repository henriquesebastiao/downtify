"""Settings switches for Artist Watch's Deezer and MusicBrainz sources
(issue #670): what a save stores. Offline."""

from __future__ import annotations

import asyncio

from downtify import api
from downtify.api import DEFAULT_SETTINGS


class _Request:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def _save(monkeypatch, payload, before=None):
    monkeypatch.setattr(
        api.state, 'settings', {**DEFAULT_SETTINGS, **(before or {})}
    )
    monkeypatch.setattr(api.state, 'settings_path', None)
    monkeypatch.setattr(api.state, 'downloader', None)
    return asyncio.run(api.update_settings_endpoint(_Request(payload)))


def test_both_sources_are_on_by_default():
    assert DEFAULT_SETTINGS['artist_watch_deezer'] is True
    assert DEFAULT_SETTINGS['artist_watch_musicbrainz'] is True


def test_the_switches_are_saved_as_booleans(monkeypatch):
    saved = _save(
        monkeypatch,
        {'artist_watch_deezer': False, 'artist_watch_musicbrainz': 'no'},
    )
    assert saved['artist_watch_deezer'] is False
    assert saved['artist_watch_musicbrainz'] is False
    saved = _save(monkeypatch, {'artist_watch_deezer': True})
    assert saved['artist_watch_deezer'] is True


def test_the_kinds_are_saved_as_known_kinds_in_order(monkeypatch):
    saved = _save(
        monkeypatch,
        {
            'artist_watch_musicbrainz_kinds': [
                'live',
                'junk',
                'mixtape',
                'live',
            ]
        },
    )
    assert saved['artist_watch_musicbrainz_kinds'] == ['mixtape', 'live']
    saved = _save(monkeypatch, {'artist_watch_musicbrainz_kinds': []})
    assert saved['artist_watch_musicbrainz_kinds'] == []


def test_kinds_that_are_not_a_list_keep_the_saved_ones(monkeypatch):
    saved = _save(
        monkeypatch,
        {'artist_watch_musicbrainz_kinds': 'live'},
        before={'artist_watch_musicbrainz_kinds': ['soundtrack']},
    )
    assert saved['artist_watch_musicbrainz_kinds'] == ['soundtrack']
