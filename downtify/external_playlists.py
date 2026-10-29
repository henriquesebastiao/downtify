"""Discover external M3U files and import selected snapshots, never audio."""

from __future__ import annotations

import hashlib
import os
import threading
from dataclasses import dataclass
from pathlib import Path

from . import m3u
from .library_catalog import AUDIO_EXTENSIONS, LibraryContext
from .library_paths import library_stored_path
from .manual_playlists import copy_playlist, existing_playlist_names
from .playlist_catalog import ManualPlaylistOwners
from .playlist_shares import PlaylistShares
from .sqlite_utils import connect_sqlite

MAX_BYTES = 2 * 1024 * 1024
MAX_LINES = 20_000
MAX_CANDIDATES = 500
MAX_SCAN_ENTRIES = 100_000


@dataclass(frozen=True)
class ExternalPlaylist:
    source_id: str
    name: str
    folder: str
    revision: str
    files: tuple[str, ...]
    missing: int
    duplicates: int


def _within(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path.is_relative_to(root) for root in roots)


def read_external_playlist(
    path: Path, root: Path, ctx: LibraryContext
) -> ExternalPlaylist:
    root = root.resolve()
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError('Playlist must stay inside its configured folder')
    with path.open('rb') as stream:
        blob = stream.read(MAX_BYTES + 1)
    if len(blob) > MAX_BYTES:
        raise ValueError('Playlist exceeds the 2 MiB limit')
    try:
        text = blob.decode('utf-8-sig')
    except UnicodeDecodeError:
        if path.suffix.lower() == '.m3u8':
            raise ValueError('M3U8 must be UTF-8') from None
        text = blob.decode('cp1252')
    lines = text.splitlines()
    if len(lines) > MAX_LINES:
        raise ValueError('Playlist exceeds the entry limit')
    roots = tuple(
        folder.resolve()
        for folder in (
            ctx.download_dir,
            *((ctx.slskd_dir,) if ctx.slskd_dir else ()),
            *(ctx.extra_dirs or ()),
        )
    )
    files: list[str] = []
    seen: set[str] = set()
    missing = duplicates = 0
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if '\x00' in line or '://' in line:
            missing += 1
            continue
        entry = Path(line.replace('\\', '/'))
        # Check lexical containment before resolving: an absolute UNC path must
        # never initiate access to an unconfigured network share on Windows.
        target = Path(
            os.path.abspath(
                entry if entry.is_absolute() else path.parent / entry
            )
        )
        if not _within(target, roots):
            missing += 1
            continue
        try:
            full = target.resolve()
            if (
                not _within(full, roots)
                or not full.is_file()
                or full.suffix.lower() not in AUDIO_EXTENSIONS
            ):
                missing += 1
                continue
            stored = library_stored_path(
                full, ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs
            )
        except OSError:
            missing += 1
            continue
        if stored in seen:
            duplicates += 1
            continue
        seen.add(stored)
        files.append(stored)
    identity = (
        os.path.normcase(str(root)) + '\0' + path.relative_to(root).as_posix()
    )
    return ExternalPlaylist(
        hashlib.sha256(identity.encode()).hexdigest(),
        path.parent.name if path.stem.casefold() == 'playlist' else path.stem,
        root.name,
        hashlib.sha256(blob).hexdigest(),
        tuple(files),
        missing,
        duplicates,
    )


def discover_external_playlists(
    ctx: LibraryContext,
) -> tuple[list[ExternalPlaylist], list[str], bool]:
    found: list[ExternalPlaylist] = []
    warnings: list[str] = []
    visited = 0
    for raw_root in ctx.extra_dirs or ():
        root = raw_root.resolve()
        if not root.is_dir():
            warnings.append(f'Folder unavailable: {root.name}')
            continue
        try:
            for path in root.rglob('*'):
                visited += 1
                if visited > MAX_SCAN_ENTRIES or len(found) >= MAX_CANDIDATES:
                    return found, warnings, True
                if (
                    path.suffix.lower() not in {'.m3u', '.m3u8'}
                    or not path.is_file()
                ):
                    continue
                try:
                    found.append(read_external_playlist(path, root, ctx))
                except (OSError, ValueError, UnicodeError):
                    warnings.append(
                        f'Playlist unavailable or invalid: {path.name}'
                    )
        except OSError:
            warnings.append(f'Folder could not be fully scanned: {root.name}')
    return (
        sorted(found, key=lambda item: (item.name.casefold(), item.source_id)),
        warnings,
        False,
    )


class ExternalPlaylistImports:
    def __init__(self, db_path: Path) -> None:
        self.path = str(db_path)
        self.lock = threading.RLock()
        with connect_sqlite(self.path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS external_playlist_imports (
                user_id INTEGER NOT NULL, source_id TEXT NOT NULL,
                playlist_name TEXT NOT NULL, revision TEXT NOT NULL,
                PRIMARY KEY(user_id, source_id))""")

    def imported(self, user_id: int) -> dict[str, str]:
        with connect_sqlite(self.path) as conn:
            return dict(
                conn.execute(
                    'SELECT source_id, playlist_name FROM external_playlist_imports WHERE user_id = ?',
                    (user_id,),
                )
            )

    def import_snapshot(
        self,
        ctx: LibraryContext,
        user_id: int,
        source: ExternalPlaylist,
        files: list[str],
    ) -> dict:
        with self.lock:
            previous = self.imported(user_id).get(source.source_id)
            owners = ManualPlaylistOwners(Path(self.path))
            if (
                previous
                and owners.owner_map().get(previous.casefold()) == user_id
                and m3u.find_m3u_for_name(ctx.download_dir, previous)
            ):
                return {
                    'source_id': source.source_id,
                    'status': 'already_present',
                    'name': previous,
                }
            base = (
                m3u.sanitize_playlist_name(source.name)[:110]
                or 'Imported playlist'
            )
            if base.casefold() == 'downtify liked songs':
                base = 'Imported playlist'
            taken = existing_playlist_names(ctx.download_dir)
            name = base
            suffix = 2
            while name.casefold() in taken:
                name = f'{base} ({suffix})'
                suffix += 1
            result = copy_playlist(ctx, files, name)
            owners.set_owner(result['name'], user_id)
            PlaylistShares(Path(self.path)).forget(result['name'])
            with connect_sqlite(self.path) as conn:
                conn.execute(
                    'INSERT INTO external_playlist_imports VALUES (?, ?, ?, ?) '
                    'ON CONFLICT(user_id, source_id) DO UPDATE SET '
                    'playlist_name=excluded.playlist_name, revision=excluded.revision',
                    (
                        user_id,
                        source.source_id,
                        result['name'],
                        source.revision,
                    ),
                )
            return {'source_id': source.source_id, 'status': 'added', **result}

    def rename(self, old: str, new: str) -> None:
        with connect_sqlite(self.path) as conn:
            conn.execute(
                'UPDATE external_playlist_imports SET playlist_name = ? WHERE playlist_name = ?',
                (new, old),
            )

    def forget(self, name: str) -> None:
        with connect_sqlite(self.path) as conn:
            conn.execute(
                'DELETE FROM external_playlist_imports WHERE playlist_name = ?',
                (name,),
            )
