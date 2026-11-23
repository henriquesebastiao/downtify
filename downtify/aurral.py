"""Hand-over downloads for Aurral (https://github.com/lklynet/aurral).

Aurral is a self-hosted music app with its own library and download
sources. Its Downtify plugin (in ``lklynet/aurral-plugins``) uses
Downtify as one of those sources: Aurral asks Downtify for a song or an
album, Downtify fetches it the way it fetches its own downloads
(YouTube Music, slskd, SoundCloud, Deezer through deemix, with covers,
lyrics and tags), and Aurral takes the finished files and files them in
its own library.

Off until an admin turns it on (``aurral_enabled``, Settings > Apps >
Aurral). Nothing else in Downtify changes either way.

A hand-over download stays out of Downtify's own library:

* it is written to its own folder, ``aurral-handover/<job>`` beside
  ``settings.json``, never to the music folder;
* none of the after-download bookkeeping runs: no track index, library
  listing, playlists, Navidrome, download log or "where it came from"
  record;
* a song Downtify already has is handed over from the library as it is
  (read only), so it isn't downloaded a second time;
* with slskd, the file is copied out of slskd's folder and slskd's own
  copy is left alone, so nothing in slskd's folder is ever deleted;
* the folder is deleted when Aurral has taken the files, when Aurral
  cancels, after :data:`JOB_TTL_SECONDS`, and on every start.

Jobs live in memory: after a restart Aurral's next status check gets a
404 and Aurral moves on to its next source, as it does for any failed
download.
"""

from __future__ import annotations

import asyncio
import contextlib
import copy
import secrets
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger

from .api import _effective_audio_providers
from .library_paths import locate_library_file, slskd_dir_from_downloader
from .track_index import resolve_existing_download

#: The setting that turns hand-over on.
SETTING = 'aurral_enabled'
#: The folder hand-over downloads go to, beside ``settings.json``.
FOLDER_NAME = 'aurral-handover'
#: A job and its files are dropped this long after it was asked for
#: (Aurral gives up on a download after a day).
JOB_TTL_SECONDS = 26 * 3600
#: The most tracks one album job downloads.
MAX_ALBUM_TRACKS = 200
#: The most results one search returns (Aurral reads up to 50).
MAX_RESULTS = 20

AUDIO_SUFFIXES = frozenset({
    '.mp3',
    '.flac',
    '.m4a',
    '.ogg',
    '.opus',
    '.wav',
    '.aac',
    '.alac',
    '.aiff',
    '.wma',
    '.webm',
})

QUEUED = 'queued'
DOWNLOADING = 'downloading'
DONE = 'done'
FAILED = 'failed'


def enabled(settings: dict[str, Any]) -> bool:
    return bool((settings or {}).get(SETTING))


# ── Search results, shaped for Aurral ────────────────────────────────


def search_query(*parts: Any) -> str:
    """One search text from the non-empty *parts* (artist, title...)."""

    return ' '.join(
        str(part).strip() for part in parts if str(part or '').strip()
    )


def _artist_text(row: dict[str, Any]) -> str:
    artists = row.get('artists')
    if isinstance(artists, list):
        names = [str(name).strip() for name in artists if str(name).strip()]
        if names:
            return ', '.join(names)
    return str(row.get('artist') or '').strip()


def _year(value: Any) -> Optional[int]:
    text = str(value or '').strip()[:4]
    return int(text) if text.isdigit() else None


def audio_quality(
    settings: dict[str, Any],
) -> tuple[Optional[str], Optional[int]]:
    """``(format, kbps)`` every download will have, when it is known.

    Only YouTube sources are converted to the chosen format; slskd,
    SoundCloud and deemix files keep their own, so with any of those on
    the quality isn't known before the download.
    """

    sources = set(_effective_audio_providers(settings))
    fmt = str(settings.get('format') or '').strip().lower()
    if not sources <= {'youtube-music', 'youtube'} or fmt in {'', 'original'}:
        return None, None
    try:
        kbps = int(str(settings.get('bitrate') or '').strip())
    except ValueError:
        kbps = None
    return fmt, (kbps if fmt in {'mp3', 'm4a', 'ogg', 'opus'} else None)


def track_result(
    row: dict[str, Any], settings: dict[str, Any]
) -> Optional[dict[str, Any]]:
    """A song search row as an Aurral track result, or ``None``."""

    song_id = str(row.get('song_id') or '').strip()
    title = str(row.get('name') or '').strip()
    artist = _artist_text(row)
    if not song_id or not title or not artist:
        return None
    fmt, kbps = audio_quality(settings)
    try:
        duration_ms = int(float(row.get('duration') or 0) * 1000) or None
    except (TypeError, ValueError):
        duration_ms = None
    return {
        'id': song_id,
        'title': title,
        'artist': artist,
        'album': str(row.get('album_name') or '').strip() or None,
        'durationMs': duration_ms,
        'format': fmt,
        'bitrate': kbps,
        'data': {'song': row},
    }


