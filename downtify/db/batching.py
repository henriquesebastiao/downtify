"""Many small writes, grouped into a few short transactions.

Each ``with store._connect()`` block on its own opens a connection and
commits; on SQLite that also means opening the file and its ``-wal`` and
``-shm`` again. A loop that writes one row at a time pays that per row:
about 50 ms a row on a plain disk, so a start-up pass over tens of
thousands of watch-history rows took most of an hour.

``Database.connect()`` is re-entrant on a thread, so holding one open
around a run of rows makes the store methods inside it share that one
connection and commit once. Nothing else changes: the same statements
run, in the same order, on the same connection a lone call would use.
"""

from __future__ import annotations

import time
from collections.abc import Iterable, Iterator
from typing import TypeVar

from downtify.db.core import Database

T = TypeVar('T')

_END = object()

#: A transaction ends after this many rows ...
BATCH_ROWS = 500
#: ... or after this long, whichever comes first. On SQLite a write
#: transaction keeps other writers waiting (up to the 30 s busy timeout),
#: so a slow disk must not stretch it.
BATCH_SECONDS = 0.5


def in_short_transactions(
    db: Database,
    items: Iterable[T],
    *,
    max_rows: int = BATCH_ROWS,
    max_seconds: float = BATCH_SECONDS,
) -> Iterator[T]:
    """Yield *items* with a connection of *db* held open around them.

    Every *max_rows* items or *max_seconds* the transaction commits and a
    new one starts. On SQLite the write lock is taken at the first write,
    as with a lone store call, and other writers wait for the commit
    (up to the busy timeout).

    An exception raised by the caller's loop body rolls back only the
    rows of the current transaction (earlier ones are already committed)
    and propagates. Stopping the loop early (``break``) also rolls back
    the current transaction, so callers should not.
    """

    iterator = iter(items)
    # Looked up before a transaction opens, so none is ever left empty.
    pending: object = next(iterator, _END)
    while pending is not _END:
        started = time.monotonic()
        count = 0
        with db.connect():
            while pending is not _END:
                yield pending  # type: ignore[misc]
                count += 1
                pending = next(iterator, _END)
                if (
                    count >= max_rows
                    or time.monotonic() - started >= max_seconds
                ):
                    break
