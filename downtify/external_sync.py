"""Background extra-folder sync and unmapping a folder from the library."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from .external_library import (
    AUDIO_EXTENSIONS,
    effective_external_library,
    sync_external_library,
)
from .library_catalog import LibraryContext
from .library_cleanup import delete_lrc_sidecar
from .library_paths import (
    EXTERNAL_LIBRARY_PREFIX,
    extra_dir_id,
    library_stored_path,
    locate_library_file,
)
from .library_paths_cache import invalidate_library_paths_cache
from .manual_playlists import prune_files_from_manual_playlists

STATE_IDLE = 'idle'
STATE_RUNNING = 'running'
STATE_DONE = 'done'
STATE_ERROR = 'error'


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _empty_progress() -> dict[str, Any]:
    return {'done': 0, 'total': 0, 'current': ''}


class ExternalSyncJob:
    """One extra-folder sync at a time, with the last finished log on disk."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._live: dict[str, Any] = {
            'state': STATE_IDLE,
            'started_at': '',
            'finished_at': '',
            'progress': _empty_progress(),
            'error': '',
            'result': None,
        }
        self._load()
        if self._live.get('state') == STATE_RUNNING:
            self._live['state'] = STATE_ERROR
            self._live['error'] = 'interrupted'
            self._live['finished_at'] = _now_iso()
            self._save_locked()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._live))

    def try_begin(self) -> bool:
        with self._lock:
            if self._live.get('state') == STATE_RUNNING:
                return False
            self._live['state'] = STATE_RUNNING
            self._live['started_at'] = _now_iso()
            self._live['finished_at'] = ''
            self._live['error'] = ''
            self._live['progress'] = _empty_progress()
            self._save_locked()
            return True

    def set_progress(self, done: int, total: int, current: str = '') -> None:
        with self._lock:
            self._live['progress'] = {
                'done': int(done),
                'total': int(total),
                'current': str(current or ''),
            }

    def finish(
        self,
        *,
        result: Optional[dict[str, Any]] = None,
        error: str = '',
    ) -> None:
        with self._lock:
            self._live['finished_at'] = _now_iso()
            self._live['error'] = str(error or '')
            if result is not None:
                self._live['result'] = result
            progress = self._live.get('progress') or _empty_progress()
            total = int(progress.get('total') or 0)
            if total:
                progress['done'] = total
                progress['current'] = ''
                self._live['progress'] = progress
            self._live['state'] = STATE_ERROR if error else STATE_DONE
            self._save_locked()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(raw, dict):
            return
        with self._lock:
            for key in (
                'state',
                'started_at',
                'finished_at',
                'error',
                'result',
            ):
                if key in raw:
                    self._live[key] = raw[key]
            progress = raw.get('progress')
            if isinstance(progress, dict):
                self._live['progress'] = {
                    'done': int(progress.get('done') or 0),
                    'total': int(progress.get('total') or 0),
                    'current': str(progress.get('current') or ''),
                }

    def _save_locked(self) -> None:
        payload = {
            'state': self._live.get('state') or STATE_IDLE,
            'started_at': self._live.get('started_at') or '',
            'finished_at': self._live.get('finished_at') or '',
            'error': self._live.get('error') or '',
            'result': self._live.get('result'),
            'progress': self._live.get('progress') or _empty_progress(),
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(payload, indent=2),
                encoding='utf-8',
            )
        except OSError:
            logger.opt(exception=True).warning(
                'Could not persist extra-folder sync status'
            )


