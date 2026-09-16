"""Bundle selected library files into one ZIP download.

The Library page's multi-select can cover hundreds of tracks, and
saving them to the machine in front of the user meant clicking the
download icon once per track. This builds a single ZIP instead.

The archive is streamed as it is built: entries are *stored*, not
deflated (audio files don't compress), and each chunk is handed to the
response as soon as it exists, so a multi-gigabyte selection never
lands in the server's memory or in a temp file. Because the size isn't
known up front, the response has no ``Content-Length`` — browsers show
the download without a progress percentage.

Selections are handed out as short-lived, single-use tickets: the file
list arrives in a POST body (a few hundred paths don't fit in a URL),
and the ticket is what the browser then navigates to so the download
lands in the user's download folder like any other file.
"""

from __future__ import annotations

import secrets
import time
import zipfile
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from loguru import logger

#: Hard cap on one archive request, mirroring the batch-delete cap in
#: ``main.py``: an accidental "select everything" on a huge library
#: shouldn't build a ZIP nobody can use.
MAX_ARCHIVE_FILES = 2000

#: How long a prepared selection stays downloadable. Long enough for a
#: slow browser to follow the redirect, short enough that abandoned
#: tickets don't pile up.
TICKET_TTL_SECONDS = 300

#: Bytes buffered before a chunk is yielded to the response.
_CHUNK_SIZE = 256 * 1024


class _StreamBuffer:
    """Write target for :class:`zipfile.ZipFile` over a stream.

    ``ZipFile`` needs ``write``/``tell``/``flush``; without ``seek`` it
    writes data descriptors instead of rewinding to patch headers,
    which is exactly what a streamed archive needs.
    """

    def __init__(self) -> None:
        self._parts: list[bytes] = []
        self._pending = 0
        self.offset = 0

    def write(self, data: bytes) -> int:
        self._parts.append(bytes(data))
        self._pending += len(data)
        self.offset += len(data)
        return len(data)

    def tell(self) -> int:
        return self.offset

    @staticmethod
    def flush() -> None:
        """No-op: ``ZipFile`` flushes its output; chunks are drained."""

    def has_chunk(self) -> bool:
        return self._pending >= _CHUNK_SIZE

    def drain(self) -> bytes:
        data = b''.join(self._parts)
        self._parts.clear()
        self._pending = 0
        return data


def archive_filename(now: datetime | None = None) -> str:
    """Name for the downloaded ZIP, stamped so repeats don't collide."""

    moment = now or datetime.now(timezone.utc).astimezone()
    return f'downtify-library-{moment.strftime("%Y%m%d-%H%M%S")}.zip'


def _entry_chunks(
    archive: zipfile.ZipFile,
    buffer: _StreamBuffer,
    name: str,
    path: Path,
) -> Iterator[bytes]:
    """Copy one file into the archive, yielding buffered chunks.

    The source is opened before the archive entry, so a file that can't
    be read at all never leaves a stray entry behind.
    """

    with path.open('rb') as source, archive.open(name, mode='w') as target:
        while chunk := source.read(_CHUNK_SIZE):
            target.write(chunk)
            if buffer.has_chunk():
                yield buffer.drain()


def stream_library_zip(
    entries: Iterable[tuple[str, Path]],
) -> Iterator[bytes]:
    """Yield the bytes of a ZIP holding every ``(name, path)`` entry.

    ``name`` is the path the file keeps inside the archive - the
    library path, so per-playlist and artist/album folders survive the
    round trip. Unreadable files are skipped rather than failing the
    whole download, which is already in progress by then.
    """

    buffer = _StreamBuffer()
    written = 0
    with zipfile.ZipFile(
        buffer, mode='w', compression=zipfile.ZIP_STORED, allowZip64=True
    ) as archive:
        for name, path in entries:
            try:
                yield from _entry_chunks(archive, buffer, name, path)
            except (OSError, ValueError):
                logger.opt(exception=True).warning(
                    'Library archive: skipping unreadable file {}', path
                )
                continue
            written += 1
            if buffer.has_chunk():
                yield buffer.drain()
    remainder = buffer.drain()
    if remainder:
        yield remainder
    logger.info('Library archive: streamed {} file(s)', written)


class ArchiveTicketStore:
    """Short-lived, single-use tickets for prepared archive selections."""

    def __init__(self, ttl_seconds: int = TICKET_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._lock = Lock()
        self._tickets: dict[str, tuple[float, list[tuple[str, Path]]]] = {}

    def create(self, entries: list[tuple[str, Path]]) -> str:
        token = secrets.token_urlsafe(16)
        with self._lock:
            self._prune()
            self._tickets[token] = (time.monotonic(), list(entries))
        return token

    def pop(self, token: str) -> list[tuple[str, Path]] | None:
        """Claim a ticket. ``None`` when unknown, already used or expired."""

        with self._lock:
            self._prune()
            found = self._tickets.pop(token, None)
        if found is None:
            return None
        return found[1]

    def _prune(self) -> None:
        cutoff = time.monotonic() - self._ttl
        for token, (created, _) in list(self._tickets.items()):
            if created < cutoff:
                del self._tickets[token]
