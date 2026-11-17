"""UserStore on both backends: the same results on SQLite and PostgreSQL."""

from __future__ import annotations

import pytest

from downtify.db.config import Dialect
from downtify.db.errors import IntegrityError
from downtify.users import (
    DEFAULT_PASSWORD,
    DEFAULT_USERNAME,
    ROLE_ADMIN,
    ROLE_USER,
    UserError,
    UserStore,
    clean_preferences,
    hash_password,
    verify_password,
)
from tests.db.helpers import execute, query

ISSUER = 'https://idp.example'


def _admin_store(db) -> UserStore:
    store = UserStore(db)
    assert store.ensure_default_admin(existing_install=False) is True
    return store


def test_constructor_accepts_a_path(tmp_path) -> None:
    store = UserStore(tmp_path / 'auth.db')
    assert store.db.dialect is Dialect.SQLITE
    assert store._path == str(tmp_path / 'auth.db')


def test_scrypt_round_trip() -> None:
    stored = hash_password('a good password')
    assert stored.startswith('scrypt$')
    assert verify_password('a good password', stored) is True
    assert verify_password('wrong', stored) is False
    assert verify_password('a good password', 'not-a-hash') is False


def test_clean_preferences_keeps_known_keys_typed() -> None:
    assert clean_preferences(None) == {}
    assert clean_preferences({'theme': 'dark', 'x': 1, 'show_lyrics': 0}) == {
        'theme': 'dark',
        'show_lyrics': False,
    }


def test_first_run_creates_default_admin(backend_db) -> None:
    store = UserStore(backend_db)
    assert store.ensure_default_admin(existing_install=False) is True
    assert store.ensure_default_admin(existing_install=False) is False

    admin = store.first_admin()
    assert admin is not None
    assert admin['username'] == DEFAULT_USERNAME
    assert admin['role'] == ROLE_ADMIN
    assert admin['default_password'] is True
    assert isinstance(admin['id'], int)
    assert store.admin_count() == 1
    assert store.notice() is None

    assert store.check_password(admin['id'], DEFAULT_PASSWORD) is True
    assert store.check_password(admin['id'], 'nope nope nope') is False
    assert store.check_password(999, DEFAULT_PASSWORD) is False
    signed_in = store.authenticate('admin', DEFAULT_PASSWORD)
    assert signed_in is not None
    assert signed_in['id'] == admin['id']
    assert store.authenticate('ADMIN', DEFAULT_PASSWORD) is not None
    assert store.authenticate('admin', 'wrong wrong') is None


def test_upgrade_keeps_legacy_password_and_shows_notice(backend_db) -> None:
    store = UserStore(backend_db)
    execute(
        backend_db,
        'insert into auth_config (key, value) values (?, ?)',
        'password_hash',
        hash_password('legacy secret'),
    )
    execute(
        backend_db,
        'create table if not exists auth_devices (id text primary key, '
        "name text not null, platform text not null default '', "
        'token_hash text not null, created_at text not null, '
        "last_seen_at text, last_ip text not null default '', "
        'revoked_at text, user_id bigint not null default 0)',
    )
    execute(
        backend_db,
        'insert into auth_devices (id, name, token_hash, created_at, '
        'user_id) values (?, ?, ?, ?, 0)',
        'dev1',
        'Phone',
        'hash',
        '2024-01-01T00:00:00+00:00',
    )

    assert store.ensure_default_admin(existing_install=True) is True
    admin = store.first_admin()
    assert admin is not None
    assert admin['default_password'] is False
    assert store.authenticate('admin', 'legacy secret') is not None
    assert store.notice() == {'username': 'admin', 'password': None}
    assert (
        query(
            backend_db,
            'select count(*) from auth_config where key = ?',
            'password_hash',
        )[0][0]
        == 0
    )
    device = query(
        backend_db, 'select user_id from auth_devices where id = ?', 'dev1'
    )
    assert int(device[0][0]) == admin['id']

    store.clear_notice()
    assert store.notice() is None


