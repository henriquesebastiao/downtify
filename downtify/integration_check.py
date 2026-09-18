"""Try a slskd or Navidrome configuration and say what is wrong with it.

Both integrations are set up by pasting an address and a credential, and
a typo shows up much later: a download that quietly falls back to YouTube,
a playlist that never appears. The checks here run the same first requests
those features would make, so the Settings page can answer "is this
right?" while the values are still in the form.

A result is a list of checks, each ``{id, status, code, detail}``. Codes
are stable identifiers the UI translates; ``detail`` is only ever a short
fact (a path, a state name, an HTTP status). Nothing from an exception
message is passed on: httpx puts the request URL in them, and a Subsonic
URL carries the login token.
"""

from __future__ import annotations

import os
import re
import ssl
from pathlib import Path
from typing import Any, Optional

import httpx
from loguru import logger

from .navidrome import SUBSONIC_AUTH_FAILED, NavidromeClient, SubsonicError
from .slskd_provider import SlskdClient

#: Seconds each request may take. A test that hangs is worse than one
#: that says "no answer".
PROBE_TIMEOUT = 8.0

STATUS_OK = 'ok'
STATUS_WARN = 'warn'
STATUS_FAIL = 'fail'

_VERSION = re.compile(r'^\d+(\.\d+)+')


def _get(url: str, **kwargs: Any) -> httpx.Response:
    """The one place a slskd probe touches the network (tests replace it)."""

    return httpx.get(url, follow_redirects=True, **kwargs)


def _check(
    check_id: str, status: str, code: str = '', detail: str = ''
) -> dict[str, str]:
    return {'id': check_id, 'status': status, 'code': code, 'detail': detail}


def _result(checks: list[dict[str, str]], server: str = '') -> dict[str, Any]:
    return {
        'ok': all(check['status'] != STATUS_FAIL for check in checks),
        'server': server,
        'checks': checks,
    }


def _transport_code(exc: BaseException) -> str:
    """Why a request never got an answer, without quoting the error."""

    if isinstance(exc, httpx.TimeoutException):
        return 'timeout'
    if isinstance(exc, (httpx.InvalidURL, httpx.UnsupportedProtocol)):
        return 'bad_url'
    seen: set[int] = set()
    cause: Optional[BaseException] = exc
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        if isinstance(cause, ssl.SSLError):
            return 'tls'
        cause = cause.__cause__ or cause.__context__
    return 'unreachable'


def _log_failure(what: str, exc: BaseException) -> None:
    # The type only: the message may carry the URL, and with it a token.
    logger.info('{} check failed: {}', what, type(exc).__name__)


# ── slskd ────────────────────────────────────────────────────────────
def _slskd_version(resp: httpx.Response) -> Optional[str]:
    """The version slskd reports, or ``None`` if this isn't slskd."""

    try:
        body = resp.json()
    except ValueError:
        body = resp.text
    text = str(body).strip().strip('"') if isinstance(body, str) else ''
    return text if _VERSION.match(text) else None


