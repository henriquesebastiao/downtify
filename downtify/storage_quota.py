"""How much each account may download: per-user storage quotas.

On a shared server one account can otherwise fill the disk. An admin
sets a **default quota** that every user (role ``user``) follows, and
can give a user **their own** quota or make them **unlimited**. Admins
are never limited - they manage the server, and its disk.

What counts against a quota is the size on disk of the library files an
account downloaded (:mod:`downtify.track_owners`), as they are after
conversion and tagging - measured from the library listing, so it is
what is really there. A file two accounts downloaded counts for both
(each would have needed it). Deleting one's own downloads frees space;
an admin can also *reset* an account's usage, which forgets what it
downloaded without deleting any file.

A quota can't know a song's size before it is downloaded, so it is
enforced when a download is asked for and again when it starts: once an
account has no space left, its downloads are refused with a message
saying so. A download that started with space left still finishes, so
usage can go past the quota by up to one song per parallel download.

Stored in ``downtify_library.db`` (``user_storage_quotas``): one row per
account with a quota of its own (:data:`UNLIMITED` for none), plus the
default under the reserved user id :data:`DEFAULT_ROW` (no row = no
default, everyone unlimited).
"""

from __future__ import annotations

import threading
from collections.abc import Collection, Mapping
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Optional

from .db.config import Dialect
from .db.core import Connection, Database, as_database

#: A stored quota meaning "no limit".
UNLIMITED = -1
#: The row holding the default quota (no account has id 0).
DEFAULT_ROW = 0
#: Largest quota accepted (1 PiB); anything bigger is a typo.
MAX_QUOTA = 1024**5

#: Where an account's quota comes from.
SOURCE_ADMIN = 'admin'
SOURCE_USER = 'user'
SOURCE_DEFAULT = 'default'

#: HTTP status of a download refused for lack of space.
QUOTA_STATUS_CODE = 507

_UNITS = ('B', 'KB', 'MB', 'GB', 'TB', 'PB')


class QuotaError(ValueError):
    """A quota value that can't be stored; the message says why."""


class QuotaExceededError(Exception):
    """A download refused because its account has no space left."""


def format_bytes(value: int) -> str:
    """``1.5 GB`` - the same binary units the web app shows."""

    size = float(max(0, int(value or 0)))
    unit = 0
    while size >= 1024 and unit < len(_UNITS) - 1:
        size /= 1024
        unit += 1
    digits = 0 if unit == 0 or size >= 100 else 1
    return f'{size:.{digits}f} {_UNITS[unit]}'


def clean_quota(value: Any) -> Optional[int]:
    """*value* as a stored quota: ``None`` (none set), :data:`UNLIMITED`
    or a positive number of bytes - or :class:`QuotaError`."""

    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        raise QuotaError('A quota is a number of bytes')
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise QuotaError('A quota is a number of bytes') from exc
    if number == UNLIMITED:
        return UNLIMITED
    if number <= 0:
        raise QuotaError('A quota must be more than 0 bytes')
    if number > MAX_QUOTA:
        raise QuotaError('That quota is too large')
    return number


def effective_quota(
    is_admin: bool, own: Optional[int], default: Optional[int]
) -> tuple[Optional[int], str]:
    """``(limit, source)`` for one account: ``limit`` is ``None`` when
    it is unlimited; ``source`` is :data:`SOURCE_ADMIN`,
    :data:`SOURCE_USER` (its own) or :data:`SOURCE_DEFAULT`."""

    if is_admin:
        return None, SOURCE_ADMIN
    if own is not None:
        return (None if own == UNLIMITED else own), SOURCE_USER
    if default is None or default == UNLIMITED:
        return None, SOURCE_DEFAULT
    return default, SOURCE_DEFAULT


def used_bytes(owned: Collection[str], sizes: Mapping[str, int]) -> int:
    """Size of the files in *owned* (content keys) still in the library
    (*sizes*: content key -> bytes)."""

    return sum(int(sizes[key]) for key in owned if key in sizes)


