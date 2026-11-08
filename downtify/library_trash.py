"""Persistent, reversible music trash.

Filesystem work runs in a worker: inside the app (``embedded``, the
default) or as a separate process (``python -m downtify.trash_worker``)
for installs whose app only mounts the music read-only. No playlist,
favourite or ownership record is deleted by this module. A confirmed
operation reserves its original path until restored or expired.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import platform
import re
import secrets
import sqlite3
import stat
import sys
import time
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping, Optional

if os.name == 'nt':
    import msvcrt
else:
    import fcntl

TRASH_DIR = '.downtify-trash'
RETENTION_DAYS = 30
RETENTION_SECONDS = RETENTION_DAYS * 86400
PREVIEW_SECONDS = 600
WORKER_MODES = ('embedded', 'external')
#: How long the hidden paths are trusted before the journal's revision is
#: read again (a separate worker process changes it behind our back).
HIDDEN_RECHECK_SECONDS = 2.0
_TRUE = {'1', 'true', 'yes', 'on'}
#: The operations a worker pass picks up (``?`` is the current time).
_WORK = (
    "FROM library_trash WHERE state IN ('pending','moving',"
    "'restore_pending','restoring','purging') OR "
    "(state='trashed' AND expires<=?)"
)
BLOCKING_STATES = (
    'pending',
    'moving',
    'trashed',
    'restore_pending',
    'restoring',
    'purging',
    'purged',
    'error',
)


class TrashError(ValueError):
    """A stable, translatable failure code; never exposes private paths."""


def identity_keys(song: dict) -> set[str]:
    """Use provider IDs and exact release tags, preserving edition names."""
    keys = set()
    for field in ('spotify_id', 'deezer_id', 'youtube_id', 'isrc'):
        value = song.get(field)
        if value:
            keys.add(
                field
                + ':'
                + (
                    str(value).strip().upper()
                    if field == 'isrc'
                    else str(value).strip()
                )
            )
    song_id = str(song.get('song_id') or '')
    if re.fullmatch('[a-zA-Z0-9]{22}', song_id) and song.get('source') not in {
        'deezer',
        'youtube',
    }:
        keys.add('spotify_id:' + song_id)
    if song.get('source') == 'youtube' and song_id:
        keys.add('youtube_id:' + song_id)

    def normal(value):
        return ' '.join(
            unicodedata.normalize('NFKC', str(value or '')).casefold().split()
        )

    title = normal(song.get('title') or song.get('name'))
    album = normal(song.get('album') or song.get('album_name'))
    artists = song.get('artists')
    if not isinstance(artists, list) or not artists:
        artists = str(song.get('artist') or '').split(';')
    artist = json.dumps(sorted(normal(a) for a in artists if normal(a)))
    if artist == '[]':
        artist = ''
    if title and artist and album:
        keys.add(
            'release:'
            + hashlib.sha256(
                json.dumps([title, artist, album]).encode()
            ).hexdigest()
        )
    return keys


@contextmanager
def worker_lock(path: Path):
    """Process lifetime lock: a second worker must never race the first."""
    with path.open('a+b') as handle:
        if os.name == 'nt':
            if os.fstat(handle.fileno()).st_size == 0:
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                yield False
                return
            try:
                yield True
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
                return
            try:
                yield True
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


@dataclass(frozen=True)
class TrashRoot:
    path: Path
    marker: str = ''
    marker_value: str = ''

    def check(self) -> Path:
        root = self.path.absolute()
        if root.is_symlink() or not root.is_dir():
            raise TrashError('root_unavailable')
        if self.marker:
            marker = root / self.marker
            if marker.is_symlink() or not marker.is_file():
                raise TrashError('nas_marker_missing')
            if marker.read_text().strip() != self.marker_value:
                raise TrashError('nas_marker_changed')
        # The root itself may not be a link, but a folder above it may
        # (``/home`` on some distributions): every later step opens each
        # component without following links, so start from the real path.
        return root.resolve()


def _relative(value: str, *, internal: bool = False) -> str:
    if not value or '\\' in value or '\0' in value:
        raise TrashError('invalid_path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(
        p in {'', '.', '..'} or ':' in p for p in path.parts
    ):
        raise TrashError('invalid_path')
    if not internal and TRASH_DIR in path.parts:
        raise TrashError('invalid_path')
    return path.as_posix()


def _safe(root: Path, relative: str, *, internal: bool = False) -> Path:
    relative = _relative(relative, internal=internal)
    full = root
    for component in PurePosixPath(relative).parts:
        full /= component
        if full.is_symlink():
            raise TrashError('unsafe_symlink')
    if not full.resolve().is_relative_to(root.resolve()):
        raise TrashError('invalid_path')
    return full


def fingerprint(path: Path) -> dict:
    flags = (
        os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
    )
    if os.name == 'nt':
        fd = os.open(path, flags)
    else:
        with _directory_fd(path.parent) as directory:
            fd = os.open(path.name, flags, dir_fd=directory)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise TrashError('not_regular_file')
        digest = hashlib.sha256()
        while chunk := os.read(fd, 1024 * 1024):
            digest.update(chunk)
        after = os.fstat(fd)
        keys = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if any(getattr(before, k) != getattr(after, k) for k in keys):
            raise TrashError('file_changed')
        return {
            'size': after.st_size,
            'mtime_ns': after.st_mtime_ns,
            'dev': after.st_dev,
            'ino': after.st_ino,
            'sha256': digest.hexdigest(),
        }
    finally:
        os.close(fd)


def _matches(path: Path, expected: dict, *, original: bool = False) -> bool:
    actual = fingerprint(path)
    keys = (
        ('size', 'sha256', 'mtime_ns', 'dev', 'ino')
        if original
        else ('size', 'sha256')
    )
    return all(actual[k] == expected[k] for k in keys)


def _fsync_dir(path: Path) -> None:
    if os.name == 'nt':
        return
    with _directory_fd(path) as fd:
        os.fsync(fd)


#: ``renameat2``'s syscall number, for a C library without the wrapper
#: (musl before 1.2.5, as in some Alpine images).
_RENAMEAT2_SYSCALL = {
    'x86_64': 316,
    'amd64': 316,
    'i386': 353,
    'i686': 353,
    'aarch64': 276,
    'arm64': 276,
    'riscv64': 276,
    'armv7l': 382,
    'armv6l': 382,
}
_RENAME_NOREPLACE = 1


def _renameat2() -> Callable[[int, bytes, int, bytes, int], int]:
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is not None:
        rename.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename.restype = ctypes.c_int
        return rename
    number = _RENAMEAT2_SYSCALL.get(platform.machine().lower())
    if number is None:
        raise TrashError('atomic_move_unsupported')
    syscall = libc.syscall
    syscall.restype = ctypes.c_long

    def via_syscall(src_fd, src, dst_fd, dst, flags):
        return syscall(
            ctypes.c_long(number),
            ctypes.c_int(src_fd),
            ctypes.c_char_p(src),
            ctypes.c_int(dst_fd),
            ctypes.c_char_p(dst),
            ctypes.c_uint(flags),
        )

    return via_syscall


def _rename_no_replace(source: Path, target: Path) -> None:
    """Same-mount atomic rename which never replaces a concurrent file."""
    if sys.platform == 'linux':
        rename = _renameat2()
        with (
            _directory_fd(source.parent) as source_fd,
            _directory_fd(target.parent) as target_fd,
        ):
            if rename(
                source_fd,
                os.fsencode(source.name),
                target_fd,
                os.fsencode(target.name),
                _RENAME_NOREPLACE,
            ):
                code = ctypes.get_errno()
                if code == errno.EEXIST:
                    raise TrashError('restore_collision')
                if code in {errno.EINVAL, errno.ENOSYS, errno.EOPNOTSUPP}:
                    # The filesystem (or kernel) can't promise not to
                    # replace: refuse rather than fall back to rename().
                    raise TrashError('atomic_move_unsupported')
                raise OSError(code, os.strerror(code))
    elif os.name == 'nt':
        # Windows rename fails if the destination already exists.
        os.rename(source, target)
    else:
        raise TrashError('atomic_move_unsupported')
    _fsync_dir(source.parent)
    _fsync_dir(target.parent)


@contextmanager
def _directory_fd(path: Path):
    """Open each directory component without ever following a symlink."""
    path = path.absolute()
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            next_fd = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd
            )
            os.close(fd)
            fd = next_fd
        yield fd
    finally:
        os.close(fd)


def _mkdir_beneath(root: Path, relative: str) -> None:
    relative = _relative(relative, internal=True)
    if os.name == 'nt':
        _safe(root, relative, internal=True).mkdir(
            parents=True, exist_ok=True, mode=0o700
        )
        return
    with _directory_fd(root) as root_fd:
        current = os.dup(root_fd)
        try:
            for part in PurePosixPath(relative).parts:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=current)
                    os.fsync(current)
                except FileExistsError:
                    pass
                next_fd = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=current,
                )
                os.close(current)
                current = next_fd
        finally:
            os.close(current)


def _unlink_verified(path: Path, expected: dict) -> None:
    actual = fingerprint(path)
    if any(actual[k] != expected[k] for k in ('size', 'sha256')):
        raise TrashError('trash_file_changed')
    if os.name == 'nt':
        path.unlink()
        return
    with _directory_fd(path.parent) as directory:
        current = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        if (
            not stat.S_ISREG(current.st_mode)
            or current.st_dev != actual['dev']
            or current.st_ino != actual['ino']
            or current.st_size != actual['size']
            or current.st_mtime_ns != actual['mtime_ns']
        ):
            raise TrashError('trash_file_changed')
        os.unlink(path.name, dir_fd=directory)
        os.fsync(directory)


@dataclass
class _Hidden:
    revision: int
    files: frozenset[str]
    resolved: frozenset[str]
    checked: float


class LibraryTrash:
    def __init__(
        self,
        db: Path,
        roots: dict[str, TrashRoot],
        *,
        clock: Callable[[], float] = time.time,
        worker: str = 'embedded',
    ):
        if worker not in WORKER_MODES:
            raise TrashError('unsupported_configuration')
        self.db = Path(db)
        self.roots = roots
        self.clock = clock
        self.worker = worker
        self._hidden: Optional[_Hidden] = None
        self.db.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS library_trash (
                    id TEXT PRIMARY KEY, batch TEXT NOT NULL,
                    user_id INTEGER NOT NULL, root_key TEXT NOT NULL,
                    relative TEXT NOT NULL, stored TEXT NOT NULL,
                    track_id TEXT NOT NULL DEFAULT '', row_json TEXT NOT NULL,
                    manifest TEXT NOT NULL, state TEXT NOT NULL,
                    action TEXT NOT NULL DEFAULT 'move', created REAL NOT NULL,
                    moved REAL, expires REAL, error TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_trash_batch ON library_trash(batch);
                CREATE INDEX IF NOT EXISTS idx_trash_stored ON library_trash(stored,state);
                CREATE TABLE IF NOT EXISTS library_trash_blocks (
                    identity TEXT NOT NULL, item_id TEXT NOT NULL,
                    PRIMARY KEY(identity, item_id)
                );
                CREATE TABLE IF NOT EXISTS library_trash_meta (
                    key TEXT PRIMARY KEY, value INTEGER NOT NULL
                );
                INSERT OR IGNORE INTO library_trash_meta VALUES ('revision',0);
            """)
            block_columns = conn.execute(
                'PRAGMA table_info(library_trash_blocks)'
            ).fetchall()
            if not any(
                row[1] == 'item_id' and row[5] for row in block_columns
            ):
                # Old development journals used only identity as the key;
                # several independently trashed copies must remain excluded.
                conn.execute('BEGIN IMMEDIATE')
                conn.execute(
                    'CREATE TABLE library_trash_blocks_v2 (identity TEXT NOT NULL, item_id TEXT NOT NULL, PRIMARY KEY(identity,item_id))'
                )
                conn.execute(
                    'INSERT OR IGNORE INTO library_trash_blocks_v2 SELECT identity,item_id FROM library_trash_blocks'
                )
                conn.execute('DROP TABLE library_trash_blocks')
                conn.execute(
                    'ALTER TABLE library_trash_blocks_v2 RENAME TO library_trash_blocks'
                )
            columns = {
                r[1] for r in conn.execute('PRAGMA table_info(library_trash)')
            }
            if 'blocked' not in columns:
                conn.execute(
                    'ALTER TABLE library_trash ADD COLUMN blocked INTEGER NOT NULL DEFAULT 1'
                )
            if 'requested_by' not in columns:
                conn.execute(
                    'ALTER TABLE library_trash ADD COLUMN requested_by INTEGER NOT NULL DEFAULT 0'
                )

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _root(self, key: str) -> Path:
        if key not in self.roots:
            raise TrashError('unsupported_collection')
        return self.roots[key].check()

    def preview(self, user_id: int, tracks: list[dict]) -> dict:
        if user_id <= 0 or not tracks or len(tracks) > 200:
            raise TrashError('invalid_selection')
        batch = secrets.token_urlsafe(32)
        rows = []
        seen = set()
        for track in tracks:
            stored = str(track['stored'])
            if stored in seen:
                continue
            seen.add(stored)
            root = self._root(track['root_key'])
            relative = _relative(track['relative'])
            audio = _safe(root, relative)
            item_id = secrets.token_hex(16)
            if not identity_keys(track.get('metadata', {})):
                raise TrashError('identity_uncertain')
            manifest = []
            sources = [(track['root_key'], root, audio)]
            shared_sidecar = any(
                p != audio
                and p.suffix.lower()
                in {'.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav', '.aac'}
                and p.stem == audio.stem
                for p in audio.parent.iterdir()
            )
            # Only track-specific sidecars; never shared folder artwork.
            for suffix in ('.lrc', '.txt', '.srt'):
                sidecar = audio.with_suffix(suffix)
                if sidecar.exists() or sidecar.is_symlink():
                    if shared_sidecar:
                        continue
                    sources.append((track['root_key'], root, sidecar))
            if not shared_sidecar:
                for sidecar in track.get('extra_sidecars', []):
                    side_root = self._root(sidecar['root_key'])
                    side_rel = _relative(sidecar['relative'])
                    source = _safe(side_root, side_rel)
                    if source.suffix.lower() != '.lrc':
                        raise TrashError('invalid_path')
                    if source.exists() and not any(
                        source == item[2] for item in sources
                    ):
                        sources.append((
                            sidecar['root_key'],
                            side_root,
                            source,
                        ))
            for index, (source_key, source_root, source) in enumerate(sources):
                rel = source.relative_to(source_root).as_posix()
                _safe(source_root, rel)
                manifest.append({
                    'source': rel,
                    'target': f'{TRASH_DIR}/{item_id}/{index}{source.suffix.lower()}',
                    'root_key': source_key,
                    'fingerprint': fingerprint(source),
                })
            rows.append({
                'id': item_id,
                'batch': batch,
                'user_id': user_id,
                'root_key': track['root_key'],
                'relative': relative,
                'stored': stored,
                'track_id': track.get('track_id', ''),
                'row_json': json.dumps(track.get('metadata', {})),
                'manifest': json.dumps(manifest),
                'state': 'preview',
                'created': self.clock(),
            })
        with self.connect() as conn:
            for row in rows:
                conn.execute(
                    """INSERT INTO library_trash
                    (id,batch,user_id,root_key,relative,stored,track_id,row_json,manifest,state,created)
                    VALUES (:id,:batch,:user_id,:root_key,:relative,:stored,:track_id,:row_json,:manifest,:state,:created)""",
                    row,
                )
        return {
            'confirmation': batch,
            'expires_at': self.clock() + PREVIEW_SECONDS,
            'items': [self._public(row) for row in rows],
        }

    @staticmethod
    def _public(row) -> dict:
        row = dict(row)
        return {
            'id': row['id'],
            'file': row['stored'],
            'track_id': row.get('track_id', ''),
            'metadata': json.loads(row['row_json']),
            'state': row['state'],
            'size': sum(
                x['fingerprint']['size'] for x in json.loads(row['manifest'])
            ),
            'expires_at': row.get('expires'),
            'error': row.get('error', ''),
        }

    def confirm(self, user_id: int, batch: str) -> list[str]:
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            rows = conn.execute(
                'SELECT * FROM library_trash WHERE batch=? AND user_id=?',
                (batch, user_id),
            ).fetchall()
            if not rows:
                raise TrashError('confirmation_invalid')
            if all(r['state'] != 'preview' for r in rows):
                return [r['id'] for r in rows]
            if any(
                r['state'] != 'preview'
                or self.clock() - r['created'] > PREVIEW_SECONDS
                for r in rows
            ):
                raise TrashError('confirmation_expired')
            for row in rows:
                if conn.execute(
                    "SELECT 1 FROM library_trash WHERE stored=? AND state NOT IN ('preview','restored','purged')",
                    (row['stored'],),
                ).fetchone():
                    raise TrashError('operation_already_pending')
                for file in json.loads(row['manifest']):
                    root = self._root(file.get('root_key', row['root_key']))
                    if not _matches(
                        _safe(root, file['source']),
                        file['fingerprint'],
                        original=True,
                    ):
                        raise TrashError('file_changed')
            conn.execute(
                "UPDATE library_trash SET state='pending' WHERE batch=?",
                (batch,),
            )
            conn.execute(
                "UPDATE library_trash_meta SET value=value+1 WHERE key='revision'"
            )
            for row in rows:
                for key in identity_keys(json.loads(row['row_json'])):
                    conn.execute(
                        'INSERT OR IGNORE INTO library_trash_blocks(identity,item_id) VALUES (?,?)',
                        (key, row['id']),
                    )
        self._hidden = None
        return [r['id'] for r in rows]

    def confirmation_files(self, user_id: int, batch: str) -> list[str]:
        with self.connect() as conn:
            return [
                r[0]
                for r in conn.execute(
                    'SELECT stored FROM library_trash WHERE batch=? AND user_id=?',
                    (batch, user_id),
                )
            ]

    def list(
        self, *, offset: int = 0, limit: int = 50, search: str = ''
    ) -> dict:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM library_trash WHERE state NOT IN ('preview','restored','purged') ORDER BY created DESC"
            ).fetchall()
        matching = [
            r
            for r in rows
            if search.casefold() in (r['stored'] + r['row_json']).casefold()
        ]
        return {
            'items': [
                self._public(r)
                for r in matching[offset : offset + min(limit, 100)]
            ],
            'total': len(matching),
            'size': sum(self._public(r)['size'] for r in matching),
        }

    def request_restore(self, ids: list[str], *, user_id: int = 0) -> None:
        if not ids or len(ids) > 200:
            raise TrashError('invalid_selection')
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            for item in set(ids):
                row = conn.execute(
                    'SELECT * FROM library_trash WHERE id=?', (item,)
                ).fetchone()
                if row is None or row['state'] == 'preview':
                    raise TrashError('item_not_found')
                if row['state'] == 'restored':
                    continue
                if row['state'] in {'moving', 'restoring'}:
                    raise TrashError('operation_in_progress')
                if row['state'] in {'purging', 'purged'} or (
                    row['expires'] is not None
                    and self.clock() >= row['expires']
                ):
                    raise TrashError('retention_expired')
                conn.execute(
                    "UPDATE library_trash SET state='restore_pending', action='restore', requested_by=?, error='' WHERE id=?",
                    (user_id or row['user_id'], item),
                )

    def hidden(self) -> tuple[frozenset[str], frozenset[str]]:
        """The library paths kept out of every listing, as stored and as
        resolved on disk. Read on every request, so cached until the
        journal's revision moves."""

        now = time.monotonic()
        cached = self._hidden
        if cached is not None and now - cached.checked < (
            HIDDEN_RECHECK_SECONDS
        ):
            return cached.files, cached.resolved
        with self.connect() as conn:
            revision = conn.execute(
                "SELECT value FROM library_trash_meta WHERE key='revision'"
            ).fetchone()[0]
            if cached is not None and cached.revision == revision:
                cached.checked = now
                return cached.files, cached.resolved
            rows = conn.execute(
                "SELECT stored,root_key,relative FROM library_trash WHERE state NOT IN ('preview','restored') AND blocked=1"
            ).fetchall()
        bases = {}
        for key, root in self.roots.items():
            try:
                bases[key] = root.path.absolute().resolve()
            except OSError:
                continue
        files = frozenset(r['stored'] for r in rows)
        resolved = frozenset(
            str(bases[r['root_key']] / r['relative'])
            for r in rows
            if r['root_key'] in bases
        )
        self._hidden = _Hidden(revision, files, resolved, now)
        return files, resolved

    def hidden_paths(self) -> frozenset[str]:
        return self.hidden()[0]

    def hidden_resolved(self) -> frozenset[str]:
        return self.hidden()[1]

    def _update(self, item: str, **values) -> None:
        with self.connect() as conn:
            conn.execute(
                'UPDATE library_trash SET '
                + ','.join(k + '=?' for k in values)
                + ' WHERE id=?',
                (*values.values(), item),
            )
            if 'blocked' in values or values.get('state') == 'restored':
                conn.execute(
                    "UPDATE library_trash_meta SET value=value+1 WHERE key='revision'"
                )
        self._hidden = None

    def revision(self) -> int:
        with self.connect() as conn:
            return conn.execute(
                "SELECT value FROM library_trash_meta WHERE key='revision'"
            ).fetchone()[0]

    def process(
        self,
        *,
        limit: int = 10,
        authorized: Callable[[int], bool],
        skip_ids: frozenset[str] = frozenset(),
    ) -> list[dict]:
        with worker_lock(
            self.db.with_suffix('.trash-worker.lock')
        ) as acquired:
            if not acquired:
                return []
            return self._process(
                limit=limit, authorized=authorized, skip_ids=skip_ids
            )

    def blocked(self, song: dict) -> bool:
        with self.connect() as conn:
            for key in identity_keys(song):
                if conn.execute(
                    """SELECT 1 FROM library_trash_blocks b JOIN library_trash t ON t.id=b.item_id
                    WHERE b.identity=? AND t.blocked=1 AND t.state NOT IN ('preview','restored')""",
                    (key,),
                ).fetchone():
                    return True
        return False

    def allow_download(self, ids: list[str]) -> None:
        if not ids or len(ids) > 200:
            raise TrashError('invalid_selection')
        with self.connect() as conn:
            for item in ids:
                row = conn.execute(
                    'SELECT state FROM library_trash WHERE id=?', (item,)
                ).fetchone()
                if row is None or row['state'] not in {
                    'trashed',
                    'purged',
                    'restored',
                }:
                    raise TrashError('operation_not_complete')
                conn.execute(
                    'UPDATE library_trash SET blocked=0 WHERE id=?', (item,)
                )
            conn.execute(
                "UPDATE library_trash_meta SET value=value+1 WHERE key='revision'"
            )
        self._hidden = None

    def retry(self, ids: list[str], *, user_id: int) -> None:
        if not ids or len(ids) > 200:
            raise TrashError('invalid_selection')
        with self.connect() as conn:
            for item in ids:
                row = conn.execute(
                    'SELECT * FROM library_trash WHERE id=?', (item,)
                ).fetchone()
                if row is None or row['state'] != 'error':
                    raise TrashError('operation_not_complete')
                state = {
                    'move': 'pending',
                    'restore': 'restore_pending',
                    'purge': 'purging',
                }[row['action']]
                conn.execute(
                    'UPDATE library_trash SET state=?,requested_by=?,error=? WHERE id=?',
                    (state, user_id, '', item),
                )

    def has_work(self) -> bool:
        """Whether a worker pass would do anything (cheap: one query)."""

        with self.connect() as conn:
            return (
                conn.execute(
                    'SELECT 1 ' + _WORK + ' LIMIT 1',
                    (self.clock(),),
                ).fetchone()
                is not None
            )

    def work_files(self) -> dict[str, str]:
        """``{operation id: library path}`` of the work waiting, so the
        embedded worker can hold back a song that is playing."""

        with self.connect() as conn:
            return {
                r['id']: r['stored']
                for r in conn.execute(
                    'SELECT id,stored ' + _WORK, (self.clock(),)
                )
            }

    def exclusions(self) -> list[dict]:
        with self.connect() as conn:
            return [
                self._public(r)
                for r in conn.execute(
                    "SELECT * FROM library_trash WHERE blocked=1 AND state='purged' ORDER BY created DESC"
                )
            ]

    def _process(
        self,
        *,
        limit: int,
        authorized: Callable[[int], bool],
        skip_ids: frozenset[str],
    ) -> list[dict]:
        """One bounded, single-worker pass. Authorization is rechecked here."""
        result = []
        with self.connect() as conn:
            rows = conn.execute(
                'SELECT * ' + _WORK + ' ORDER BY created LIMIT ?',
                (self.clock(), limit + len(skip_ids)),
            ).fetchall()
        for row in rows:
            if row['id'] in skip_ids:
                continue
            if len(result) >= limit:
                break
            try:
                if self._process_item(dict(row), authorized=authorized):
                    result.append({'id': row['id'], 'ok': True})
            except (OSError, TrashError) as exc:
                error = (
                    str(exc)
                    if isinstance(exc, TrashError)
                    else 'filesystem_unavailable'
                )
                self._update(row['id'], state='error', error=error)
                result.append({'id': row['id'], 'ok': False, 'error': error})
        return result

    def _process_item(self, row: dict, *, authorized=None) -> bool:
        action = row['action']
        if row['state'] in {'trashed', 'purging'}:
            if row['expires'] is None or self.clock() < row['expires']:
                raise TrashError('retention_not_expired')
            action = 'purge'
        next_state = {
            'move': 'moving',
            'restore': 'restoring',
            'purge': 'purging',
        }[action]
        with self.connect() as conn:
            claimed = conn.execute(
                'UPDATE library_trash SET state=?,action=? WHERE id=? AND state=? AND action=?',
                (next_state, action, row['id'], row['state'], row['action']),
            ).rowcount
            if not claimed:
                return False
        if action in {'move', 'restore'} and authorized is not None:
            if not authorized(row['requested_by'] or row['user_id']):
                raise TrashError('admin_access_revoked')
        files = json.loads(row['manifest'])
        roots = {}
        for file in files:
            key = file.get('root_key', row['root_key'])
            if key not in roots:
                roots[key] = self._root(key)
        if action == 'move':
            for root in roots.values():
                trash = _safe(root, TRASH_DIR, internal=True)
                _mkdir_beneath(root, TRASH_DIR)
                if os.name != 'nt' and trash.stat().st_mode & 0o077:
                    raise TrashError('trash_permissions_unsafe')
                ignore = trash / '.ignore'
                if ignore.is_symlink():
                    raise TrashError('unsafe_symlink')
                if not ignore.exists():
                    with ignore.open('xb'):
                        pass
                    _fsync_dir(trash)
                if ignore.stat().st_size:
                    raise TrashError('trash_ignore_invalid')
                _safe(root, f'{TRASH_DIR}/{row["id"]}', internal=True)
                _mkdir_beneath(root, f'{TRASH_DIR}/{row["id"]}')
        # Validate the whole operation before the first move/unlink.
        for file in files:
            root = roots[file.get('root_key', row['root_key'])]
            source = _safe(root, file['source'])
            target = _safe(root, file['target'], internal=True)
            current = source if action == 'move' else target
            other = target if action == 'move' else source
            if action == 'purge':
                if target.exists():
                    if not _matches(target, file['fingerprint']):
                        raise TrashError('trash_file_changed')
                elif not file.get('purge_intent'):
                    raise TrashError('trash_file_missing')
            elif current.exists():
                if other.exists():
                    raise TrashError('restore_collision')
                if not _matches(
                    current, file['fingerprint'], original=action == 'move'
                ):
                    raise TrashError('file_changed')
            elif action == 'restore' and other.exists():
                # Never moved (a move that failed or was interrupted
                # first): the file is still where it was, whatever has
                # happened to it since. Restoring only shows it again.
                continue
            elif not other.exists() or not _matches(
                other, file['fingerprint']
            ):
                raise TrashError('file_missing')
        for file in files:
            root = roots[file.get('root_key', row['root_key'])]
            source = _safe(root, file['source'])
            target = _safe(root, file['target'], internal=True)
            if action == 'purge':
                if target.exists():
                    if not _matches(target, file['fingerprint']):
                        raise TrashError('trash_file_changed')
                    file['purge_intent'] = True
                    self._update(row['id'], manifest=json.dumps(files))
                    _unlink_verified(target, file['fingerprint'])
            elif action == 'move' and source.exists():
                if not _matches(source, file['fingerprint'], original=True):
                    raise TrashError('file_changed')
                _rename_no_replace(source, target)
                if not _matches(target, file['fingerprint']):
                    raise TrashError('file_changed_during_move')
            elif action == 'restore' and target.exists():
                parent = source.parent.relative_to(root).as_posix()
                if parent != '.':
                    _mkdir_beneath(root, parent)
                _safe(root, file['source'])
                if not _matches(target, file['fingerprint']):
                    raise TrashError('trash_file_changed')
                _rename_no_replace(target, source)
        if action == 'move':
            moved = self.clock()
            self._update(
                row['id'],
                state='trashed',
                moved=moved,
                expires=moved + RETENTION_SECONDS,
                error='',
            )
        elif action == 'restore':
            self._update(row['id'], state='restored', blocked=0, error='')
        else:
            self._update(row['id'], state='purged', error='')
        return True


