"""Bounded, asynchronous resolution of mobile track-id batches."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from typing import Any

from fastapi import HTTPException

from .manual_playlists import MAX_TRACKS_PER_EDIT


async def resolve_mobile_track_ids(
    sync: Any,
    raw_ids: Sequence[Any],
    request: Any,
    *,
    refresh: Callable[[], Any],
    filter_paths: Callable[[list[str], Any], list[str]],
    max_items: int = MAX_TRACKS_PER_EDIT,
) -> list[str]:
    """Resolve ids to paths, preserving the input order and duplicates.

    Validation and the combined-reference limit must be checked before this
    function is called by request handlers. This function also checks both so
    it can safely be used directly. SQLite and visibility work run off-loop.
    """

    if len(raw_ids) > max_items:
        raise HTTPException(
            status_code=400, detail='Too many track references'
        )
    normalized: list[str] = []
    for value in raw_ids:
        if not isinstance(value, str) or not value.strip():
            raise HTTPException(
                status_code=400, detail='track_ids must be strings'
            )
        normalized.append(value.strip())

    unique = list(dict.fromkeys(normalized))
    if not unique:
        return []

    async def lookup() -> dict[str, dict[str, Any]]:
        # Keep chunks bounded even when the request uses the full allowance.
        merged: dict[str, dict[str, Any]] = {}
        for start in range(0, len(unique), 400):
            merged.update(
                await asyncio.to_thread(
                    sync.rows_for, unique[start : start + 400]
                )
            )
        return merged

    rows = await lookup()
    if len(rows) != len(unique):
        await asyncio.to_thread(refresh)
        rows = await lookup()
    if len(rows) != len(unique):
        raise HTTPException(status_code=404, detail='Track not found')

    paths = [str(rows[track_id].get('file') or '') for track_id in unique]
    visible = await asyncio.to_thread(filter_paths, paths, request)
    visible_set = set(visible)
    if any(not path or path not in visible_set for path in paths):
        raise HTTPException(status_code=404, detail='Track not found')
    by_id = dict(zip(unique, paths))
    return [by_id[track_id] for track_id in normalized]
