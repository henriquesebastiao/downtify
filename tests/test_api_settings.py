"""Tests for the settings pipeline: DEFAULT_SETTINGS, _load_settings and
_effective_lyrics_providers."""

from __future__ import annotations

import json

from downtify.api import (
    DEFAULT_SETTINGS,
    _effective_audio_providers,
    _effective_lyrics_providers,
    _effective_slskd_settings,
    _load_settings,
)


def test_default_settings_has_required_keys():
    required = {
        'audio_providers',
        'slskd',
        'lyrics_providers',
        'download_lyrics',
        'format',
        'bitrate',
        'output',
        'generate_m3u',
        'sync_navidrome',
        'navidrome',
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
        ]
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
    assert out['base_url'] == ''
    assert out['download_dir'] == '/downloads'
    assert out['timeout_seconds'] == 20


def test_effective_slskd_settings_normalizes_values():
    out = _effective_slskd_settings(
        {
            'slskd': {
                'enabled': True,
                'base_url': 'http://slskd.local:5030/',
                'api_key': '  key ',
                'download_dir': '/data/slskd',
                'timeout_seconds': '90',
                'poll_interval_seconds': '2',
                'poll_max_attempts': '99',
            }
        }
    )
    assert out['base_url'] == 'http://slskd.local:5030'
    assert out['enabled'] is True
    assert out['api_key'] == 'key'
    assert out['download_dir'] == '/data/slskd'
    assert out['source_dir'] == '/data/slskd'
    assert out['timeout_seconds'] == 90
    assert out['poll_interval_seconds'] == 2
    assert out['poll_max_attempts'] == 99
    assert out['search_retries'] == 5


def test_load_settings_deep_merges_slskd_dict(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text(
        json.dumps({'slskd': {'base_url': 'http://slskd:5030'}}),
        encoding='utf-8',
    )
    out = _load_settings(path)
    assert out['slskd']['base_url'] == 'http://slskd:5030'
    assert out['slskd']['download_dir'] == '/downloads'


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
