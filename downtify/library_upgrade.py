"""Scan an existing library for tracks worth improving, then improve them.

A library built up over releases carries whatever each Downtify version
could do at the time: covers at the smallest size a source offered, no
lyrics, tags missing an album or a year. Re-downloading everything to fix
that wastes the files that are already fine, so this module looks at what
is on disk and repairs only what is actually behind.

Three categories are handled, all of them writes to tags:

``artwork``
    Replace a cover smaller than the target with the largest one Spotify,
    iTunes or YouTube Music has for the track.
``lyrics``
    Fill in lyrics for tracks that have none, through the ordered
    provider list (see :mod:`downtify.lyrics`).
``metadata``
    Re-read the track from Spotify and write back album, album artist,
    release date and track number.

Audio itself is never replaced: swapping the file a user already has is
a different problem (match confidence, review of uncertain matches,
playlists and M3Us pointing at the old name) and is deliberately left
out rather than done half-way.

Every write goes to a copy beside the original, which is verified and
only then moved into place, so an interrupted or failed upgrade leaves
the existing file untouched.
"""

from __future__ import annotations

import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger
from mutagen import File as MutagenFile

from . import cover_sources, spotify
from . import lyrics as lyrics_mod
from .downloader import embed_lyrics, embed_metadata
from .library_catalog import (
    UPGRADE_STAGING_MARKER,
    LibraryContext,
    list_library_entries,
)
from .library_paths import locate_library_file
from .library_upgrade_db import (
    JOB_DONE,
    JOB_FAILED,
    JOB_SKIPPED,
    STATE_CANCELLED,
    STATE_DONE,
    STATE_PAUSED,
    STATE_READY,
    STATE_RUNNING,
    STATE_SCANNING,
    LibraryUpgradeDB,
    check_is_fresh,
)
from .lyrics import read_track_lyrics

#: The name an upgrade writes its working copy under. The extension is
#: kept because the tag writers dispatch on it, and
#: ``UPGRADE_STAGING_MARKER`` keeps the library listing from picking the
#: copy up as a track while it exists.
STAGING_TEMPLATE = '{stem}' + UPGRADE_STAGING_MARKER + '{suffix}'

CATEGORY_ARTWORK = 'artwork'
CATEGORY_LYRICS = 'lyrics'
CATEGORY_METADATA = 'metadata'

#: Every category a scan reports on, in the order the UI shows them.
CATEGORIES = (CATEGORY_ARTWORK, CATEGORY_LYRICS, CATEGORY_METADATA)

#: How far a rewritten file's duration may drift from the original
#: before it is rejected. Tag writes don't touch audio, so this only
#: catches a truncated or corrupted copy.
_DURATION_TOLERANCE_SECONDS = 2.0

DEFAULT_ARTWORK_MIN_PX = 600
DEFAULT_RECHECK_DAYS = 30

#: Upper bound on how often progress is pushed to connected clients: a
#: run is tens of thousands of tracks long and every message costs a
#: count query plus a broadcast.
_PUBLISH_INTERVAL_SECONDS = 1.0


@dataclass(frozen=True)
class UpgradeOptions:
    """What an upgrade run should do, and how picky it should be."""

    categories: tuple[str, ...] = CATEGORIES
    artwork_min_px: int = DEFAULT_ARTWORK_MIN_PX
    artwork_source: str = cover_sources.PREFERENCE_HIGHEST
    recheck_days: int = DEFAULT_RECHECK_DAYS

    def as_dict(self) -> dict[str, Any]:
        return {
            'categories': list(self.categories),
            'artwork_min_px': self.artwork_min_px,
            'artwork_source': self.artwork_source,
            'recheck_days': self.recheck_days,
        }


def normalize_categories(raw: Any) -> tuple[str, ...]:
    """Keep the known categories from *raw*, in the canonical order."""

    if not isinstance(raw, (list, tuple)):
        return CATEGORIES
    wanted = {str(item) for item in raw}
    picked = tuple(name for name in CATEGORIES if name in wanted)
    return picked or CATEGORIES


