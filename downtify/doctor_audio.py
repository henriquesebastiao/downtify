"""Audio-only fingerprints, so two files can be proven to hold the same
recording even when their tags and embedded artwork differ.

Downtify rewrites the tags and the cover of every file it imports from
slskd, so the library copy and the transfer slskd left behind never have
the same bytes. Their *audio* is untouched, though: slskd files are not
transcoded. :func:`audio_md5` asks ``ffmpeg`` to copy the first audio
stream's packets - no decoding - into its ``md5`` muxer, which hashes
exactly the encoded audio and nothing else. Two files with the same
digest carry bit-identical audio, whatever their tags say.

Hashing reads the whole file, so digests are kept in a small SQLite
cache keyed by path, size and modification time (:class:`AudioHashCache`).
"""

from __future__ import annotations

import sqlite3
import subprocess
import threading
from pathlib import Path
from typing import Optional

from loguru import logger

#: Seconds one file may take; a 200 MB FLAC on a slow disk stays well
#: inside it.
HASH_TIMEOUT = 300

_MD5_PREFIX = 'MD5='


def audio_md5(path: Path, *, ffmpeg: str = 'ffmpeg') -> Optional[str]:
    """MD5 of the encoded packets of *path*'s first audio stream.

    ``None`` when ffmpeg can't read the file (not audio, truncated,
    missing) - never a guess.
    """

    command = [
        ffmpeg,
        '-v',
        'error',
        '-nostdin',
        '-i',
        str(path),
        '-map',
        '0:a:0',
        '-c:a',
        'copy',
        '-f',
        'md5',
        '-',
    ]
    try:
        done = subprocess.run(  # noqa: S603 - fixed argv, no shell
            command,
            capture_output=True,
            text=True,
            timeout=HASH_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.info('doctor: could not hash {}: {}', path, exc)
        return None
    if done.returncode != 0:
        logger.info(
            'doctor: ffmpeg could not read {}: {}',
            path,
            (done.stderr or '').strip()[:200],
        )
        return None
    for raw in (done.stdout or '').splitlines():
        line = raw.strip()
        if line.startswith(_MD5_PREFIX):
            digest = line[len(_MD5_PREFIX) :].strip().lower()
            if len(digest) == 32:
                return digest
    return None


class AudioHashCache:
    """``audio_md5`` results, reused while a file's size and mtime hold."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audio_hashes (
                    path TEXT PRIMARY KEY,
                    size INTEGER NOT NULL,
                    mtime_ns INTEGER NOT NULL,
                    digest TEXT NOT NULL
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=30)

    def digest(self, path: Path) -> Optional[str]:
        """The audio digest of *path*, from the cache when still valid."""

        try:
            stat = path.stat()
        except OSError:
            return None
        key = str(path)
        with self._lock, self._connect() as conn:
            row = conn.execute(
                'SELECT size, mtime_ns, digest FROM audio_hashes '
                'WHERE path = ?',
                (key,),
            ).fetchone()
        if row and row[0] == stat.st_size and row[1] == stat.st_mtime_ns:
            return str(row[2])
        digest = audio_md5(path)
        if digest is None:
            return None
        with self._lock, self._connect() as conn:
            conn.execute(
                'INSERT OR REPLACE INTO audio_hashes '
                '(path, size, mtime_ns, digest) VALUES (?, ?, ?, ?)',
                (key, stat.st_size, stat.st_mtime_ns, digest),
            )
        return digest

    def forget(self, paths: list[str]) -> None:
        if not paths:
            return
        with self._lock, self._connect() as conn:
            conn.executemany(
                'DELETE FROM audio_hashes WHERE path = ?',
                [(p,) for p in paths],
            )
