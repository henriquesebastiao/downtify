from __future__ import annotations

from typing import Any

from downtify.db.core import Database


def query(db: Database, sql: str, *params: Any) -> list[Any]:
    """Run ``sql`` with ``?`` placeholders and return all rows."""
    with db.connect() as conn:
        return conn.execute(sql, params).fetchall()


def execute(db: Database, sql: str, *params: Any) -> int:
    """Run ``sql`` with ``?`` placeholders, commit, return the rowcount."""
    with db.connect() as conn:
        rowcount = conn.execute(sql, params).rowcount
        conn.commit()
    return rowcount
