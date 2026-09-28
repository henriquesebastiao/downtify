"""Sign-in for the web UI and paired apps.

Everything but the web app's own files and a few public routes needs a
signed-in user (:mod:`downtify.users`): a browser signed in with a
username and password (a session cookie), or an app paired to a user's
account in Settings > Apps.

* **Web sessions.** ``POST /api/auth/login`` with the username and
  password sets an HttpOnly cookie that lasts 30 days after it was last
  used. An *admin* user's session has the admin scope: everything. A
  normal *user*'s has the user scope: what a paired app may do, plus
  their own account, preferences and devices.
* **Paired devices** (the Android app). Settings > Apps shows a short
  code (and a QR code carrying it); an app that sends it back to
  ``POST /api/auth/pair`` within five minutes gets a long-lived device
  token, ``dtfy_<device id>_<secret>``, sent as ``Authorization: Bearer``,
  tied to the user who paired it. Only a hash of the secret is stored; a
  device can be revoked at any time. Devices get the *client* scope: they
  can read and play the library and ask for downloads, but settings,
  credentials, deleting files and managing devices need a browser.

Players that can't send headers (a Chromecast receiver fetching a stream
itself) use **signed URLs**: ``exp``, ``kid`` (the device) and ``sig``
query parameters, an HMAC over the method, path and every other query
parameter, valid until ``exp`` and only while the device isn't revoked.
Long-lived tokens never go in a URL.

Everything here is stored in ``<data>/downtify_auth.db`` and
``<data>/.auth_secret`` (the signing key) - never in ``settings.json``,
which ``GET /api/settings`` hands out. Passwords are hashed with scrypt
(standard library); tokens and session ids, being random and long, with
SHA-256. Every comparison of a secret is constant-time.

:class:`AuthMiddleware` enforces all of it for HTTP routes, static mounts
and the WebSocket alike, from one table of path rules (:data:`RULES`);
anything not listed there needs the admin scope, so a new route can't be
left open by mistake (a test checks every route is listed on purpose).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from collections import deque
from collections.abc import Awaitable, Callable, Iterable, MutableMapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode

from loguru import logger

from .sqlite_utils import connect_sqlite
from .users import ROLE_ADMIN, UserStore, public_user

# ── Scopes and principals ───────────────────────────────────────────────

PUBLIC = 'public'
#: A paired app (or a signed URL for one).
CLIENT = 'client'
#: A browser signed in as a normal user: CLIENT, plus their own account.
USER = 'user'
#: A browser signed in as an admin: everything.
ADMIN = 'admin'

_RANK = {PUBLIC: 0, CLIENT: 1, USER: 2, ADMIN: 3}


def allows(held: str, needed: str) -> bool:
    """Whether a principal with scope *held* may use a route that needs
    *needed*."""

    return _RANK.get(held, 0) >= _RANK.get(needed, 3)


#: The cookie a signed-in browser carries.
SESSION_COOKIE = 'downtify_session'
#: How long a web session lasts without being used.
SESSION_TTL = timedelta(days=30)
#: A web session's expiry is pushed back at most this often.
SESSION_TOUCH_INTERVAL = timedelta(hours=1)
#: A device's last-seen time and IP are written at most this often.
DEVICE_TOUCH_INTERVAL = timedelta(minutes=1)
#: How long a pairing code shown in Settings > Apps can be used.
PAIRING_TTL_SECONDS = 300
#: How long a WebSocket ticket can be used.
WS_TICKET_TTL_SECONDS = 60
#: Signed URLs: default and longest lifetime, in seconds.
SIGNED_URL_DEFAULT_TTL = 3600
SIGNED_URL_MAX_TTL = 24 * 3600
#: Longest device name kept.
MAX_DEVICE_NAME = 64

TOKEN_PREFIX = 'dtfy_'
_DEVICE_ID_ALPHABET = 'abcdefghijkmnpqrstuvwxyz23456789'
_DEVICE_ID_LENGTH = 12
_TOKEN_RE = re.compile(r'^dtfy_([a-z2-9]{12})_([A-Za-z0-9_-]{32,64})$')

# Pairing codes: Crockford base32 (no I, L, O, U), 8 characters ≈ 40 bits,
# shown as XXXX-XXXX. Typed codes are normalised (case, dashes, and the
# letters Crockford reads as digits).
_PAIR_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
_PAIR_CODE_LENGTH = 8
_PAIR_TYPO_MAP = str.maketrans({'I': '1', 'L': '1', 'O': '0', 'U': 'V'})


@dataclass(frozen=True)
class Principal:
    """Who made a request."""

    #: 'session' (a signed-in browser), 'device' (a paired app, by token),
    #: 'signed' (a signed URL), 'ticket' (a WebSocket ticket).
    kind: str
    scope: str
    device_id: str = ''
    #: The signed-in user (``0`` for a signed URL, which only knows the
    #: device), their name and role.
    user_id: int = 0
    username: str = ''
    role: str = ''

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(when: datetime) -> str:
    return when.isoformat()


def _parse(value: Any) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


# ── Pairing codes ───────────────────────────────────────────────────────


def new_pairing_code() -> str:
    """A random ``XXXX-XXXX`` pairing code."""

    raw = ''.join(
        secrets.choice(_PAIR_ALPHABET) for _ in range(_PAIR_CODE_LENGTH)
    )
    return f'{raw[:4]}-{raw[4:]}'


def normalize_pairing_code(value: Any) -> str:
    """A typed or scanned code in its canonical form (no dash, upper
    case, look-alike letters read as Crockford does), or ``''``."""

    text = re.sub(r'[\s-]', '', str(value or '')).upper()
    text = text.translate(_PAIR_TYPO_MAP)
    if len(text) != _PAIR_CODE_LENGTH or any(
        ch not in _PAIR_ALPHABET for ch in text
    ):
        return ''
    return text


def clean_device_name(value: Any) -> str:
    text = ' '.join(str(value or '').split())[:MAX_DEVICE_NAME]
    return text or 'Unnamed device'


class PairingStore:
    """Pairing sessions waiting for an app, kept in memory.

    Each has an id (for the web page to follow it) and a code (what the
    app sends). Only the code's hash is kept; claiming it is atomic and
    single-use. Pending sessions don't survive a restart, which is fine
    for something that lasts five minutes.
    """

    def __init__(self, ttl_seconds: int = PAIRING_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        # pairing id -> {code_hash, expires, device}
        self._sessions: dict[str, dict[str, Any]] = {}

    def _prune(self, now: float) -> None:
        for pid, entry in list(self._sessions.items()):
            # A claimed one stays a little longer so the page sees it.
            if entry['expires'] + (60 if entry['device'] else 0) < now:
                del self._sessions[pid]

    def create(self, user_id: int = 0) -> dict[str, Any]:
        """A new pairing session for *user_id*'s account:
        ``{pairing_id, code, expires_in}``."""

        code = new_pairing_code()
        pairing_id = secrets.token_urlsafe(12)
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            self._sessions[pairing_id] = {
                'code_hash': _sha256(normalize_pairing_code(code)),
                'expires': now + self._ttl,
                'device': None,
                'user_id': user_id,
            }
        return {
            'pairing_id': pairing_id,
            'code': code,
            'expires_in': self._ttl,
        }

    def claim(self, code: Any) -> Optional[str]:
        """The id of the pending session *code* belongs to, now used up;
        ``None`` for a wrong, expired or already used code."""

        canonical = normalize_pairing_code(code)
        if not canonical:
            return None
        wanted = _sha256(canonical)
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            for pid, entry in self._sessions.items():
                if entry['device'] is not None or entry['expires'] < now:
                    continue
                if hmac.compare_digest(entry['code_hash'], wanted):
                    # Used up at once, before the token is even made.
                    entry['code_hash'] = ''
                    entry['device'] = {}
                    return pid
        return None

    def owner(self, pairing_id: str) -> Optional[int]:
        """The user a pairing session is for, while it exists."""

        with self._lock:
            entry = self._sessions.get(pairing_id)
        return None if entry is None else int(entry['user_id'])

    def complete(self, pairing_id: str, device: dict[str, Any]) -> None:
        with self._lock:
            entry = self._sessions.get(pairing_id)
            if entry is not None:
                entry['device'] = device

    def status(self, pairing_id: str) -> dict[str, Any]:
        """``{status: pending|paired|expired, device?, expires_in?}``."""

        now = time.monotonic()
        with self._lock:
            self._prune(now)
            entry = self._sessions.get(pairing_id)
            if entry is None:
                return {'status': 'expired'}
            if entry['device']:
                return {'status': 'paired', 'device': entry['device']}
            if entry['expires'] < now:
                return {'status': 'expired'}
            return {
                'status': 'pending',
                'expires_in': max(0, int(entry['expires'] - now)),
            }

    def cancel(self, pairing_id: str) -> None:
        with self._lock:
            self._sessions.pop(pairing_id, None)


class TicketStore:
    """Single-use, short-lived WebSocket tickets, kept in memory."""

    def __init__(self, ttl_seconds: int = WS_TICKET_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._tickets: dict[str, tuple[float, Principal]] = {}

    def create(self, principal: Principal) -> str:
        ticket = secrets.token_urlsafe(24)
        now = time.monotonic()
        with self._lock:
            for key, (expires, _p) in list(self._tickets.items()):
                if expires < now:
                    del self._tickets[key]
            self._tickets[_sha256(ticket)] = (now + self._ttl, principal)
        return ticket

    def claim(self, ticket: str) -> Optional[Principal]:
        with self._lock:
            found = self._tickets.pop(_sha256(str(ticket or '')), None)
        if found is None or found[0] < time.monotonic():
            return None
        return found[1]


# ── Rate limiting and client addresses ──────────────────────────────────


class RateLimiter:
    """At most *limit* failures per key within *window* seconds."""

    def __init__(self, limit: int = 10, window: float = 300.0) -> None:
        self._limit = limit
        self._window = window
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = {}

    def _recent(self, key: str, now: float) -> deque[float]:
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self._window:
            hits.popleft()
        return hits

    def retry_after(self, key: str) -> int:
        """Seconds until *key* may try again; ``0`` when it may now."""

        now = time.monotonic()
        with self._lock:
            hits = self._recent(key, now)
            if len(hits) < self._limit:
                return 0
            return max(1, int(hits[0] + self._window - now) + 1)

    def fail(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._recent(key, now).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)


def trusted_proxies_from_env() -> list[Any]:
    """``DOWNTIFY_TRUSTED_PROXIES``: comma-separated IPs or networks whose
    ``X-Forwarded-For`` is believed. Unset: nobody's is."""

    networks = []
    for raw in os.getenv('DOWNTIFY_TRUSTED_PROXIES', '').split(','):
        part = raw.strip()
        if not part:
            continue
        try:
            networks.append(ip_network(part, strict=False))
        except ValueError:
            logger.warning('DOWNTIFY_TRUSTED_PROXIES: ignoring {!r}', part)
    return networks


