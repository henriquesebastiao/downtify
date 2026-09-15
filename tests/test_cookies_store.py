"""Tests for the managed cookies.txt storage (downtify/cookies.py) and the
/api/cookies endpoints that expose it to the settings UI.

Covers the rules the feature hinges on: DOWNTIFY_COOKIES_FILE always
wins and locks the UI out, uploads are validated before they can break
every later download, and the file lives in /data so it survives a
container update.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from downtify import api
from downtify.cookies import (
    ENV_VAR,
    MAX_COOKIES_BYTES,
    CookiesStore,
    InvalidCookiesFile,
    validate_cookies,
)
from downtify.downloader import Downloader

_COOKIE_LINE = (
    '.youtube.com\tTRUE\t/\tTRUE\t1800000000\tSID\tsome-session-value'
)
VALID_COOKIES = (
    '# Netscape HTTP Cookie File\n' + _COOKIE_LINE + '\n'
).encode()


def _store(tmp_path) -> CookiesStore:
    return CookiesStore(tmp_path / 'cookies.txt')


# ── validate_cookies ─────────────────────────────────────────────────────────


def test_validate_accepts_netscape_file():
    assert validate_cookies(VALID_COOKIES) == []


def test_validate_accepts_httponly_prefixed_lines():
    # Browser export extensions write this prefix on normal records; it
    # must not be mistaken for a comment.
    content = f'# Netscape HTTP Cookie File\n#HttpOnly_{_COOKIE_LINE}\n'
    assert validate_cookies(content.encode()) == []


def test_validate_rejects_empty_file():
    with pytest.raises(InvalidCookiesFile):
        validate_cookies(b'   \n')


def test_validate_rejects_non_netscape_text():
    with pytest.raises(InvalidCookiesFile):
        validate_cookies(b'SID=abc; HSID=def\n')


def test_validate_rejects_binary_content():
    with pytest.raises(InvalidCookiesFile):
        validate_cookies(b'\x00\x01\x02\xff')


def test_validate_rejects_oversized_file():
    with pytest.raises(InvalidCookiesFile):
        validate_cookies(b'#\n' * MAX_COOKIES_BYTES)


def test_validate_warns_when_no_youtube_cookies():
    content = (
        '.example.com\tTRUE\t/\tTRUE\t1800000000\tSID\tvalue\n'
    ).encode()
    warnings = validate_cookies(content)
    assert len(warnings) == 1
    assert 'youtube.com' in warnings[0]


# ── CookiesStore ─────────────────────────────────────────────────────────────


def test_status_reports_nothing_configured(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    status = _store(tmp_path).status()
    assert status['configured'] is False
    assert status['source'] is None
    assert status['locked'] is False


def test_save_then_status_reports_upload(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    store = _store(tmp_path)
    assert store.save(VALID_COOKIES) == []

    status = store.status()
    assert status['configured'] is True
    assert status['source'] == 'upload'
    assert status['locked'] is False
    assert status['size'] == len(VALID_COOKIES)
    assert store.path.read_bytes() == VALID_COOKIES


def test_save_replaces_previous_file(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    store = _store(tmp_path)
    store.save(VALID_COOKIES)
    replacement = VALID_COOKIES.replace(b'some-session-value', b'newer-value')
    store.save(replacement)
    assert store.path.read_bytes() == replacement


def test_invalid_upload_leaves_previous_file_intact(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    store = _store(tmp_path)
    store.save(VALID_COOKIES)
    with pytest.raises(InvalidCookiesFile):
        store.save(b'not a cookie jar')
    assert store.path.read_bytes() == VALID_COOKIES


def test_delete_removes_file(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    store = _store(tmp_path)
    store.save(VALID_COOKIES)
    assert store.delete() is True
    assert store.path.exists() is False
    assert store.delete() is False


def test_env_var_wins_over_uploaded_file(tmp_path, monkeypatch):
    env_file = tmp_path / 'mounted.txt'
    env_file.write_bytes(VALID_COOKIES)
    monkeypatch.setenv(ENV_VAR, str(env_file))
    store = _store(tmp_path)
    store.save(VALID_COOKIES)  # an upload from before the env var existed

    status = store.status()
    assert status['locked'] is True
    assert status['source'] == 'env'
    assert status['path'] == str(env_file)
    assert store.active_path() == env_file


def test_env_var_pointing_at_missing_file_is_reported(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_VAR, str(tmp_path / 'nope.txt'))
    status = _store(tmp_path).status()
    # Still locked (the operator owns the config) but flagged as broken,
    # which is what the UI turns into "check the path / volume mount".
    assert status['locked'] is True
    assert status['configured'] is False


# ── Downloader wiring ────────────────────────────────────────────────────────


def test_downloader_uses_uploaded_cookies_file(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    store = _store(tmp_path)
    store.save(VALID_COOKIES)
    d = Downloader(tmp_path / 'downloads', cookies_store=store)
    assert d._resolve_cookies_file() == str(store.path)


def test_downloader_prefers_env_var(tmp_path, monkeypatch):
    env_file = tmp_path / 'mounted.txt'
    env_file.write_bytes(VALID_COOKIES)
    monkeypatch.setenv(ENV_VAR, str(env_file))
    store = _store(tmp_path)
    store.save(VALID_COOKIES)
    d = Downloader(tmp_path / 'downloads', cookies_store=store)
    assert d._resolve_cookies_file() == str(env_file)


def test_downloader_without_store_falls_back_to_env(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_VAR, '/mounted/cookies.txt')
    d = Downloader(tmp_path / 'downloads')
    assert d._resolve_cookies_file() == '/mounted/cookies.txt'


def test_downloader_reports_no_cookies_when_none_configured(
    tmp_path, monkeypatch
):
    monkeypatch.delenv(ENV_VAR, raising=False)
    d = Downloader(tmp_path / 'downloads', cookies_store=_store(tmp_path))
    assert not d._resolve_cookies_file()


# ── /api/cookies endpoints ───────────────────────────────────────────────────


class _FakeRequest:
    def __init__(self, body: bytes) -> None:
        self._body = body

    async def body(self) -> bytes:
        return self._body


def test_endpoint_upload_and_delete_round_trip(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    store = _store(tmp_path)
    monkeypatch.setattr(api.state, 'cookies_store', store)

    uploaded = asyncio.run(
        api.upload_cookies_endpoint(_FakeRequest(VALID_COOKIES))
    )
    assert uploaded['configured'] is True
    assert uploaded['warnings'] == []

    assert api.get_cookies_endpoint()['source'] == 'upload'

    deleted = asyncio.run(api.delete_cookies_endpoint())
    assert deleted['deleted'] is True
    assert deleted['configured'] is False


def test_endpoint_rejects_invalid_upload(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setattr(api.state, 'cookies_store', _store(tmp_path))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.upload_cookies_endpoint(_FakeRequest(b'nope')))
    assert exc.value.status_code == 400


def test_endpoint_upload_blocked_while_env_var_set(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_VAR, str(tmp_path / 'mounted.txt'))
    monkeypatch.setattr(api.state, 'cookies_store', _store(tmp_path))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.upload_cookies_endpoint(_FakeRequest(VALID_COOKIES)))
    assert exc.value.status_code == 409


def test_endpoint_delete_blocked_while_env_var_set(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_VAR, str(tmp_path / 'mounted.txt'))
    monkeypatch.setattr(api.state, 'cookies_store', _store(tmp_path))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.delete_cookies_endpoint())
    assert exc.value.status_code == 409


def test_endpoint_reports_warnings_from_upload(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setattr(api.state, 'cookies_store', _store(tmp_path))
    content = (
        '.example.com\tTRUE\t/\tTRUE\t1800000000\tSID\tvalue\n'
    ).encode()
    result = asyncio.run(api.upload_cookies_endpoint(_FakeRequest(content)))
    assert result['configured'] is True
    assert len(result['warnings']) == 1
