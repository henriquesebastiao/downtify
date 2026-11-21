"""Pick the database for one store group at runtime.

``db_target`` reads the environment when it is called: with
``DATABASE_URL`` set it returns one shared PostgreSQL ``Database`` (after
the schema migrations ran once for this process), otherwise the SQLite
file path the group has always used under ``DATABASE_DIR``.
"""

from __future__ import annotations

import threading
from dataclasses import replace
from pathlib import Path

from downtify.db.config import DbConfig, Dialect
from downtify.db.core import Database
from downtify.db.migrations.runner import run_migrations

_LOCK = threading.Lock()
#: Migrations already applied in this process, per (url, search_path).
_MIGRATED: set[tuple[str, str | None]] = set()
#: Databases this process opened; ``shutdown`` closes them.
_OPENED: dict[tuple[str, str | None], Database] = {}


def _key(cfg: DbConfig) -> tuple[str, str | None]:
    assert cfg.url is not None
    return (cfg.url, cfg.search_path)


def db_target(group: str, data_dir: Path | None = None) -> Path | Database:
    """Return where the store for ``group`` keeps its data.

    ``data_dir``, when given, overrides ``DATABASE_DIR`` for SQLite. On
    PostgreSQL the result is a ``Database`` shared by every group.
    """
    cfg = DbConfig.from_env()
    if data_dir is not None:
        cfg = replace(cfg, data_dir=Path(data_dir))
    if cfg.dialect is Dialect.SQLITE:
        return cfg.sqlite_path(group)

    key = _key(cfg)
    with _LOCK:
        db = _OPENED.get(key)
        if db is None:
            db = Database.for_group(cfg, group)
            _OPENED[key] = db
        if key not in _MIGRATED:
            run_migrations(db)
            _MIGRATED.add(key)
    return db


def shutdown() -> None:
    """Close every PostgreSQL pool this process opened."""
    with _LOCK:
        opened = list(_OPENED.values())
        _OPENED.clear()
        _MIGRATED.clear()
    for db in opened:
        db.close()


def healthcheck() -> bool | None:
    """True/False for the PostgreSQL server; None on SQLite."""
    cfg = DbConfig.from_env()
    if cfg.dialect is Dialect.SQLITE:
        return None
    with _LOCK:
        db = _OPENED.get(_key(cfg))
    if db is None:
        db = Database.for_group(cfg, 'library')
        try:
            return db.healthcheck()
        finally:
            db.close()
    return db.healthcheck()
