"""Backups of what a Downtify install knows, so a fresh install can be
brought back: its settings, every watch with its options, and one record
per library song (artist, title, album, where it came from).

The music files themselves are not in a backup. When they are lost, the
song list tells a restored install what it had, and the songs missing on
disk can be queued for download again (see
:func:`missing_songs`).

A backup is one gzip-compressed JSON file in the backups folder. Writing
one never leaves the folder without two good copies: the new file is
written under a temporary name, flushed to disk, read back and checked,
and only then renamed into place - after which the oldest is deleted, so
the newest two remain (:func:`write_backup`).
"""

from __future__ import annotations

import gzip
import json
import os
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

FORMAT = 'downtify-backup'
VERSION = 1
#: Backups kept in the folder: a new one bumps the oldest out.
KEEP = 2
#: How often scheduled backups may run, in hours (``0``: off).
INTERVALS = (0, 24, 72, 168)

_NAME = 'downtify-backup-{stamp}.json.gz'
_NAME_RE = re.compile(r'^downtify-backup-(\d{8}-\d{6})\.json\.gz$')
_PARTIAL_SUFFIX = '.partial'
#: An uploaded backup is refused past this size (compressed).
MAX_UPLOAD_BYTES = 200 * 1024 * 1024


class BackupError(ValueError):
    """Not a Downtify backup, or one this version can't read."""


@dataclass(frozen=True)
class BackupInfo:
    """One backup file in the backups folder."""

    name: str
    created_at: str
    size: int
    settings: bool
    watches: int
    songs: int

    def to_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'created_at': self.created_at,
            'size': self.size,
            'settings': self.settings,
            'watches': self.watches,
            'songs': self.songs,
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def clamp_interval(value: Any) -> int:
    """A valid schedule in hours: one of :data:`INTERVALS`, else off."""

    try:
        hours = int(value)
    except (TypeError, ValueError):
        return 0
    return hours if hours in INTERVALS else 0


# ── Building ────────────────────────────────────────────────────────


#: Library row fields a backup keeps: enough to find the song again.
_SONG_FIELDS = (
    'file',
    'title',
    'artist',
    'artists',
    'album',
    'album_artist',
    'track_number',
    'year',
    'release_date',
    'genre',
    'duration',
    'isrc',
    'explicit',
)


def song_record(
    row: dict[str, Any],
    *,
    spotify_id: str = '',
    provider: str = '',
) -> dict[str, Any]:
    """The backup record of one library song (a ``/tracks`` row)."""

    record = {key: row.get(key) for key in _SONG_FIELDS if key in row}
    if spotify_id:
        record['spotify_id'] = spotify_id
    if provider:
        record['provider'] = provider
    return record


