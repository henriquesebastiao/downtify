"""CPU-only catalog folding, isolated from the web process's Python GIL.

Only plain listing rows cross the process boundary. Database stores and
filesystem mutations remain in the application process. One worker and
one submission at a time bound memory use during download bursts.
"""

from __future__ import annotations

import multiprocessing
import threading
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Optional

_LOCK = threading.Lock()
_WORK = threading.Lock()
_pool: Optional[ProcessPoolExecutor] = None


def start_catalog_worker() -> None:
    """Enable the process worker for a running web application's lifespan."""

    global _pool
    with _LOCK:
        if _pool is None:
            _pool = ProcessPoolExecutor(
                max_workers=1,
                mp_context=multiprocessing.get_context('spawn'),
            )


def stop_catalog_worker() -> None:
    """Release the web pool and restore inline library use; idempotent."""

    global _pool
    with _LOCK:
        pool, _pool = _pool, None
    if pool is not None:
        pool.shutdown(wait=True, cancel_futures=True)


def fold_library_entries(
    entries: list[dict[str, Any]],
    primary_extra_id: str = '',
) -> list[dict[str, Any]]:
    """Fold in the worker, or inline outside a web application's lifespan.

    A failed calculation never publishes a partial snapshot. Let callers
    report the failure and retain their last successfully stored listing.
    """

    from .external_library import finish_library_entries  # noqa: PLC0415  # import cycle

    with _WORK:
        with _LOCK:
            pool = _pool
            future = (
                pool.submit(finish_library_entries, entries, primary_extra_id)
                if primary_extra_id and pool is not None
                else pool.submit(finish_library_entries, entries)
                if pool is not None
                else None
            )
        if future is not None:
            return future.result()
        return (
            finish_library_entries(entries, primary_extra_id)
            if primary_extra_id
            else finish_library_entries(entries)
        )