def client_ip(scope: MutableMapping[str, Any], trusted: list[Any]) -> str:
    """The client's address: the TCP peer, or - only when the peer is a
    trusted proxy - the last address in ``X-Forwarded-For`` that isn't
    one. Believing that header from anyone would let a client pick the
    address its failed logins are counted against."""

    peer = (scope.get('client') or ('', 0))[0] or ''
    if not trusted or not _in_networks(peer, trusted):
        return peer
    forwarded = _header(scope, 'x-forwarded-for')
    hops = [h.strip() for h in forwarded.split(',') if h.strip()]
    for hop in reversed(hops):
        if not _in_networks(hop, trusted):
            return hop
    return peer


def _in_networks(address: str, networks: list[Any]) -> bool:
    try:
        addr = ip_address(address)
    except ValueError:
        return False
    return any(addr in net for net in networks)


def _header(scope: MutableMapping[str, Any], name: str) -> str:
    wanted = name.lower().encode()
    for key, value in scope.get('headers') or []:
        if key.lower() == wanted:
            return value.decode('latin-1')
    return ''


# ── The store ───────────────────────────────────────────────────────────


class AuthStore:
    """Users, web sessions, paired devices and the signing key.

    The accounts themselves are :attr:`users` (:class:`UserStore`); every
    session and device belongs to one of them.
    """

    def __init__(
        self,
        db_path: Path,
        secret_path: Path,
        *,
        existing_install: bool = False,
    ) -> None:
        self._path = str(db_path)
        self._lock = threading.Lock()
        self._init_db()
        self.users = UserStore(db_path)
        if self.users.ensure_default_admin(existing_install=existing_install):
            # Sessions from before accounts belong to nobody.
            self.end_all_sessions()
        self.signer = UrlSigner(secret_path, self.device_active)

    # Storage

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS auth_devices (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    platform TEXT NOT NULL DEFAULT '',
                    token_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT,
                    last_ip TEXT NOT NULL DEFAULT '',
                    revoked_at TEXT,
                    user_id INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    id_hash TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    touched_at TEXT NOT NULL,
                    ip TEXT NOT NULL DEFAULT '',
                    user_agent TEXT NOT NULL DEFAULT '',
                    user_id INTEGER NOT NULL DEFAULT 0
                )
            """)
            # Databases from before accounts: sessions and devices gain
            # their owner.
            for table in ('auth_devices', 'auth_sessions'):
                columns = {
                    row[1]
                    for row in conn.execute(f'PRAGMA table_info({table})')
                }
                if 'user_id' not in columns:
                    conn.execute(
                        f'ALTER TABLE {table} ADD COLUMN user_id '
                        'INTEGER NOT NULL DEFAULT 0'
                    )

    # Web sessions

    def create_session(
        self, user_id: int, ip: str = '', user_agent: str = ''
    ) -> str:
        token = secrets.token_urlsafe(32)
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO auth_sessions
                   (id_hash, created_at, expires_at, touched_at, ip,
                    user_agent, user_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    _sha256(token),
                    _iso(now),
                    _iso(now + SESSION_TTL),
                    _iso(now),
                    ip[:64],
                    user_agent[:200],
                    user_id,
                ),
            )
        return token

    def session_user(self, token: str) -> Optional[dict[str, Any]]:
        """The user a live web session *token* belongs to (and keep the
        session alive); ``None`` for an unknown or expired one."""

        if not token or len(token) > 128:
            return None
        key = _sha256(token)
        with self._connect() as conn:
            row = conn.execute(
                'SELECT s.expires_at, s.touched_at, u.* '
                'FROM auth_sessions s JOIN users u ON u.id = s.user_id '
                'WHERE s.id_hash = ?',
                (key,),
            ).fetchone()
            if row is None:
                return None
            now = _now()
            expires = _parse(row['expires_at'])
            if expires is None or expires <= now:
                conn.execute(
                    'DELETE FROM auth_sessions WHERE id_hash = ?', (key,)
                )
                return None
            touched = _parse(row['touched_at'])
            if touched is None or now - touched >= SESSION_TOUCH_INTERVAL:
                conn.execute(
                    'UPDATE auth_sessions SET expires_at = ?, touched_at = ? '
                    'WHERE id_hash = ?',
                    (_iso(now + SESSION_TTL), _iso(now), key),
                )
        return public_user(row)

    def end_session(self, token: str) -> None:
        with self._connect() as conn:
            conn.execute(
                'DELETE FROM auth_sessions WHERE id_hash = ?',
                (_sha256(token or ''),),
            )

    def end_all_sessions(self) -> int:
        with self._connect() as conn:
            return conn.execute('DELETE FROM auth_sessions').rowcount

    def end_user_sessions(self, user_id: int, keep: str = '') -> int:
        """Sign *user_id* out of every browser but the one with the
        session *keep* (e.g. the one that just changed the password)."""

        with self._connect() as conn:
            return conn.execute(
                'DELETE FROM auth_sessions WHERE user_id = ? AND id_hash != ?',
                (user_id, _sha256(keep) if keep else ''),
            ).rowcount

    # Devices

    def create_device(
        self, name: str, platform: str = '', ip: str = '', user_id: int = 0
    ) -> tuple[dict[str, Any], str]:
        """Register a device paired to *user_id*: ``(device, token)``.
        The token is shown to the app once and never stored."""

        device_id = ''.join(
            secrets.choice(_DEVICE_ID_ALPHABET)
            for _ in range(_DEVICE_ID_LENGTH)
        )
        secret = secrets.token_urlsafe(32)
        now = _iso(_now())
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO auth_devices
                   (id, name, platform, token_hash, created_at,
                    last_seen_at, last_ip, user_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    device_id,
                    clean_device_name(name),
                    str(platform or '')[:32],
                    _sha256(secret),
                    now,
                    now,
                    ip[:64],
                    user_id,
                ),
            )
        return self.get_device(device_id) or {}, (
            f'{TOKEN_PREFIX}{device_id}_{secret}'
        )

    _DEVICE_COLUMNS = (
        'd.id, d.name, d.platform, d.created_at, d.last_seen_at, '
        "d.last_ip, d.user_id, COALESCE(u.username, '') AS username"
    )

    def get_device(self, device_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                f'SELECT {self._DEVICE_COLUMNS}, d.revoked_at '
                'FROM auth_devices d LEFT JOIN users u ON u.id = d.user_id '
                'WHERE d.id = ?',
                (device_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_devices(
        self, user_id: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Paired devices - *user_id*'s, or everyone's when ``None``."""

        where = 'd.revoked_at IS NULL'
        args: tuple[Any, ...] = ()
        if user_id is not None:
            where += ' AND d.user_id = ?'
            args = (user_id,)
        with self._connect() as conn:
            rows = conn.execute(
                f'SELECT {self._DEVICE_COLUMNS} '
                'FROM auth_devices d LEFT JOIN users u ON u.id = d.user_id '
                f'WHERE {where} ORDER BY d.created_at DESC',
                args,
            ).fetchall()
        return [dict(row) for row in rows]

    def device_active(self, device_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT 1 FROM auth_devices WHERE id = ? '
                'AND revoked_at IS NULL',
                (device_id,),
            ).fetchone()
        return row is not None

    def verify_device_token(
        self, token: str, ip: str = ''
    ) -> Optional[dict[str, Any]]:
        """The device *token* belongs to and its user, when it's valid,
        not revoked and its user still exists (and note that it was
        seen); else ``None``."""

        match = _TOKEN_RE.match(token or '')
        if not match:
            return None
        device_id, secret = match.groups()
        with self._connect() as conn:
            row = conn.execute(
                'SELECT d.id, d.name, d.token_hash, d.last_seen_at, '
                'd.revoked_at, d.user_id, u.username, u.role '
                'FROM auth_devices d LEFT JOIN users u ON u.id = d.user_id '
                'WHERE d.id = ?',
                (device_id,),
            ).fetchone()
            if row is None:
                # Same work either way, so timing doesn't say it's unknown.
                hmac.compare_digest(_sha256(secret), _sha256(''))
                return None
            if not hmac.compare_digest(row['token_hash'], _sha256(secret)):
                return None
            if row['revoked_at'] or row['username'] is None:
                return None
            now = _now()
            seen = _parse(row['last_seen_at'])
            if seen is None or now - seen >= DEVICE_TOUCH_INTERVAL:
                conn.execute(
                    'UPDATE auth_devices SET last_seen_at = ?, last_ip = ? '
                    'WHERE id = ?',
                    (_iso(now), ip[:64], device_id),
                )
        return {
            'id': row['id'],
            'name': row['name'],
            'user_id': int(row['user_id']),
            'username': row['username'],
            'role': row['role'],
        }

    def rename_device(self, device_id: str, name: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                'UPDATE auth_devices SET name = ? WHERE id = ? '
                'AND revoked_at IS NULL',
                (clean_device_name(name), device_id),
            )
            return cur.rowcount > 0

    def revoke_device(self, device_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                'UPDATE auth_devices SET revoked_at = ? WHERE id = ? '
                'AND revoked_at IS NULL',
                (_iso(_now()), device_id),
            )
            return cur.rowcount > 0

    def revoke_user(self, user_id: int, keep_session: str = '') -> list[str]:
        """Sign *user_id* out everywhere - every paired device and every
        browser but *keep_session*. The ids of the devices unpaired."""

        with self._connect() as conn:
            ids = [
                row['id']
                for row in conn.execute(
                    'SELECT id FROM auth_devices WHERE user_id = ? '
                    'AND revoked_at IS NULL',
                    (user_id,),
                ).fetchall()
            ]
            conn.execute(
                'UPDATE auth_devices SET revoked_at = ? WHERE user_id = ? '
                'AND revoked_at IS NULL',
                (_iso(_now()), user_id),
            )
        self.end_user_sessions(user_id, keep_session)
        return ids

    def revoke_everything(self) -> None:
        """Sign every device and browser out, and void every signed URL
        (a new signing key)."""

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    'UPDATE auth_devices SET revoked_at = ? '
                    'WHERE revoked_at IS NULL',
                    (_iso(_now()),),
                )
                conn.execute('DELETE FROM auth_sessions')
            self.signer.rotate()

    def reset(self) -> dict[str, Any]:
        """Recovery (``python main.py auth-reset``): the admin ``admin``
        with the default password, signed out of every browser. Paired
        devices stay paired. The admin, as :meth:`UserStore.get` has it."""

        admin = self.users.reset_admin()
        self.end_user_sessions(int(admin['id']))
        return admin


