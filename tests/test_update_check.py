"""Tests for downtify/update_check.py: the hourly GitHub Releases check
that powers the "a new version of Downtify is available" footer
notification, and the ``GET /api/check_update`` endpoint it feeds.

``GET /api/check_update`` used to be a permanent stub returning
``None`` — this wires it up for real. All offline: ``httpx.get`` is
monkeypatched throughout (a live call against the real GitHub API was
used to hand-verify the request/response shape during development, but
doesn't belong in the suite — see CLAUDE.md's "no network calls in
tests without a recorded fixture").
"""

from __future__ import annotations

import asyncio

import httpx

from downtify import api
from downtify import update_check as update_check_mod
from downtify.update_check import (
    DEFAULT_RELEASES_PAGE_URL,
    UpdateChecker,
    _parse_version,
    is_newer,
)

# ── _parse_version / is_newer ────────────────────────────────────────────────


def test_parse_version_plain():
    assert _parse_version('2.11.0') == (2, 11, 0)


def test_parse_version_with_v_prefix():
    assert _parse_version('v2.11.0') == (2, 11, 0)


def test_parse_version_with_surrounding_text():
    assert _parse_version('Downtify 2.11.0') == (2, 11, 0)


def test_parse_version_unparseable_is_empty_tuple():
    assert _parse_version('not-a-version') == ()
    assert _parse_version('') == ()
    assert _parse_version(None) == ()


def test_is_newer_true_for_a_higher_version():
    assert is_newer('2.12.0', '2.11.0') is True


def test_is_newer_false_for_the_same_version():
    assert is_newer('2.11.0', '2.11.0') is False


def test_is_newer_false_for_an_older_version():
    assert is_newer('2.9.0', '2.11.0') is False


def test_is_newer_compares_numerically_not_lexicographically():
    # '2.9.0' < '2.10.0' lexicographically but not numerically — a naive
    # string comparison would get this backwards.
    assert is_newer('2.10.0', '2.9.0') is True


def test_is_newer_handles_v_prefix_on_either_side():
    assert is_newer('v2.11.1', '2.11.0') is True


def test_is_newer_false_when_latest_is_unparseable():
    assert is_newer('not-a-version', '2.11.0') is False


# ── UpdateChecker ─────────────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPError(f'{self.status_code} error')

    def json(self):
        return self._payload


def test_check_now_populates_status_on_success(monkeypatch):
    monkeypatch.setattr(
        httpx,
        'get',
        lambda *a, **kw: _FakeResponse({
            'tag_name': '2.12.0',
            'html_url': 'https://github.com/x/y/releases/tag/2.12.0',
        }),
    )
    checker = UpdateChecker()
    checker.check_now()

    status = checker.status(current_version='2.11.0')
    assert status['latest_version'] == '2.12.0'
    assert status['update_available'] is True
    assert (
        status['release_url'] == 'https://github.com/x/y/releases/tag/2.12.0'
    )
    assert status['last_checked'] is not None


def test_status_reports_no_update_when_versions_match(monkeypatch):
    monkeypatch.setattr(
        httpx,
        'get',
        lambda *a, **kw: _FakeResponse({'tag_name': '2.11.0'}),
    )
    checker = UpdateChecker()
    checker.check_now()

    status = checker.status(current_version='2.11.0')
    assert status['update_available'] is False


def test_status_before_any_check_has_no_latest_version():
    checker = UpdateChecker()
    status = checker.status(current_version='2.11.0')
    assert status['latest_version'] is None
    assert status['update_available'] is False
    assert status['last_checked'] is None
    assert status['release_url'] == DEFAULT_RELEASES_PAGE_URL


def test_check_now_network_error_does_not_raise(monkeypatch):
    def _raise(*_a, **_kw):
        raise httpx.ConnectError('offline')

    monkeypatch.setattr(httpx, 'get', _raise)
    checker = UpdateChecker()
    checker.check_now()  # must not raise

    status = checker.status(current_version='2.11.0')
    assert status['latest_version'] is None
    assert status['last_checked'] is not None  # attempt was still recorded


def test_check_now_http_error_does_not_raise(monkeypatch):
    monkeypatch.setattr(
        httpx, 'get', lambda *a, **kw: _FakeResponse({}, status=404)
    )
    checker = UpdateChecker()
    checker.check_now()  # must not raise
    assert checker.status(current_version='2.11.0')['latest_version'] is None


def test_check_now_missing_tag_name_does_not_raise(monkeypatch):
    monkeypatch.setattr(
        httpx, 'get', lambda *a, **kw: _FakeResponse({'tag_name': ''})
    )
    checker = UpdateChecker()
    checker.check_now()  # must not raise
    assert checker.status(current_version='2.11.0')['latest_version'] is None


def test_a_later_failed_check_keeps_the_previous_result(monkeypatch):
    monkeypatch.setattr(
        httpx,
        'get',
        lambda *a, **kw: _FakeResponse({'tag_name': '2.12.0'}),
    )
    checker = UpdateChecker()
    checker.check_now()

    def _raise(*_a, **_kw):
        raise httpx.ConnectionError('offline this time')

    monkeypatch.setattr(httpx, 'get', _raise)
    checker.check_now()

    # The stale-but-real result from the first check carries over rather
    # than being wiped by a transient failure.
    status = checker.status(current_version='2.11.0')
    assert status['latest_version'] == '2.12.0'
    assert status['update_available'] is True


# ── GET /api/check_update ────────────────────────────────────────────────────


def test_check_update_endpoint_returns_none_before_startup(monkeypatch):
    monkeypatch.setattr(api.state, 'update_checker', None)
    assert api.check_update() is None


def test_check_update_endpoint_returns_checker_status(monkeypatch):
    monkeypatch.setattr(api.state, 'version', '2.11.0')
    checker = UpdateChecker()
    monkeypatch.setattr(
        httpx,
        'get',
        lambda *a, **kw: _FakeResponse({'tag_name': '2.12.0'}),
    )
    checker.check_now()
    monkeypatch.setattr(api.state, 'update_checker', checker)

    result = api.check_update()
    assert result['update_available'] is True
    assert result['current_version'] == '2.11.0'


# ── update_check_loop ─────────────────────────────────────────────────────────


class _Stop(Exception):
    pass


def test_update_check_loop_checks_then_sleeps_the_configured_interval(
    monkeypatch,
):
    calls = []
    monkeypatch.setattr(
        UpdateChecker, 'check_now', lambda self: calls.append('checked')
    )

    async def _stop(seconds):
        calls.append(('slept', seconds))
        raise _Stop

    monkeypatch.setattr(update_check_mod.asyncio, 'sleep', _stop)

    async def _scenario():
        try:
            await update_check_mod.update_check_loop(
                UpdateChecker(), interval_seconds=123
            )
        except _Stop:
            pass

    asyncio.run(_scenario())

    assert calls == ['checked', ('slept', 123)]


def test_update_check_loop_survives_a_checker_exception(monkeypatch):
    def _raise(self):
        raise RuntimeError('boom')

    monkeypatch.setattr(UpdateChecker, 'check_now', _raise)

    async def _stop(_seconds):
        raise _Stop

    monkeypatch.setattr(update_check_mod.asyncio, 'sleep', _stop)

    async def _scenario():
        try:
            await update_check_mod.update_check_loop(UpdateChecker())
        except _Stop:
            pass

    asyncio.run(_scenario())  # must not raise/propagate the RuntimeError