def _slskd_soulseek(
    base_url: str, headers: dict[str, str]
) -> Optional[dict[str, str]]:
    """Whether slskd is logged in to the Soulseek network."""

    try:
        resp = _get(
            f'{base_url}/api/v0/server', headers=headers, timeout=PROBE_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        _log_failure('slskd server state', exc)
        return None
    if not isinstance(data, dict) or 'isLoggedIn' not in data:
        return None
    if data.get('isLoggedIn'):
        return _check(
            'soulseek', STATUS_OK, 'ok', str(data.get('username') or '')
        )
    return _check(
        'soulseek', STATUS_WARN, 'offline', str(data.get('state') or '')
    )


def _slskd_folder(cfg: dict[str, Any]) -> dict[str, str]:
    """Whether Downtify can read the folder slskd's files end up in."""

    source = str(cfg.get('source_dir') or '')
    probe_cfg = {**cfg, 'timeout_seconds': int(PROBE_TIMEOUT)}
    candidates = [source]
    try:
        # slskd's own idea of where it downloads, in case it is mounted
        # here at the same path.
        candidates += SlskdClient(probe_cfg).remote_download_directories()
    except Exception as exc:
        _log_failure('slskd folders', exc)
    for raw in candidates:
        path = Path(raw) if raw else None
        if path is not None and path.is_dir() and os.access(path, os.R_OK):
            return _check('folder', STATUS_OK, 'ok', str(path))
    return _check('folder', STATUS_WARN, 'missing', source)


def check_slskd(cfg: dict[str, Any]) -> dict[str, Any]:
    """Test a normalized slskd configuration (see ``_effective_slskd_settings``)."""

    base_url = str(cfg.get('base_url') or '')
    api_key = str(cfg.get('api_key') or '')
    if not base_url or not api_key:
        return _result([_check('config', STATUS_FAIL, 'missing')])

    headers = {'X-API-Key': api_key}
    try:
        resp = _get(
            f'{base_url}/api/v0/application/version',
            headers=headers,
            timeout=PROBE_TIMEOUT,
        )
    except Exception as exc:
        _log_failure('slskd connection', exc)
        return _result([
            _check('connection', STATUS_FAIL, _transport_code(exc))
        ])

    if resp.status_code in {401, 403}:
        return _result([
            _check('connection', STATUS_OK),
            _check('auth', STATUS_FAIL, 'bad_key'),
        ])
    if resp.status_code == 404:
        return _result([_check('connection', STATUS_FAIL, 'not_slskd')])
    if resp.status_code >= 400:
        return _result([
            _check(
                'connection',
                STATUS_FAIL,
                'http_error',
                str(resp.status_code),
            )
        ])
    version = _slskd_version(resp)
    if version is None:
        return _result([_check('connection', STATUS_FAIL, 'not_slskd')])

    checks = [_check('connection', STATUS_OK), _check('auth', STATUS_OK)]
    soulseek = _slskd_soulseek(base_url, headers)
    if soulseek is not None:
        checks.append(soulseek)
    checks.append(_slskd_folder(cfg))
    return _result(checks, f'slskd {version}')


# ── Navidrome ────────────────────────────────────────────────────────
def _navidrome_failure(exc: BaseException) -> dict[str, str]:
    """The connection/auth check that an exception from a request means."""

    if isinstance(exc, SubsonicError):
        if exc.code == SUBSONIC_AUTH_FAILED:
            return _check('auth', STATUS_FAIL, 'bad_credentials')
        # The server's own words, never a URL.
        return _check('auth', STATUS_FAIL, 'api_error', str(exc)[:160])
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in {401, 403}:
            return _check('auth', STATUS_FAIL, 'bad_credentials')
        if status in {404, 405}:
            return _check('connection', STATUS_FAIL, 'not_navidrome')
        return _check('connection', STATUS_FAIL, 'http_error', str(status))
    if isinstance(exc, (httpx.HTTPError, httpx.InvalidURL)):
        return _check('connection', STATUS_FAIL, _transport_code(exc))
    # A page that isn't JSON, or JSON that isn't a Subsonic reply.
    return _check('connection', STATUS_FAIL, 'not_navidrome')


def _navidrome_scan(
    client: NavidromeClient, cfg: dict[str, Any]
) -> Optional[dict[str, str]]:
    """Whether the account used for library scans is allowed to start one.

    ``startScan`` is admin-only in Navidrome, and a refusal there is only
    ever logged, so a scan account that can't scan looks like it works.
    ``getUser`` on oneself tells without starting a scan.
    """

    user, password = client._scan_credentials()
    separate = bool(cfg.get('admin_username') and cfg.get('admin_password'))
    try:
        body = client._request(
            'getUser', {'username': user}, username=user, password=password
        )
    except SubsonicError as exc:
        if separate and exc.code == SUBSONIC_AUTH_FAILED:
            return _check('scan', STATUS_FAIL, 'bad_admin')
        return None
    except Exception as exc:
        _log_failure('navidrome scan account', exc)
        return None
    info = body.get('user')
    admin = info.get('adminRole') if isinstance(info, dict) else None
    if admin is True:
        return _check('scan', STATUS_OK, 'ok')
    if admin is False:
        return _check(
            'scan',
            STATUS_WARN,
            'not_admin_separate' if separate else 'not_admin',
        )
    return None


def check_navidrome(cfg: dict[str, Any]) -> dict[str, Any]:
    """Test a normalized Navidrome configuration (see ``_effective_navidrome_settings``)."""

    if not (cfg.get('url') and cfg.get('username') and cfg.get('password')):
        return _result([_check('config', STATUS_FAIL, 'missing')])

    client = NavidromeClient(cfg)
    client.timeout = PROBE_TIMEOUT
    try:
        body = client._request('ping')
    except Exception as exc:
        _log_failure('navidrome connection', exc)
        failure = _navidrome_failure(exc)
        if failure['id'] == 'auth':
            return _result([_check('connection', STATUS_OK), failure])
        return _result([failure])

    checks = [_check('connection', STATUS_OK), _check('auth', STATUS_OK)]
    if cfg.get('scan_after_download', True):
        scan = _navidrome_scan(client, cfg)
        if scan is not None:
            checks.append(scan)
    name = str(body.get('type') or 'Subsonic')
    version = str(body.get('serverVersion') or '')
    return _result(checks, f'{name} {version}'.strip())
