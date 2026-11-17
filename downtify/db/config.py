from __future__ import annotations

import enum
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_POSTGRES_PREFIXES = ('postgres://', 'postgresql://')
_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,62}$')


class Dialect(enum.Enum):
    SQLITE = 'sqlite'
    POSTGRES = 'postgres'


# DB group -> SQLite file, relative to the data directory.
GROUP_FILES: dict[str, str] = {
    'library': 'downtify_library.db',
    'monitor': 'downtify_monitor.db',
    'auth': 'downtify_auth.db',
    'activity': 'downtify_activity.db',
    'doctor_hashes': 'doctor/audio_hashes.db',
    'doctor_dupes': 'doctor/duplicates.db',
}


def _parse_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        raise ValueError(f'{name} must be an integer, got {raw.strip()!r}')


def _parse_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw.strip())
    except ValueError:
        raise ValueError(f'{name} must be a number, got {raw.strip()!r}')


@dataclass(frozen=True)
class DbConfig:
    url: str | None = None
    data_dir: Path = Path('/data')
    pool_min: int = 2
    pool_max: int = 20
    pool_timeout: float = 10.0
    #: PostgreSQL schema to use (``DB_SEARCH_PATH``); None keeps the
    #: server default (``public``).
    search_path: str | None = None

    @property
    def dialect(self) -> Dialect:
        return Dialect.POSTGRES if self.url else Dialect.SQLITE

    def sqlite_path(self, group: str) -> Path:
        try:
            filename = GROUP_FILES[group]
        except KeyError:
            raise ValueError(f'unknown DB group: {group!r}') from None
        return self.data_dir / filename

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> DbConfig:
        if env is None:
            env = os.environ

        # Never echo the URL in an error message: it may contain a password.
        url = (env.get('DATABASE_URL') or '').strip() or None
        if url is not None and not url.startswith(_POSTGRES_PREFIXES):
            raise ValueError(
                'DATABASE_URL must start with postgres:// or postgresql://'
            )

        data_dir = Path(env.get('DATABASE_DIR') or '/data')
        pool_min = _parse_int(env, 'DB_POOL_MIN', 2)
        pool_max = _parse_int(env, 'DB_POOL_MAX', 20)
        pool_timeout = _parse_float(env, 'DB_POOL_TIMEOUT', 10.0)

        if pool_min < 0:
            raise ValueError('DB_POOL_MIN must be >= 0')
        if pool_max < 1:
            raise ValueError('DB_POOL_MAX must be >= 1')
        if pool_max < pool_min:
            raise ValueError('DB_POOL_MAX must be >= DB_POOL_MIN')

        search_path = (env.get('DB_SEARCH_PATH') or '').strip() or None
        if search_path is not None and not _IDENTIFIER.match(search_path):
            raise ValueError(
                'DB_SEARCH_PATH must be a plain identifier (letters, digits '
                'and underscores, not starting with a digit)'
            )

        return cls(
            url=url,
            data_dir=data_dir,
            pool_min=pool_min,
            pool_max=pool_max,
            pool_timeout=pool_timeout,
            search_path=search_path,
        )
