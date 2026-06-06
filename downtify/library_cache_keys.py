"""Stable cache keys for library files (survive path / folder changes)."""

from __future__ import annotations

import hashlib
from pathlib import Path


def file_content_key(full_path: Path) -> str | None:
    """Hash of basename + file size — same identity after a folder move."""

    if not full_path.is_file():
        return None
    try:
        size = int(full_path.stat().st_size)
    except OSError:
        return None
    base = full_path.name.casefold()
    if not base:
        return None
    payload = f'{base}:{size}'.encode()
    return hashlib.sha256(payload).hexdigest()


def file_content_key_from_name_and_size(
    name: str, file_size: int
) -> str | None:
    """Rebuild the content key when only basename and size are known."""

    base = Path(str(name or '').replace('\\', '/')).name.casefold()
    if not base or file_size < 0:
        return None
    return hashlib.sha256(f'{base}:{int(file_size)}'.encode()).hexdigest()
