"""YouTube cookies settings and yt-dlp option wiring."""

from __future__ import annotations

from pathlib import Path

from downtify.api import (
    DEFAULT_SETTINGS,
    _effective_youtube_settings,
    _validate_youtube_cookies_bytes,
    _youtube_cookies_storage_path,
    _youtube_settings_for_response,
)
from downtify.downloader import (
    _youtube_watch_urls,
    apply_ytdlp_cookie_opts,
    ytdlp_cookies_configured,
)


def test_default_settings_includes_youtube():
    assert 'youtube' in DEFAULT_SETTINGS
    assert DEFAULT_SETTINGS['youtube']['cookies_file'] == ''


def test_effective_youtube_settings_strips_paths():
    settings = {
        'youtube': {
            'cookies_file': '  /data/cookies.txt  ',
            'cookies_from_browser': ' chrome:Default ',
        }
    }
    out = _effective_youtube_settings(settings)
    assert out['cookies_file'] == '/data/cookies.txt'
    assert out['cookies_from_browser'] == 'chrome:Default'


def test_apply_ytdlp_cookie_opts_from_settings(tmp_path: Path):
    cookie_path = tmp_path / 'cookies.txt'
    cookie_path.write_text(
        '# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tx\ty\n',
        encoding='utf-8',
    )
    opts: dict = {}
    apply_ytdlp_cookie_opts(
        opts, {'cookies_file': str(cookie_path), 'cookies_from_browser': ''}
    )
    assert opts['cookiefile'] == str(cookie_path)


def test_apply_ytdlp_cookie_opts_skips_missing_file():
    opts: dict = {}
    apply_ytdlp_cookie_opts(opts, {'cookies_file': '/no/such/cookies.txt'})
    assert 'cookiefile' not in opts


def test_youtube_settings_for_response_exists_flag(tmp_path: Path):
    cookie_path = tmp_path / 'cookies.txt'
    cookie_path.write_text(
        '.youtube.com\n',
        encoding='utf-8',
    )
    settings = {'youtube': {'cookies_file': str(cookie_path)}}
    out = _youtube_settings_for_response(settings)
    assert out['cookies_file_exists'] is True


def test_youtube_cookies_storage_path_next_to_settings(tmp_path: Path):
    settings_path = tmp_path / 'settings.json'
    assert _youtube_cookies_storage_path(settings_path) == (
        tmp_path / 'youtube-cookies.txt'
    )


def test_youtube_watch_urls_prefers_www_with_cookies(tmp_path: Path):
    cookie_path = tmp_path / 'cookies.txt'
    cookie_path.write_text(
        '.youtube.com\n',
        encoding='utf-8',
    )
    settings = {'cookies_file': str(cookie_path)}
    urls = _youtube_watch_urls('abc123', settings)
    assert urls[0] == 'https://www.youtube.com/watch?v=abc123'
    assert 'music.youtube.com' in urls[1]


def test_youtube_watch_urls_music_first_without_cookies():
    urls = _youtube_watch_urls('abc123', {})
    assert urls[0].startswith('https://music.youtube.com/')


def test_ytdlp_cookies_configured_false_when_missing_file():
    assert not ytdlp_cookies_configured({'cookies_file': '/no/such.txt'})


def test_validate_youtube_cookies_bytes_rejects_empty():
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _validate_youtube_cookies_bytes(b'   ')
    assert exc.value.status_code == 400