def options_from(payload: dict[str, Any]) -> UpgradeOptions:
    """Build options from a request body, clamped to sane values."""

    def _int(key: str, default: int, low: int, high: int) -> int:
        try:
            value = int(payload.get(key, default))
        except (TypeError, ValueError):
            value = default
        return min(high, max(low, value))

    source = str(payload.get('artwork_source') or '')
    if source not in cover_sources.ARTWORK_SOURCES:
        source = cover_sources.PREFERENCE_HIGHEST
    return UpgradeOptions(
        categories=normalize_categories(payload.get('categories')),
        artwork_min_px=_int(
            'artwork_min_px', DEFAULT_ARTWORK_MIN_PX, 100, 3000
        ),
        artwork_source=source,
        recheck_days=_int('recheck_days', DEFAULT_RECHECK_DAYS, 0, 3650),
    )


# ── Detection ─────────────────────────────────────────────────────────
def _metadata_gaps(entry: dict[str, Any]) -> list[str]:
    """Tag fields a downloaded track should have but doesn't."""

    gaps: list[str] = []
    if not str(entry.get('album') or '').strip():
        gaps.append('album')
    if not str(entry.get('album_artist') or '').strip():
        gaps.append('album_artist')
    if not str(entry.get('year') or '').strip():
        gaps.append('year')
    if not int(entry.get('track_number') or 0):
        gaps.append('track_number')
    return gaps


def _summarize(
    jobs: list[dict[str, Any]], recently_checked: int = 0
) -> dict[str, Any]:
    """How many tracks (and bytes) each category accounts for."""

    counts = {name: 0 for name in CATEGORIES}
    sizes = {name: 0 for name in CATEGORIES}
    for job in jobs:
        for name in job.get('categories') or []:
            if name in counts:
                counts[name] += 1
                sizes[name] += int(job.get('size') or 0)
    return {
        'categories': counts,
        'category_bytes': sizes,
        'tracks': len(jobs),
        # Tracks the scan didn't even read, because every category had
        # been looked at recently enough.
        'recently_checked': int(recently_checked),
    }


def track_findings(
    entry: dict[str, Any],
    full_path: Path,
    *,
    artwork_min_px: int,
) -> list[str]:
    """Which categories this track is behind on."""

    found: list[str] = []
    if int(entry.get('cover_px') or 0) < artwork_min_px:
        found.append(CATEGORY_ARTWORK)
    existing = read_track_lyrics(full_path)
    if not (existing.get('synced') or existing.get('plain')):
        found.append(CATEGORY_LYRICS)
    if _metadata_gaps(entry):
        found.append(CATEGORY_METADATA)
    return found


# ── The song a track describes ────────────────────────────────────────
def _song_from_tags(entry: dict[str, Any]) -> dict[str, Any]:
    artist = str(entry.get('artist') or '')
    artists = [part.strip() for part in artist.split(';') if part.strip()]
    return {
        'name': str(entry.get('title') or ''),
        'artists': artists or ([artist] if artist else []),
        'artist': artist,
        'album_name': str(entry.get('album') or ''),
        'album_artist': str(entry.get('album_artist') or ''),
        'year': str(entry.get('year') or ''),
        'track_number': int(entry.get('track_number') or 0),
        'duration': float(entry.get('duration') or 0.0),
    }


def _merge_remote(
    local: dict[str, Any], remote: dict[str, Any]
) -> dict[str, Any]:
    """Remote metadata wins, but never blanks something the file has."""

    merged = dict(local)
    for key, value in remote.items():
        if value in (None, '', [], 0):
            continue
        merged[key] = value
    if not merged.get('name'):
        merged['name'] = local.get('name', '')
    return merged


