"""Tests for the YouTube cookie keep-alive (downtify/cookie_refresh.py) and
the merge-back of rotated cookies (downtify/cookies.py).

Exported cookies "expire" because Google rotates the session cookies as
they are used; these tests pin the two halves of keeping them alive
offline: the values yt-dlp (or the keep-alive) learns are written back to
the shared cookies.txt without rolling back newer ones, and the health
the settings page shows follows what YouTube says.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import requests
from yt_dlp.cookies import YoutubeDLCookieJar

from downtify import api, cookie_refresh
from downtify.cookies import (
    ENV_VAR,
    CookiesStore,
    changed_cookies,
    load_jar,
    merge_into,
    private_cookiefile,
)

_HEADER = '# Netscape HTTP Cookie File\n'
_EXPIRES = 1900000000


def _line(name: str, value: str, domain: str = '.youtube.com') -> str:
    return f'{domain}\tTRUE\t/\tTRUE\t{_EXPIRES}\t{name}\t{value}\n'


def _write(path: Path, *lines: str) -> Path:
    path.write_text(_HEADER + ''.join(lines), encoding='utf-8')
    return path


def _values(path: Path) -> dict[str, str]:
    return {key[2]: cookie.value for key, cookie in load_jar(path).items()}


def _rewrite(path: Path, **values: str) -> None:
    """Change cookie values in *path* the way yt-dlp's save would."""

    jar = YoutubeDLCookieJar(str(path))
    jar.load()
    for cookie in jar:
        if cookie.name in values:
            cookie.value = values[cookie.name]
    jar.save()


# ── merge-back ──────────────────────────────────────────────────────────────


def test_changed_cookies_reports_new_and_changed_only(tmp_path):
    before_path = _write(
        tmp_path / 'a.txt', _line('SID', 's'), _line('PSIDTS', 'old')
    )
    after_path = _write(
        tmp_path / 'b.txt',
        _line('SID', 's'),
        _line('PSIDTS', 'new'),
        _line('SIDCC', 'cc'),
    )
    names = {
        c.name
        for c in changed_cookies(load_jar(before_path), load_jar(after_path))
    }
    assert names == {'PSIDTS', 'SIDCC'}


def test_merge_into_updates_and_keeps_the_rest(tmp_path):
    shared = _write(
        tmp_path / 'cookies.txt', _line('SID', 's'), _line('PSIDTS', 'old')
    )
    rotated = _write(tmp_path / 'r.txt', _line('PSIDTS', 'new'))
    assert merge_into(shared, list(load_jar(rotated).values())) == 1
    assert _values(shared) == {'SID': 's', 'PSIDTS': 'new'}


def test_merge_into_missing_file_is_a_no_op(tmp_path):
    rotated = _write(tmp_path / 'r.txt', _line('PSIDTS', 'new'))
    missing = tmp_path / 'gone.txt'
    assert merge_into(missing, list(load_jar(rotated).values())) == 0
    assert not missing.exists()


def test_private_cookiefile_saves_rotated_cookies_back(tmp_path):
    shared = _write(
        tmp_path / 'cookies.txt', _line('SID', 's'), _line('PSIDTS', 'old')
    )
    opts = {'cookiefile': str(shared)}
    with private_cookiefile(opts):
        assert opts['cookiefile'] != str(shared)
        _rewrite(Path(opts['cookiefile']), PSIDTS='rotated')
    assert opts['cookiefile'] == str(shared)
    assert _values(shared) == {'SID': 's', 'PSIDTS': 'rotated'}


def test_a_slow_download_does_not_roll_back_a_newer_cookie(tmp_path):
    shared = _write(
        tmp_path / 'cookies.txt', _line('SID', 's'), _line('PSIDTS', 'v1')
    )
    opts = {'cookiefile': str(shared)}
    with private_cookiefile(opts):
        # Another download rotated PSIDTS meanwhile; this one only saw
        # SIDCC change and still holds the old PSIDTS in its copy.
        _write(shared, _line('SID', 's'), _line('PSIDTS', 'v2'))
        jar = YoutubeDLCookieJar(opts['cookiefile'])
        jar.load()
        extra = YoutubeDLCookieJar()
        extra.load(str(_write(tmp_path / 'x.txt', _line('SIDCC', 'cc'))))
        for cookie in extra:
            jar.set_cookie(cookie)
        jar.save()
    assert _values(shared) == {'SID': 's', 'PSIDTS': 'v2', 'SIDCC': 'cc'}


