"""Each catalogued release's date, so an announced one can be shown and
downloaded on its release day.

Mirrors :class:`downtify.artist_catalogue.ArtistCatalogue`.
"""

from __future__ import annotations

from downtify.db.core import Connection

DDL: list[str] = [
    """
    ALTER TABLE artist_catalogue
        ADD COLUMN IF NOT EXISTS release_date TEXT NOT NULL DEFAULT ''
    """,
]


def up(conn: Connection) -> None:
    for stmt in DDL:
        conn.execute(stmt)
