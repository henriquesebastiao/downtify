"""User accounts: who signs in to Downtify, and what they may do.

Every web page and API call is made by a user, signed in with a username
and password (or through a phone paired to their account - see
:mod:`downtify.auth`). There are two roles:

* **admin** - everything: every setting, every user, the activity log.
* **user** - listen, search, download, like; in Settings only General,
  Apps and About, and only their own account, preferences and devices.

A new install starts with one admin, ``admin`` / ``downtify``
(:data:`DEFAULT_USERNAME`, :data:`DEFAULT_PASSWORD`), flagged as still
using the default password so the web app keeps suggesting a change. An
install upgraded from a version without accounts gets the same account -
or, when it had set the single sign-in password of the version before,
that password (so it keeps working) - and a one-time notice on the
sign-in page saying accounts exist now (:meth:`UserStore.notice`).

The last admin can't be deleted or made a normal user: somebody has to
be able to manage the server. ``python main.py auth-reset`` puts
``admin`` / ``downtify`` back (as an admin) for a forgotten password.

Stored in ``downtify_auth.db`` next to devices and sessions. Passwords
are scrypt hashes (:func:`hash_password`).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .sqlite_utils import connect_sqlite

#: Shortest password accepted.
MIN_PASSWORD_LENGTH = 8

# scrypt: N=2**15, r=8, p=1 (~32 MiB, ~50-100 ms) - the OWASP minimum.
_SCRYPT_N = 2**15
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_MAXMEM = 64 * 1024 * 1024

ROLE_ADMIN = 'admin'
ROLE_USER = 'user'
ROLES = (ROLE_ADMIN, ROLE_USER)

DEFAULT_USERNAME = 'admin'
DEFAULT_PASSWORD = 'downtify'

#: Usernames: 3-32 letters, digits, dots, dashes or underscores.
_USERNAME_RE = re.compile(r'^[A-Za-z0-9._-]{3,32}$')

#: The preferences a user keeps for themselves (Settings > General), with
#: their type. Anything else sent is ignored.
PREFERENCES: dict[str, type] = {
    'theme': str,
    'locale': str,
    'show_lyrics': bool,
    'search_albums': bool,
}


class UserError(ValueError):
    """A request about users that can't be done; the message says why."""


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def hash_password(password: str) -> str:
    """``scrypt$N$r$p$<salt>$<hash>`` for *password*."""

    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        maxmem=_SCRYPT_MAXMEM,
    )
    return (
        f'scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}$'
        f'{_b64(salt)}${_b64(digest)}'
    )


