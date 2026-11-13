"""Merging duplicate songs into one file (the Doctor's duplicate review).

Deleting one copy of a duplicate isn't enough: the playlists, likes and
Playlist Monitor records that pointed at it now point at nothing, so the
song looks missing and a watch downloads it again (issue #582). Merging
keeps one copy and moves **every reference** to the others onto it
first - the M3U files (manual playlists too), the playlist catalog, the
track index, likes, owners, hidden-song rules, the mobile apps' offline
copies (an alias, as a replaced song's), Playlist Monitor's downloaded
tracks and artist releases, and the watch history - and only then
removes the other copies. Nothing is "missing" afterwards, and the song
stays in every playlist it was in.

It is the same publication Replace audio does
(:class:`downtify.deemix_upgrade_store.AudioReplacementStore`), with a
receipt per removed copy: M3U files first, then the library tables in
one transaction, then a check that none still names a removed copy.

"Keep both" (:class:`KeptApart`) is the other answer: the copies are
different recordings that only look alike (an edit, a live take), and
the Doctor stops listing them.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from . import m3u
from .deemix_upgrade_playlists import digest, rewrite_playlists
from .deemix_upgrade_store import AudioReplacementStore
from .library_cache_keys import file_content_key
from .library_catalog import LibraryContext, resolve_library_file
from .library_metadata import library_entry_for_file
from .manual_playlists import drop_copies_of
from .monitor import repoint_downloaded_file

#: ``run_id`` of a merge's receipts (a library upgrade run is 1 or more).
MERGE_RUN = 0
#: A receipt left by an earlier merge or replacement of the same path,
#: done with, may be replaced by a new one.
_DONE_STATES = ('removed', 'complete', 'retained')


class MergeError(ValueError):
    """A merge refused before anything changed; ``code`` for the UI."""

    def __init__(self, code: str, file: str = '') -> None:
        super().__init__(code)
        self.code = code
        self.file = file


def _norm(value: Any) -> str:
    return str(value or '').strip().replace('\\', '/')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Keep both
# ---------------------------------------------------------------------------


class KeptApart:
    """Library files an admin said are different songs, by pairs.

    A group of look-alikes stays out of the Doctor's list while every
    pair in it is recorded, so a third copy turning up later brings the
    group back (with the new file to decide on).
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kept_apart (
                    a TEXT NOT NULL,
                    b TEXT NOT NULL,
                    kept_at TEXT NOT NULL,
                    PRIMARY KEY (a, b)
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    @staticmethod
    def _pairs(files: list[str]) -> list[tuple[str, str]]:
        names = sorted({_norm(f) for f in files if _norm(f)})
        return list(combinations(names, 2))

    def keep(self, files: list[str]) -> int:
        """Record *files* as different songs; returns the new pairs."""

        pairs = self._pairs(files)
        now = _now()
        with self._connect() as conn:
            before = conn.total_changes
            conn.executemany(
                'INSERT OR IGNORE INTO kept_apart VALUES (?, ?, ?)',
                [(a, b, now) for a, b in pairs],
            )
            return conn.total_changes - before

    def pairs(self) -> set[tuple[str, str]]:
        with self._connect() as conn:
            return {
                (str(a), str(b))
                for a, b in conn.execute('SELECT a, b FROM kept_apart')
            }

    def settled(
        self, files: list[str], pairs: Optional[set[tuple[str, str]]] = None
    ) -> bool:
        """Whether every pair of *files* was kept apart."""

        known = self.pairs() if pairs is None else pairs
        wanted = self._pairs(files)
        return bool(wanted) and all(pair in known for pair in wanted)

    def forget(self) -> int:
        """Forget every decision: all groups are listed again."""

        with self._connect() as conn:
            return conn.execute('DELETE FROM kept_apart').rowcount

    def forget_files(self, files: list[str]) -> None:
        """Drop the decisions about files that are gone (merged)."""

        names = [_norm(f) for f in files if _norm(f)]
        if not names:
            return
        marks = ','.join('?' * len(names))
        with self._connect() as conn:
            conn.execute(
                f'DELETE FROM kept_apart WHERE a IN ({marks}) '
                f'OR b IN ({marks})',
                names + names,
            )


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------


@dataclass
class MergeStores:
    """What a merge rewrites besides the library database tables."""

    ctx: LibraryContext
    replacements: AudioReplacementStore
    monitor_db: Any = None
    library_visibility: Any = None
    playlist_hidden: Any = None
    file_providers: Any = None
    playlist_catalog: Any = None


@dataclass
class MergePlan:
    """A checked merge: *keep* stays, every file of *extras* goes."""

    keep: str
    keep_path: Path
    extras: list[tuple[str, Path]]
    receipts: list[dict[str, Any]] = field(default_factory=list)
    playlists: set[str] = field(default_factory=set)


def plan_merge(keep: str, extras: list[str], ctx: LibraryContext) -> MergePlan:
    """Check that *keep* and every one of *extras* are library files
    (distinct ones). Raises :class:`MergeError`; changes nothing."""

    keep = _norm(keep)
    names = list(dict.fromkeys(_norm(e) for e in extras if _norm(e)))
    if not keep or not names or keep in names:
        raise MergeError('dedupe_invalid')
    keep_path = resolve_library_file(keep, ctx)
    if keep_path is None or not keep_path.is_file():
        raise MergeError('dedupe_missing', keep)
    found: list[tuple[str, Path]] = []
    for name in names:
        path = resolve_library_file(name, ctx)
        if path is None or not path.is_file():
            raise MergeError('dedupe_missing', name)
        if path.resolve() == keep_path.resolve():
            raise MergeError('dedupe_invalid', name)
        found.append((name, path))
    return MergePlan(keep=keep, keep_path=keep_path, extras=found)


def _receipts(
    plan: MergePlan, store: AudioReplacementStore
) -> list[dict[str, Any]]:
    keep_key = file_content_key(plan.keep_path) or ''
    keep_sha = digest(plan.keep_path)
    metadata = library_entry_for_file(plan.keep, plan.keep_path)
    metadata['file'] = plan.keep
    receipts = []
    for name, path in plan.extras:
        earlier = store.get(name)
        if earlier is not None and earlier['state'] not in _DONE_STATES:
            # A Replace audio run is still working on this file.
            raise MergeError('dedupe_replacement_pending', name)
        receipts.append({
            'old_file': name,
            'run_id': MERGE_RUN,
            'new_file': plan.keep,
            'old_key': file_content_key(path) or '',
            'new_key': keep_key,
            'old_sha': digest(path),
            'new_sha': keep_sha,
            'new_metadata': metadata,
            'catalog': {'merged_into': plan.keep},
            'delete_original': 1,
        })
    return receipts


def relink_duplicates(plan: MergePlan, stores: MergeStores) -> MergePlan:
    """Point everything that names one of *plan*'s extras at its keeper.

    The extras stay on disk: the caller removes them (to the music trash
    or for good) and then calls :func:`finish_merge`. Raises when a
    reference could not be moved; a rerun picks up where it stopped.
    """

    ctx = stores.ctx
    store = stores.replacements
    plan.receipts = _receipts(plan, store)
    extras = [name for name, _path in plan.extras]
    if stores.playlist_catalog is not None:
        for names in stores.playlist_catalog.playlists_by_filenames(
            extras
        ).values():
            plan.playlists.update(names)

    # A manual playlist holding both copies keeps the one it already
    # has, rather than listing the kept file twice.
    plan.playlists.update(drop_copies_of(ctx, plan.keep, extras))
    roots = [ctx.download_dir, *ctx.extra_dirs]
    if ctx.slskd_dir is not None:
        roots.append(ctx.slskd_dir)
    duration = float(plan.receipts[0]['new_metadata'].get('duration') or 0)
    target = plan.keep_path.resolve()
    rewrite_playlists(
        roots,
        ctx.download_dir,
        {path.resolve(): (target, duration) for _name, path in plan.extras},
        stopped=lambda: False,
    )
    plan.playlists.update(_m3u_names_with(ctx, plan.keep))

    for receipt in plan.receipts:
        # The copy kept stays as visible as it was: hiding the extra
        # copy (to tidy the library) mustn't hide the song.
        if (
            stores.library_visibility is not None
            and receipt['old_key']
            and receipt['old_key'] != receipt['new_key']
        ):
            stores.library_visibility.drop_track(receipt['old_key'])
        _save_receipt(store, receipt)
    store.relink(plan.receipts)
    store.assert_relinked(plan.receipts)

    for receipt in plan.receipts:
        old_key, new_key = receipt['old_key'], receipt['new_key']
        if stores.playlist_hidden is not None and old_key != new_key:
            stores.playlist_hidden.rekey(old_key, new_key, plan.keep)
        if stores.monitor_db is not None:
            repoint_downloaded_file(
                stores.monitor_db, receipt['old_file'], plan.keep
            )
    logger.info(
        'Doctor: {} copy/copies of {} merged into it (playlists: {})',
        len(plan.receipts),
        plan.keep,
        ', '.join(sorted(plan.playlists)) or 'none',
    )
    return plan


def _save_receipt(
    store: AudioReplacementStore, receipt: dict[str, Any]
) -> None:
    earlier = store.get(receipt['old_file'])
    if earlier is not None:
        with store.connect() as db:
            db.execute(
                'DELETE FROM library_audio_replacements WHERE old_file = ?',
                (receipt['old_file'],),
            )
    store.save_prepared(receipt)


def _m3u_names_with(ctx: LibraryContext, stored: str) -> set[str]:
    names = set()
    for path in m3u.iter_m3u_files(ctx.download_dir):
        entries = m3u.read_m3u_entries(
            path, ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs
        )
        if any(_norm(entry) == stored for entry, _extinf in entries):
            names.add(path.stem)
    return names


def finish_merge(
    plan: MergePlan, stores: MergeStores, removed: list[str]
) -> None:
    """Record the extras that are gone, and forget what only they had
    (an extra's provider record; not one its keeper shares a key with:
    a file's key is its name and size, which exact copies share)."""

    gone = {_norm(name) for name in removed}
    for receipt in plan.receipts:
        if receipt['old_file'] not in gone:
            continue
        stores.replacements.mark(
            receipt['old_file'],
            'removed',
            'Duplicate merged into ' + plan.keep,
            deleted=True,
        )
        old_key = receipt['old_key']
        if (
            stores.file_providers is not None
            and old_key
            and old_key != receipt['new_key']
        ):
            stores.file_providers.drop(old_key)


def leftover_references(plan: MergePlan, stores: MergeStores) -> list[str]:
    """Where a merged extra is still named (empty after a good merge)."""

    found = []
    try:
        stores.replacements.assert_relinked(plan.receipts)
    except ValueError:
        found.append('library')
    if stores.monitor_db is not None:
        names = {name for name, _path in plan.extras}
        if any(
            _norm(row.get('filename')) in names
            for row in stores.monitor_db.list_all_downloaded_tracks()
        ):
            found.append('monitor')
    for name, _path in plan.extras:
        if _m3u_names_with(stores.ctx, name):
            found.append('m3u')
            break
    return found
