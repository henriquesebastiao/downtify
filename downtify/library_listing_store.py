"""SQLite snapshot of ``GET /tracks`` / ``GET /playlists`` / path pairs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .library_metadata_cache import META_VERSION
from .sqlite_utils import connect_sqlite

#: Bump when the JSON shape of a snapshot row changes.
LISTING_FORMAT = 1


class LibraryListingStore:
    """Persists a folded library listing so a restart can skip the disk walk."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self):
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS library_listing (
                    cache_key TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    listing_format INTEGER NOT NULL,
                    meta_version INTEGER NOT NULL,
                    paths_json TEXT NOT NULL,
                    playlists_json TEXT NOT NULL,
                    entries_json TEXT NOT NULL
                )
            """)

    def load(self, cache_key: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT fingerprint, listing_format, meta_version,
                       paths_json, playlists_json, entries_json
                FROM library_listing
                WHERE cache_key = ?
                """,
                (cache_key,),
            ).fetchone()
        if row is None:
            return None
        if int(row['listing_format'] or 0) != LISTING_FORMAT:
            return None
        if int(row['meta_version'] or 0) < META_VERSION:
            return None
        try:
            paths = [
                (str(stored), str(resolved))
                for stored, resolved in json.loads(row['paths_json'])
            ]
            playlists = json.loads(row['playlists_json'])
            entries = json.loads(row['entries_json'])
        except (TypeError, ValueError):
            return None
        if not isinstance(playlists, list) or not isinstance(entries, list):
            return None
        return {
            'fingerprint': str(row['fingerprint'] or ''),
            'paths': paths,
            'playlists': playlists,
            'entries': entries,
        }

    def save(
        self,
        cache_key: str,
        fingerprint: str,
        paths: list[tuple[str, str]],
        playlists: list[dict[str, Any]],
        entries: list[dict[str, Any]],
    ) -> None:
        payload = (
            cache_key,
            fingerprint,
            LISTING_FORMAT,
            META_VERSION,
            json.dumps(paths),
            json.dumps(playlists),
            json.dumps(entries),
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO library_listing (
                    cache_key, fingerprint, listing_format, meta_version,
                    paths_json, playlists_json, entries_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    fingerprint = excluded.fingerprint,
                    listing_format = excluded.listing_format,
                    meta_version = excluded.meta_version,
                    paths_json = excluded.paths_json,
                    playlists_json = excluded.playlists_json,
                    entries_json = excluded.entries_json
                """,
                payload,
            )

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute('DELETE FROM library_listing')