class UrlSigner:
    """Signs and checks URLs with the key in ``<data>/.auth_secret``.

    *device_active* says whether the device a URL was issued to is still
    paired, so revoking a device voids its URLs at once.
    """

    def __init__(
        self, secret_path: Path, device_active: Callable[[str], bool]
    ) -> None:
        self._path = Path(secret_path)
        self._device_active = device_active
        self._secret = self._load()

    def _load(self) -> bytes:
        try:
            data = self._path.read_bytes()
            if len(data) >= 32:
                return data
        except OSError:
            pass
        return self.rotate()

    def rotate(self) -> bytes:
        """A new key: every URL signed so far stops working."""

        secret = secrets.token_bytes(32)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(
            str(self._path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
        )
        with os.fdopen(fd, 'wb') as handle:
            handle.write(secret)
        self._secret = secret
        return secret

    def _signature(
        self, method: str, path: str, params: list[tuple[str, str]]
    ) -> str:
        canonical = '\n'.join([
            method.upper(),
            path,
            urlencode(sorted(params)),
        ])
        digest = hmac.new(
            self._secret, canonical.encode(), hashlib.sha256
        ).digest()
        return _b64(digest)

    def sign_url(
        self,
        path: str,
        params: Iterable[tuple[str, str]] = (),
        *,
        device_id: str,
        ttl: int = SIGNED_URL_DEFAULT_TTL,
        method: str = 'GET',
    ) -> str:
        """*path* with its query and ``exp``/``kid``/``sig`` added."""

        ttl = max(1, min(int(ttl), SIGNED_URL_MAX_TTL))
        items = [(k, v) for k, v in params if k not in {'exp', 'kid', 'sig'}]
        items += [
            ('exp', str(int(time.time()) + ttl)),
            ('kid', device_id),
        ]
        sig = self._signature(method, path, items)
        return f'{path}?{urlencode([*items, ("sig", sig)])}'

    def verify_signed(
        self, method: str, path: str, query: str
    ) -> Optional[str]:
        """The device id a signed URL was issued to, when its signature,
        expiry and device are all good; else ``None``. Only for reads."""

        if method.upper() not in {'GET', 'HEAD'}:
            return None
        params = parse_qsl(query, keep_blank_values=True)
        values = dict(params)
        sig = values.get('sig', '')
        device_id = values.get('kid', '')
        try:
            expires = int(values.get('exp', ''))
        except ValueError:
            return None
        if not sig or not device_id or expires < time.time():
            return None
        items = [(k, v) for k, v in params if k != 'sig']
        # A HEAD is checked like the GET it stands for.
        expected = self._signature('GET', path, items)
        if not hmac.compare_digest(sig, expected):
            return None
        if not self._device_active(device_id):
            return None
        return device_id


# ── Which routes need what ──────────────────────────────────────────────

_ALL = frozenset({'*'})
_READ = frozenset({'GET', 'HEAD'})


def _m(*methods: str) -> frozenset[str]:
    return frozenset(methods)


#: ``(methods, path regex, scope)``, first match wins. Paths outside the
#: prefixes in :data:`PROTECTED_PREFIXES` are the web app's own files,
#: public so the sign-in page can load; inside them, anything unmatched
#: needs the admin scope.
RULES: list[tuple[frozenset[str], re.Pattern[str], str]] = [
    (r[0], re.compile(r[1]), r[2])
    for r in [
        # Public: an app checks an address, signs in or pairs.
        (_READ, r'^/api/health$', PUBLIC),
        (_READ, r'^/api/version$', PUBLIC),
        (_READ, r'^/api/server/info$', PUBLIC),
        (_READ, r'^/api/auth/status$', PUBLIC),
        (_m('POST'), r'^/api/auth/login$', PUBLIC),
        (_m('POST'), r'^/api/auth/logout$', PUBLIC),
        (_m('POST'), r'^/api/auth/pair$', PUBLIC),
        # Any signed-in user: their own account, devices and pairing
        # (the routes check whose), and a WebSocket ticket.
        (_m('POST'), r'^/api/auth/ws-ticket$', CLIENT),
        (_READ, r'^/api/me$', CLIENT),
        (_ALL, r'^/api/me(/|$)', USER),
        (_ALL, r'^/api/auth/(devices|pairing)(/|$)', USER),
        # Admin: signing everyone out, settings and credentials.
        (_ALL, r'^/api/auth/', ADMIN),
        (_ALL, r'^/api/server$', ADMIN),
        (_ALL, r'^/api/settings', ADMIN),
        (_ALL, r'^/api/cookies$', ADMIN),
        (_ALL, r'^/api/(slskd|navidrome)/test$', ADMIN),
        (_ALL, r'^/api/library/(upgrade|reconcile|archive)', ADMIN),
        (_ALL, r'^/api/library/playlist$', ADMIN),
        (_ALL, r'^/(delete|delete/batch)$', ADMIN),
        (_ALL, r'^/(docs|redoc|openapi\.json)', ADMIN),
        # Client: what a paired app does.
        (_ALL, r'^/api/v1/', CLIENT),
        (_ALL, r'^/api/ws$', CLIENT),
        (
            _READ,
            r'^/(tracks|list|playlists|lyrics|cover|playlist-cover)$',
            CLIENT,
        ),
        (_READ, r'^/(downloads|media)/', CLIENT),
        (_READ, r'^/api/(songs|albums|artists)/search$', CLIENT),
        (_READ, r'^/api/artists/', CLIENT),
        (_m('POST'), r'^/api/artists/(art/bulk|profile/ensure)$', CLIENT),
        (_READ, r'^/api/(song/url|url|url/resolve|preview)$', CLIENT),
        (_m('POST'), r'^/api/download/(url|batch|album)$', CLIENT),
        (_READ, r'^/api/queue$', CLIENT),
        (_READ, r'^/api/playlists/(batches|incomplete)', CLIENT),
        (_READ, r'^/api/likes$', CLIENT),
        (_m('PUT'), r'^/api/likes$', CLIENT),
        (_m('POST'), r'^/api/discover(/collections|/listens)?$', CLIENT),
        (_ALL, r'^/api/discover/blocked$', CLIENT),
        (_READ, r'^/api/podcasts/', CLIENT),
        (
            _m('POST'),
            r'^/api/podcasts/(resolve|episodes/\d+/download)$',
            CLIENT,
        ),
        (_m('PUT'), r'^/api/podcasts/episodes/\d+/playback$', CLIENT),
        (_m('POST'), r'^/api/activity/playback$', CLIENT),
        (_READ, r'^/api/monitor/playlists$', CLIENT),
        (_READ, r'^/api/check_update$', CLIENT),
        # Admin (after the client rules, which carve out exceptions):
        # changes to the library, the queue, watches and profiles.
        (_m('POST', 'PUT', 'DELETE'), r'^/api/artists/(art|profile)', ADMIN),
        (_m('POST'), r'^/api/download/csv$', ADMIN),
        (_m('POST'), r'^/api/playlist/m3u$', ADMIN),
        (_m('POST', 'DELETE'), r'^/api/playlists/', ADMIN),
        (_m('DELETE'), r'^/api/queue', ADMIN),
        (_m('POST'), r'^/api/likes/clear$', ADMIN),
        (_m('DELETE'), r'^/api/discover/listens$', ADMIN),
        (_m('POST', 'PATCH', 'DELETE'), r'^/api/podcasts/', ADMIN),
        (_m('POST', 'PATCH', 'DELETE'), r'^/api/monitor/', ADMIN),
        (_ALL, r'^/api/(users|activity)(/|$)', ADMIN),
    ]
]

#: Where the rules apply; everything else is the web app itself.
PROTECTED_PREFIXES = (
    '/api/',
    '/downloads/',
    '/media/',
    '/tracks',
    '/list',
    '/playlists',
    '/lyrics',
    '/cover',
    '/playlist-cover',
    '/delete',
    '/docs',
    '/redoc',
    '/openapi.json',
)


def classify(method: str, path: str) -> str:
    """The scope *method* on *path* needs: PUBLIC, CLIENT or ADMIN."""

    if not path.startswith(PROTECTED_PREFIXES):
        return PUBLIC
    method = method.upper()
    for methods, pattern, scope in RULES:
        if ('*' in methods or method in methods) and pattern.search(path):
            return scope
    return ADMIN


def rule_for(method: str, path: str) -> Optional[str]:
    """The explicit rule *method* on *path* matches, or ``None`` - for the
    test that keeps every route deliberately classified."""

    method = method.upper()
    for methods, pattern, scope in RULES:
        if ('*' in methods or method in methods) and pattern.search(path):
            return scope
    return None


# ── The middleware ──────────────────────────────────────────────────────

_UNSAFE = frozenset({'POST', 'PUT', 'PATCH', 'DELETE'})

ASGIApp = Callable[..., Awaitable[None]]


def _cookie(scope: MutableMapping[str, Any], name: str) -> str:
    raw = _header(scope, 'cookie')
    if not raw:
        return ''
    jar = SimpleCookie()
    try:
        jar.load(raw)
    except Exception:
        return ''
    morsel = jar.get(name)
    return morsel.value if morsel else ''


def _same_origin(scope: MutableMapping[str, Any], trusted: list[Any]) -> bool:
    """Whether the request's ``Origin`` (or ``Referer``) is this host.
    A request with neither (a non-browser client) passes.
    ``X-Forwarded-Host`` only counts from a trusted proxy."""

    origin = _header(scope, 'origin') or _header(scope, 'referer')
    if not origin:
        return True
    peer = (scope.get('client') or ('', 0))[0] or ''
    forwarded = (
        _header(scope, 'x-forwarded-host')
        if trusted and _in_networks(peer, trusted)
        else ''
    )
    host = forwarded or _header(scope, 'host')
    match = re.match(r'^[a-z][a-z0-9+.-]*://([^/]+)', origin, re.I)
    return bool(match and host and match.group(1).lower() == host.lower())


def identify(
    scope: MutableMapping[str, Any], store: AuthStore, ip: str = ''
) -> tuple[Optional[Principal], bool]:
    """``(principal, bad_token)`` from a request's device token or web
    session cookie - the two credentials any route may be asked with.
    *bad_token* is ``True`` when a device token was sent and isn't good."""

    auth = _header(scope, 'authorization')
    if auth[:7].lower() == 'bearer ':
        device = store.verify_device_token(auth[7:].strip(), ip)
        if device is None:
            return None, True
        return (
            Principal(
                'device',
                CLIENT,
                device['id'],
                device['user_id'],
                device['username'],
                device['role'],
            ),
            False,
        )
    session = _cookie(scope, SESSION_COOKIE)
    user = store.session_user(session) if session else None
    if user is not None:
        return (
            Principal(
                'session',
                ADMIN if user['role'] == ROLE_ADMIN else USER,
                '',
                user['id'],
                user['username'],
                user['role'],
            ),
            False,
        )
    return None, False


def session_cookie(scope: MutableMapping[str, Any]) -> str:
    """The web session cookie a request carries, or ``''``."""

    return _cookie(scope, SESSION_COOKIE)


class AuthMiddleware:
    """Enforces :data:`RULES` for HTTP and WebSocket requests.

    Whoever is recognised - a web session, a device token, a signed URL
    or a WebSocket ticket - is put in ``scope['state']['principal']``
    for the routes that need to know (e.g. the WebSocket, to close a
    revoked device's socket).

    A request that sends a revoked device token is told so (401) even on
    a route anyone may use, so an app learns it was unpaired.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        get_store: Callable[[], Optional[AuthStore]],
        get_tickets: Callable[[], Optional[TicketStore]],
        trusted_proxies: Optional[list[Any]] = None,
    ) -> None:
        self.app = app
        self._get_store = get_store
        self._get_tickets = get_tickets
        self._trusted = (
            trusted_proxies
            if trusted_proxies is not None
            else trusted_proxies_from_env()
        )

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: Callable[..., Awaitable[Any]],
        send: Callable[..., Awaitable[None]],
    ) -> None:
        kind = scope.get('type')
        store = self._get_store()
        if kind not in {'http', 'websocket'} or store is None:
            await self.app(scope, receive, send)
            return
        method = 'WS' if kind == 'websocket' else scope.get('method', 'GET')
        path = scope.get('path', '')
        needed = (
            classify('GET', path)
            if kind == 'websocket'
            else classify(method, path)
        )
        if needed == PUBLIC:
            await self.app(scope, receive, send)
            return

        ip = client_ip(scope, self._trusted)
        principal, bad_token = self._authenticate(scope, store, ip, method)
        scope.setdefault('state', {})['principal'] = principal

        if bad_token:
            await self._deny(scope, send, 401, 'Invalid or revoked token')
            return
        if principal is None:
            await self._deny(scope, send, 401, 'Sign in required')
            return
        if not allows(principal.scope, needed):
            detail = (
                'This needs an admin'
                if principal.kind == 'session'
                else 'This needs a signed-in browser'
            )
            await self._deny(scope, send, 403, detail)
            return
        # A cookie is sent by the browser on its own, to any site that
        # asks: only this site's own pages may use it to change things.
        if (
            principal is not None
            and principal.kind == 'session'
            and (method in _UNSAFE or kind == 'websocket')
            and not _same_origin(scope, self._trusted)
        ):
            await self._deny(scope, send, 403, 'Cross-site request refused')
            return
        await self.app(scope, receive, send)

    def _authenticate(
        self,
        scope: MutableMapping[str, Any],
        store: AuthStore,
        ip: str,
        method: str,
    ) -> tuple[Optional[Principal], bool]:
        """``(principal, bad_token)``: who made the request, and whether
        it sent a device token that's no good."""

        principal, bad_token = identify(scope, store, ip)
        if principal is not None or bad_token:
            return principal, bad_token

        query = (scope.get('query_string') or b'').decode('latin-1')
        if 'sig=' in query and method in {'GET', 'HEAD'}:
            device_id = store.signer.verify_signed(
                method, scope['path'], query
            )
            if device_id:
                return Principal('signed', CLIENT, device_id), False
        if 'ticket=' in query and scope.get('type') == 'websocket':
            tickets = self._get_tickets()
            ticket = dict(parse_qsl(query)).get('ticket', '')
            principal = tickets.claim(ticket) if tickets else None
            if principal is not None and (
                not principal.device_id
                or store.device_active(principal.device_id)
            ):
                return principal, False
        return None, False

    @staticmethod
    async def _deny(
        scope: MutableMapping[str, Any],
        send: Callable[..., Awaitable[None]],
        status: int,
        detail: str,
    ) -> None:
        if scope.get('type') == 'websocket':
            # Before accept(), a close is answered with HTTP 403.
            await send({'type': 'websocket.close', 'code': 4401})
            return
        body = json.dumps({'detail': detail}).encode()
        headers = [
            (b'content-type', b'application/json'),
            (b'content-length', str(len(body)).encode()),
            (b'cache-control', b'no-store'),
        ]
        if status == 401:
            headers.append((b'www-authenticate', b'Bearer realm="Downtify"'))
        await send({
            'type': 'http.response.start',
            'status': status,
            'headers': headers,
        })
        await send({'type': 'http.response.body', 'body': body})
