"""Checked sign-ins are cached briefly, and every revocation is instant.

The auth middleware checks a session or device token on every request,
on the event loop; a database read there for each cover and API call
added up. The cache must never outlive a sign-out, a revoked device or
an account change.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from downtify.auth import AuthStore
from downtify.users import ROLE_ADMIN, ROLE_USER


def _store(tmp_path: Path) -> AuthStore:
    return AuthStore(tmp_path / 'auth.db', tmp_path / '.secret')


def _forbid_db(monkeypatch: pytest.MonkeyPatch, store: AuthStore) -> None:
    def no_db() -> Any:
        raise AssertionError('the database was asked again')

    monkeypatch.setattr(store, '_connect', no_db)


@pytest.fixture
def maria(tmp_path):
    store = _store(tmp_path)
    user = store.users.create('maria', 'password123', role=ROLE_USER)
    return store, int(user['id'])


def test_a_session_is_checked_once_then_served_from_memory(maria, monkeypatch):
    store, uid = maria
    token = store.create_session(uid)
    assert store.session_user(token)['username'] == 'maria'

    _forbid_db(monkeypatch, store)
    assert store.session_user(token)['id'] == uid


def test_a_device_token_is_checked_once_then_served_from_memory(
    maria, monkeypatch
):
    store, uid = maria
    _device, token = store.create_device('Phone', user_id=uid)
    assert store.verify_device_token(token)['user_id'] == uid

    _forbid_db(monkeypatch, store)
    assert store.verify_device_token(token)['username'] == 'maria'


def test_a_wrong_device_secret_is_never_served_from_the_cache(maria):
    store, uid = maria
    _device, token = store.create_device('Phone', user_id=uid)
    assert store.verify_device_token(token) is not None

    wrong = token[:-1] + ('y' if token.endswith('x') else 'x')
    assert store.verify_device_token(wrong) is None


def test_signing_out_is_instant(maria):
    store, uid = maria
    token = store.create_session(uid)
    store.session_user(token)

    store.end_session(token)
    assert store.session_user(token) is None


def test_signing_a_user_out_everywhere_is_instant(maria):
    store, uid = maria
    token = store.create_session(uid)
    _device, device_token = store.create_device('Phone', user_id=uid)
    store.session_user(token)
    store.verify_device_token(device_token)

    store.revoke_user(uid)
    assert store.session_user(token) is None
    assert store.verify_device_token(device_token) is None


def test_revoking_a_device_is_instant(maria):
    store, uid = maria
    device, token = store.create_device('Phone', user_id=uid)
    store.verify_device_token(token)

    store.revoke_device(device['id'])
    assert store.verify_device_token(token) is None


def test_revoke_everything_is_instant(maria):
    store, uid = maria
    token = store.create_session(uid)
    _device, device_token = store.create_device('Phone', user_id=uid)
    store.session_user(token)
    store.verify_device_token(device_token)

    store.revoke_everything()
    assert store.session_user(token) is None
    assert store.verify_device_token(device_token) is None


def test_a_role_change_is_seen_on_the_next_request(maria):
    store, uid = maria
    token = store.create_session(uid)
    assert store.session_user(token)['role'] == ROLE_USER

    store.users.update(uid, role=ROLE_ADMIN)
    assert store.session_user(token)['role'] == ROLE_ADMIN


def test_a_deleted_account_is_signed_out_at_once(maria):
    store, uid = maria
    token = store.create_session(uid)
    _device, device_token = store.create_device('Phone', user_id=uid)
    store.session_user(token)
    store.verify_device_token(device_token)

    store.users.delete(uid)
    assert store.session_user(token) is None
    assert store.verify_device_token(device_token) is None


def test_a_password_change_drops_cached_sign_ins(maria, monkeypatch):
    store, uid = maria
    token = store.create_session(uid)
    store.session_user(token)

    store.users.set_password(uid, 'another-password')
    asked = []
    real = store._connect

    def counting():
        asked.append(True)
        return real()

    monkeypatch.setattr(store, '_connect', counting)
    assert store.session_user(token) is not None
    assert asked


def test_an_answer_read_before_a_revocation_is_not_cached(maria, monkeypatch):
    """A check that read the session just before it was revoked must not
    store that stale answer."""

    store, uid = maria
    token = store.create_session(uid)
    real = store._connect

    def revoke_mid_lookup():
        conn = real()
        store._signed_in.clear()
        return conn

    monkeypatch.setattr(store, '_connect', revoke_mid_lookup)
    assert store.session_user(token) is not None

    _forbid_db(monkeypatch, store)
    with pytest.raises(AssertionError, match='asked again'):
        store.session_user(token)
