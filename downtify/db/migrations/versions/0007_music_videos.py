"""Each song's music video (issue #680).

Mirrors :class:`downtify.music_video.MusicVideos`.
"""

from __future__ import annotations

from downtify.db.core import Connection

DDL: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS music_videos (
        file TEXT PRIMARY KEY,
        video TEXT NOT NULL,
        video_id TEXT NOT NULL DEFAULT '',
        added_at TEXT NOT NULL,
        crop TEXT NOT NULL DEFAULT ''
    )
    """,
]


def up(conn: Connection) -> None:
    for stmt in DDL:
        conn.execute(stmt)