def trash_from_config(config_path: Path, db: Path) -> LibraryTrash:
    config = json.loads(config_path.read_text(encoding='utf-8'))
    if config.get('version') != 1:
        raise TrashError('unsupported_configuration')
    roots = {}
    for key, value in config['roots'].items():
        path = Path(value['path'])
        if not path.is_absolute():
            raise TrashError('invalid_root')
        marker = str(value.get('marker', ''))
        if marker:
            _relative(marker)
        roots[key] = TrashRoot(
            path, marker, str(value.get('marker_value', ''))
        )
    if not roots:
        raise TrashError('invalid_root')
    return LibraryTrash(
        db, roots, worker=str(config.get('worker', 'embedded'))
    )


def trash_from_env(
    download_dir: Path,
    db: Path,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[LibraryTrash]:
    """The trash the operator turned on, or ``None``.

    ``DOWNTIFY_TRASH_CONFIG`` (a JSON file naming each folder, and where
    the worker runs) wins; otherwise ``DOWNTIFY_TRASH=true`` keeps it to
    the download folder, with the worker inside the app."""

    env = os.environ if env is None else env
    config = str(env.get('DOWNTIFY_TRASH_CONFIG') or '').strip()
    if config:
        return trash_from_config(Path(config), db)
    if str(env.get('DOWNTIFY_TRASH') or '').strip().lower() in _TRUE:
        return LibraryTrash(
            db, {'downloads': TrashRoot(Path(download_dir).absolute())}
        )
    return None
