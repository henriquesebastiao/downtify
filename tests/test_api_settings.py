"""Tests for the settings pipeline: DEFAULT_SETTINGS, _load_settings and
_effective_lyrics_providers."""

from __future__ import annotations

import json

from downtify.api import (
    DEFAULT_SETTINGS,
    _effective_lyrics_providers,
    _load_settings,
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