def song_for_track(
    entry: dict[str, Any],
    *,
    spotify_id: str = '',
    refresh_metadata: bool = False,
) -> dict[str, Any]:
    """The track as Downtify would describe it when tagging it today.

    Without ``refresh_metadata`` this is only what the file's own tags
    say, which is what an artwork- or lyrics-only upgrade writes back:
    nothing else about the file then changes.
    """

    song = _song_from_tags(entry)
    if spotify_id:
        song['song_id'] = spotify_id
    if not (refresh_metadata and spotify_id):
        return song
    try:
        remote = spotify.track_from_id(spotify_id)
    except Exception:
        logger.opt(exception=True).debug(
            'Library upgrade: Spotify lookup failed for {}', spotify_id
        )
        return song
    return _merge_remote(song, remote or {})


# ── Safe file replacement ─────────────────────────────────────────────
def _audio_length(path: Path) -> float:
    try:
        audio = MutagenFile(str(path))
    except Exception:
        return 0.0
    info = getattr(audio, 'info', None)
    return float(getattr(info, 'length', 0.0) or 0.0)


def _verify_replacement(staged: Path, expected_seconds: float) -> bool:
    """A rewritten file must still be readable audio of the same length."""

    try:
        if staged.stat().st_size <= 0:
            return False
    except OSError:
        return False
    length = _audio_length(staged)
    if length <= 0:
        return False
    if expected_seconds <= 0:
        return True
    return abs(length - expected_seconds) <= _DURATION_TOLERANCE_SECONDS


@dataclass
class _Staged:
    original: Path
    staged: Path
    mtime_ns: int
    atime_ns: int
    duration: float


def staging_path(path: Path) -> Path:
    return path.with_name(
        STAGING_TEMPLATE.format(stem=path.stem, suffix=path.suffix)
    )


def _stage(path: Path) -> _Staged:
    staged = staging_path(path)
    shutil.copy2(str(path), str(staged))
    st = path.stat()
    return _Staged(
        original=path,
        staged=staged,
        mtime_ns=int(st.st_mtime_ns),
        atime_ns=int(st.st_atime_ns),
        duration=_audio_length(path),
    )


def _commit(stage: _Staged) -> bool:
    """Swap the working copy in, or throw it away if it doesn't verify."""

    if not _verify_replacement(stage.staged, stage.duration):
        logger.warning(
            'Library upgrade: staged copy of {} failed verification',
            stage.original.name,
        )
        stage.staged.unlink(missing_ok=True)
        return False
    os.replace(str(stage.staged), str(stage.original))
    # Keep the original timestamp: the Library sorts "recently added" by
    # it, and an upgrade is not a new download.
    try:
        os.utime(str(stage.original), ns=(stage.atime_ns, stage.mtime_ns))
    except OSError:
        pass
    return True


def _discard(stage: _Staged) -> None:
    stage.staged.unlink(missing_ok=True)


# ── Applying one track ────────────────────────────────────────────────
@dataclass
class UpgradeOutcome:
    status: str = JOB_SKIPPED
    detail: str = ''
    changed: list[str] = field(default_factory=list)
    artwork_px: int = 0
    artwork_source: str = ''


@dataclass
class UpgradeDeps:
    """Everything an upgrade needs from the running app."""

    context: Callable[[], LibraryContext]
    settings: Callable[[], dict[str, Any]]
    version: str = '0.0.0'
    spotify_id_for: Optional[Callable[[str], str]] = None
    lyrics_cache: Any = None
    publish: Optional[Callable[[dict[str, Any]], None]] = None


def resolve_track(stored_path: str, ctx: LibraryContext) -> Optional[Path]:
    return locate_library_file(stored_path, ctx.download_dir, ctx.slskd_dir)


@dataclass
class _Artwork:
    """The cover an upgrade decided on, and where it came from."""

    data: Optional[bytes] = None
    px: int = 0
    source: str = ''


def _library_entry(
    stored_path: str, ctx: LibraryContext
) -> Optional[tuple[Path, dict[str, Any]]]:
    full = resolve_track(stored_path, ctx)
    if full is None or ctx.metadata_cache is None:
        return None
    entries = ctx.metadata_cache.get_entries_batch([(stored_path, full)])
    return (full, entries[0]) if entries else None


