from __future__ import annotations

import os

import pytest

from downtify import providers, proxy_config

_PROXY_ENV = (
    'DOWNTIFY_PROXY',
    'DOWNTIFY_PROXY_STRICT',
    'DOWNTIFY_PROXY_BYPASS',
    'HTTP_PROXY',
    'http_proxy',
    'HTTPS_PROXY',
    'https_proxy',
    'ALL_PROXY',
    'all_proxy',
    'NO_PROXY',
    'no_proxy',
)


@pytest.fixture
def clean_proxy_environment(monkeypatch):
    for name in _PROXY_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(proxy_config, '_config', None)


def test_socks5h_config_preserves_remote_dns_for_supported_clients(
    monkeypatch, clean_proxy_environment
):
    monkeypatch.setenv(
        'DOWNTIFY_PROXY', 'socks5h://user:pass@tor-gateway:9050'
    )
    monkeypatch.setenv('DOWNTIFY_PROXY_BYPASS', 'slskd,navidrome')

    config = proxy_config.configure_outbound_proxy()

    assert config.strict is False
    assert os.environ['HTTP_PROXY'] == 'socks5://user:pass@tor-gateway:9050'
    assert os.environ['HTTPS_PROXY'] == 'socks5://user:pass@tor-gateway:9050'
    assert os.environ['ALL_PROXY'] == 'socks5://user:pass@tor-gateway:9050'
    assert 'localhost' in os.environ['NO_PROXY'].split(',')
    assert 'slskd' in os.environ['NO_PROXY'].split(',')
    assert proxy_config.requests_proxies_for_youtube_music() == {
        'http': 'socks5h://user:pass@tor-gateway:9050',
        'https': 'socks5h://user:pass@tor-gateway:9050',
    }


def test_standard_proxy_variables_are_normalized_for_httpx(
    monkeypatch, clean_proxy_environment
):
    monkeypatch.setenv('http_proxy', 'socks5h://tor-gateway:9050')
    monkeypatch.setenv('https_proxy', 'socks5h://tor-gateway:9050')

    proxy_config.configure_outbound_proxy()

    assert os.environ['http_proxy'] == 'socks5://tor-gateway:9050'
    assert os.environ['https_proxy'] == 'socks5://tor-gateway:9050'
    assert proxy_config.requests_proxies_for_youtube_music() == {
        'http': 'socks5h://tor-gateway:9050',
        'https': 'socks5h://tor-gateway:9050',
    }


def test_strict_mode_requires_http_and_https_proxy_coverage(
    monkeypatch, clean_proxy_environment
):
    monkeypatch.setenv('DOWNTIFY_PROXY_STRICT', 'true ')
    monkeypatch.setenv('HTTPS_PROXY', 'http://proxy:8080')

    with pytest.raises(proxy_config.ProxyConfigurationError, match='requires'):
        proxy_config.configure_outbound_proxy()


def test_invalid_strict_mode_value_is_not_silently_disabled(
    monkeypatch, clean_proxy_environment
):
    monkeypatch.setenv('DOWNTIFY_PROXY_STRICT', 'tru')
    monkeypatch.setenv('DOWNTIFY_PROXY', 'http://proxy:8080')

    with pytest.raises(proxy_config.ProxyConfigurationError, match='boolean'):
        proxy_config.configure_outbound_proxy()


def test_strict_mode_rejects_wildcard_bypass(
    monkeypatch, clean_proxy_environment
):
    monkeypatch.setenv('DOWNTIFY_PROXY_STRICT', 'true')
    monkeypatch.setenv('DOWNTIFY_PROXY', 'http://proxy:8080')
    monkeypatch.setenv('NO_PROXY', '*')

    with pytest.raises(proxy_config.ProxyConfigurationError, match='NO_PROXY'):
        proxy_config.configure_outbound_proxy()


def test_configured_bypass_skips_youtube_music_proxy(
    monkeypatch, clean_proxy_environment
):
    monkeypatch.setenv('DOWNTIFY_PROXY', 'socks5h://tor-gateway:9050')
    monkeypatch.setenv('DOWNTIFY_PROXY_BYPASS', 'music.youtube.com')

    proxy_config.configure_outbound_proxy()

    assert proxy_config.requests_proxies_for_youtube_music() == {
        'http': None,
        'https': None,
    }


def test_ytmusic_client_receives_original_proxy_url(
    monkeypatch, clean_proxy_environment
):
    monkeypatch.setenv('DOWNTIFY_PROXY', 'socks5h://tor-gateway:9050')
    proxy_config.configure_outbound_proxy()
    constructed = []

    class FakeYTMusic:
        def __init__(self, **kwargs):
            constructed.append(kwargs)

    monkeypatch.setattr(providers, 'YTMusic', FakeYTMusic)
    monkeypatch.setattr(providers, '_client', None)

    providers._ytm()

    assert constructed == [
        {
            'proxies': {
                'http': 'socks5h://tor-gateway:9050',
                'https': 'socks5h://tor-gateway:9050',
            }
        }
    ]
