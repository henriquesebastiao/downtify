"""Formats to avoid: no download brings a file in one of them into the
library, whatever slskd's format list or whitelist say."""

from __future__ import annotations

import asyncio

from downtify import api
from downtify.api import DEFAULT_SETTINGS, _effective_slskd_settings
from downtify.downloader import Downloader
from downtify.slskd_provider import _select_download_candidates

FLAC_FIRST = [
    {'filename': 'Artist - Track.flac', 'match_score': 10, 'bitRate': 0},
    {'filename': 'Artist - Track.mp3', 'match_score': 8, 'bitRate': 320},
]


def test_slskd_never_picks_an_avoided_format_with_the_default_list():
    # The default list is "mp3, flac" with no whitelist: FLAC was allowed.
    settings = {'extensions': ['mp3', 'flac'], 'avoid_formats': ['flac']}

    selected = _select_download_candidates(FLAC_FIRST, settings)

    assert [r['filename'] for r in selected] == ['Artist - Track.mp3']


def test_without_formats_to_avoid_nothing_changes():
    selected = _select_download_candidates(
        FLAC_FIRST, {'extensions': ['mp3', 'flac']}
    )

    assert [r['filename'] for r in selected] == [
        'Artist - Track.flac',
        'Artist - Track.mp3',
    ]


def test_strict_format_priority_drops_the_avoided_tier_too():
    settings = {
        'extensions': ['flac', 'mp3'],
        'strict_format_priority': True,
        'avoid_formats': ['flac'],
    }

    selected = _select_download_candidates(FLAC_FIRST, settings)

    assert [r['filename'] for r in selected] == ['Artist - Track.mp3']


def _downloader(tmp_path, avoid):
    return Downloader(
        tmp_path,
        audio_format='mp3',
        audio_providers=['slskd', 'youtube-music'],
        slskd_settings={'enabled': True, 'avoid_formats': avoid},
    )


def test_a_file_slskd_hands_over_in_an_avoided_format_is_passed_over(
    monkeypatch, tmp_path
):
    """slskd can still deliver one (a file already in its folder): the
    next source is used instead, and the file never reaches the library."""

    delivered = tmp_path / 'slskd' / 'Track.flac'
    delivered.parent.mkdir()
    delivered.write_bytes(b'fLaC')
    monkeypatch.setattr(
        'downtify.downloader.download_from_slskd', lambda *a, **k: delivered
    )
    monkeypatch.setattr(
        'downtify.downloader.find_match',
        lambda song: ('yt123', {'name': song.get('name')}),
    )

    video_id, _match, provider, local = _downloader(
        tmp_path, ['flac']
    )._resolve_source({'name': 'Track', 'artists': ['Artist']}, None)

    assert (provider, video_id, local) == ('youtube-music', 'yt123', None)
    assert delivered.exists(), 'left where slskd put it'


def test_an_allowed_file_from_slskd_is_used(monkeypatch, tmp_path):
    delivered = tmp_path / 'Track.mp3'
    delivered.write_bytes(b'ID3')
    monkeypatch.setattr(
        'downtify.downloader.download_from_slskd', lambda *a, **k: delivered
    )

    _video, _match, provider, local = _downloader(
        tmp_path, ['flac']
    )._resolve_source({'name': 'Track', 'artists': ['Artist']}, None)

    assert (provider, local) == ('slskd', delivered)


class _Request:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def _save(monkeypatch, payload):
    monkeypatch.setattr(api.state, 'settings', dict(DEFAULT_SETTINGS))
    monkeypatch.setattr(api.state, 'settings_path', None)
    monkeypatch.setattr(api.state, 'downloader', None)
    return asyncio.run(api.update_settings_endpoint(_Request(payload)))


def test_the_setting_is_saved_as_known_formats_only(monkeypatch):
    saved = _save(monkeypatch, {'avoid_formats': ['FLAC', 'aif', 'junk']})

    assert saved['avoid_formats'] == ['flac', 'aiff']


def test_the_downloads_format_cannot_be_avoided(monkeypatch):
    saved = _save(
        monkeypatch, {'format': 'flac', 'avoid_formats': ['flac', 'wav']}
    )

    assert saved['avoid_formats'] == ['wav']


def test_switching_the_downloads_format_takes_it_off_the_list(monkeypatch):
    _save(monkeypatch, {'avoid_formats': ['flac', 'opus']})
    saved = asyncio.run(
        api.update_settings_endpoint(_Request({'format': 'opus'}))
    )

    assert saved['avoid_formats'] == ['flac']


def test_slskd_gets_the_list(monkeypatch):
    settings = {**DEFAULT_SETTINGS, 'avoid_formats': ['flac']}

    assert _effective_slskd_settings(settings)['avoid_formats'] == ['flac']