def _pick_artwork(
    song: dict[str, Any],
    full: Path,
    entry: dict[str, Any],
    *,
    options: UpgradeOptions,
) -> _Artwork:
    """A bigger cover than the file has, or the file's own size."""

    have = int(entry.get('cover_px') or 0)
    if CATEGORY_ARTWORK not in options.categories:
        return _Artwork(px=have)
    if have >= options.artwork_min_px:
        return _Artwork(px=have)
    better = cover_sources.best_cover(
        song,
        current=cover_sources.current_cover(full),
        preference=options.artwork_source,
    )
    if better is None:
        return _Artwork(px=have)
    return _Artwork(data=better.data, px=better.width, source=better.source)


def _pick_lyrics(
    song: dict[str, Any],
    full: Path,
    *,
    deps: UpgradeDeps,
    options: UpgradeOptions,
) -> Optional[lyrics_mod.Lyrics]:
    """Lyrics for a track that has none, or ``None`` to leave it be."""

    if CATEGORY_LYRICS not in options.categories:
        return None
    existing = read_track_lyrics(full)
    if existing.get('synced') or existing.get('plain'):
        return None
    providers = list(deps.settings().get('lyrics_providers') or [])
    if not providers:
        return None
    found = lyrics_mod.fetch(song, providers, deps.lyrics_cache)
    return found if found is not None and found.has_any() else None


def _write_upgrade(
    full: Path,
    song: dict[str, Any],
    *,
    artwork: _Artwork,
    new_lyrics: Optional[lyrics_mod.Lyrics],
    write_tags: bool,
) -> Optional[str]:
    """Rewrite *full* through a verified working copy; error text or ``None``."""

    try:
        stage = _stage(full)
    except OSError as exc:
        return f'Could not stage a copy: {exc}'

    try:
        if write_tags:
            # The existing cover is written back when nothing better was
            # found, so a metadata-only pass never strips artwork.
            keep = cover_sources.current_cover(full)
            embed_metadata(
                stage.staged,
                song,
                download_cover=True,
                cover_bytes=artwork.data
                or (keep.data if keep is not None else None),
            )
        if new_lyrics is not None:
            embed_lyrics(stage.staged, new_lyrics)
    except Exception as exc:
        _discard(stage)
        logger.opt(exception=True).warning(
            'Library upgrade failed for {}', full.name
        )
        return str(exc)[:200]

    staged_lrc = stage.staged.with_suffix('.lrc')
    if not _commit(stage):
        staged_lrc.unlink(missing_ok=True)
        return 'The rewritten file did not verify; kept the original'
    if new_lyrics is not None and staged_lrc.exists():
        # embed_lyrics wrote the .lrc beside the working copy.
        os.replace(str(staged_lrc), str(full.with_suffix('.lrc')))
    return None


def _outcome_detail(changed: list[str], artwork: _Artwork) -> str:
    parts: list[str] = []
    for name in changed:
        if name == CATEGORY_ARTWORK and artwork.px:
            parts.append(f'artwork {artwork.px}px ({artwork.source})')
        else:
            parts.append(name)
    return ', '.join(parts)