def build(
    *,
    settings: dict[str, Any],
    watches: Iterable[dict[str, Any]],
    songs: Iterable[dict[str, Any]],
    app_version: str = '',
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """The backup document."""

    return {
        'format': FORMAT,
        'version': VERSION,
        'created_at': (now or _now()).isoformat(timespec='seconds'),
        'app_version': app_version,
        'settings': dict(settings),
        'watches': list(watches),
        'songs': list(songs),
    }


# ── Reading ─────────────────────────────────────────────────────────


def parse(raw: bytes) -> dict[str, Any]:
    """A backup document from a file's bytes (gzip or plain JSON).

    Raises :class:`BackupError` when it isn't a readable Downtify backup.
    """

    try:
        text = gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw
        data = json.loads(text)
    except (OSError, EOFError, ValueError) as exc:
        raise BackupError('Not a Downtify backup file') from exc
    if not isinstance(data, dict) or data.get('format') != FORMAT:
        raise BackupError('Not a Downtify backup file')
    version = data.get('version')
    if not isinstance(version, int) or version > VERSION:
        raise BackupError(
            'This backup was made by a newer Downtify; update first'
        )
    if not isinstance(data.get('settings'), dict):
        raise BackupError('The backup has no settings')
    for key in ('watches', 'songs'):
        if not isinstance(data.get(key), list):
            raise BackupError(f'The backup has no {key} list')
    return data


def read(path: Path) -> dict[str, Any]:
    return parse(Path(path).read_bytes())


# ── The folder ──────────────────────────────────────────────────────


def _info(path: Path, data: dict[str, Any]) -> BackupInfo:
    return BackupInfo(
        name=path.name,
        created_at=str(data.get('created_at') or ''),
        size=path.stat().st_size,
        settings=bool(data.get('settings')),
        watches=len(data.get('watches') or []),
        songs=len(data.get('songs') or []),
    )


def backup_names(folder: Path) -> list[str]:
    """Backup file names in *folder*, newest first."""

    try:
        names = [p.name for p in Path(folder).iterdir() if p.is_file()]
    except OSError:
        return []
    return sorted((n for n in names if _NAME_RE.match(n)), reverse=True)


def path_of(folder: Path, name: str) -> Optional[Path]:
    """The backup called *name* in *folder* (``None``: not one of them)."""

    if not _NAME_RE.match(str(name or '')):
        return None
    path = Path(folder) / name
    return path if path.is_file() else None


def list_backups(folder: Path) -> list[BackupInfo]:
    """The backups in *folder*, newest first. An unreadable file is
    left out (and logged) rather than failing the list."""

    found: list[BackupInfo] = []
    for name in backup_names(folder):
        path = Path(folder) / name
        try:
            found.append(_info(path, read(path)))
        except (OSError, BackupError):
            logger.warning('Unreadable backup {}', path)
    return found


def _fsync_dir(folder: Path) -> None:
    # Makes the rename itself durable; not possible on Windows.
    try:
        fd = os.open(folder, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def write_backup(
    folder: Path,
    data: dict[str, Any],
    *,
    keep: int = KEEP,
    now: Optional[datetime] = None,
) -> BackupInfo:
    """Save *data* as a new backup in *folder* and keep the newest *keep*.

    The file is written under a temporary name, flushed to disk, read
    back and compared with *data*; only a backup that passed is renamed
    into place, and only after that are older ones deleted. A failure at
    any point leaves every existing backup as it was.
    """

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    when = now or _now()
    name = _NAME.format(stamp=when.strftime('%Y%m%d-%H%M%S'))
    final = folder / name
    if final.exists():
        # Two backups within one second: the second waits its turn.
        when += timedelta(seconds=1)
        return write_backup(folder, data, keep=keep, now=when)
    partial = folder / (name + _PARTIAL_SUFFIX)
    payload = json.dumps(data, ensure_ascii=False, default=str).encode()
    try:
        with (
            open(partial, 'wb') as raw,
            gzip.GzipFile(
                filename=name, mode='wb', fileobj=raw, mtime=0
            ) as out,
        ):
            out.write(payload)
        with open(partial, 'rb+') as raw:
            os.fsync(raw.fileno())
        written = read(partial)
        if written != json.loads(payload):
            raise BackupError('The written backup does not match')
        os.replace(partial, final)
        _fsync_dir(folder)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    info = _info(final, written)
    prune(folder, keep=keep)
    logger.info(
        'Backup saved: {} ({} watches, {} songs, {} bytes)',
        info.name,
        info.watches,
        info.songs,
        info.size,
    )
    return info


def prune(folder: Path, *, keep: int = KEEP) -> list[str]:
    """Delete all but the newest *keep* backups (and leftover temporary
    files from an interrupted backup). Returns the names deleted."""

    folder = Path(folder)
    removed: list[str] = []
    for name in backup_names(folder)[max(1, keep) :]:
        try:
            (folder / name).unlink()
            removed.append(name)
        except OSError:
            logger.warning('Could not delete the old backup {}', name)
    try:
        leftovers = [
            p for p in folder.iterdir() if p.name.endswith(_PARTIAL_SUFFIX)
        ]
    except OSError:
        leftovers = []
    for path in leftovers:
        path.unlink(missing_ok=True)
    return removed


def due(
    last: Optional[str], interval_hours: int, now: Optional[datetime] = None
) -> bool:
    """Whether a scheduled backup should run (``last``: ISO time of the
    newest backup, ``None`` when there is none)."""

    if interval_hours <= 0:
        return False
    if not last:
        return True
    try:
        then = datetime.fromisoformat(last)
    except ValueError:
        return True
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return (now or _now()) - then >= timedelta(hours=interval_hours)


# ── Restoring ───────────────────────────────────────────────────────


def missing_songs(
    songs: Iterable[dict[str, Any]], on_disk: Callable[[str], bool]
) -> list[dict[str, Any]]:
    """The backup's songs whose file isn't there any more, as songs the
    download pipeline can look up again (title, artists, album; the
    Spotify track when the backup knew it)."""

    found: list[dict[str, Any]] = []
    for record in songs:
        if not isinstance(record, dict):
            continue
        title = str(record.get('title') or '').strip()
        if not title:
            continue
        stored = str(record.get('file') or '')
        if stored and on_disk(stored):
            continue
        artists = [
            str(a).strip() for a in record.get('artists') or [] if str(a)
        ] or [
            a.strip()
            for a in str(record.get('artist') or '').split(',')
            if a.strip()
        ]
        song: dict[str, Any] = {
            'name': title,
            'artists': artists,
            'artist': ', '.join(artists),
            'album_name': str(record.get('album') or ''),
            'year': str(record.get('year') or ''),
            'release_date': str(record.get('release_date') or ''),
            'duration': int(float(record.get('duration') or 0)),
        }
        if record.get('isrc'):
            song['isrc'] = str(record['isrc'])
        spotify_id = str(record.get('spotify_id') or '')
        if spotify_id:
            song['song_id'] = spotify_id
            song['url'] = f'https://open.spotify.com/track/{spotify_id}'
        found.append(song)
    return found


#: Watch fields a restore writes after adding the watch.
WATCH_OPTIONS = (
    'enabled',
    'deezer_id',
    'musicbrainz_id',
    'musicbrainz_kinds',
)