def verify_password(password: str, stored: str) -> bool:
    """Whether *password* matches a :func:`hash_password` value."""

    try:
        scheme, n, r, p, salt_b64, hash_b64 = stored.split('$')
        if scheme != 'scrypt':
            return False
        salt = base64.urlsafe_b64decode(salt_b64 + '=' * (-len(salt_b64) % 4))
        expected = base64.urlsafe_b64decode(
            hash_b64 + '=' * (-len(hash_b64) % 4)
        )
        digest = hashlib.scrypt(
            password.encode(),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            maxmem=_SCRYPT_MAXMEM,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_username(value: Any) -> str:
    """*value* as a username, or :class:`UserError`."""

    name = str(value or '').strip()
    if not _USERNAME_RE.fullmatch(name):
        raise UserError(
            'Usernames are 3 to 32 letters, digits, dots, dashes or '
            'underscores'
        )
    return name


def check_password_rules(password: Any) -> str:
    text = str(password or '')
    if len(text) < MIN_PASSWORD_LENGTH:
        raise UserError(f'Use at least {MIN_PASSWORD_LENGTH} characters')
    if len(text) > 256:
        raise UserError('That password is too long')
    return text


def clean_preferences(values: Any) -> dict[str, Any]:
    """The known preferences in *values*, each of its type."""

    if not isinstance(values, dict):
        return {}
    clean: dict[str, Any] = {}
    for key, kind in PREFERENCES.items():
        if key not in values:
            continue
        value = values[key]
        if kind is bool:
            clean[key] = bool(value)
        elif value is None:
            clean[key] = ''
        else:
            clean[key] = str(value)[:32]
    return clean


def public_user(row: Any) -> dict[str, Any]:
    """A user as the API shows it - never the password hash."""

    return {
        'id': int(row['id']),
        'username': row['username'],
        'role': row['role'],
        'default_password': bool(row['default_password']),
        'created_at': row['created_at'],
        'last_login_at': row['last_login_at'],
        'last_login_ip': row['last_login_ip'] or '',
    }


class UserStore:
    """The users table (and the one-time accounts notice)."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._lock = threading.Lock()
        self._init_db()
        self._dummy: Optional[str] = None

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    @property
    def _dummy_hash(self) -> str:
        """A hash to check against when there's no user, so an unknown
        username takes as long as a wrong password."""

        if self._dummy is None:
            self._dummy = hash_password('not a real password')
        return self._dummy

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    default_password INTEGER NOT NULL DEFAULT 0,
                    prefs_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    last_login_at TEXT,
                    last_login_ip TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS auth_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

    @staticmethod
    def _config(conn: sqlite3.Connection, key: str) -> Optional[str]:
        row = conn.execute(
            'SELECT value FROM auth_config WHERE key = ?', (key,)
        ).fetchone()
        return row['value'] if row else None

    @staticmethod
    def _set_config(
        conn: sqlite3.Connection, key: str, value: Optional[str]
    ) -> None:
        if value is None:
            conn.execute('DELETE FROM auth_config WHERE key = ?', (key,))
        else:
            conn.execute(
                """INSERT INTO auth_config (key, value) VALUES (?, ?)
                   ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
                (key, value),
            )

    # First run and upgrades

    def ensure_default_admin(self, *, existing_install: bool) -> bool:
        """Create the first admin when there are no users yet. Returns
        whether one was created.

        An *existing_install* (upgraded from a version without accounts)
        also gets the accounts notice. The single sign-in password of the
        version before, if one was set, becomes the admin's password, and
        the paired devices of that version are given to the admin.
        """

        with self._lock, self._connect() as conn:
            if conn.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                return False
            legacy = self._config(conn, 'password_hash')
            conn.execute(
                'INSERT INTO users (username, password_hash, role, '
                'default_password, created_at) VALUES (?, ?, ?, ?, ?)',
                (
                    DEFAULT_USERNAME,
                    legacy or hash_password(DEFAULT_PASSWORD),
                    ROLE_ADMIN,
                    0 if legacy else 1,
                    _now(),
                ),
            )
            admin_id = conn.execute(
                'SELECT id FROM users WHERE username = ?', (DEFAULT_USERNAME,)
            ).fetchone()['id']
            # Devices paired before accounts existed belong to the admin.
            columns = {
                r[1] for r in conn.execute('PRAGMA table_info(auth_devices)')
            }
            if 'user_id' in columns:
                conn.execute(
                    'UPDATE auth_devices SET user_id = ? WHERE user_id = 0',
                    (admin_id,),
                )
            if existing_install:
                self._set_config(
                    conn,
                    'accounts_notice',
                    'kept_password' if legacy else 'default_password',
                )
            self._set_config(conn, 'password_hash', None)
            self._set_config(conn, 'require_sign_in', None)
        return True

    def notice(self) -> Optional[dict[str, Any]]:
        """The one-time notice for an upgraded install, shown on the
        sign-in page until an admin has signed in with a password of
        their own: ``{username, password}`` - the password only when it
        is still the default (``None`` when the old one was kept)."""

        with self._connect() as conn:
            kind = self._config(conn, 'accounts_notice')
        if not kind:
            return None
        return {
            'username': DEFAULT_USERNAME,
            'password': DEFAULT_PASSWORD
            if kind == 'default_password'
            else None,
        }

    def clear_notice(self) -> None:
        with self._connect() as conn:
            self._set_config(conn, 'accounts_notice', None)

    def reset_admin(self) -> dict[str, Any]:
        """Recovery (``python main.py auth-reset``): an admin ``admin``
        with the default password, whether or not it existed."""

        with self._lock, self._connect() as conn:
            row = conn.execute(
                'SELECT id FROM users WHERE username = ?', (DEFAULT_USERNAME,)
            ).fetchone()
            if row is None:
                conn.execute(
                    'INSERT INTO users (username, password_hash, role, '
                    'default_password, created_at) VALUES (?, ?, ?, 1, ?)',
                    (
                        DEFAULT_USERNAME,
                        hash_password(DEFAULT_PASSWORD),
                        ROLE_ADMIN,
                        _now(),
                    ),
                )
            else:
                conn.execute(
                    'UPDATE users SET password_hash = ?, role = ?, '
                    'default_password = 1 WHERE id = ?',
                    (hash_password(DEFAULT_PASSWORD), ROLE_ADMIN, row['id']),
                )
        return self.by_username(DEFAULT_USERNAME) or {}

    # Signing in

    def authenticate(
        self, username: str, password: str
    ) -> Optional[dict[str, Any]]:
        """The user, when *username* and *password* match; else ``None``.
        Takes as long either way."""

        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM users WHERE username = ?',
                (str(username or '').strip(),),
            ).fetchone()
        stored = row['password_hash'] if row else self._dummy_hash
        ok = verify_password(str(password or ''), stored)
        if row is None or not ok:
            return None
        return public_user(row)

    def record_login(self, user_id: int, ip: str) -> None:
        with self._connect() as conn:
            conn.execute(
                'UPDATE users SET last_login_at = ?, last_login_ip = ? '
                'WHERE id = ?',
                (_now(), ip[:64], user_id),
            )

    # Reading

    def get(self, user_id: int) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM users WHERE id = ?', (user_id,)
            ).fetchone()
        return public_user(row) if row else None

    def by_username(self, username: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM users WHERE username = ?', (username,)
            ).fetchone()
        return public_user(row) if row else None

    def list(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT * FROM users ORDER BY username COLLATE NOCASE'
            ).fetchall()
        return [public_user(r) for r in rows]

    def admin_count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT COUNT(*) AS n FROM users WHERE role = ?', (ROLE_ADMIN,)
            ).fetchone()
        return int(row['n'])

    # Changing

    def create(
        self, username: Any, password: Any, role: str = ROLE_USER
    ) -> dict[str, Any]:
        name = clean_username(username)
        secret = check_password_rules(password)
        if role not in ROLES:
            raise UserError('Unknown role')
        try:
            with self._connect() as conn:
                conn.execute(
                    'INSERT INTO users (username, password_hash, role, '
                    'created_at) VALUES (?, ?, ?, ?)',
                    (name, hash_password(secret), role, _now()),
                )
        except sqlite3.IntegrityError as exc:
            raise UserError('That username is taken') from exc
        return self.by_username(name) or {}

    def update(
        self,
        user_id: int,
        *,
        username: Any = None,
        role: Optional[str] = None,
    ) -> dict[str, Any]:
        """Rename a user and/or change their role. Refuses to leave the
        server without an admin."""

        with self._lock:
            current = self.get(user_id)
            if current is None:
                raise UserError('User not found')
            updates: dict[str, Any] = {}
            if username is not None:
                updates['username'] = clean_username(username)
            if role is not None:
                if role not in ROLES:
                    raise UserError('Unknown role')
                if (
                    current['role'] == ROLE_ADMIN
                    and role != ROLE_ADMIN
                    and self.admin_count() <= 1
                ):
                    raise UserError('The last admin must stay an admin')
                updates['role'] = role
            if updates:
                assignments = ', '.join(f'{key} = ?' for key in updates)
                try:
                    with self._connect() as conn:
                        conn.execute(
                            f'UPDATE users SET {assignments} WHERE id = ?',
                            (*updates.values(), user_id),
                        )
                except sqlite3.IntegrityError as exc:
                    raise UserError('That username is taken') from exc
        return self.get(user_id) or {}

    def set_password(self, user_id: int, password: Any) -> None:
        secret = check_password_rules(password)
        with self._connect() as conn:
            cur = conn.execute(
                'UPDATE users SET password_hash = ?, default_password = 0 '
                'WHERE id = ?',
                (hash_password(secret), user_id),
            )
            if cur.rowcount == 0:
                raise UserError('User not found')

    def check_password(self, user_id: int, password: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT password_hash FROM users WHERE id = ?', (user_id,)
            ).fetchone()
        stored = row['password_hash'] if row else self._dummy_hash
        return bool(row) and verify_password(str(password or ''), stored)

    def delete(self, user_id: int) -> dict[str, Any]:
        with self._lock:
            current = self.get(user_id)
            if current is None:
                raise UserError('User not found')
            if current['role'] == ROLE_ADMIN and self.admin_count() <= 1:
                raise UserError('The last admin cannot be deleted')
            with self._connect() as conn:
                conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        return current

    # Preferences

    def preferences(self, user_id: int) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT prefs_json FROM users WHERE id = ?', (user_id,)
            ).fetchone()
        if row is None:
            return {}
        try:
            data = json.loads(row['prefs_json'])
        except ValueError:
            return {}
        return clean_preferences(data)

    def set_preferences(self, user_id: int, values: Any) -> dict[str, Any]:
        """Merge *values* into the user's preferences; the result."""

        merged = {**self.preferences(user_id), **clean_preferences(values)}
        with self._connect() as conn:
            conn.execute(
                'UPDATE users SET prefs_json = ? WHERE id = ?',
                (json.dumps(merged), user_id),
            )
        return merged
