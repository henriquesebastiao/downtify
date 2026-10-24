"""Which audio provider fetched each library file.

A file carries no mark of where its audio came from - YouTube Music,
YouTube, Soulseek (slskd) or Deemix all end up as a tagged file in the
library - so the playlist page couldn't tell them apart. From now on the
provider is remembered when a download finishes (``Downloader.on_downloaded``
in ``main.py``), by the file's content key (name + size, which survives a
folder move) and its library path (which survives a rewrite in place).
Flows that rewrite or delete a file re-point or drop the row
(``api.rekey_file_owners`` / ``api.drop_file_owners``).

Files downloaded before this was kept have no row; :func:`guess_provider`
still recognises the ones whose path says it - slskd files left in
place (``slskd/...``) and files from extra music folders (``ext/...``).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .library_paths import EXTERNAL_LIBRARY_PREFIX, SLSKD_LIBRARY_PREFIX
from .sqlite_utils import connect_sqlite

#: Not a download at all: a file from an extra music folder.
FOLDER = 'folder'


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_path(path: object) -> str:
    return str(path or '').strip().replace('\\', '/')


def guess_provider(path: object) -> str:
    """The provider a library path gives away, or ``''``."""

    normal = _norm_path(path)
    if normal.startswith(SLSKD_LIBRARY_PREFIX):
        return 'slskd'
    if normal.startswith(EXTERNAL_LIBRARY_PREFIX):
        return FOLDER
    return ''


def _chunked(values: list[str], size: int = 400):
    for index in range(0, len(values), size):
        yield values[index : index + size]


class FileProviders:
    """``content key -> provider`` (plus the path), in the library database."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_providers (
                    content_key TEXT PRIMARY KEY,
                    path TEXT NOT NULL DEFAULT '',
                    provider TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_providers_path
                ON file_providers (path)
            """)

    def record(self, content_key: str, path: str, provider: str) -> None:
        """Remember that *provider* fetched the file (the latest wins: a
        file downloaded again replaced the old one)."""

        key = str(content_key or '').strip()
        name = str(provider or '').strip()
        if not key or not name:
            return
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO file_providers
                   (content_key, path, provider, recorded_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(content_key) DO UPDATE SET
                   path = excluded.path,
                   provider = excluded.provider,
                   recorded_at = excluded.recorded_at""",
                (key, _norm_path(path), name, _now_iso()),
            )

    def lookup(self, keys_by_path: dict[str, str]) -> dict[str, str]:
        """``{path: provider}`` for the library files ``{path: content
        key}`` - by content key, else by path; files nobody recorded are
        left out."""

        wanted = {_norm_path(p): str(k or '') for p, k in keys_by_path.items()}
        wanted.pop('', None)
        if not wanted:
            return {}
        by_key: dict[str, str] = {}
        by_path: dict[str, str] = {}
        keys = sorted({k for k in wanted.values() if k})
        paths = sorted(wanted)
        with self._connect() as conn:
            for chunk in _chunked(keys):
                marks = ','.join('?' * len(chunk))
                for row in conn.execute(
                    'SELECT content_key, provider FROM file_providers '
                    f'WHERE content_key IN ({marks})',
                    chunk,
                ):
                    by_key[row['content_key']] = row['provider']
            for chunk in _chunked(paths):
                marks = ','.join('?' * len(chunk))
                for row in conn.execute(
                    'SELECT path, provider FROM file_providers '
                    f'WHERE path IN ({marks})',
                    chunk,
                ):
                    by_path.setdefault(row['path'], row['provider'])
        found: dict[str, str] = {}
        for path, key in wanted.items():
            provider = by_key.get(key) or by_path.get(path)
            if provider:
                found[path] = provider
        return found

    def rekey(self, old_key: str, new_key: str, stored_path: str = '') -> int:
        """Follow a file rewritten in place (upgrade, replaced audio)."""

        old = str(old_key or '').strip()
        new = str(new_key or '').strip()
        if not old or not new or old == new:
            return 0
        with self._connect() as conn:
            cur = conn.execute(
                'UPDATE OR REPLACE file_providers SET content_key = ?, '
                "path = COALESCE(NULLIF(?, ''), path) WHERE content_key = ?",
                (new, _norm_path(stored_path), old),
            )
            return cur.rowcount

    def drop(self, content_key: str) -> None:
        """Forget a deleted file."""

        key = str(content_key or '').strip()
        if not key:
            return
        with self._connect() as conn:
            conn.execute(
                'DELETE FROM file_providers WHERE content_key = ?', (key,)
            )


def providers_for(
    store: FileProviders | None, keys_by_path: dict[str, str]
) -> dict[str, str]:
    """``{path: provider}`` for every file whose provider is known:
    recorded, else guessed from its path (see :func:`guess_provider`)."""

    recorded = store.lookup(keys_by_path) if store is not None else {}
    found: dict[str, str] = {}
    for path in keys_by_path:
        provider = recorded.get(_norm_path(path)) or guess_provider(path)
        if provider:
            found[path] = provider
    return found
