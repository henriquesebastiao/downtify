"""Trying a slskd or Navidrome configuration from the Settings page.

Everything runs offline: the one network call per integration is replaced
with canned answers shaped like the real services' (slskd's
``/api/v0/...`` and Navidrome's Subsonic ``ping`` / ``getUser``).
"""

from __future__ import annotations

import asyncio
import json
import ssl
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from loguru import logger

from downtify import api, integration_check, navidrome
from downtify.api import (
    _effective_navidrome_settings,
    _effective_slskd_settings,
)
from downtify.integration_check import check_navidrome, check_slskd
from downtify.slskd_provider import SlskdClient

# ── helpers ────────────────────────────────────────────────────────────


def _response(status: int = 200, **kwargs: Any) -> httpx.Response:
    """A real httpx response, so ``.json()`` and ``raise_for_status`` work."""

    return httpx.Response(
        status, request=httpx.Request('GET', 'http://test/'), **kwargs
    )


def _by_id(result: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {check['id']: check for check in result['checks']}


# ── slskd ──────────────────────────────────────────────────────────────


def _slskd_cfg(tmp_path, **over: Any) -> dict[str, Any]:
    cfg = _effective_slskd_settings({
        'slskd': {
            'base_url': 'http://slskd:5030/',
            'api_key': 'KEY',
            'source_dir': str(tmp_path),
            **over,
        }
    })
    return cfg


def _slskd_server(
    *,
    version: Any = '0.21.4',
    server: Any = None,
    version_status: int = 200,
    seen: list | None = None,
) -> Callable[..., httpx.Response]:
    """A fake slskd keyed on the request path."""

    if server is None:
        server = {
            'isLoggedIn': True,
            'state': 'Connected, LoggedIn',
            'username': 'me',
        }

    def fake(url: str, **kwargs: Any) -> httpx.Response:
        if seen is not None:
            seen.append((url, kwargs.get('headers')))
        path = urlparse(url).path
        if path == '/api/v0/application/version':
            if version_status != 200:
                return _response(version_status)
            if isinstance(version, str) and version.startswith('<'):
                return _response(200, text=version)
            return _response(200, json=version)
        if path == '/api/v0/server':
            if isinstance(server, Exception):
                raise server
            return _response(200, json=server)
        return _response(404)

    return fake


@pytest.fixture(autouse=True)
def _no_remote_folders(monkeypatch):
    """slskd's own folder list is another request; off unless a test wants it."""

    monkeypatch.setattr(
        SlskdClient, 'remote_download_directories', lambda s: []
    )


def test_a_working_slskd_reports_its_version_and_every_check(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(integration_check, '_get', _slskd_server())

    result = check_slskd(_slskd_cfg(tmp_path))

    assert result['ok'] is True
    assert result['server'] == 'slskd 0.21.4'
    checks = _by_id(result)
    assert checks['connection']['status'] == 'ok'
    assert checks['auth']['status'] == 'ok'
    assert (checks['soulseek']['status'], checks['soulseek']['detail']) == (
        'ok',
        'me',
    )
    assert checks['folder']['status'] == 'ok'
    assert checks['folder']['detail'] == str(tmp_path)


def test_the_api_key_goes_in_a_header_never_in_the_url(monkeypatch, tmp_path):
    seen: list = []
    monkeypatch.setattr(integration_check, '_get', _slskd_server(seen=seen))

    check_slskd(_slskd_cfg(tmp_path))

    assert seen
    for url, headers in seen:
        assert 'KEY' not in url
        assert headers == {'X-API-Key': 'KEY'}
    # The trailing slash of the saved address is gone before it is used.
    assert seen[0][0] == 'http://slskd:5030/api/v0/application/version'


def test_a_rejected_key_is_an_auth_failure_not_a_dead_server(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        integration_check, '_get', _slskd_server(version_status=401)
    )

    result = check_slskd(_slskd_cfg(tmp_path))

    assert result['ok'] is False
    checks = _by_id(result)
    assert checks['connection']['status'] == 'ok'
    assert (checks['auth']['status'], checks['auth']['code']) == (
        'fail',
        'bad_key',
    )
    assert not result['server']
    # Nothing past the door is tried.
    assert 'soulseek' not in checks
    assert 'folder' not in checks


def test_something_that_is_not_slskd_is_recognised(monkeypatch, tmp_path):
    cfg = _slskd_cfg(tmp_path)
    for fake in (
        _slskd_server(version_status=404),
        _slskd_server(version='<html>welcome</html>'),
        _slskd_server(version={'not': 'a version'}),
    ):
        monkeypatch.setattr(integration_check, '_get', fake)
        result = check_slskd(cfg)
        assert result['ok'] is False
        assert _by_id(result)['connection']['code'] == 'not_slskd'


def test_other_http_errors_report_the_status(monkeypatch, tmp_path):
    monkeypatch.setattr(
        integration_check, '_get', _slskd_server(version_status=502)
    )

    check = _by_id(check_slskd(_slskd_cfg(tmp_path)))['connection']

    assert (check['code'], check['detail']) == ('http_error', '502')


def _tls_error() -> httpx.ConnectError:
    error = httpx.ConnectError('certificate verify failed')
    error.__cause__ = ssl.SSLCertVerificationError('self signed certificate')
    return error


@pytest.mark.parametrize(
    ('exc', 'code'),
    [
        (httpx.ConnectError('refused'), 'unreachable'),
        (httpx.ConnectTimeout('slow'), 'timeout'),
        (httpx.ReadTimeout('slow'), 'timeout'),
        (httpx.UnsupportedProtocol('no scheme'), 'bad_url'),
        (httpx.InvalidURL('bad'), 'bad_url'),
        (_tls_error(), 'tls'),
    ],
)
def test_a_request_that_gets_no_answer_says_why(
    monkeypatch, tmp_path, exc, code
):
    def boom(url: str, **kwargs: Any) -> httpx.Response:
        raise exc

    monkeypatch.setattr(integration_check, '_get', boom)

    result = check_slskd(_slskd_cfg(tmp_path))

    assert result['ok'] is False
    assert _by_id(result)['connection']['code'] == code


def test_slskd_signed_out_of_soulseek_is_a_warning_not_a_failure(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        integration_check,
        '_get',
        _slskd_server(server={'isLoggedIn': False, 'state': 'Disconnected'}),
    )

    result = check_slskd(_slskd_cfg(tmp_path))

    # Connected and authorised, so the settings are right; searches just
    # won't find anything until slskd logs in.
    assert result['ok'] is True
    check = _by_id(result)['soulseek']
    assert (check['status'], check['code'], check['detail']) == (
        'warn',
        'offline',
        'Disconnected',
    )


def test_an_unreadable_server_state_is_skipped_not_guessed(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        integration_check,
        '_get',
        _slskd_server(server=httpx.ReadTimeout('slow')),
    )

    result = check_slskd(_slskd_cfg(tmp_path))

    assert result['ok'] is True
    assert 'soulseek' not in _by_id(result)


def test_a_missing_download_folder_is_a_warning_with_the_path(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(integration_check, '_get', _slskd_server())
    gone = tmp_path / 'not-mounted'

    result = check_slskd(_slskd_cfg(tmp_path, source_dir=str(gone)))

    assert result['ok'] is True
    check = _by_id(result)['folder']
    assert (check['status'], check['code'], check['detail']) == (
        'warn',
        'missing',
        str(gone),
    )


def test_a_file_where_the_folder_should_be_does_not_count(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(integration_check, '_get', _slskd_server())
    afile = tmp_path / 'afile'
    afile.write_text('x')

    check = _by_id(check_slskd(_slskd_cfg(tmp_path, source_dir=str(afile))))[
        'folder'
    ]

    assert check['status'] == 'warn'


def test_slskds_own_folder_counts_when_it_is_mounted_here(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(integration_check, '_get', _slskd_server())
    mounted = tmp_path / 'mounted'
    mounted.mkdir()
    monkeypatch.setattr(
        SlskdClient, 'remote_download_directories', lambda s: [str(mounted)]
    )

    check = _by_id(
        check_slskd(_slskd_cfg(tmp_path, source_dir=str(tmp_path / 'nope')))
    )['folder']

    assert (check['status'], check['detail']) == ('ok', str(mounted))


@pytest.mark.parametrize('field', ['base_url', 'api_key'])
def test_slskd_without_its_address_or_key_is_not_even_tried(
    monkeypatch, tmp_path, field
):
    def never(url: str, **kwargs: Any) -> httpx.Response:
        raise AssertionError('no request should be made')

    monkeypatch.setattr(integration_check, '_get', never)

    result = check_slskd(_slskd_cfg(tmp_path, **{field: ''}))

    assert result['ok'] is False
    assert _by_id(result)['config']['code'] == 'missing'


# ── Navidrome ──────────────────────────────────────────────────────────


def _navidrome_cfg(**over: Any) -> dict[str, Any]:
    return _effective_navidrome_settings({
        'navidrome': {
            'url': 'http://navidrome:4533/',
            'username': 'listener',
            'password': 'pw',
            **over,
        }
    })


def _subsonic(body: dict[str, Any]) -> httpx.Response:
    return _response(200, json={'subsonic-response': body})


def _ok_body(**extra: Any) -> dict[str, Any]:
    return {'status': 'ok', 'version': '1.16.1', **extra}


def _failed(code: int, message: str) -> dict[str, Any]:
    return {'status': 'failed', 'error': {'code': code, 'message': message}}


def _navidrome_server(
    *,
    ping: Any = None,
    users: dict[str, Any] | None = None,
    seen: list | None = None,
) -> Callable[..., httpx.Response]:
    """A fake Navidrome: ``ping`` for everyone, ``getUser`` per account.

    ``users`` maps a username to the ``getUser`` body it gets; an account
    that isn't listed is refused as a wrong login.
    """

    if ping is None:
        ping = _ok_body(type='navidrome', serverVersion='0.53.3 (abc123)')
    users = users or {}

    def fake(url: str, **kwargs: Any) -> httpx.Response:
        endpoint = urlparse(url).path.rsplit('/', 1)[-1]
        params = parse_qs(urlparse(url).query)
        user = params.get('u', [''])[0]
        if seen is not None:
            seen.append((endpoint, user))
        if endpoint == 'ping':
            if isinstance(ping, Exception):
                raise ping
            if isinstance(ping, httpx.Response):
                return ping
            return _subsonic(ping)
        if endpoint == 'getUser':
            if user not in users:
                return _subsonic(_failed(40, 'Wrong username or password'))
            return _subsonic(users[user])
        return _response(404)

    return fake


def _admin(name: str, admin: bool) -> dict[str, Any]:
    return _ok_body(user={'username': name, 'adminRole': admin})


def test_a_working_navidrome_reports_its_server_and_scan_rights(monkeypatch):
    monkeypatch.setattr(
        navidrome.httpx,
        'get',
        _navidrome_server(users={'listener': _admin('listener', True)}),
    )

    result = check_navidrome(_navidrome_cfg())

    assert result['ok'] is True
    assert result['server'] == 'navidrome 0.53.3 (abc123)'
    checks = _by_id(result)
    assert checks['connection']['status'] == 'ok'
    assert checks['auth']['status'] == 'ok'
    assert (checks['scan']['status'], checks['scan']['code']) == ('ok', 'ok')


def test_a_wrong_password_is_reported_as_one_after_reaching_the_server(
    monkeypatch,
):
    monkeypatch.setattr(
        navidrome.httpx,
        'get',
        _navidrome_server(ping=_failed(40, 'Wrong username or password')),
    )

    result = check_navidrome(_navidrome_cfg())

    assert result['ok'] is False
    checks = _by_id(result)
    assert checks['connection']['status'] == 'ok'
    assert (checks['auth']['status'], checks['auth']['code']) == (
        'fail',
        'bad_credentials',
    )
    assert 'scan' not in checks


def test_any_other_subsonic_refusal_passes_on_the_servers_words(monkeypatch):
    monkeypatch.setattr(
        navidrome.httpx,
        'get',
        _navidrome_server(ping=_failed(0, 'Library is being upgraded')),
    )

    check = _by_id(check_navidrome(_navidrome_cfg()))['auth']

    assert (check['code'], check['detail']) == (
        'api_error',
        'Library is being upgraded',
    )


def test_a_normal_account_that_cannot_scan_is_a_warning(monkeypatch):
    # startScan is admin-only in Navidrome and its refusal is only logged,
    # so this is the one place the mistake shows up.
    monkeypatch.setattr(
        navidrome.httpx,
        'get',
        _navidrome_server(users={'listener': _admin('listener', False)}),
    )

    result = check_navidrome(_navidrome_cfg())

    assert result['ok'] is True
    check = _by_id(result)['scan']
    assert (check['status'], check['code']) == ('warn', 'not_admin')


def test_the_scan_account_is_the_one_that_gets_checked(monkeypatch):
    seen: list = []
    monkeypatch.setattr(
        navidrome.httpx,
        'get',
        _navidrome_server(
            users={
                'listener': _admin('listener', False),
                'boss': _admin('boss', True),
            },
            seen=seen,
        ),
    )

    result = check_navidrome(
        _navidrome_cfg(admin_username='boss', admin_password='pw2')
    )

    assert _by_id(result)['scan']['status'] == 'ok'
    # Playlists use the normal account; scans use the admin one.
    assert ('ping', 'listener') in seen
    assert ('getUser', 'boss') in seen
    assert ('getUser', 'listener') not in seen


def test_a_scan_account_that_is_not_an_admin_says_so_separately(monkeypatch):
    monkeypatch.setattr(
        navidrome.httpx,
        'get',
        _navidrome_server(users={'boss': _admin('boss', False)}),
    )

    check = _by_id(
        check_navidrome(
            _navidrome_cfg(admin_username='boss', admin_password='pw2')
        )
    )['scan']

    assert (check['status'], check['code']) == ('warn', 'not_admin_separate')


def test_a_rejected_scan_account_is_a_failure(monkeypatch):
    monkeypatch.setattr(
        navidrome.httpx,
        'get',
        # 'boss' isn't a known account, so it is refused as a wrong login.
        _navidrome_server(users={'listener': _admin('listener', True)}),
    )

    result = check_navidrome(
        _navidrome_cfg(admin_username='boss', admin_password='wrong')
    )

    assert result['ok'] is False
    checks = _by_id(result)
    assert checks['auth']['status'] == 'ok'
    assert (checks['scan']['status'], checks['scan']['code']) == (
        'fail',
        'bad_admin',
    )


def test_scan_rights_are_not_looked_at_when_scanning_is_off(monkeypatch):
    seen: list = []
    monkeypatch.setattr(navidrome.httpx, 'get', _navidrome_server(seen=seen))

    result = check_navidrome(_navidrome_cfg(scan_after_download=False))

    assert 'scan' not in _by_id(result)
    assert [endpoint for endpoint, _ in seen] == ['ping']


def test_a_server_without_getuser_is_skipped_not_blamed(monkeypatch):
    def older_server(url: str, **kwargs: Any) -> httpx.Response:
        endpoint = urlparse(url).path.rsplit('/', 1)[-1]
        if endpoint == 'ping':
            return _subsonic(_ok_body())
        return _subsonic(_failed(70, 'Data not found'))

    monkeypatch.setattr(navidrome.httpx, 'get', older_server)

    result = check_navidrome(_navidrome_cfg())

    assert result['ok'] is True
    assert 'scan' not in _by_id(result)
    # No server type reported: still named, just generically.
    assert result['server'] == 'Subsonic'


@pytest.mark.parametrize(
    'reply',
    [
        _response(200, text='<html>Welcome</html>'),
        _response(200, json={'unrelated': True}),
        _response(404),
        _response(405),
    ],
)
def test_something_that_is_not_navidrome_is_recognised(monkeypatch, reply):
    monkeypatch.setattr(navidrome.httpx, 'get', _navidrome_server(ping=reply))

    result = check_navidrome(_navidrome_cfg())

    assert result['ok'] is False
    assert _by_id(result)['connection']['code'] == 'not_navidrome'


def test_a_proxy_that_wants_a_login_reads_as_a_credentials_problem(
    monkeypatch,
):
    monkeypatch.setattr(
        navidrome.httpx, 'get', _navidrome_server(ping=_response(401))
    )

    check = _by_id(check_navidrome(_navidrome_cfg()))['auth']

    assert check['code'] == 'bad_credentials'


@pytest.mark.parametrize(
    ('exc', 'code'),
    [
        (httpx.ConnectError('refused'), 'unreachable'),
        (httpx.ReadTimeout('slow'), 'timeout'),
        (httpx.UnsupportedProtocol('no scheme'), 'bad_url'),
        (_tls_error(), 'tls'),
    ],
)
def test_navidrome_that_gets_no_answer_says_why(monkeypatch, exc, code):
    monkeypatch.setattr(navidrome.httpx, 'get', _navidrome_server(ping=exc))

    result = check_navidrome(_navidrome_cfg())

    assert result['ok'] is False
    assert _by_id(result)['connection']['code'] == code


def test_no_login_token_ever_reaches_the_answer_or_the_log(
    monkeypatch, capsys
):
    logged: list[str] = []
    sink = logger.add(lambda message: logged.append(str(message)))
    secret = 'TOKEN-MUST-NOT-LEAK'

    def leaky(url: str, **kwargs: Any) -> httpx.Response:
        # httpx puts the full request URL, query string included, in its
        # errors — and a Subsonic URL carries the salted password hash.
        raise httpx.ConnectError(f'cannot reach {url}&t={secret}')

    monkeypatch.setattr(navidrome.httpx, 'get', leaky)
    try:
        result = check_navidrome(_navidrome_cfg())
    finally:
        logger.remove(sink)

    everything = json.dumps(result) + ''.join(logged) + capsys.readouterr().out
    assert secret not in everything
    assert 'pw' not in json.dumps(result)
    assert _by_id(result)['connection']['code'] == 'unreachable'


@pytest.mark.parametrize('field', ['url', 'username', 'password'])
def test_navidrome_without_its_address_or_login_is_not_even_tried(
    monkeypatch, field
):
    def never(url: str, **kwargs: Any) -> httpx.Response:
        raise AssertionError('no request should be made')

    monkeypatch.setattr(navidrome.httpx, 'get', never)

    result = check_navidrome(_navidrome_cfg(**{field: ''}))

    assert result['ok'] is False
    assert _by_id(result)['config']['code'] == 'missing'


def test_a_subsonic_error_is_still_a_value_error_for_existing_callers():
    error = navidrome.SubsonicError('nope', 40)

    assert isinstance(error, ValueError)
    assert (str(error), error.code) == ('nope', 40)


# ── the endpoints ──────────────────────────────────────────────────────


class _Body:
    """A request whose JSON body is ``payload`` (or unreadable)."""

    def __init__(self, payload: Any = None, *, broken: bool = False):
        self._payload = payload
        self._broken = broken

    async def json(self) -> Any:
        if self._broken:
            raise ValueError('not json')
        return self._payload


def _spy(monkeypatch, name: str) -> list[dict[str, Any]]:
    """Record the config an endpoint hands to a check, and answer for it."""

    seen: list[dict[str, Any]] = []

    def fake(cfg: dict[str, Any]) -> dict[str, Any]:
        seen.append(cfg)
        return {'ok': True, 'server': 'fake 1.0', 'checks': []}

    monkeypatch.setattr(integration_check, name, fake)
    return seen


def test_the_slskd_endpoint_tests_the_form_not_the_saved_settings(
    monkeypatch,
):
    seen = _spy(monkeypatch, 'check_slskd')
    monkeypatch.setattr(
        api.state,
        'settings',
        {'slskd': {'base_url': 'http://saved:1', 'api_key': 'SAVED'}},
    )

    result = asyncio.run(
        api.test_slskd_endpoint(
            _Body({'base_url': 'http://typed:2/', 'api_key': 'TYPED'})
        )
    )

    assert result['ok'] is True
    assert (seen[0]['base_url'], seen[0]['api_key']) == (
        'http://typed:2',
        'TYPED',
    )


def test_an_empty_body_tests_what_is_saved(monkeypatch):
    seen = _spy(monkeypatch, 'check_slskd')
    monkeypatch.setattr(
        api.state,
        'settings',
        {'slskd': {'base_url': 'http://saved:1', 'api_key': 'SAVED'}},
    )

    for body in (
        _Body({}),
        _Body(broken=True),
        _Body(['not', 'an', 'object']),
    ):
        asyncio.run(api.test_slskd_endpoint(body))

    assert [cfg['base_url'] for cfg in seen] == ['http://saved:1'] * 3


def test_a_cleared_field_in_the_form_is_not_refilled_from_the_saved_one(
    monkeypatch,
):
    seen = _spy(monkeypatch, 'check_slskd')
    monkeypatch.setattr(
        api.state,
        'settings',
        {'slskd': {'base_url': 'http://saved:1', 'api_key': 'SAVED'}},
    )

    asyncio.run(
        api.test_slskd_endpoint(
            _Body({'base_url': 'http://typed:2', 'api_key': ''})
        )
    )

    # Testing the saved key would say "fine" about a form that isn't.
    assert not seen[0]['api_key']


def test_the_navidrome_endpoint_tests_the_form_and_normalises_it(monkeypatch):
    seen = _spy(monkeypatch, 'check_navidrome')
    monkeypatch.setattr(
        api.state, 'settings', {'navidrome': {'url': 'http://saved:1'}}
    )

    asyncio.run(
        api.test_navidrome_endpoint(
            _Body({
                'url': 'http://typed:2/',
                'username': ' me ',
                'password': 'pw',
            })
        )
    )
    asyncio.run(api.test_navidrome_endpoint(_Body({})))

    assert (seen[0]['url'], seen[0]['username']) == ('http://typed:2', 'me')
    assert seen[1]['url'] == 'http://saved:1'


def test_a_failed_test_is_an_answer_not_an_error(monkeypatch, tmp_path):
    def refused(url: str, **kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError('refused')

    monkeypatch.setattr(integration_check, '_get', refused)
    monkeypatch.setattr(api.state, 'settings', {})

    result = asyncio.run(
        api.test_slskd_endpoint(
            _Body({'base_url': 'http://nowhere:1', 'api_key': 'K'})
        )
    )

    # A plain dict is returned, so the client gets a 200 to read.
    assert result['ok'] is False
    assert result['checks'][0]['code'] == 'unreachable'