def test_fresh_upgrade_notice_has_default_password(backend_db) -> None:
    store = UserStore(backend_db)
    store.ensure_default_admin(existing_install=True)
    assert store.notice() == {
        'username': DEFAULT_USERNAME,
        'password': DEFAULT_PASSWORD,
    }
    store.clear_notice()
    assert store.notice() is None


def test_reset_admin_inserts_then_resets(backend_db) -> None:
    store = UserStore(backend_db)
    created = store.reset_admin()
    assert created['username'] == DEFAULT_USERNAME
    assert created['role'] == ROLE_ADMIN
    assert created['default_password'] is True

    store.set_password(created['id'], 'another password')
    again = store.reset_admin()
    assert again['id'] == created['id']
    assert again['default_password'] is True
    assert store.check_password(created['id'], DEFAULT_PASSWORD) is True


def test_create_get_list_and_lookup(backend_db) -> None:
    store = _admin_store(backend_db)
    alice = store.create('Alice', 'password one', ROLE_USER)
    bob = store.create('bob.smith', 'password two', ROLE_ADMIN)

    assert alice['username'] == 'Alice'
    assert alice['role'] == ROLE_USER
    assert alice['default_password'] is False
    assert store.get(alice['id']) == alice
    assert store.get(999) is None
    assert store.by_username('alice') == alice
    assert store.by_username('nobody') is None
    assert [u['username'] for u in store.list()] == [
        DEFAULT_USERNAME,
        'Alice',
        'bob.smith',
    ]
    assert bob['role'] == ROLE_ADMIN
    assert store.admin_count() == 2


def test_create_rejects_bad_input_and_duplicates(backend_db) -> None:
    store = _admin_store(backend_db)
    store.create('Alice', 'password one')

    with pytest.raises(UserError, match='taken'):
        store.create('alice', 'password three')
    with pytest.raises(UserError, match='Unknown role'):
        store.create('carol', 'password four', 'superuser')
    with pytest.raises(UserError, match='Usernames'):
        store.create('x y', 'password four')
    with pytest.raises(UserError, match='at least'):
        store.create('carol', 'short')
    with pytest.raises(UserError, match='too long'):
        store.create('carol', 'x' * 257)


def test_unique_username_is_case_insensitive_at_the_db(backend_db) -> None:
    _admin_store(backend_db)
    with pytest.raises(IntegrityError):
        execute(
            backend_db,
            'insert into users (username, password_hash, created_at) '
            'values (?, ?, ?)',
            'ADMIN',
            'x',
            '2024-01-01T00:00:00+00:00',
        )


def test_update_rename_role_and_last_admin(backend_db) -> None:
    store = _admin_store(backend_db)
    admin = store.first_admin()
    assert admin is not None
    bob = store.create('bob', 'password one')

    assert store.update(bob['id'], username='Robert')['username'] == 'Robert'
    with pytest.raises(UserError, match='taken'):
        store.update(bob['id'], username='ADMIN')
    with pytest.raises(UserError, match='Unknown role'):
        store.update(bob['id'], role='weird')
    with pytest.raises(UserError, match='User not found'):
        store.update(999, role=ROLE_USER)

    assert store.update(bob['id'], role=ROLE_ADMIN)['role'] == ROLE_ADMIN
    assert store.admin_count() == 2
    assert store.update(admin['id'], role=ROLE_USER)['role'] == ROLE_USER
    with pytest.raises(UserError, match='last admin'):
        store.update(bob['id'], role=ROLE_USER)
    assert store.update(bob['id'])['username'] == 'Robert'


def test_set_password_clears_default_flag(backend_db) -> None:
    store = _admin_store(backend_db)
    admin = store.first_admin()
    assert admin is not None
    assert admin['default_password'] is True

    store.set_password(admin['id'], 'a brand new password')
    assert store.get(admin['id'])['default_password'] is False
    assert store.check_password(admin['id'], 'a brand new password') is True
    assert store.check_password(admin['id'], DEFAULT_PASSWORD) is False
    with pytest.raises(UserError, match='at least'):
        store.set_password(admin['id'], 'short')
    with pytest.raises(UserError, match='User not found'):
        store.set_password(999, 'another password')


