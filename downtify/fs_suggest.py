"""Directory-name suggestions for Settings path fields."""

from __future__ import annotations

import os
from pathlib import Path

MAX_SUGGESTIONS = 32
_SCAN_CAP = 500
_SKIP_AT_ROOT = frozenset({'proc', 'sys', 'dev'})
_EMPTY_HINTS = ('/data', '/downloads', '/music', '/home')


def suggest_directories(
    prefix: str, *, limit: int = MAX_SUGGESTIONS
) -> list[str]:
    """Absolute directory paths that complete *prefix* as the user types."""

    cap = max(1, min(int(limit), MAX_SUGGESTIONS))
    text = str(prefix or '').strip()
    if not text:
        out: list[str] = []
        for hint in _EMPTY_HINTS:
            path = Path(hint)
            if path.is_dir() and not _blocked(path):
                out.append(str(path))
            if len(out) >= cap:
                break
        return out

    if not text.startswith('/'):
        text = '/' + text.lstrip('/')

    trailing = text.endswith('/')
    raw = Path(text)
    if trailing:
        parent = raw
        name_prefix = ''
    else:
        parent = raw.parent if raw.parent.as_posix() != '.' else Path('/')
        name_prefix = raw.name.lower()

    if _blocked(parent) or not parent.is_dir():
        return []

    matches: list[str] = []
    scanned = 0
    try:
        with os.scandir(parent) as entries:
            for entry in entries:
                scanned += 1
                if scanned > _SCAN_CAP:
                    break
                try:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                except OSError:
                    continue
                if parent == Path('/') and entry.name in _SKIP_AT_ROOT:
                    continue
                if name_prefix and not entry.name.lower().startswith(
                    name_prefix
                ):
                    continue
                child = Path(entry.path)
                if _blocked(child):
                    continue
                matches.append(str(child))
                if len(matches) >= cap:
                    break
    except OSError:
        return []
    matches.sort()
    return matches[:cap]


def _blocked(path: Path) -> bool:
    try:
        parts = path.resolve().parts
    except OSError:
        parts = path.parts
    if len(parts) >= 2 and parts[1] in _SKIP_AT_ROOT:
        return True
    return False
