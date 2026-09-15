"""Tests for the settings pipeline: DEFAULT_SETTINGS, _load_settings and
_effective_lyrics_providers."""

from __future__ import annotations

import asyncio
import inspect
import json

import pytest
from fastapi import HTTPException

from downtify import api
from downtify.api import (
    DEFAULT_SETTINGS,
    MAX_COVER_RESOLUTION,
    MAX_DOWNLOAD_DELAY_SECONDS,
    MAX_PARALLEL_DOWNLOADS,
    MIN_COVER_RESOLUTION,
    MIN_DOWNLOAD_DELAY_SECONDS,
    MIN_PARALLEL_DOWNLOADS,
    _clamp_cover_resolution,
    _clamp_download_delay,
    _clamp_parallel_downloads,
    _effective_audio_providers,
    _effective_lyrics_providers,
    _effective_slskd_settings,
    _load_settings,
    artist_info_endpoint,
    artist_similar_endpoint,
    artist_top_albums_endpoint,
    artist_top_songs_endpoint,
    search_albums_endpoint,
    search_artists_endpoint,
)
from downtify.downloader import Downloader


def test_default_settings_has_required_keys():
    required = {
        'audio_providers',
        'lyrics_providers',
        'download_lyrics',
        'format',
        'bitrate',
        'output',
        'generate_m3u',
        'organize_by_artist',
        'slskd',
        'sync_navidrome',
        'navidrome',
        'cache_cover_art',
    }
    assert required <= set(DEFAULT_SETTINGS)


def test_default_organize_by_artist_is_false():
    assert DEFAULT_SETTINGS['organize_by_artist'] is False


def test_default_generate_m3u_is_true():
    assert DEFAULT_SETTINGS['generate_m3u'] is True


def test_default_download_lyrics_is_true():
    assert DEFAULT_SETTINGS['download_lyrics'] is True


def test_default_format_is_mp3():
    assert DEFAULT_SETTINGS['format'] == 'mp3'


def test_default_search_albums_is_true():
    assert DEFAULT_SETTINGS['search_albums'] is True


def test_default_mini_player_enabled_is_true():
    assert DEFAULT_SETTINGS['mini_player_enabled'] is True


# ── search_albums_endpoint ─────────────────────────────────────────────────────


def test_search_albums_endpoint_calls_provider_when_enabled(monkeypatch):
    monkeypatch.setitem(api.state.settings, 'search_albums', True)
    monkeypatch.setattr(
        api.providers,
        'search_albums',
        lambda query, limit: [{'name': 'Driftlight'}],
    )
    assert search_albums_endpoint(query='Driftlight') == [
        {'name': 'Driftlight'}
    ]


def test_search_albums_endpoint_default_limit_is_25():
    # Regression: this used to be hardcoded to 10, capping how many
    # albums a caller (e.g. the Music Assistant provider) could ever see
    # regardless of what it asked for. Calling the route function
    # directly (as the other tests here do) doesn't resolve FastAPI's
    # `Query(...)` default the way a real request would, so this checks
    # the declared default via the signature instead.
    limit_param = inspect.signature(search_albums_endpoint).parameters['limit']
    assert limit_param.default.default == 25


def test_search_albums_endpoint_honors_custom_limit(monkeypatch):
    monkeypatch.setitem(api.state.settings, 'search_albums', True)
    captured = {}

    def _fake(query, limit):
        captured['limit'] = limit
        return []

    monkeypatch.setattr(api.providers, 'search_albums', _fake)
    search_albums_endpoint(query='Driftlight', limit=50)
    assert captured['limit'] == 50


def test_search_albums_endpoint_short_circuits_when_disabled(monkeypatch):
    monkeypatch.setitem(api.state.settings, 'search_albums', False)

    def _boom(*_a, **_kw):
        raise AssertionError('should not search when disabled')

    monkeypatch.setattr(api.providers, 'search_albums', _boom)
    assert search_albums_endpoint(query='Driftlight') == []