def upgrade_track(
    stored_path: str,
    *,
    deps: UpgradeDeps,
    options: UpgradeOptions,
    on_stage: Optional[Callable[[str], None]] = None,
) -> UpgradeOutcome:
    """Apply the requested categories to one library track."""

    def stage_now(name: str) -> None:
        if on_stage:
            on_stage(name)

    ctx = deps.context()
    found = _library_entry(stored_path, ctx)
    if found is None:
        return UpgradeOutcome(JOB_SKIPPED, 'File is no longer in the library')
    full, entry = found

    spotify_id = (
        deps.spotify_id_for(stored_path) or ''
        if deps.spotify_id_for is not None
        else ''
    )
    stage_now('matching')
    song = song_for_track(
        entry,
        spotify_id=spotify_id,
        refresh_metadata=CATEGORY_METADATA in options.categories,
    )

    stage_now('artwork')
    artwork = _pick_artwork(song, full, entry, options=options)
    stage_now('lyrics')
    new_lyrics = _pick_lyrics(song, full, deps=deps, options=options)

    changed: list[str] = []
    if artwork.data is not None:
        changed.append(CATEGORY_ARTWORK)
    if (
        CATEGORY_METADATA in options.categories
        and spotify_id
        and _metadata_gaps(entry)
    ):
        changed.append(CATEGORY_METADATA)
    if not changed and new_lyrics is None:
        return UpgradeOutcome(
            JOB_SKIPPED,
            'Already up to date',
            artwork_px=artwork.px,
            artwork_source=artwork.source,
        )

    stage_now('writing')
    error = _write_upgrade(
        full,
        song,
        artwork=artwork,
        new_lyrics=new_lyrics,
        write_tags=bool(changed),
    )
    if error:
        return UpgradeOutcome(JOB_FAILED, error)

    if new_lyrics is not None:
        changed.append(CATEGORY_LYRICS)
    if ctx.metadata_cache is not None:
        try:
            ctx.metadata_cache.refresh(stored_path, full)
        except Exception:
            logger.debug('Library upgrade: metadata cache refresh failed')

    return UpgradeOutcome(
        JOB_DONE,
        _outcome_detail(changed, artwork),
        changed=changed,
        artwork_px=artwork.px,
        artwork_source=artwork.source,
    )


