"""Postgres DDL for the Doctor's audio-hash cache and kept-apart pairs.

Mirrors :class:`downtify.doctor_audio.AudioHashCache` and
:class:`downtify.duplicate_merge.KeptApart`.
"""

from __future__ import annotations

DDL: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS audio_hashes (
        path TEXT PRIMARY KEY,
        size BIGINT NOT NULL,
        mtime_ns BIGINT NOT NULL,
        digest TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS kept_apart (
        a TEXT NOT NULL,
        b TEXT NOT NULL,
        kept_at TEXT NOT NULL,
        PRIMARY KEY (a, b)
    )
    """,
]