# ── search_artists_endpoint ────────────────────────────────────────────────────


def test_search_artists_endpoint_calls_provider(monkeypatch):
    monkeypatch.setattr(
        api.providers,
        'search_artists',
        lambda query, limit: [{'name': 'Mica Ferreira'}],
    )
    assert search_artists_endpoint(query='Mica Ferreira') == [
        {'name': 'Mica Ferreira'}
    ]


# ── artist_top_songs_endpoint / artist_top_albums_endpoint ────────────────────


def test_artist_top_songs_endpoint_calls_provider(monkeypatch):
    monkeypatch.setattr(
        api.providers,
        'artist_top_songs_from_channel_id',
        lambda channel_id: [{'song_id': channel_id}],
    )
    assert artist_top_songs_endpoint(channel_id='UCxxx') == [
        {'song_id': 'UCxxx'}
    ]


def test_artist_top_albums_endpoint_calls_provider(monkeypatch):
    monkeypatch.setattr(
        api.providers,
        'artist_top_albums_from_channel_id',
        lambda channel_id: [{'album_id': channel_id}],
    )
    assert artist_top_albums_endpoint(channel_id='UCxxx') == [
        {'album_id': 'UCxxx'}
    ]


def test_artist_info_endpoint_calls_provider(monkeypatch):
    monkeypatch.setattr(
        api.providers,
        'artist_info_from_channel_id',
        lambda channel_id: {'artist_id': channel_id},
    )
    assert artist_info_endpoint(channel_id='UCxxx') == {'artist_id': 'UCxxx'}


def test_artist_similar_endpoint_calls_provider(monkeypatch):
    monkeypatch.setattr(
        api.providers,
        'artist_similar_from_channel_id',
        lambda channel_id: [{'artist_id': channel_id}],
    )
    assert artist_similar_endpoint(channel_id='UCxxx') == [
        {'artist_id': 'UCxxx'}
    ]


# ── _load_settings ────────────────────────────────────────────────────────────


def test_load_settings_returns_defaults_for_missing_file(tmp_path):
    result = _load_settings(tmp_path / 'nonexistent.json')
    assert result == DEFAULT_SETTINGS