def quota_status(
    used: int,
    limit: Optional[int],
    source: str,
    own: Optional[int] = None,
) -> dict[str, Any]:
    """What ``GET /api/me/storage`` answers for one account.

    ``{used, limit, remaining, unlimited, exceeded, source, own}`` -
    ``limit`` / ``remaining`` are ``None`` when unlimited, ``own`` is
    the account's own setting (``None`` = follows the default, ``-1`` =
    unlimited).
    """

    used = max(0, int(used or 0))
    unlimited = limit is None
    return {
        'used': used,
        'limit': None if unlimited else int(limit),
        'remaining': None if unlimited else max(0, int(limit) - used),
        'unlimited': unlimited,
        'exceeded': (not unlimited) and used >= int(limit),
        'source': source,
        'own': own,
    }


def exceeded_message(status: Mapping[str, Any]) -> str:
    """Why a download was refused, with the space used and left."""

    return (
        'Storage quota reached: '
        f'{format_bytes(status.get("used") or 0)} of '
        f'{format_bytes(status.get("limit") or 0)} used, '
        f'{format_bytes(status.get("remaining") or 0)} left. '
        'Delete some of your downloads or ask an admin for more space.'
    )


class StorageQuotas:
    """``user_storage_quotas`` rows: each account's own quota and the
    default (:data:`DEFAULT_ROW`)."""

    def __init__(self, path_or_db: str | Path | Database) -> None:
        self.db = as_database(path_or_db, 'library')
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> AbstractContextManager[Connection]:
        return self.db.connect()

    def _init_db(self) -> None:
        # PostgreSQL gets its schema from the migrations.
        if self.db.dialect is not Dialect.SQLITE:
            return
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_storage_quotas (
                    user_id INTEGER PRIMARY KEY,
                    quota_bytes INTEGER NOT NULL
                )
            """)

    def _read(self, user_id: int) -> Optional[int]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT quota_bytes FROM user_storage_quotas '
                'WHERE user_id = ?',
                (int(user_id),),
            ).fetchone()
        return None if row is None else int(row['quota_bytes'])

    def _write(self, user_id: int, value: Any) -> Optional[int]:
        quota = clean_quota(value)
        with self._lock, self._connect() as conn:
            if quota is None:
                conn.execute(
                    'DELETE FROM user_storage_quotas WHERE user_id = ?',
                    (int(user_id),),
                )
            else:
                conn.execute(
                    """INSERT INTO user_storage_quotas
                       (user_id, quota_bytes) VALUES (?, ?)
                       ON CONFLICT(user_id) DO UPDATE
                       SET quota_bytes = excluded.quota_bytes""",
                    (int(user_id), quota),
                )
        return quota

    def default(self) -> Optional[int]:
        """The default quota in bytes; ``None`` when there is none."""

        value = self._read(DEFAULT_ROW)
        return None if value in {None, UNLIMITED} else value

    def set_default(self, value: Any) -> Optional[int]:
        """Set (bytes) or clear (``None`` / :data:`UNLIMITED`) the
        default; returns what is stored."""

        quota = clean_quota(value)
        return self._write(DEFAULT_ROW, None if quota == UNLIMITED else quota)

    def get(self, user_id: int) -> Optional[int]:
        """*user_id*'s own quota: bytes, :data:`UNLIMITED`, or ``None``
        when they follow the default."""

        if not user_id:
            return None
        return self._read(user_id)

    def set(self, user_id: int, value: Any) -> Optional[int]:
        """Give *user_id* a quota of their own (bytes or
        :data:`UNLIMITED`), or ``None`` to follow the default again."""

        if not user_id or int(user_id) == DEFAULT_ROW:
            raise QuotaError('Unknown account')
        return self._write(user_id, value)

    def any_set(self) -> bool:
        """Whether any account can be limited at all: a default, or a
        quota of someone's own (an unlimited one doesn't count)."""

        with self._connect() as conn:
            row = conn.execute(
                'SELECT 1 FROM user_storage_quotas WHERE quota_bytes > 0 '
                'LIMIT 1'
            ).fetchone()
        return row is not None

    def all(self) -> dict[int, int]:
        """Every account's own quota (the default row left out)."""

        with self._connect() as conn:
            rows = conn.execute(
                'SELECT user_id, quota_bytes FROM user_storage_quotas '
                'WHERE user_id != ?',
                (DEFAULT_ROW,),
            ).fetchall()
        return {int(row['user_id']): int(row['quota_bytes']) for row in rows}

    def remove_user(self, user_id: int) -> None:
        """Forget a deleted account's quota."""

        if not user_id:
            return
        with self._lock, self._connect() as conn:
            conn.execute(
                'DELETE FROM user_storage_quotas WHERE user_id = ?',
                (int(user_id),),
            )
