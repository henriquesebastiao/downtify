"""SQLite cache of per-file library display metadata (title/artist/album)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .library_cache_keys import (
    file_content_key,
    file_content_key_from_name_and_size,
)
from .library_metadata import library_entry_for_file
from .library_paths import locate_library_file


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_filename(filename: str) -> str:
    return str(filename or '').strip().replace('\\', '/')


def _file_stat(full_path: Path) -> tuple[int, int]:
    st = full_path.stat()
    return int(st.st_mtime_ns), int(st.st_size)


def _chunked(values: list[str], size: int):
    for index in range(0, len(values), size):
        chunk = values[index : index + size]
        if chunk:
            yield chunk


class LibraryMetadataCache:
    """Caches ``/list`` rows; primary key is basename+size, not full path."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name='library_metadata'"
            ).fetchone()
            if row is None:
                conn.execute("""
                    CREATE TABLE library_metadata (
                        content_key TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        title TEXT NOT NULL DEFAULT '',
                        artist TEXT NOT NULL DEFAULT '',
                        album TEXT NOT NULL DEFAULT '',
                        file_mtime_ns INTEGER NOT NULL,
                        file_size INTEGER NOT NULL,
                        cached_at TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_library_metadata_filename
                    ON library_metadata (filename)
                """)
                return
            if row[0] and 'content_key' in str(row[0]):
                return
            self._migrate_legacy_table(conn)

    @staticmethod
    def _migrate_legacy_table(conn: sqlite3.Connection) -> None:
        conn.execute("""
            CREATE TABLE library_metadata_new (
                content_key TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                artist TEXT NOT NULL DEFAULT '',
                album TEXT NOT NULL DEFAULT '',
                file_mtime_ns INTEGER NOT NULL,
                file_size INTEGER NOT NULL,
                cached_at TEXT NOT NULL
            )
        """)
        rows = conn.execute('SELECT * FROM library_metadata').fetchall()
        for row in rows:
            filename = str(row['filename'])
            file_size = int(row['file_size'])
            ck = file_content_key_from_name_and_size(filename, file_size)
            if not ck:
                continue
            conn.execute(
                """INSERT OR REPLACE INTO library_metadata_new
                   (content_key, filename, title, artist, album,
                    file_mtime_ns, file_size, cached_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ck,
                    filename,
                    str(row['title'] or ''),
                    str(row['artist'] or ''),
                    str(row['album'] or ''),
                    int(row['file_mtime_ns']),
                    file_size,
                    str(row['cached_at']),
                ),
            )
        conn.execute('DROP TABLE library_metadata')
        conn.execute(
            'ALTER TABLE library_metadata_new RENAME TO library_metadata'
        )
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_library_metadata_filename
            ON library_metadata (filename)
        """)

    def get_entry(self, stored_path: str, full_path: Path) -> dict[str, str]:
        """Return a ``/list`` row, reading tags only when cache is missing or stale."""

        rows = self.get_entries_batch([(stored_path, full_path)])
        return rows[0] if rows else library_entry_for_file(stored_path, full_path)

    def get_entries_batch(
        self, items: list[tuple[str, Path]]
    ) -> list[dict[str, str]]:
        """Resolve many ``/list`` rows with one DB connection and batched lookups."""

        if not items:
            return []

        prepared: list[dict[str, Any]] = []
        for stored_path, full_path in items:
            name = _norm_filename(stored_path)
            if not name or not full_path.is_file():
                prepared.append({
                    'stored': stored_path,
                    'full': full_path,
                    'ready': False,
                })
                continue
            try:
                mtime_ns, size = _file_stat(full_path)
            except OSError:
                prepared.append({
                    'stored': stored_path,
                    'full': full_path,
                    'ready': False,
                })
                continue
            ck = file_content_key_from_name_and_size(full_path.name, size)
            prepared.append({
                'stored': stored_path,
                'full': full_path,
                'name': name,
                'ck': ck,
                'mtime_ns': mtime_ns,
                'size': size,
                'ready': True,
            })

        content_keys = [
            str(p['ck']) for p in prepared if p.get('ready') and p.get('ck')
        ]
        filenames = [str(p['name']) for p in prepared if p.get('ready')]

        by_ck: dict[str, sqlite3.Row] = {}
        by_name: dict[str, sqlite3.Row] = {}
        with self._connect() as conn:
            for chunk in _chunked(content_keys, 400):
                placeholders = ','.join('?' * len(chunk))
                query = f"""SELECT content_key, filename, file_mtime_ns, file_size,
                            title, artist, album
                            FROM library_metadata
                            WHERE content_key IN ({placeholders})"""
                for row in conn.execute(query, chunk):
                    by_ck[str(row['content_key'])] = row
            for chunk in _chunked(filenames, 400):
                placeholders = ','.join('?' * len(chunk))
                query = f"""SELECT content_key, filename, file_mtime_ns, file_size,
                            title, artist, album
                            FROM library_metadata
                            WHERE filename IN ({placeholders})"""
                for row in conn.execute(query, chunk):
                    by_name[_norm_filename(str(row['filename']))] = row

            results: list[dict[str, str]] = []
            filename_updates: list[tuple[str, str]] = []

            for item in prepared:
                stored = str(item['stored'])
                full = item['full']
                if not item.get('ready'):
                    results.append(library_entry_for_file(stored, full))
                    continue

                name = str(item['name'])
                mtime_ns = int(item['mtime_ns'])
                size = int(item['size'])
                ck = item.get('ck')

                row = by_ck.get(str(ck)) if ck else None
                if row is None:
                    row = by_name.get(name)
                if row is not None:
                    if (
                        int(row['file_mtime_ns']) == mtime_ns
                        and int(row['file_size']) == size
                    ):
                        if _norm_filename(str(row['filename'])) != name and ck:
                            filename_updates.append((name, str(ck)))
                        results.append({
                            'file': stored,
                            'title': str(row['title'] or ''),
                            'artist': str(row['artist'] or ''),
                            'album': str(row['album'] or ''),
                        })
                        continue

                entry = library_entry_for_file(stored, full)
                results.append(entry)
                self._store_conn(
                    conn, name, ck, entry, mtime_ns, size
                )

            for name, ck in filename_updates:
                conn.execute(
                    'UPDATE library_metadata SET filename = ? WHERE content_key = ?',
                    (name, ck),
                )

        return results

    def refresh(self, stored_path: str, full_path: Path) -> Optional[dict[str, str]]:
        """Re-read tags from disk and update the cache (e.g. after download)."""

        name = _norm_filename(stored_path)
        if not name or not full_path.is_file():
            self.forget(stored_path, full_path=full_path)
            return None
        try:
            mtime_ns, size = _file_stat(full_path)
        except OSError:
            self.forget(stored_path, full_path=full_path)
            return None
        entry = library_entry_for_file(stored_path, full_path)
        self._store(name, full_path, entry, mtime_ns, size)
        return entry

    def refresh_stored_path(
        self,
        stored_path: str,
        *,
        download_dir: Path,
        slskd_dir: Optional[Path] = None,
    ) -> None:
        full = locate_library_file(stored_path, download_dir, slskd_dir)
        if full is not None:
            self.refresh(stored_path, full)

    def forget(
        self,
        filename: str,
        *,
        full_path: Optional[Path] = None,
    ) -> None:
        name = _norm_filename(filename)
        if not name:
            return
        keys: list[str] = []
        if full_path is not None:
            ck = file_content_key(full_path)
            if ck:
                keys.append(ck)
        with self._connect() as conn:
            conn.execute('DELETE FROM library_metadata WHERE filename = ?', (name,))
            for ck in keys:
                conn.execute(
                    'DELETE FROM library_metadata WHERE content_key = ?', (ck,)
                )

    def _fetch_valid(
        self,
        stored_path: str,
        full_path: Path,
        mtime_ns: int,
        size: int,
    ) -> Optional[tuple[int, int, str, str, str]]:
        ck = file_content_key(full_path)
        if ck:
            row = self._fetch_by_content_key(ck)
            if (
                row is not None
                and row[0] == mtime_ns
                and row[1] == size
            ):
                self._touch_filename(ck, stored_path)
                return row
        row = self._fetch_by_filename(stored_path)
        if row is not None and row[0] == mtime_ns and row[1] == size:
            return row
        return None

    def _touch_filename(self, content_key: str, filename: str) -> None:
        name = _norm_filename(filename)
        if not name:
            return
        with self._connect() as conn:
            conn.execute(
                'UPDATE library_metadata SET filename = ? WHERE content_key = ?',
                (name, content_key),
            )

    def _fetch_by_content_key(
        self, content_key: str
    ) -> Optional[tuple[int, int, str, str, str]]:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT file_mtime_ns, file_size, title, artist, album
                   FROM library_metadata WHERE content_key = ?""",
                (content_key,),
            ).fetchone()
        if row is None:
            return None
        return (
            int(row['file_mtime_ns']),
            int(row['file_size']),
            str(row['title'] or ''),
            str(row['artist'] or ''),
            str(row['album'] or ''),
        )

    def _fetch_by_filename(
        self, filename: str
    ) -> Optional[tuple[int, int, str, str, str]]:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT file_mtime_ns, file_size, title, artist, album
                   FROM library_metadata WHERE filename = ?""",
                (filename,),
            ).fetchone()
        if row is None:
            return None
        return (
            int(row['file_mtime_ns']),
            int(row['file_size']),
            str(row['title'] or ''),
            str(row['artist'] or ''),
            str(row['album'] or ''),
        )

    @staticmethod
    def _store_conn(
        conn: sqlite3.Connection,
        filename: str,
        content_key: Optional[str],
        entry: dict[str, str],
        mtime_ns: int,
        file_size: int,
    ) -> None:
        if not content_key:
            return
        name = _norm_filename(filename)
        conn.execute(
            """INSERT INTO library_metadata
               (content_key, filename, title, artist, album,
                file_mtime_ns, file_size, cached_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(content_key) DO UPDATE SET
               filename=excluded.filename,
               title=excluded.title,
               artist=excluded.artist,
               album=excluded.album,
               file_mtime_ns=excluded.file_mtime_ns,
               file_size=excluded.file_size,
               cached_at=excluded.cached_at""",
            (
                content_key,
                name,
                str(entry.get('title') or ''),
                str(entry.get('artist') or ''),
                str(entry.get('album') or ''),
                mtime_ns,
                file_size,
                _now_iso(),
            ),
        )

    def _store(
        self,
        filename: str,
        full_path: Path,
        entry: dict[str, str],
        mtime_ns: int,
        file_size: int,
    ) -> None:
        ck = file_content_key(full_path)
        if not ck:
            return
        with self._connect() as conn:
            self._store_conn(
                conn,
                filename,
                ck,
                entry,
                mtime_ns,
                file_size,
            )