def test_load_settings_merges_saved_settings(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text(
        json.dumps({'format': 'flac', 'bitrate': '128'}), encoding='utf-8'
    )
    result = _load_settings(path)
    assert result['format'] == 'flac'
    assert result['bitrate'] == '128'
    assert result['generate_m3u'] == DEFAULT_SETTINGS['generate_m3u']


def test_load_settings_ignores_unknown_keys(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text(
        json.dumps({'format': 'mp3', 'unknown_key': 'value'}), encoding='utf-8'
    )
    result = _load_settings(path)
    assert 'unknown_key' not in result


def test_load_settings_handles_invalid_json(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text('not valid json {{ }}', encoding='utf-8')
    result = _load_settings(path)
    assert result == DEFAULT_SETTINGS


def test_load_settings_handles_non_dict_json(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text(json.dumps([1, 2, 3]), encoding='utf-8')
    result = _load_settings(path)
    assert result == DEFAULT_SETTINGS


def test_load_settings_preserves_organize_by_artist(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text(json.dumps({'organize_by_artist': True}), encoding='utf-8')
    result = _load_settings(path)
    assert result['organize_by_artist'] is True


def test_load_settings_empty_object_returns_defaults(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text('{}', encoding='utf-8')
    result = _load_settings(path)
    assert result == DEFAULT_SETTINGS


# ── _effective_lyrics_providers ───────────────────────────────────────────────


def test_effective_providers_when_enabled():
    settings = {'download_lyrics': True, 'lyrics_providers': ['lrclib']}
    assert _effective_lyrics_providers(settings) == ['lrclib']


def test_effective_providers_when_disabled():
    settings = {'download_lyrics': False, 'lyrics_providers': ['lrclib']}
    assert _effective_lyrics_providers(settings) == []


def test_effective_providers_filters_empty_strings():
    settings = {
        'download_lyrics': True,
        'lyrics_providers': ['lrclib', '', 'genius'],
    }
    result = _effective_lyrics_providers(settings)
    assert '' not in result
    assert 'lrclib' in result


def test_effective_providers_filters_none_entries():
    settings = {
        'download_lyrics': True,
        'lyrics_providers': ['lrclib', None],
    }
    result = _effective_lyrics_providers(settings)
    assert None not in result


def test_effective_providers_defaults_to_enabled_when_key_missing():
    settings = {'lyrics_providers': ['lrclib']}
    assert _effective_lyrics_providers(settings) == ['lrclib']


def test_effective_providers_empty_list_when_no_providers():
    settings = {'download_lyrics': True, 'lyrics_providers': []}
    assert _effective_lyrics_providers(settings) == []


# ── _clamp_parallel_downloads ───────────────────────────────────────────────


def test_clamp_parallel_downloads_within_range_is_unchanged():
    assert _clamp_parallel_downloads(12) == 12


def test_clamp_parallel_downloads_caps_above_max():
    assert _clamp_parallel_downloads(9999) == MAX_PARALLEL_DOWNLOADS


def test_clamp_parallel_downloads_floors_below_min():
    assert _clamp_parallel_downloads(0) == MIN_PARALLEL_DOWNLOADS
    assert _clamp_parallel_downloads(-5) == MIN_PARALLEL_DOWNLOADS


def test_clamp_parallel_downloads_accepts_string_numbers():
    assert _clamp_parallel_downloads('20') == 20


def test_clamp_parallel_downloads_falls_back_on_garbage():
    assert (
        _clamp_parallel_downloads('not-a-number')
        == DEFAULT_SETTINGS['max_parallel_downloads']
    )
    assert (
        _clamp_parallel_downloads(None)
        == DEFAULT_SETTINGS['max_parallel_downloads']
    )


def test_clamp_parallel_downloads_boundaries_are_inclusive():
    assert _clamp_parallel_downloads(MIN_PARALLEL_DOWNLOADS) == (
        MIN_PARALLEL_DOWNLOADS
    )
    assert _clamp_parallel_downloads(MAX_PARALLEL_DOWNLOADS) == (
        MAX_PARALLEL_DOWNLOADS
    )


def test_load_settings_clamps_out_of_range_parallel_downloads(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text(
        json.dumps({'max_parallel_downloads': 500}), encoding='utf-8'
    )
    result = _load_settings(path)
    assert result['max_parallel_downloads'] == MAX_PARALLEL_DOWNLOADS


# ── update_settings_endpoint ────────────────────────────────────────────────


class _FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def _call_update_settings(monkeypatch, payload):
    monkeypatch.setitem(
        api.state.settings,
        'max_parallel_downloads',
        DEFAULT_SETTINGS['max_parallel_downloads'],
    )
    monkeypatch.setattr(api.state, 'settings_path', None)
    return asyncio.run(api.update_settings_endpoint(_FakeRequest(payload)))


def test_update_settings_clamps_excessive_parallel_downloads(monkeypatch):
    result = _call_update_settings(
        monkeypatch, {'max_parallel_downloads': 1000}
    )
    assert result['max_parallel_downloads'] == MAX_PARALLEL_DOWNLOADS


def test_update_settings_clamps_zero_parallel_downloads(monkeypatch):
    result = _call_update_settings(monkeypatch, {'max_parallel_downloads': 0})
    assert result['max_parallel_downloads'] == MIN_PARALLEL_DOWNLOADS


def test_update_settings_accepts_in_range_parallel_downloads(monkeypatch):
    result = _call_update_settings(monkeypatch, {'max_parallel_downloads': 25})
    assert result['max_parallel_downloads'] == 25


def test_update_settings_toggles_mini_player_enabled(monkeypatch):
    # A plain passthrough boolean — the backend never acts on it, only
    # stores and returns whatever the UI last set (see
    # docs/features/player.md#mini-player-bar).
    result = _call_update_settings(monkeypatch, {'mini_player_enabled': False})
    assert result['mini_player_enabled'] is False


# ── _clamp_download_delay ────────────────────────────────────────────────────


def test_clamp_download_delay_within_range_is_unchanged():
    assert _clamp_download_delay(60) == 60


def test_clamp_download_delay_caps_above_max():
    assert _clamp_download_delay(9999) == MAX_DOWNLOAD_DELAY_SECONDS


def test_clamp_download_delay_floors_below_min():
    assert _clamp_download_delay(-5) == MIN_DOWNLOAD_DELAY_SECONDS


def test_clamp_download_delay_accepts_string_numbers():
    assert _clamp_download_delay('30') == 30


def test_clamp_download_delay_falls_back_on_garbage():
    assert (
        _clamp_download_delay('not-a-number')
        == DEFAULT_SETTINGS['download_delay_seconds']
    )
    assert (
        _clamp_download_delay(None)
        == DEFAULT_SETTINGS['download_delay_seconds']
    )


def test_clamp_download_delay_boundaries_are_inclusive():
    assert (
        _clamp_download_delay(MIN_DOWNLOAD_DELAY_SECONDS)
        == MIN_DOWNLOAD_DELAY_SECONDS
    )
    assert (
        _clamp_download_delay(MAX_DOWNLOAD_DELAY_SECONDS)
        == MAX_DOWNLOAD_DELAY_SECONDS
    )


def test_load_settings_clamps_out_of_range_download_delay(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text(
        json.dumps({'download_delay_seconds': 99999}), encoding='utf-8'
    )
    result = _load_settings(path)
    assert result['download_delay_seconds'] == MAX_DOWNLOAD_DELAY_SECONDS


def test_update_settings_clamps_excessive_download_delay(monkeypatch):
    monkeypatch.setitem(
        api.state.settings,
        'download_delay_seconds',
        DEFAULT_SETTINGS['download_delay_seconds'],
    )
    result = _call_update_settings(
        monkeypatch, {'download_delay_seconds': 99999}
    )
    assert result['download_delay_seconds'] == MAX_DOWNLOAD_DELAY_SECONDS


def test_update_settings_accepts_in_range_download_delay(monkeypatch):
    monkeypatch.setitem(
        api.state.settings,
        'download_delay_seconds',
        DEFAULT_SETTINGS['download_delay_seconds'],
    )
    result = _call_update_settings(monkeypatch, {'download_delay_seconds': 45})
    assert result['download_delay_seconds'] == 45


# ── _clamp_cover_resolution ──────────────────────────────────────────────────


def test_clamp_cover_resolution_within_range_is_unchanged():
    assert _clamp_cover_resolution(800) == 800


def test_clamp_cover_resolution_caps_above_max():
    assert _clamp_cover_resolution(9999) == MAX_COVER_RESOLUTION


def test_clamp_cover_resolution_floors_below_min():
    assert _clamp_cover_resolution(1) == MIN_COVER_RESOLUTION
    assert _clamp_cover_resolution(-5) == MIN_COVER_RESOLUTION


def test_clamp_cover_resolution_accepts_string_numbers():
    assert _clamp_cover_resolution('900') == 900


def test_clamp_cover_resolution_falls_back_on_garbage():
    assert (
        _clamp_cover_resolution('not-a-number')
        == DEFAULT_SETTINGS['cover_resolution']
    )
    assert (
        _clamp_cover_resolution(None) == DEFAULT_SETTINGS['cover_resolution']
    )


def test_clamp_cover_resolution_boundaries_are_inclusive():
    assert _clamp_cover_resolution(MIN_COVER_RESOLUTION) == (
        MIN_COVER_RESOLUTION
    )
    assert _clamp_cover_resolution(MAX_COVER_RESOLUTION) == (
        MAX_COVER_RESOLUTION
    )


def test_load_settings_clamps_out_of_range_cover_resolution(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text(json.dumps({'cover_resolution': 99999}), encoding='utf-8')
    result = _load_settings(path)
    assert result['cover_resolution'] == MAX_COVER_RESOLUTION


def test_update_settings_clamps_excessive_cover_resolution(monkeypatch):
    monkeypatch.setitem(
        api.state.settings,
        'cover_resolution',
        DEFAULT_SETTINGS['cover_resolution'],
    )
    # This endpoint call also propagates to the real
    # providers.set_cover_resolution; stub it out so this test (which
    # only cares about the clamped response value) doesn't leak global
    # provider state into whichever test runs next.
    monkeypatch.setattr(
        api.providers, 'set_cover_resolution', lambda *_a: None
    )
    result = _call_update_settings(monkeypatch, {'cover_resolution': 99999})
    assert result['cover_resolution'] == MAX_COVER_RESOLUTION


def test_update_settings_accepts_in_range_cover_resolution(monkeypatch):
    monkeypatch.setitem(
        api.state.settings,
        'cover_resolution',
        DEFAULT_SETTINGS['cover_resolution'],
    )
    monkeypatch.setattr(
        api.providers, 'set_cover_resolution', lambda *_a: None
    )
    result = _call_update_settings(monkeypatch, {'cover_resolution': 900})
    assert result['cover_resolution'] == 900


def test_update_settings_applies_cover_resolution_to_providers(monkeypatch):
    monkeypatch.setitem(
        api.state.settings,
        'cover_resolution',
        DEFAULT_SETTINGS['cover_resolution'],
    )
    captured = []
    monkeypatch.setattr(api.providers, 'set_cover_resolution', captured.append)
    _call_update_settings(monkeypatch, {'cover_resolution': 900})
    assert captured == [900]


def test_update_settings_leaves_providers_untouched_when_key_absent(
    monkeypatch,
):
    monkeypatch.setitem(
        api.state.settings,
        'cover_resolution',
        DEFAULT_SETTINGS['cover_resolution'],
    )
    captured = []
    monkeypatch.setattr(api.providers, 'set_cover_resolution', captured.append)
    _call_update_settings(monkeypatch, {'format': 'flac'})
    assert captured == []


# ── audio providers / slskd / Navidrome settings (PR #182) ────────────────


def test_effective_audio_providers_keeps_allowed_order():
    settings = {
        'audio_providers': ['youtube', 'slskd', 'youtube-music'],
        'slskd': {'enabled': True},
    }
    assert _effective_audio_providers(settings) == [
        'youtube',
        'slskd',
        'youtube-music',
    ]


def test_effective_audio_providers_filters_invalid_and_dedupes():
    settings = {
        'audio_providers': [
            'youtube',
            'invalid',
            'youtube',
            'slskd',
            'youtube-music',
        ],
        'slskd': {'enabled': True},
    }
    assert _effective_audio_providers(settings) == [
        'youtube',
        'slskd',
        'youtube-music',
    ]


def test_effective_audio_providers_adds_youtube_fallback_when_only_slskd():
    settings = {
        'audio_providers': ['slskd'],
        'slskd': {'enabled': True},
    }
    assert _effective_audio_providers(settings) == [
        'slskd',
        'youtube-music',
        'youtube',
    ]


def test_effective_audio_providers_skips_slskd_when_disabled():
    settings = {
        'audio_providers': ['youtube', 'slskd', 'youtube-music'],
        'slskd': {'enabled': False},
    }
    assert _effective_audio_providers(settings) == ['youtube', 'youtube-music']


def test_effective_audio_providers_defaults_when_missing():
    assert _effective_audio_providers({}) == ['youtube-music']


def test_effective_slskd_settings_defaults_when_missing():
    out = _effective_slskd_settings({})
    assert out['enabled'] is False
    assert not out['base_url']
    assert out['download_dir'] == '/downloads'
    assert out['timeout_seconds'] == 20


def test_effective_slskd_settings_normalizes_values():
    out = _effective_slskd_settings({
        'slskd': {
            'enabled': True,
            'base_url': 'http://slskd.local:5030/',
            'api_key': '  key ',
            'download_dir': '/data/slskd',
            'timeout_seconds': '90',
            'poll_interval_seconds': '2',
            'poll_max_attempts': '99',
        }
    })
    assert out['base_url'] == 'http://slskd.local:5030'
    assert out['enabled'] is True
    assert out['api_key'] == 'key'
    assert out['download_dir'] == '/data/slskd'
    assert out['source_dir'] == '/slskd'
    assert out['timeout_seconds'] == 90
    assert out['poll_interval_seconds'] == 2
    assert out['poll_max_attempts'] == 99
    assert out['search_retries'] == 5


def test_effective_slskd_settings_caps_parallelism_at_eight():
    out = _effective_slskd_settings({'max_parallel_downloads': 30})
    assert out['max_parallel_downloads'] == 8


def test_load_settings_deep_merges_slskd_dict(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text(
        json.dumps({'slskd': {'base_url': 'http://slskd:5030'}}),
        encoding='utf-8',
    )
    out = _load_settings(path)
    assert out['slskd']['base_url'] == 'http://slskd:5030'
    assert out['slskd']['download_dir'] == '/downloads'
    assert out['slskd']['duration_tolerance_percent'] == 15


def test_load_settings_keeps_explicit_duration_tolerance(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text(
        json.dumps({
            'slskd': {
                'duration_tolerance_percent': 20,
                'duration_tolerance_seconds': 10,
                'mix_duration_tolerance_percent': 50,
            },
        }),
        encoding='utf-8',
    )
    out = _load_settings(path)
    assert out['slskd']['duration_tolerance_percent'] == 20


class _JsonRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def _update(monkeypatch, payload, downloader=None):
    monkeypatch.setattr(api.state, 'settings', dict(DEFAULT_SETTINGS))
    monkeypatch.setattr(api.state, 'settings_path', None)
    monkeypatch.setattr(api.state, 'downloader', downloader)
    return asyncio.run(
        api.update_settings_endpoint(_JsonRequest(payload), client_id='')
    )


def test_update_settings_rejects_enabled_slskd_without_url(monkeypatch):
    with pytest.raises(HTTPException) as exc_info:
        _update(monkeypatch, {'slskd': {'enabled': True, 'api_key': 'k'}})
    assert exc_info.value.status_code == 400
    # A rejected save leaves the stored settings untouched.
    assert api.state.settings['slskd']['enabled'] is False


def test_update_settings_rejects_enabled_navidrome_without_password(
    monkeypatch,
):
    with pytest.raises(HTTPException) as exc_info:
        _update(
            monkeypatch,
            {
                'navidrome': {
                    'enabled': True,
                    'url': 'http://nd',
                    'username': 'u',
                }
            },
        )
    assert 'password' in exc_info.value.detail


def test_update_settings_applies_providers_and_slskd_to_downloader(
    monkeypatch, tmp_path
):
    downloader = Downloader(tmp_path)
    out = _update(
        monkeypatch,
        {
            'audio_providers': ['slskd', 'youtube-music'],
            'slskd': {
                'enabled': True,
                'base_url': 'http://slskd:5030/',
                'api_key': 'key',
            },
        },
        downloader=downloader,
    )
    assert out['audio_providers'] == ['slskd', 'youtube-music']
    assert out['slskd']['base_url'] == 'http://slskd:5030'
    assert 'max_parallel_downloads' not in out['slskd']
    assert downloader.audio_providers == ['slskd', 'youtube-music']
    assert downloader.slskd_settings['enabled'] is True
    assert downloader.slskd_settings['output_dir'] == str(tmp_path)
