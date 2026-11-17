"""Baseline schema: every table, index and sequence as of migration 0001."""

from __future__ import annotations

from downtify.db.core import Connection
from downtify.db.migrations.schema import (
    activity,
    auth,
    doctor,
    library_a,
    library_b,
    monitor,
)


def up(conn: Connection) -> None:
    statements = (
        auth.DDL
        + activity.DDL
        + doctor.DDL
        + monitor.DDL
        + library_a.DDL
        + library_b.DDL
    )
    for stmt in statements:
        conn.execute(stmt)
