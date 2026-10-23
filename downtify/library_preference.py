"""A non-destructive listing preference for one external source."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from typing import Any


def _key(value: Any) -> str:
    text = unicodedata.normalize('NFKD', str(value or '').casefold())
    return re.sub(
        r'[^\w]+', '', ''.join(c for c in text if not unicodedata.combining(c))
    )


def _release(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _key(entry.get('artist')),
        _key(entry.get('title')),
        _key(entry.get('album')),
    )


def prefer_entries(
    entries: list[dict[str, Any]],
    folder_id: str,
    fold: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Prefer full recording/release metadata, without mutating input rows.

    Do not use an old clip's duration to override an explicit preference.
    Unknown artist/title/album and distinct versions remain separate.
    """
    prefix = f'ext/{folder_id}/'
    chosen = [
        dict(e) for e in entries if str(e.get('file', '')).startswith(prefix)
    ]
    if not chosen:
        return fold(entries)
    others = [
        e for e in entries if not str(e.get('file', '')).startswith(prefix)
    ]
    by_release = {_release(e): e for e in chosen if all(_release(e))}
    kept = []
    for row in fold(others):
        preferred = by_release.get(_release(row))
        if preferred is None:
            kept.append(row)
            continue
        playlists = list(preferred.get('playlists') or [])
        for playlist in row.get('playlists') or []:
            if playlist not in playlists:
                playlists.append(playlist)
        if playlists:
            preferred['playlists'] = playlists
    return chosen + kept