def run_external_sync(
    job: ExternalSyncJob,
    *,
    ctx: Any,
    download_dir: Path,
    settings: dict[str, Any],
    lang: str,
    image_kinds: tuple[str, ...],
    lyrics_cache: Optional[Any],
    cover_cache: Optional[Any] = None,
    on_update: Optional[Callable[[dict[str, Any]], None]] = None,
) -> dict[str, Any]:
    """Run a sync on the worker thread and keep *job* up to date."""

    last_push = 0.0

    def _progress(done: int, total: int, current: str = '') -> None:
        nonlocal last_push
        job.set_progress(done, total, current)
        now = time.monotonic()
        if on_update is None:
            return
        if now - last_push < 0.4 and done < total:
            return
        last_push = now
        on_update(job.snapshot())

    try:
        result = sync_external_library(
            ctx,
            download_dir=download_dir,
            settings=settings,
            lang=lang,
            image_kinds=image_kinds,
            lyrics_cache=lyrics_cache,
            cover_cache=cover_cache,
            on_progress=_progress,
        )
    except Exception as exc:
        logger.opt(exception=True).error('External library sync failed')
        job.finish(error=str(exc)[:300])
        snapshot = job.snapshot()
        if on_update is not None:
            on_update(snapshot)
        return snapshot
    job.finish(result=result)
    snapshot = job.snapshot()
    if on_update is not None:
        on_update(snapshot)
    return snapshot


def extra_audio_paths(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    found: list[Path] = []
    for path in root.rglob('*'):
        try:
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                found.append(path)
        except OSError:
            continue
    return found


def unmap_extra_folder(
    root: Path,
    *,
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
    extra_dirs: Sequence[Path] = (),
    cover_cache: Optional[Any] = None,
    metadata_cache: Optional[Any] = None,
    playlist_catalog: Optional[Any] = None,
    track_index: Optional[Any] = None,
    likes: Optional[Any] = None,
    navidrome_index: Optional[Any] = None,
) -> dict[str, Any]:
    """Drop a mapped extra folder from the library without deleting audio."""

    extras = list(extra_dirs)
    try:
        want = root.resolve()
    except OSError:
        want = root
    if not any(_same_path(item, want) for item in extras):
        extras.append(root)
    folder_id = extra_dir_id(root)
    prefix = f'{EXTERNAL_LIBRARY_PREFIX}{folder_id}/'
    stored_set: set[str] = set()
    if track_index is not None:
        for name in track_index.list_filenames():
            if str(name).startswith(prefix):
                stored_set.add(str(name))
    for full in extra_audio_paths(root):
        stored_set.add(
            library_stored_path(full, download_dir, slskd_dir, extras)
        )

    unmapped = 0
    for stored in sorted(stored_set):
        full = locate_library_file(stored, download_dir, slskd_dir, extras)
        if full is not None:
            delete_lrc_sidecar(full)
        if cover_cache is not None:
            if full is not None:
                cover_cache.forget(stored, full_path=full)
            else:
                cover_cache.forget_by_stored_path(stored)
        if metadata_cache is not None:
            metadata_cache.forget(stored, full_path=full)
        if playlist_catalog is not None:
            playlist_catalog.remove_tracks_for_filename(stored)
        if track_index is not None:
            track_index.remove_by_filename(stored)
        if likes is not None:
            likes.unlike(stored)
        if navidrome_index is not None:
            navidrome_index.forget_filename(stored, full_path=full)
        unmapped += 1

    ctx = LibraryContext(
        download_dir=download_dir,
        slskd_dir=slskd_dir,
        extra_dirs=tuple(extras),
    )
    prune_files_from_manual_playlists(ctx, sorted(stored_set))

    invalidate_library_paths_cache()
    logger.info(
        'Unmapped extra folder {} ({} track{})',
        root,
        unmapped,
        '' if unmapped == 1 else 's',
    )
    return {
        'folder': str(root),
        'folder_id': folder_id,
        'unmapped': unmapped,
    }


def _same_path(path: Path, other: Path) -> bool:
    try:
        return path.resolve() == other
    except OSError:
        return path == other


def folders_removed(
    before: dict[str, Any], after: dict[str, Any]
) -> list[Path]:
    """Absolute folders present in *before* and gone from *after*."""

    old_text = set(effective_external_library(before)['folders'])
    new_text = set(effective_external_library(after)['folders'])
    return [Path(item) for item in sorted(old_text - new_text)]
