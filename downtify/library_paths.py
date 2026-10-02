"""Paths for files stored outside the main download_dir tree."""

from __future__ import annotations

import functools
import hashlib
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

SLSKD_LIBRARY_PREFIX = 'slskd/'
EXTERNAL_LIBRARY_PREFIX = 'ext/'


def path_relative_to_anchor(file_path: Path, anchor: Path) -> str:
    """Return a stable path relative to *anchor* (may use ``..`` segments)."""

    file_resolved = file_path.resolve()
    anchor_resolved = anchor.resolve()
    try:
        return file_resolved.relative_to(anchor_resolved).as_posix()
    except ValueError:
        return os.path.relpath(file_resolved, anchor_resolved).replace(
            '\\', '/'
        )


def resolve_stored_path(stored: str, anchor: Path) -> Path:
    """Resolve a stored relative path against *anchor*."""

    return (anchor / stored).resolve()


@functools.lru_cache(maxsize=256)
def extra_dir_id(root: Path) -> str:
    """Stable id for an extra library folder (path hash, not the index)."""

    try:
        key = str(root.resolve())
    except OSError:
        key = str(root)
    return hashlib.sha1(key.encode('utf-8')).hexdigest()[:12]


def extra_dir_lookup(
    extra_dirs: Optional[Sequence[Path]],
) -> dict[str, Path]:
    """``folder_id → root`` for the current extra-folder settings."""

    return {extra_dir_id(root): root for root in extra_dirs or ()}


@dataclass(frozen=True)
class ResolvedLibraryRoots:
    """Resolved download / slskd / extra roots, built once per listing."""

    download: Path
    slskd: Optional[Path]
    extras: tuple[tuple[Path, str], ...]

    @classmethod
    def from_dirs(
        cls,
        download_dir: Path,
        slskd_dir: Optional[Path] = None,
        extra_dirs: Optional[Sequence[Path]] = None,
    ) -> ResolvedLibraryRoots:
        try:
            download = download_dir.resolve()
        except OSError:
            download = Path(download_dir)
        slskd: Optional[Path] = None
        if slskd_dir is not None:
            try:
                slskd = slskd_dir.resolve()
            except OSError:
                slskd = Path(slskd_dir)
        extras: list[tuple[Path, str]] = []
        for root in extra_dirs or ():
            try:
                resolved = root.resolve()
            except OSError:
                resolved = Path(root)
            extras.append((resolved, extra_dir_id(root)))
        return cls(download=download, slskd=slskd, extras=tuple(extras))

    def stored_for(self, file_resolved: Path) -> str:
        """Library key for an already-resolved audio path."""

        try:
            return file_resolved.relative_to(self.download).as_posix()
        except ValueError:
            pass
        if self.slskd is not None:
            try:
                rel = file_resolved.relative_to(self.slskd).as_posix()
                return f'{SLSKD_LIBRARY_PREFIX}{rel}'
            except ValueError:
                pass
        for extra_root, folder_id in self.extras:
            try:
                rel = file_resolved.relative_to(extra_root).as_posix()
            except ValueError:
                continue
            return f'{EXTERNAL_LIBRARY_PREFIX}{folder_id}/{rel}'
        return path_relative_to_anchor(file_resolved, self.download)


def extra_library_relative(stored: str) -> Optional[tuple[str, str]]:
    """``(folder_id, relative_path)`` for ``ext/<id>/...`` keys, else
    ``None``.
    """

    text = str(stored or '').strip().replace('\\', '/')
    if not text.startswith(EXTERNAL_LIBRARY_PREFIX):
        return None
    rest = text[len(EXTERNAL_LIBRARY_PREFIX) :].lstrip('/')
    folder_id, sep, rel = rest.partition('/')
    if not folder_id or not sep or not rel:
        return None
    return folder_id, rel


def library_file_root(
    stored: str,
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
    extra_dirs: Optional[Sequence[Path]] = None,
) -> tuple[Path, str]:
    """``(tree root, path relative to it)`` for a library stored key.

    Extra folders (``ext/<id>/...``) and slskd (``slskd/...``) live
    outside *download_dir*; deletes and leftover pruning must stop at
    that tree, not treat the key as a file under ``/downloads``.
    """

    text = str(stored or '').replace('\\', '/')
    parsed = extra_library_relative(text)
    if parsed is not None:
        folder_id, rel = parsed
        root = extra_dir_lookup(extra_dirs).get(folder_id)
        if root is not None:
            try:
                return root.resolve(), rel
            except OSError:
                return root, rel
        return download_dir, text
    if slskd_dir is not None and text.startswith(SLSKD_LIBRARY_PREFIX):
        return slskd_dir.resolve(), text[len(SLSKD_LIBRARY_PREFIX) :]
    return download_dir, text


def library_stored_path(
    file_path: Path,
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
    extra_dirs: Optional[Sequence[Path]] = None,
) -> str:
    """Stable library key for API/DB/URLs (no ``..`` segments).

    Files under *download_dir* stay relative to it. Files under *slskd_dir*
    use the virtual prefix ``slskd/`` so clients request
    ``/media/slskd/...`` instead of ``/media/../slskd/...`` (browsers
    normalize the latter away from the media route). Extra library folders
    (see ``downtify.external_library``) use ``ext/<id>/...``.
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
    for root in extra_dirs or ():
        try:
            extra_resolved = root.resolve()
            rel = file_resolved.relative_to(extra_resolved).as_posix()
        except (OSError, ValueError):
            continue
        return f'{EXTERNAL_LIBRARY_PREFIX}{extra_dir_id(root)}/{rel}'
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
    extra_dirs: Optional[Sequence[Path]] = None,
) -> Path:
    """Resolve a library stored path to an absolute filesystem path."""

    text = str(stored or '').strip().replace('\\', '/')
    parsed = extra_library_relative(text)
    if parsed is not None:
        folder_id, rel = parsed
        root = extra_dir_lookup(extra_dirs).get(folder_id)
        if root is not None:
            return (root / rel).resolve()
        return (download_dir / text).resolve()
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
    extra_dirs: Optional[Sequence[Path]] = None,
) -> Optional[Path]:
    """Resolve *stored* to an on-disk file (extra, slskd, legacy roots)."""

    text = str(stored or '').strip().replace('\\', '/')
    if not text or text.startswith('/'):
        return None

    candidates: list[Path] = []
    parsed = extra_library_relative(text)
    if parsed is not None:
        folder_id, rel = parsed
        root = extra_dir_lookup(extra_dirs).get(folder_id)
        if root is not None:
            candidates.append((root / rel).resolve())
    rel = _slskd_relative(text)
    if rel is not None:
        if slskd_dir is not None:
            candidates.append((slskd_dir / rel).resolve())
        for root in default_slskd_source_roots(download_dir):
            candidates.append((root / rel).resolve())
        candidates.append((download_dir / 'slskd' / rel).resolve())
    candidates.append(
        resolve_library_stored_path(text, download_dir, slskd_dir, extra_dirs)
    )

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