def album_result(row: dict[str, Any]) -> Optional[dict[str, Any]]:
    """An album search row as an Aurral album result, or ``None``."""

    album_id = str(row.get('album_id') or '').strip()
    title = str(row.get('name') or '').strip()
    artist = _artist_text(row)
    url = str(row.get('url') or '').strip()
    if not album_id or not title or not artist or not url:
        return None
    return {
        'id': album_id,
        'title': title,
        'artist': artist,
        'year': _year(row.get('year')),
        'data': {'url': url},
    }


# ── Jobs ────────────────────────────────────────────────────────────────


@dataclass
class HandoverFile:
    path: Path
    #: Shown to Aurral: the file's name inside the job.
    name: str
    #: From Downtify's own library (never deleted with the job).
    from_library: bool = False

    def to_dict(self, index: int) -> dict[str, Any]:
        try:
            size = self.path.stat().st_size
        except OSError:
            size = 0
        return {'index': index, 'name': self.name, 'size': size}


@dataclass
class Job:
    id: str
    kind: str
    label: str
    user_id: int
    folder: Path
    created: float = field(default_factory=time.time)
    status: str = QUEUED
    message: str = ''
    total: int = 1
    finished: int = 0
    failed: int = 0
    files: list[HandoverFile] = field(default_factory=list)
    cancelled: bool = False
    task: Optional[asyncio.Task] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'kind': self.kind,
            'label': self.label,
            'status': self.status,
            'message': self.message,
            'total': self.total,
            'finished': self.finished,
            'failed': self.failed,
            'files': [f.to_dict(i) for i, f in enumerate(self.files)],
        }


