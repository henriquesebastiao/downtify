"""Discover and apply versioned PostgreSQL migrations.

Each migration is a module named ``NNNN_name`` (four digits, then a lowercase
name) inside the versions package. It defines ``up(conn)``, which receives a
``Connection`` and performs its DDL/DML. ``run_migrations`` applies every
pending migration in one transaction, guarded by a PostgreSQL advisory lock
so concurrent starters queue up instead of racing.

SQLite schemas stay owned by each store's ``_init_db``; this module does
nothing on SQLite.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
from collections.abc import Callable
from dataclasses import dataclass

from downtify.db.config import Dialect
from downtify.db.core import Connection, Database

DEFAULT_PACKAGE = 'downtify.db.migrations.versions'

_MODULE_PATTERN = re.compile(r'^(\d{4})_[a-z0-9_]+$')
_LOCK_SQL = "select pg_advisory_xact_lock(hashtext('downtify_migrations'))"
_CREATE_TABLE_SQL = """
create table if not exists schema_migrations (
    version integer primary key,
    name text not null,
    applied_at timestamptz not null default now()
)
"""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    up: Callable[[Connection], None]


def discover(package: str = DEFAULT_PACKAGE) -> list[Migration]:
    """Import the migration modules in ``package``, sorted by version."""
    pkg = importlib.import_module(package)
    found: list[Migration] = []
    seen: dict[int, str] = {}
    for info in pkgutil.iter_modules(pkg.__path__):
        match = _MODULE_PATTERN.match(info.name)
        if match is None:
            continue
        module_name = f'{package}.{info.name}'
        module = importlib.import_module(module_name)
        up = getattr(module, 'up', None)
        if not callable(up):
            raise RuntimeError(f'migration {module_name} has no up(conn)')
        version = int(match.group(1))
        if version in seen:
            raise RuntimeError(
                f'duplicate migration version {version:04d}: '
                f'{seen[version]} and {info.name}'
            )
        seen[version] = info.name
        found.append(Migration(version=version, name=info.name, up=up))
    found.sort(key=lambda migration: migration.version)
    return found


def _applied(conn: Connection) -> list[int]:
    exists = conn.execute(
        "select to_regclass('schema_migrations') is not null"
    ).fetchone()[0]
    if not exists:
        return []
    rows = conn.execute(
        'select version from schema_migrations order by version'
    ).fetchall()
    return [row[0] for row in rows]


def applied_versions(db: Database) -> list[int]:
    """Versions recorded in ``schema_migrations``; empty if none or SQLite."""
    if db.dialect is Dialect.SQLITE:
        return []
    with db.connect() as conn:
        return _applied(conn)


def run_migrations(db: Database, package: str = DEFAULT_PACKAGE) -> list[int]:
    """Apply pending migrations; return the versions applied by this call.

    All pending migrations run in one transaction. Any failure rolls the
    whole run back, so nothing is partially applied or recorded.
    """
    if db.dialect is Dialect.SQLITE:
        return []
    migrations = discover(package)
    applied: list[int] = []
    with db.transaction() as conn:
        conn.execute(_LOCK_SQL)
        conn.execute(_CREATE_TABLE_SQL)
        done = set(_applied(conn))
        for migration in migrations:
            if migration.version in done:
                continue
            migration.up(conn)
            conn.execute(
                'insert into schema_migrations (version, name) values (?, ?)',
                (migration.version, migration.name),
            )
            applied.append(migration.version)
    return applied