def test_private_cookiefile_without_a_jar_does_nothing():
    opts: dict = {}
    with private_cookiefile(opts):
        assert 'cookiefile' not in opts


# ── keep-alive pass ─────────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code


class _FakeSession:
    """Answers like YouTube: rotation sets a new PSIDTS, the home page
    says whether the session is signed in."""

    def __init__(self, logged_in: str = 'true', fail: bool = False) -> None:
        self.headers: dict[str, str] = {}
        self.cookies = requests.cookies.RequestsCookieJar()
        self.posts: list[str] = []
        self._logged_in = logged_in
        self._fail = fail

    def post(self, url: str, **_kwargs) -> _FakeResponse:
        self.posts.append(url)
        self.cookies.set(
            '__Secure-1PSIDTS', 'rotated', domain='.youtube.com', path='/'
        )
        return _FakeResponse('')

    def get(self, url: str, **_kwargs) -> _FakeResponse:
        if self._fail:
            raise requests.ConnectionError('down')
        return _FakeResponse(f'ytcfg.set({{"LOGGED_IN":{self._logged_in}}})')


@pytest.fixture
def store(tmp_path, monkeypatch) -> CookiesStore:
    monkeypatch.delenv(ENV_VAR, raising=False)
    s = CookiesStore(tmp_path / 'cookies.txt')
    _write(
        s.path,
        _line('SID', 'sid'),
        _line('__Secure-1PSIDTS', 'old'),
    )
    return s


def _use(monkeypatch, session: _FakeSession) -> _FakeSession:
    monkeypatch.setattr(cookie_refresh, '_new_session', lambda: session)
    return session


def test_refresh_saves_rotated_cookies_and_reports_signed_in(
    store, monkeypatch
):
    session = _use(monkeypatch, _FakeSession())
    health = cookie_refresh.refresh_cookies(store)
    assert health['state'] == 'valid'
    assert health['refreshed_at'] == health['checked_at']
    assert session.posts == ['https://accounts.youtube.com/RotateCookies']
    assert _values(store.path)['__Secure-1PSIDTS'] == 'rotated'
    assert store.status()['health']['state'] == 'valid'


def test_refresh_reports_a_signed_out_session(store, monkeypatch):
    _use(monkeypatch, _FakeSession(logged_in='false'))
    assert cookie_refresh.refresh_cookies(store)['state'] == 'signed_out'


def test_refresh_reports_network_errors_without_raising(store, monkeypatch):
    _use(monkeypatch, _FakeSession(fail=True))
    health = cookie_refresh.refresh_cookies(store)
    assert health['state'] == 'error'
    assert 'ConnectionError' in health['message']


def test_refresh_skips_jars_without_an_account(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    s = CookiesStore(tmp_path / 'cookies.txt')
    _write(s.path, _line('VISITOR_INFO1_LIVE', 'v'))
    session = _use(monkeypatch, _FakeSession())
    assert cookie_refresh.refresh_cookies(s)['state'] == 'no_account'
    assert session.posts == []


def test_refresh_without_cookies_is_unknown(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    s = CookiesStore(tmp_path / 'cookies.txt')
    assert cookie_refresh.refresh_cookies(s)['state'] == 'unknown'


def test_ytdlp_warnings_feed_the_health(store):
    cookie_refresh.bind_store(store)
    try:
        cookie_refresh.note_ytdlp_message(
            "Sign in to confirm you're not a bot. Use --cookies"
        )
        assert store.health['bot_check_at']
        assert store.health['state'] == 'unknown'
        cookie_refresh.note_ytdlp_message(
            'The provided YouTube account cookies are no longer valid. '
            'They have likely been rotated in the browser'
        )
        assert store.health['state'] == 'signed_out'
    finally:
        cookie_refresh.bind_store(None)


def test_a_new_upload_resets_the_health(store):
    store.health = {**store.health, 'state': 'signed_out'}
    store.save(store.path.read_bytes())
    assert store.health['state'] == 'unknown'


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [('', 15), ('0', 0), ('-3', 0), ('2', 5), ('60', 60), ('x', 15)],
)
def test_interval_minutes(monkeypatch, raw, expected):
    monkeypatch.setenv(cookie_refresh.ENV_INTERVAL, raw)
    assert cookie_refresh.interval_minutes() == expected


def test_check_endpoint_runs_a_pass(store, monkeypatch):
    _use(monkeypatch, _FakeSession())
    monkeypatch.setattr(api.state, 'cookies_store', store)
    result = asyncio.run(api.check_cookies_endpoint())
    assert result['configured'] is True
    assert result['health']['state'] == 'valid'
