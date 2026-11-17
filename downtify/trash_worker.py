"""Bounded filesystem worker; run separately with only allowlisted mounts.

For a configuration with ``"worker": "external"``: the server then only
records what to do, and this does it. No HTTP listener, network access,
Docker socket or application startup. The auth database is opened
read-only to recheck administrator rights.

SQLite (default): ``--database`` and ``--auth-database`` are required
files. The auth database is opened with a read-only SQLite URI.

PostgreSQL: when the ``DATABASE_URL`` environment variable is set,
``--database`` and ``--auth-database`` are optional and ignored; the
library and auth stores come from ``--data-dir`` (default ``DATABASE_DIR``
or ``/data``) via ``downtify.db.runtime``. The admin recheck runs in a
read-only transaction.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Callable

from downtify.db import runtime
from downtify.db.config import Dialect
from downtify.db.core import Database

from .library_trash import trash_from_config


def make_authorizer(
    auth_target: Path | str | Database,
) -> Callable[[Any], bool]:
    """Return ``authorized(user_id) -> bool`` for the admin recheck.

    A file path (or a SQLite ``Database``) is read through a read-only
    SQLite URI. A PostgreSQL ``Database`` is read inside a transaction
    set to READ ONLY. The connection must not already be inside a
    transaction on this thread (``SET TRANSACTION`` runs first).
    """
    if isinstance(auth_target, Database):
        if auth_target.dialect is Dialect.POSTGRES:
            return _postgres_authorizer(auth_target)
        auth_path = auth_target.path
        assert auth_path is not None
    else:
        auth_path = Path(auth_target)
    return _sqlite_authorizer(auth_path)


def _sqlite_authorizer(auth_path: Path) -> Callable[[Any], bool]:
    def authorized(user_id):
        uri = auth_path.resolve().as_uri() + '?mode=ro'
        conn = sqlite3.connect(uri, uri=True)
        try:
            row = conn.execute(
                'SELECT role FROM users WHERE id=?', (user_id,)
            ).fetchone()
            return bool(row and row[0] == 'admin')
        finally:
            conn.close()

    return authorized


def _postgres_authorizer(db: Database) -> Callable[[Any], bool]:
    def authorized(user_id):
        with db.connect() as conn:
            conn.execute('SET TRANSACTION READ ONLY')
            row = conn.execute(
                'SELECT role FROM users WHERE id=?', (user_id,)
            ).fetchone()
        return bool(row and row[0] == 'admin')

    return authorized


def _database_url_set() -> bool:
    return bool((os.environ.get('DATABASE_URL') or '').strip())


def main():
    parser = argparse.ArgumentParser(
        epilog=(
            'With DATABASE_URL set (PostgreSQL), --database and '
            '--auth-database are optional and ignored; --data-dir is only '
            'used for the database group locations.'
        )
    )
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument(
        '--database',
        type=Path,
        help='SQLite library file (ignored when DATABASE_URL is set)',
    )
    parser.add_argument(
        '--auth-database',
        type=Path,
        help='SQLite auth file, opened read-only (ignored when '
        'DATABASE_URL is set)',
    )
    parser.add_argument(
        '--data-dir',
        type=Path,
        default=None,
        help='directory for database groups; default DATABASE_DIR or /data',
    )
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--skip-id', action='append', default=[])
    options = parser.parse_args()
    if not _database_url_set() and (
        options.database is None or options.auth_database is None
    ):
        parser.error(
            'the following arguments are required: --database, --auth-database'
        )
    try:
        if _database_url_set():
            result = _run_postgres(options)
        else:
            result = _run_sqlite(options)
    finally:
        runtime.shutdown()
    print(json.dumps(result))


def _run_sqlite(options) -> dict:
    if not options.auth_database.is_file() or not options.database.is_file():
        raise SystemExit('required_database_unavailable')
    store = trash_from_config(options.config, options.database)
    _note_if_embedded(store)
    authorized = make_authorizer(options.auth_database)
    rows = store.process(
        limit=_limit(options.limit),
        authorized=authorized,
        skip_ids=frozenset(options.skip_id),
    )
    return _summary(rows)


def _run_postgres(options) -> dict:
    data_dir = options.data_dir
    if data_dir is None:
        data_dir = Path(os.environ.get('DATABASE_DIR') or '/data')
    library = runtime.db_target('library', data_dir)
    auth = runtime.db_target('auth', data_dir)
    store = trash_from_config(options.config, library)
    _note_if_embedded(store)
    rows = store.process(
        limit=_limit(options.limit),
        authorized=make_authorizer(auth),
        skip_ids=frozenset(options.skip_id),
    )
    return _summary(rows)


def _limit(value: int) -> int:
    return max(1, min(value, 20))


def _summary(result: list[dict]) -> dict:
    return {
        'processed': len(result),
        'succeeded': sum(row['ok'] for row in result),
        'failed': sum(not row['ok'] for row in result),
    }


def _note_if_embedded(store) -> None:
    if store.worker != 'external':
        # Harmless (one worker at a time), but the server already does it.
        print(
            'note: this configuration runs the worker inside the server; '
            'set "worker": "external" to run it here instead',
            file=sys.stderr,
        )


if __name__ == '__main__':
    main()
