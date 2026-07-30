"""Tests for the settings pipeline: DEFAULT_SETTINGS, _load_settings and
_effective_lyrics_providers."""

from __future__ import annotations

import inspect
import json

from downtify import api
from downtify.api import (
    DEFAULT_SETTINGS,
    _effective_lyrics_providers,
    _load_settings,
    artist_info_endpoint,
    artist_similar_endpoint,
    artist_top_albums_endpoint,
    artist_top_songs_endpoint,
    search_albums_endpoint,
    search_artists_endpoint,
)


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