def test_record_login(backend_db) -> None:
    store = _admin_store(backend_db)
    admin = store.first_admin()
    assert admin is not None
    store.record_login(admin['id'], '10.0.0.1')
    seen = store.get(admin['id'])
    assert seen['last_login_ip'] == '10.0.0.1'
    assert seen['last_login_at']

    store.record_login(admin['id'], 'x' * 100)
    assert len(store.get(admin['id'])['last_login_ip']) == 64


def test_delete_guards_last_admin(backend_db) -> None:
    store = _admin_store(backend_db)
    admin = store.first_admin()
    assert admin is not None
    bob = store.create('bob', 'password one')

    assert store.delete(bob['id'])['username'] == 'bob'
    assert store.get(bob['id']) is None
    with pytest.raises(UserError, match='User not found'):
        store.delete(bob['id'])
    with pytest.raises(UserError, match='last admin'):
        store.delete(admin['id'])

    store.create('second', 'password two', ROLE_ADMIN)
    assert store.delete(admin['id'])['username'] == DEFAULT_USERNAME
    assert store.first_admin()['username'] == 'second'


def test_oidc_identity_lifecycle(backend_db) -> None:
    store = _admin_store(backend_db)
    store.create('Ana', 'password one')

    maria = store._get_or_create_oidc_user(ISSUER, 'sub-1', 'Maria', ROLE_USER)
    assert maria['username'] == 'Maria'
    again = store._get_or_create_oidc_user(ISSUER, 'sub-1', 'Maria', ROLE_USER)
    assert again['id'] == maria['id']

    ana = store._get_or_create_oidc_user(ISSUER, 'sub-2', 'Ana', ROLE_USER)
    assert ana['username'].startswith('Ana_')
    assert ana['username'] != 'Ana'

    promoted = store._get_or_create_oidc_user(
        ISSUER, 'sub-1', 'Maria', ROLE_ADMIN
    )
    assert promoted['role'] == ROLE_ADMIN
    store.delete(store.first_admin()['id'])
    with pytest.raises(UserError, match='last admin'):
        store._get_or_create_oidc_user(ISSUER, 'sub-1', 'Maria', ROLE_USER)

    with pytest.raises(UserError, match='issuer and subject'):
        store._get_or_create_oidc_user('', 'sub-3', 'Nope', ROLE_USER)
    with pytest.raises(UserError, match='Unknown role'):
        store._get_or_create_oidc_user(ISSUER, 'sub-3', 'Nope', 'weird')

    # Deleting the account drops its identity, so the next sign-in
    # provisions a fresh account.
    store.create('boss', 'password two', ROLE_ADMIN)
    store.delete(maria['id'])
    fresh = store._get_or_create_oidc_user(ISSUER, 'sub-1', 'Maria', ROLE_USER)
    assert fresh['id'] != maria['id']


def test_preferences_merge(backend_db) -> None:
    store = _admin_store(backend_db)
    alice = store.create('alice', 'password one')
    assert store.preferences(alice['id']) == {}

    merged = store.set_preferences(
        alice['id'],
        {'theme': 'dark', 'show_lyrics': 0, 'bogus': 1, 'locale': None},
    )
    assert merged == {'theme': 'dark', 'show_lyrics': False, 'locale': ''}
    assert store.preferences(alice['id']) == merged

    merged = store.set_preferences(alice['id'], {'theme': 'light'})
    assert merged == {'theme': 'light', 'show_lyrics': False, 'locale': ''}
    assert store.set_preferences(alice['id'], 'not a dict') == merged
    assert store.preferences(999) == {}


def test_change_listeners_fire_once_per_change(backend_db) -> None:
    store = _admin_store(backend_db)
    calls: list[int] = []

    def listener() -> None:
        calls.append(1)

    store.add_change_listener(listener)
    store.add_change_listener(listener)
    alice = store.create('alice', 'password one')
    assert calls == []

    store.set_password(alice['id'], 'another password')
    store.update(alice['id'], username='alicia')
    store.delete(alice['id'])
    assert len(calls) == 3
