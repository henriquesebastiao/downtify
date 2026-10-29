"""Bounded filesystem worker; run separately with only allowlisted mounts.

For a configuration with ``"worker": "external"``: the server then only
records what to do, and this does it. No HTTP listener, network access,
Docker socket or application startup. The auth database is opened
read-only to recheck administrator rights.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .library_trash import trash_from_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--auth-database', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--skip-id', action='append', default=[])
    options = parser.parse_args()
    if not options.auth_database.is_file() or not options.database.is_file():
        raise SystemExit('required_database_unavailable')
    store = trash_from_config(options.config, options.database)
    if store.worker != 'external':
        # Harmless (one worker at a time), but the server already does it.
        print(
            'note: this configuration runs the worker inside the server; '
            'set "worker": "external" to run it here instead',
            file=sys.stderr,
        )

    def authorized(user_id):
        uri = options.auth_database.resolve().as_uri() + '?mode=ro'
        conn = sqlite3.connect(uri, uri=True)
        try:
            row = conn.execute(
                'SELECT role FROM users WHERE id=?', (user_id,)
            ).fetchone()
            return bool(row and row[0] == 'admin')
        finally:
            conn.close()

    result = store.process(
        limit=max(1, min(options.limit, 20)),
        authorized=authorized,
        skip_ids=frozenset(options.skip_id),
    )
    print(
        json.dumps({
            'processed': len(result),
            'succeeded': sum(row['ok'] for row in result),
            'failed': sum(not row['ok'] for row in result),
        })
    )


if __name__ == '__main__':
    main()
