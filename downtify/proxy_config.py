"""Application-wide outbound HTTP proxy configuration."""

from __future__ import annotations

import importlib.util
import os
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from loguru import logger

_PROXY_SCHEMES = ('http', 'https', 'all')
_PROXY_ENV_NAMES = {
    scheme: (f'{scheme.upper()}_PROXY', f'{scheme}_proxy')
    for scheme in _PROXY_SCHEMES
}
_LOCAL_BYPASSES = ('localhost', '127.0.0.1', '::1')
_TRUE_VALUES = {'1', 'true', 'yes', 'on'}
_FALSE_VALUES = {'0', 'false', 'no', 'off'}


@dataclass(frozen=True)
class OutboundProxyConfig:
    proxy_urls: dict[str, str]
    strict: bool
    bypass_hosts: tuple[str, ...]


class ProxyConfigurationError(ValueError):
    """The outbound proxy configuration cannot be applied safely."""


_config: OutboundProxyConfig | None = None


def _validate_proxy_url(
    value: str, *, allow_missing_scheme: bool = False
) -> str:
    url = value.strip()
    if allow_missing_scheme and '://' not in url:
        url = f'http://{url}'
    try:
        parsed = urlsplit(url)
        parsed.port
    except ValueError as exc:
        raise ProxyConfigurationError('Invalid outbound proxy URL') from exc
    if (
        parsed.scheme.lower() not in {'http', 'https', 'socks5', 'socks5h'}
        or not parsed.hostname
        or parsed.path not in {'', '/'}
        or parsed.query
        or parsed.fragment
    ):
        raise ProxyConfigurationError(
            'Proxy URL must use http, https, socks5 or socks5h and include a host'
        )
    return url


def _httpx_proxy_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme.lower() != 'socks5h':
        return value
    return urlunsplit(parsed._replace(scheme='socks5'))


def _proxy_environment() -> dict[str, str]:
    configured = os.getenv('DOWNTIFY_PROXY', '').strip()
    if configured:
        proxy = _validate_proxy_url(configured)
        return {scheme: proxy for scheme in _PROXY_SCHEMES}

    raw = urllib.request.getproxies()
    return {
        scheme: _validate_proxy_url(raw[scheme], allow_missing_scheme=True)
        for scheme in _PROXY_SCHEMES
        if raw.get(scheme)
    }


def _strict_mode() -> bool:
    value = os.getenv('DOWNTIFY_PROXY_STRICT', '').strip().lower()
    if not value:
        return False
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise ProxyConfigurationError(
        'DOWNTIFY_PROXY_STRICT must be a boolean value'
    )


def _bypass_hosts(proxy_urls: dict[str, str], strict: bool) -> tuple[str, ...]:
    existing = urllib.request.getproxies().get('no', '')
    configured = os.getenv('DOWNTIFY_PROXY_BYPASS', '')
    hosts = [
        host.strip()
        for value in (existing, configured)
        for host in value.split(',')
        if host.strip()
    ]
    if '*' in hosts and strict:
        raise ProxyConfigurationError(
            'Strict proxy mode cannot be combined with NO_PROXY=*'
        )
    if proxy_urls:
        hosts.extend(_LOCAL_BYPASSES)
    return tuple(dict.fromkeys(hosts))


def configure_outbound_proxy() -> OutboundProxyConfig:
    """Validate settings and configure standard proxy-aware HTTP clients."""

    global _config
    proxy_urls = _proxy_environment()
    strict = _strict_mode()
    bypass_hosts = _bypass_hosts(proxy_urls, strict)
    if strict and not (
        'all' in proxy_urls or {'http', 'https'} <= set(proxy_urls)
    ):
        raise ProxyConfigurationError(
            'Strict proxy mode requires DOWNTIFY_PROXY, ALL_PROXY, or both '
            'HTTP_PROXY and HTTPS_PROXY'
        )

    if any(
        urlsplit(url).scheme.lower().startswith('socks5')
        for url in proxy_urls.values()
    ):
        missing = [
            package
            for package in ('socksio', 'socks')
            if importlib.util.find_spec(package) is None
        ]
        if missing:
            raise ProxyConfigurationError(
                'SOCKS proxy support is missing: ' + ', '.join(missing)
            )

    for scheme, url in proxy_urls.items():
        for name in _PROXY_ENV_NAMES[scheme]:
            os.environ[name] = _httpx_proxy_url(url)
    if proxy_urls:
        no_proxy = ','.join(bypass_hosts)
        os.environ['NO_PROXY'] = no_proxy
        os.environ['no_proxy'] = no_proxy

    _config = OutboundProxyConfig(proxy_urls, strict, bypass_hosts)
    if proxy_urls:
        routes = ', '.join(scheme.upper() for scheme in proxy_urls)
        authorities = sorted({
            urlsplit(url).hostname or '' for url in proxy_urls.values()
        })
        logger.info(
            'Outbound proxy configured for {} via {} (strict={}, bypass_hosts={})',
            routes,
            ', '.join(authorities),
            strict,
            len(bypass_hosts),
        )
    elif strict:
        raise ProxyConfigurationError(
            'Strict proxy mode requires an outbound proxy'
        )
    else:
        logger.info(
            'Outbound proxy is not configured; direct access is allowed'
        )
    return _config


def outbound_proxy_config() -> OutboundProxyConfig:
    return _config if _config is not None else configure_outbound_proxy()


def requests_proxies_for_youtube_music() -> dict[str, str | None] | None:
    """Requests-format proxy map, retaining socks5h remote-DNS semantics."""

    config = outbound_proxy_config()
    if not config.proxy_urls:
        return None
    if urllib.request.proxy_bypass('music.youtube.com'):
        return {'http': None, 'https': None}
    proxies: dict[str, str | None] = {}
    for scheme in ('http', 'https'):
        proxies[scheme] = config.proxy_urls.get(
            scheme
        ) or config.proxy_urls.get('all')
    return proxies