# ── Scan + queue runner ───────────────────────────────────────────────
class LibraryUpgradeRunner:
    """Owns the scan and the worker thread that drains the queue."""

    def __init__(self, db: LibraryUpgradeDB, deps: UpgradeDeps) -> None:
        self.db = db
        self.deps = deps
        self._lock = threading.Lock()
        self._worker: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._cancelled = False
        self._scanned = 0
        self._scan_total = 0
        self._last_publish = 0.0

    # -- helpers --
    def _publish(
        self,
        extra: Optional[dict[str, Any]] = None,
        *,
        throttle: bool = False,
    ) -> None:
        """Broadcast progress, at most once a second while grinding."""

        if self.deps.publish is None:
            return
        now = time.monotonic()
        if throttle and now - self._last_publish < _PUBLISH_INTERVAL_SECONDS:
            return
        self._last_publish = now
        try:
            self.deps.publish(self.status(extra))
        except Exception:
            logger.debug('Library upgrade: progress broadcast failed')

    def status(self, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        run = self.db.latest_run()
        if run is None:
            return {'state': 'idle', 'run': None, 'counts': {}, 'scan': {}}
        counts = self.db.counts(int(run['id']))
        payload: dict[str, Any] = {
            'state': run['state'],
            'run': run,
            'counts': counts,
            # Carried by every progress message, not only the initial
            # GET, so a client that only ever sees WebSocket updates
            # still knows what the scan found.
            'summary': self._summary_for(run),
            'scan': {
                'scanned': self._scanned,
                'total': self._scan_total,
            },
        }
        if extra:
            payload.update(extra)
        return payload

    def busy(self) -> bool:
        worker = self._worker
        return worker is not None and worker.is_alive()

    # -- scanning --
    def start_scan(self, options: UpgradeOptions) -> dict[str, Any]:
        with self._lock:
            if self.busy():
                raise RuntimeError('A library upgrade is already running')
            run_id = self.db.create_run(list(CATEGORIES), options.as_dict())
            self._cancelled = False
            self._stop.clear()
            self._scanned = 0
            self._scan_total = 0
            self._worker = threading.Thread(
                target=self._scan,
                args=(run_id, options),
                name='downtify-upgrade-scan',
                daemon=True,
            )
            self._worker.start()
        return self.status()

    def _scan(self, run_id: int, options: UpgradeOptions) -> None:
        try:
            ctx = self.deps.context()
            entries = list_library_entries(ctx)
            self._scan_total = len(entries)
            checks = self.db.checks_for([str(e['file']) for e in entries])
            jobs: list[dict[str, Any]] = []
            checked: list[tuple[str, list[str]]] = []
            total_bytes = 0
            skipped = 0
            for index, entry in enumerate(entries, start=1):
                if self._stop.is_set():
                    self.db.set_state(run_id, STATE_CANCELLED)
                    self._publish()
                    return
                stored = str(entry['file'])
                total_bytes += int(entry.get('size') or 0)
                self._scanned = index
                self._publish(throttle=True)
                due = self._categories_due(
                    checks.get(stored) or {}, options.recheck_days
                )
                if not due:
                    # Every category was looked at recently: don't even
                    # read the file.
                    skipped += 1
                    continue
                full = resolve_track(stored, ctx)
                if full is None:
                    continue
                behind = set(
                    track_findings(
                        entry, full, artwork_min_px=options.artwork_min_px
                    )
                )
                found = [name for name in CATEGORIES if name in due & behind]
                # Looking and finding nothing counts as a check, so the
                # next scan doesn't read this file again for those.
                clean = sorted(due - behind)
                if clean:
                    checked.append((stored, clean))
                if found:
                    jobs.append({
                        'file': stored,
                        'categories': found,
                        'size': int(entry.get('size') or 0),
                        'title': str(entry.get('title') or ''),
                        'artist': str(entry.get('artist') or ''),
                    })
            self.db.record_checks(checked, app_version=self.deps.version)
            self.db.add_jobs(run_id, jobs)
            self.db.set_totals(run_id, len(entries), total_bytes)
            self.db.set_summary(run_id, _summarize(jobs, skipped))
            self.db.set_state(run_id, STATE_READY)
        except Exception:
            logger.opt(exception=True).error('Library upgrade scan failed')
            self.db.set_state(run_id, STATE_CANCELLED)
        self._publish()

    def _categories_due(
        self, track_checks: dict[str, Any], recheck_days: int
    ) -> set[str]:
        """Categories this track hasn't had looked at recently.

        Kept per category: repairing a track's artwork says nothing
        about whether anyone ever went looking for its lyrics, so a
        later run for another category must still consider it.
        """

        return {
            name
            for name in CATEGORIES
            if not check_is_fresh(
                track_checks.get(name),
                app_version=self.deps.version,
                max_age_days=recheck_days,
            )
        }

    @staticmethod
    def _summary_for(run: dict[str, Any]) -> dict[str, Any]:
        stored = run.get('summary') or {}
        return {
            'categories': stored.get('categories') or {},
            'category_bytes': stored.get('category_bytes') or {},
            'tracks': int(stored.get('tracks') or 0),
            'recently_checked': int(stored.get('recently_checked') or 0),
            'library_tracks': int(run['total_tracks'] or 0),
            'library_bytes': int(run['total_bytes'] or 0),
        }

    def scan_summary(self) -> dict[str, Any]:
        """Per-category counts for the finished scan of the latest run."""

        run = self.db.latest_run()
        if run is None:
            return {'categories': {}, 'category_bytes': {}, 'tracks': 0}
        return self._summary_for(run)

    # -- running --
    def start(self, categories: tuple[str, ...]) -> dict[str, Any]:
        with self._lock:
            if self.busy():
                raise RuntimeError('A library upgrade is already running')
            run = self.db.latest_run()
            if run is None or run['state'] not in {
                STATE_READY,
                STATE_PAUSED,
            }:
                raise RuntimeError('Scan the library before upgrading it')
            run_id = int(run['id'])
            # Remembered so a resume after a restart runs the same
            # categories the user picked, not everything the scan found.
            self.db.set_categories(run_id, list(categories))
            options = UpgradeOptions(
                categories=categories,
                artwork_min_px=int(
                    run['options'].get('artwork_min_px')
                    or DEFAULT_ARTWORK_MIN_PX
                ),
                artwork_source=str(
                    run['options'].get('artwork_source')
                    or cover_sources.PREFERENCE_HIGHEST
                ),
                recheck_days=int(
                    run['options'].get('recheck_days') or DEFAULT_RECHECK_DAYS
                ),
            )
            self._begin(run_id, options)
        return self.status()

    def _begin(self, run_id: int, options: UpgradeOptions) -> None:
        self._cancelled = False
        self._stop.clear()
        self.db.requeue_running(run_id)
        self.db.set_state(run_id, STATE_RUNNING)
        self._worker = threading.Thread(
            target=self._run,
            args=(run_id, options),
            name='downtify-upgrade',
            daemon=True,
        )
        self._worker.start()

    def _run(self, run_id: int, options: UpgradeOptions) -> None:
        wanted = set(options.categories)
        while not self._stop.is_set():
            job = self.db.take_next(run_id)
            if job is None:
                self.db.set_state(run_id, STATE_DONE)
                break
            stored = str(job['file'])
            todo = [name for name in job['categories'] if name in wanted]
            if not todo:
                self.db.finish_job(
                    run_id, stored, JOB_SKIPPED, detail='Not selected'
                )
                continue
            self._process(run_id, stored, options, todo)
            self._publish(throttle=True)
        else:
            state = STATE_CANCELLED if self._cancelled else STATE_PAUSED
            self.db.requeue_running(run_id)
            self.db.set_state(run_id, state)
        self._publish()

    def _process(
        self,
        run_id: int,
        stored: str,
        options: UpgradeOptions,
        todo: list[str],
    ) -> None:
        def on_stage(stage: str) -> None:
            self.db.set_stage(run_id, stored, stage)

        try:
            outcome = upgrade_track(
                stored,
                deps=self.deps,
                options=UpgradeOptions(
                    categories=tuple(todo),
                    artwork_min_px=options.artwork_min_px,
                    artwork_source=options.artwork_source,
                    recheck_days=options.recheck_days,
                ),
                on_stage=on_stage,
            )
        except Exception as exc:
            logger.opt(exception=True).warning(
                'Library upgrade: {} failed', stored
            )
            outcome = UpgradeOutcome(JOB_FAILED, str(exc)[:200])

        self.db.finish_job(
            run_id,
            stored,
            outcome.status,
            detail=outcome.detail,
            changed=outcome.changed,
        )
        if outcome.status != JOB_FAILED:
            # Only the categories this run actually looked at: the rest
            # stay due, so a later run for them still considers the
            # track.
            self.db.record_check(
                stored,
                todo,
                app_version=self.deps.version,
                artwork_px=outcome.artwork_px,
                artwork_source=outcome.artwork_source,
            )

    def pause(self) -> dict[str, Any]:
        self._cancelled = False
        self._stop.set()
        return self.status()

    def cancel(self) -> dict[str, Any]:
        run = self.db.latest_run()
        self._cancelled = True
        self._stop.set()
        if run is not None and not self.busy():
            self.db.set_state(int(run['id']), STATE_CANCELLED)
        return self.status()

    def resume(self) -> dict[str, Any]:
        run = self.db.latest_run()
        if run is None or run['state'] != STATE_PAUSED:
            raise RuntimeError('Nothing to resume')
        return self.start(normalize_categories(run['categories']))

    def resume_after_restart(self) -> None:
        """Pick a run back up when the process died mid-upgrade."""

        run = self.db.latest_run()
        if run is None:
            return
        run_id = int(run['id'])
        if run['state'] == STATE_SCANNING:
            # A half-finished scan can't be trusted; drop it.
            self.db.delete_run_jobs(run_id)
            self.db.set_state(run_id, STATE_CANCELLED)
            return
        if run['state'] != STATE_RUNNING:
            return
        requeued = self.db.requeue_running(run_id)
        options = UpgradeOptions(
            categories=normalize_categories(run['categories']),
            artwork_min_px=int(
                run['options'].get('artwork_min_px') or DEFAULT_ARTWORK_MIN_PX
            ),
            artwork_source=str(
                run['options'].get('artwork_source')
                or cover_sources.PREFERENCE_HIGHEST
            ),
            recheck_days=int(
                run['options'].get('recheck_days') or DEFAULT_RECHECK_DAYS
            ),
        )
        logger.info(
            'Library upgrade: resuming run {} ({} track(s) re-queued)',
            run_id,
            requeued,
        )
        with self._lock:
            self._begin(run_id, options)
