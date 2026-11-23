"""Per-user storage quotas (issue #677).

Mirrors :class:`downtify.storage_quota.StorageQuotas`.
"""

from __future__ import annotations

from downtify.db.core import Connection

DDL: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS user_storage_quotas (
        user_id BIGINT PRIMARY KEY,
        quota_bytes BIGINT NOT NULL
    )
    """,
]


def up(conn: Connection) -> None:
    for stmt in DDL:
        conn.execute(stmt)
