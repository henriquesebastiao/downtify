"""AuthStore on both backends: sessions, devices, accounts and the cache."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from downtify.auth import (
    DEVICE_TOUCH_INTERVAL,
    SESSION_TTL,
    TOKEN_PREFIX,
    AuthStore,
    _sha256,
)
from downtify.db.core import Database
from downtify.users import ROLE_USER, UserError
from tests.db.helpers import execute, query

OLD = '2000-01-01T00:00:00+00:00'


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(when: datetime) -> str:
    return when.isoformat()


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _store(db: Database, tmp_path: Path) -> AuthStore:
    return AuthStore(db, tmp_path / '.auth_secret')


def _user(store: AuthStore, name: str = 'maria') -> int:
    return int(store.users.create(name, 'password123', role=ROLE_USER)['id'])


def _no_database(*_args: object) -> None:
    raise AssertionError('the database was asked again')


def test_the_store_shares_one_database(backend_db, tmp_path) -> None:
    store = _store(backend_db, tmp_path)
    assert store.db is backend_db
    assert store.users.db is backend_db
    # The constructor made the default admin, so there is nothing to add.
    assert store.users.ensure_default_admin(existing_install=False) is False
    assert store.users.first_admin()['username'] == 'admin'


def test_accounts_created_through_the_store(backend_db, tmp_path) -> None:
    store = _store(backend_db, tmp_path)
    uid = _user(store)
    assert isinstance(uid, int)
    assert store.users.get(uid)['username'] == 'maria'
    assert store.users.by_username('maria')['id'] == uid
    assert store.users.authenticate('maria', 'password123')['id'] == uid
    assert store.users.authenticate('maria', 'wrong password') is None
    with pytest.raises(UserError):
        store.users.create('MARIA', 'password123')


def test_sessions_are_created_checked_and_expire(backend_db, tmp_path) -> None:
    store = _store(backend_db, tmp_path)
    uid = _user(store)
    token = store.create_session(uid, ip='10.0.0.1', user_agent='Firefox')

    user = store.session_user(token)
    assert user is not None
    assert user['id'] == uid
    assert user['username'] == 'maria'
    assert user['role'] == ROLE_USER
    assert 'password_hash' not in user
    assert store.session_user('') is None
    assert store.session_user('x' * 129) is None
    assert store.session_user('not-a-session') is None

    # An expired session is refused and its row dropped.
    expired = store.create_session(uid)
    execute(
        backend_db,
        'UPDATE auth_sessions SET expires_at = ? WHERE id_hash = ?',
        OLD,
        _sha256(expired),
    )
    assert store.session_user(expired) is None
    count = query(
        backend_db,
        'SELECT COUNT(*) FROM auth_sessions WHERE id_hash = ?',
        _sha256(expired),
    )
    assert count[0][0] == 0

    # Signing out ends the session at once.
    store.end_session(token)
    assert store.session_user(token) is None


def test_a_session_is_pushed_back_at_most_hourly(backend_db, tmp_path) -> None:
    store = _store(backend_db, tmp_path)
    uid = _user(store)
    token = store.create_session(uid)
    key = _sha256(token)
    marker = _iso(_now() + timedelta(days=1))

    def expiry() -> datetime:
        row = query(
            backend_db,
            'SELECT expires_at FROM auth_sessions WHERE id_hash = ?',
            key,
        )
        return _parse(row[0][0])

    # Touched five minutes ago: the expiry is left alone.
    execute(
        backend_db,
        'UPDATE auth_sessions SET expires_at = ?, touched_at = ? '
        'WHERE id_hash = ?',
        marker,
        _iso(_now() - timedelta(minutes=5)),
        key,
    )
    assert store.session_user(token) is not None
    assert expiry() == _parse(marker)

    # Touched two hours ago: pushed back to a full session lifetime.
    execute(
        backend_db,
        'UPDATE auth_sessions SET touched_at = ? WHERE id_hash = ?',
        _iso(_now() - timedelta(hours=2)),
        key,
    )
    store._signed_in.clear()
    assert store.session_user(token) is not None
    assert expiry() >= _now() + SESSION_TTL - timedelta(minutes=1)


def test_sessions_end_in_bulk(backend_db, tmp_path) -> None:
    store = _store(backend_db, tmp_path)
    uid = _user(store)
    keep = store.create_session(uid)
    other = store.create_session(uid)
    assert store.end_user_sessions(uid, keep=keep) == 1
    assert store.session_user(keep) is not None
    assert store.session_user(other) is None
    assert store.end_all_sessions() == 1
    assert store.session_user(keep) is None


def test_devices_are_paired_checked_and_revoked(backend_db, tmp_path) -> None:
    store = _store(backend_db, tmp_path)
    uid = _user(store)
    device, token = store.create_device(
        '  Pixel   8 ', platform='android', ip='10.0.0.5', user_id=uid
    )
    assert token.startswith(TOKEN_PREFIX + device['id'] + '_')
    assert device['name'] == 'Pixel 8'
    assert device['username'] == 'maria'
    assert store.get_device(device['id'])['platform'] == 'android'
    assert store.device_active(device['id'])

    assert store.verify_device_token(token, '10.0.0.6') == {
        'id': device['id'],
        'name': 'Pixel 8',
        'user_id': uid,
        'username': 'maria',
        'role': ROLE_USER,
    }
    # Only a hash of the secret is stored.
    stored = query(backend_db, 'SELECT token_hash FROM auth_devices')
    secret = token.removeprefix(TOKEN_PREFIX + device['id'] + '_')
    assert secret not in stored[0][0]

    # Seen a moment ago: the last-seen time and address are not rewritten.
    store._signed_in.clear()
    assert store.verify_device_token(token, '10.0.0.7') is not None
    assert store.get_device(device['id'])['last_ip'] == '10.0.0.5'

    # Last seen more than a minute ago: refreshed, with the new address.
    old = _now() - DEVICE_TOUCH_INTERVAL - timedelta(seconds=30)
    execute(
        backend_db,
        'UPDATE auth_devices SET last_seen_at = ? WHERE id = ?',
        _iso(old),
        device['id'],
    )
    store._signed_in.clear()
    assert store.verify_device_token(token, '10.0.0.7') is not None
    fresh = store.get_device(device['id'])
    assert fresh['last_ip'] == '10.0.0.7'
    assert _parse(fresh['last_seen_at']) > old

    assert store.verify_device_token('nonsense') is None
    forged = f'{TOKEN_PREFIX}{device["id"]}_{"A" * 43}'
    assert store.verify_device_token(forged) is None

    assert store.rename_device(device['id'], 'Work phone')
    assert [d['name'] for d in store.list_devices(uid)] == ['Work phone']
    assert store.list_devices(uid + 1000) == []

    assert store.revoke_device(device['id'])
    assert not store.revoke_device(device['id'])
    assert store.verify_device_token(token) is None
    assert not store.device_active(device['id'])
    assert store.list_devices() == []


def test_revoking_a_user_signs_out_everything(backend_db, tmp_path) -> None:
    store = _store(backend_db, tmp_path)
    uid = _user(store)
    _, first = store.create_device('A', user_id=uid)
    _, second = store.create_device('B', user_id=uid)
    session = store.create_session(uid)
    assert store.session_user(session) is not None

    assert len(store.revoke_user(uid)) == 2
    assert store.verify_device_token(first) is None
    assert store.verify_device_token(second) is None
    assert store.session_user(session) is None


def test_the_token_cache_is_served_then_dropped_on_change(
    backend_db, tmp_path, monkeypatch
) -> None:
    store = _store(backend_db, tmp_path)
    uid = _user(store)
    token = store.create_session(uid)
    _, device_token = store.create_device('Pixel', user_id=uid)
    assert store.session_user(token) is not None
    assert store.verify_device_token(device_token) is not None

    # Checked moments ago: answered from memory.
    real = store._connect
    monkeypatch.setattr(store, '_connect', _no_database)
    assert store.session_user(token)['id'] == uid
    assert store.verify_device_token(device_token)['user_id'] == uid
    monkeypatch.setattr(store, '_connect', real)

    # A password change clears it: the next check asks the database again.
    store.users.set_password(uid, 'another password')
    asked: list[bool] = []

    def counting() -> object:
        asked.append(True)
        return real()

    monkeypatch.setattr(store, '_connect', counting)
    assert store.session_user(token) is not None
    assert asked
    monkeypatch.setattr(store, '_connect', real)

    # Deleting the account drops the cache and both logins fail.
    store.users.delete(uid)
    assert store.session_user(token) is None
    assert store.verify_device_token(device_token) is None