class Jobs:
    """Hand-over jobs in memory, each with its own folder under *root*."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def clear_folder(self) -> None:
        """Delete what an earlier run left behind (on start)."""

        if self.root.is_dir():
            shutil.rmtree(self.root, ignore_errors=True)

    def new(self, kind: str, label: str, user_id: int, total: int = 1) -> Job:
        self.prune()
        job_id = secrets.token_hex(8)
        folder = self.root / job_id
        folder.mkdir(parents=True, exist_ok=True)
        job = Job(
            id=job_id,
            kind=kind,
            label=label,
            user_id=user_id,
            folder=folder,
            total=total,
        )
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(
        self, job_id: str, user_id: int, admin: bool = False
    ) -> Optional[Job]:
        """*job_id*, when it is *user_id*'s (or anyone's for an admin)."""

        with self._lock:
            job = self._jobs.get(job_id)
        if job is None or (job.user_id != user_id and not admin):
            return None
        return job

    def all(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def drop(self, job_id: str) -> Optional[Job]:
        """Forget *job_id*, stop it and delete its folder."""

        with self._lock:
            job = self._jobs.pop(job_id, None)
        if job is None:
            return None
        job.cancelled = True
        if job.task is not None and not job.task.done():
            job.task.cancel()
        shutil.rmtree(job.folder, ignore_errors=True)
        return job

    def prune(self, now: Optional[float] = None) -> list[str]:
        """Drop jobs older than :data:`JOB_TTL_SECONDS`."""

        now = time.time() if now is None else now
        stale = [
            job.id for job in self.all() if now - job.created > JOB_TTL_SECONDS
        ]
        for job_id in stale:
            self.drop(job_id)
        return stale


# ── Downloading for Aurral ───────────────────────────────────────────


def handover_downloader(downloader: Any, folder: Path) -> Any:
    """A copy of the app's *downloader* that writes to *folder* only.

    Same sources, formats, covers, lyrics and tags as Downtify's own
    downloads, but no file layout (one flat folder), no skipping of
    songs found in the library by file name (that check is done before,
    read only), no hooks into the library's stores, and slskd's copy of a
    transfer is never removed.
    """

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    dl = copy.copy(downloader)
    dl.download_dir = folder
    dl.organize_by_artist = False
    dl.organize_by_album = False
    dl.overwrite_existing_files = True
    dl.on_downloaded = None
    dl.on_outcome = None
    dl.download_sources = None
    dl.hand_replaced = None
    dl.download_policy = None
    dl._target_locks = {}
    dl._target_locks_guard = threading.Lock()
    slskd = dict(getattr(downloader, 'slskd_settings', None) or {})
    slskd['leave_in_place'] = False
    slskd['output_dir'] = str(folder)
    dl.slskd_settings = slskd
    # slskd's own copy of the transfer stays where slskd put it.
    dl._remove_slskd_source_after_import = lambda *args, **kwargs: None
    return dl


def _deemix_dirs(downloader: Any) -> list[Path]:
    settings = getattr(downloader, 'deemix_settings', None) or {}
    source = str(settings.get('source_dir') or '').strip()
    return [Path(source)] if source else []


def downloaded_file(
    stored: str, folder: Path, downloader: Any
) -> Optional[Path]:
    """The file *stored* (a name the hand-over downloader returned) in
    *folder*, copied in first when the source left it elsewhere (deemix's
    folder)."""

    if not stored:
        return None
    inside = (Path(folder) / stored).resolve()
    if inside.is_file() and Path(folder).resolve() in inside.parents:
        return inside
    found = locate_library_file(
        stored,
        Path(downloader.download_dir),
        slskd_dir_from_downloader(downloader),
        _deemix_dirs(downloader),
    )
    if found is None or not found.is_file():
        return None
    target = Path(folder) / found.name
    shutil.copy2(found, target)
    return target


def library_file(
    downloader: Any, song: dict[str, Any], track_index: Any
) -> Optional[Path]:
    """The song's file in Downtify's own library, when it has one."""

    if downloader is None:
        return None
    try:
        hit = resolve_existing_download(
            downloader, song, track_index=track_index
        )
    except Exception:
        logger.opt(exception=True).debug('Aurral: library lookup failed')
        return None
    if not hit:
        return None
    full = locate_library_file(
        hit[0],
        Path(downloader.download_dir),
        slskd_dir_from_downloader(downloader),
    )
    return full if full is not None and full.is_file() else None


def unique_name(folder_files: list[HandoverFile], name: str) -> str:
    taken = {f.name for f in folder_files}
    if name not in taken:
        return name
    stem, dot, suffix = name.rpartition('.')
    if not dot:
        stem, suffix = name, ''
    n = 2
    while True:
        candidate = f'{stem} ({n}){"." + suffix if suffix else ""}'
        if candidate not in taken:
            return candidate
        n += 1


def fetch_song(
    job: Job,
    song: dict[str, Any],
    downloader: Any,
    track_index: Any,
    progress: Optional[Callable[..., None]] = None,
) -> HandoverFile:
    """Get one song for *job*: from the library, else a fresh download
    into the job's folder. Raises when neither works."""

    existing = library_file(downloader, song, track_index)
    if existing is not None:
        return HandoverFile(
            path=existing,
            name=unique_name(job.files, existing.name),
            from_library=True,
        )
    dl = handover_downloader(downloader, job.folder)
    stored = dl.download(song, progress)
    path = downloaded_file(stored, job.folder, downloader)
    if path is None or path.suffix.lower() not in AUDIO_SUFFIXES:
        raise RuntimeError('The download finished without an audio file')
    return HandoverFile(path=path, name=unique_name(job.files, path.name))


async def run_job(
    job: Job,
    songs: list[dict[str, Any]],
    *,
    downloader: Any,
    track_index: Any,
    executor: Any,
    semaphore: Optional[asyncio.Semaphore],
) -> None:
    """Download *songs* for *job*, one at a time, each taking one of the
    shared download slots (Settings > Downloads > Parallel downloads)."""

    loop = asyncio.get_running_loop()
    errors: list[str] = []
    job.total = len(songs)
    for song in songs:
        if job.cancelled:
            return
        slot = semaphore if semaphore is not None else contextlib.nullcontext()
        async with slot:
            if job.cancelled:
                return
            job.status = DOWNLOADING
            try:
                found = await loop.run_in_executor(
                    executor,
                    lambda song=song: fetch_song(
                        job, song, downloader, track_index
                    ),
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                job.failed += 1
                errors.append(str(exc) or exc.__class__.__name__)
                logger.warning(
                    'Aurral: could not get {!r}: {}', song.get('name'), exc
                )
            else:
                job.files.append(found)
            job.finished += 1
    if job.cancelled:
        return
    if job.files:
        job.status = DONE
        job.message = (
            f'{job.failed} of {job.total} could not be downloaded'
            if job.failed
            else ''
        )
    else:
        job.status = FAILED
        job.message = errors[0] if errors else 'Nothing was downloaded'
    logger.info(
        'Aurral: {} {!r} {} ({} file(s), {} failed)',
        job.kind,
        job.label,
        job.status,
        len(job.files),
        job.failed,
    )


def file_for(job: Job, index: int) -> Optional[HandoverFile]:
    if 0 <= index < len(job.files):
        found = job.files[index]
        if found.path.is_file():
            return found
    return None
