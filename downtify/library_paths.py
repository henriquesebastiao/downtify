"""Paths for files stored outside the main download_dir tree."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

SLSKD_LIBRARY_PREFIX = 'slskd/'


def path_relative_to_anchor(file_path: Path, anchor: Path) -> str:
    """Return a stable path relative to *anchor* (may use ``..`` segments)."""

    file_resolved = file_path.resolve()
    anchor_resolved = anchor.resolve()
    try:
        return file_resolved.relative_to(anchor_resolved).as_posix()
    except ValueError:
        return os.path.relpath(file_resolved, anchor_resolved).replace('\\', '/')


def resolve_stored_path(stored: str, anchor: Path) -> Path:
    """Resolve a stored relative path against *anchor*."""

    return (anchor / stored).resolve()


def library_stored_path(
    file_path: Path,
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
) -> str:
    """Stable library key for API/DB/URLs (no ``..`` segments).

    Files under *download_dir* stay relative to it. Files under *slskd_dir*
    use the virtual prefix ``slskd/`` so clients request
    ``/media/slskd/...`` instead of ``/media/../slskd/...`` (browsers
    normalize the latter away from the media route).
    """

    file_resolved = file_path.resolve()
    anchor_resolved = download_dir.resolve()
    try:
        return file_resolved.relative_to(anchor_resolved).as_posix()
    except ValueError:
        pass
    if slskd_dir is not None:
        slskd_resolved = slskd_dir.resolve()
        try:
            rel = file_resolved.relative_to(slskd_resolved).as_posix()
            return f'{SLSKD_LIBRARY_PREFIX}{rel}'
        except ValueError:
            pass
    return path_relative_to_anchor(file_path, download_dir)


def default_slskd_source_roots(download_dir: Path) -> list[Path]:
    """Common slskd mount locations when settings omit ``source_dir``."""

    roots: list[Path] = []
    env = os.getenv('DOWNTIFY_SLSKD_SOURCE_DIR', '').strip()
    if env:
        roots.append(Path(env))
    for candidate in (Path('/slskd'), download_dir / 'slskd'):
        if candidate not in roots:
            roots.append(candidate)
    return roots


def slskd_dir_from_downloader(downloader: Any) -> Optional[Path]:
    settings = getattr(downloader, 'slskd_settings', {}) or {}
    raw = str(settings.get('source_dir') or '').strip()
    if raw:
        return Path(raw)
    if bool(settings.get('enabled')):
        download_dir = Path(str(settings.get('download_dir') or '/downloads'))
        for candidate in default_slskd_source_roots(download_dir):
            if candidate.is_dir():
                return candidate
    return None


def _slskd_relative(stored: str) -> Optional[str]:
    text = str(stored or '').strip().replace('\\', '/')
    if not text.startswith(SLSKD_LIBRARY_PREFIX):
        return None
    rel = text[len(SLSKD_LIBRARY_PREFIX) :].lstrip('/')
    return rel or None


def resolve_library_stored_path(
    stored: str,
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
) -> Path:
    """Resolve a library stored path to an absolute filesystem path."""

    text = str(stored or '').strip().replace('\\', '/')
    rel = _slskd_relative(text)
    if rel is not None:
        if slskd_dir is not None:
            return (slskd_dir / rel).resolve()
        return (download_dir / 'slskd' / rel).resolve()
    return resolve_stored_path(text, download_dir)


def locate_library_file(
    stored: str,
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Resolve *stored* to an on-disk file, trying external and legacy slskd roots."""

    text = str(stored or '').strip().replace('\\', '/')
    if not text or text.startswith('/'):
        return None

    rel = _slskd_relative(text)
    candidates: list[Path] = []
    if rel is not None:
        if slskd_dir is not None:
            candidates.append((slskd_dir / rel).resolve())
        for root in default_slskd_source_roots(download_dir):
            candidates.append((root / rel).resolve())
        candidates.append((download_dir / 'slskd' / rel).resolve())
    candidates.append(resolve_library_stored_path(text, download_dir, slskd_dir))

    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        try:
            if path.is_file():
                return path
        except OSError:
            continue
    return None
