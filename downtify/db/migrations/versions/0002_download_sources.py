"""Each file's upload and the uploads rejected per song (issue #582).

Mirrors :class:`downtify.download_sources.DownloadSources`.
"""

from __future__ import annotations

from downtify.db.core import Connection

DDL: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS file_download_sources (
        file TEXT PRIMARY KEY,
        source TEXT NOT NULL DEFAULT '',
        track_keys TEXT NOT NULL DEFAULT '[]',
        signature TEXT NOT NULL DEFAULT '',
        recorded_at DOUBLE PRECISION NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rejected_sources (
        track_key TEXT NOT NULL,
        source TEXT NOT NULL,
        rejected_at DOUBLE PRECISION NOT NULL,
        PRIMARY KEY (track_key, source)
    )
    """,
]


def up(conn: Connection) -> None:
    for stmt in DDL:
        conn.execute(stmt)
