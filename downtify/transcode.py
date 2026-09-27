"""Transcoding for streaming over a slow or metered connection.

A phone on mobile data asks for a smaller copy of a track (e.g. Opus at
160 kbps) instead of the original FLAC. Two ways to serve that:

* **Stream ffmpeg's output as it's produced.** First byte in well under a
  second, but the length isn't known up front and the client can't seek
  (no HTTP Range) until the whole thing has been produced - and seeking
  is the first thing a player does when it resumes a track.
* **Transcode to a cached file, then serve that file.** The request waits
  for ffmpeg - a few seconds for a song, since ffmpeg runs 50-100x faster
  than real time - and from then on it's an ordinary file: exact
  ``Content-Length``, full Range support, and every later play of the same
  track at the same quality is instant.

Downtify does the second: seeking must work, and songs are short. The
cache lives in ``<data>/transcode_cache``, is bounded by size (least
recently used files go first) and keyed by the source file's path, size
and modification time plus the format and bitrate, so a re-tagged or
replaced file is never served stale. At most
:data:`DEFAULT_MAX_CONCURRENT` ffmpeg processes run at once; two requests
for the same copy share one run; and when every request waiting for a run
has gone away (the client disconnected), the run is stopped and its
partial file deleted.

A track is never transcoded when the original already fits what was asked
for - a lossy file at or below the requested bitrate is served as is, the
same rule the downloader follows when it doesn't re-encode (see
``docs/features/download-settings.md``).
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from loguru import logger

#: Bitrates (kbps) a client may ask for.
BITRATES = (96, 128, 160, 192, 256, 320)
#: ffmpeg processes allowed at once, by default.
DEFAULT_MAX_CONCURRENT = 2
#: Size the cache is kept under, by default.
DEFAULT_CACHE_BYTES = 2 * 1024**3
#: Longest a single transcode may take.
TRANSCODE_TIMEOUT = 300.0

#: Codecs that are already lossy: served as is when small enough.
_LOSSY = frozenset({'mp3', 'aac', 'opus', 'vorbis'})


@dataclass(frozen=True)
class Format:
    name: str
    codec: str
    extension: str
    media_type: str
    args: tuple[str, ...]


FORMATS: dict[str, Format] = {
    'opus': Format(
        'opus',
        'opus',
        '.opus',
        'audio/ogg',
        ('-c:a', 'libopus', '-vbr', 'on', '-f', 'ogg'),
    ),
    'aac': Format(
        'aac',
        'aac',
        '.m4a',
        'audio/mp4',
        ('-c:a', 'aac', '-movflags', '+faststart', '-f', 'mp4'),
    ),
    'mp3': Format(
        'mp3',
        'mp3',
        '.mp3',
        'audio/mpeg',
        ('-c:a', 'libmp3lame', '-f', 'mp3'),
    ),
}


def normalize_bitrate(value: Any) -> int:
    """The nearest allowed bitrate at or above *value* (kbps); the
    highest one for anything above it; ``0`` for something unreadable."""

    try:
        wanted = int(value)
    except (TypeError, ValueError):
        return 0
    if wanted <= 0:
        return 0
    for bitrate in BITRATES:
        if bitrate >= wanted:
            return bitrate
    return BITRATES[-1]


def serve_original(codec: str, bitrate_bps: int, bitrate_kbps: int) -> bool:
    """Whether a file already fits a request for *bitrate_kbps*: it's
    lossy and no bigger than asked for (a small margin allows for VBR).
    Lossless and unknown files are always transcoded."""

    if codec not in _LOSSY or bitrate_bps <= 0:
        return False
    return bitrate_bps <= bitrate_kbps * 1000 * 1.1


def ffmpeg_args(
    ffmpeg: str, source: Path, target: Path, fmt: Format, bitrate_kbps: int
) -> list[str]:
    """The ffmpeg command line for one transcode: audio only (cover art
    and other streams dropped), tags kept, stereo at most."""

    return [
        ffmpeg,
        '-nostdin',
        '-hide_banner',
        '-loglevel',
        'error',
        '-y',
        '-i',
        str(source),
        '-map',
        '0:a:0',
        '-map_metadata',
        '0',
        '-vn',
        '-ac',
        '2',
        *fmt.args,
        '-b:a',
        f'{bitrate_kbps}k',
        str(target),
    ]


def cache_key(source: Path, fmt: str, bitrate_kbps: int) -> str:
    st = source.stat()
    raw = f'{source.resolve()}\n{st.st_size}\n{st.st_mtime_ns}\n{fmt}\n'
    raw += str(bitrate_kbps)
    return hashlib.sha256(raw.encode()).hexdigest()


class TranscodeError(RuntimeError):
    pass


class _Job:
    """One ffmpeg run, shared by every request waiting for its output."""

    def __init__(self, task: asyncio.Task[Path]) -> None:
        self.task = task
        self.waiters = 0


class Transcoder:
    """Cached, bounded transcoding (see the module docstring)."""

    def __init__(
        self,
        cache_dir: Path,
        *,
        max_bytes: int = DEFAULT_CACHE_BYTES,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        ffmpeg: Optional[str] = None,
    ) -> None:
        self._dir = Path(cache_dir)
        self._max_bytes = max(0, int(max_bytes))
        self._ffmpeg = ffmpeg if ffmpeg is not None else shutil.which('ffmpeg')
        self._semaphore = asyncio.Semaphore(max(1, int(max_concurrent)))
        self._jobs: dict[str, _Job] = {}
        self.running = 0

    @property
    def available(self) -> bool:
        return bool(self._ffmpeg)

    def capability(self) -> dict[str, Any]:
        """What ``GET /api/server/info`` reports under ``transcoding``."""

        return {
            'available': self.available,
            'formats': sorted(FORMATS) if self.available else [],
            'bitrates': list(BITRATES) if self.available else [],
        }

    def cached_path(
        self, source: Path, fmt: str, bitrate_kbps: int
    ) -> Optional[Path]:
        """The finished copy when it's in the cache (and mark it used)."""

        target = self._target(source, fmt, bitrate_kbps)
        if not target.is_file():
            return None
        with contextlib.suppress(OSError):
            os.utime(target)
        return target

    def _target(self, source: Path, fmt: str, bitrate_kbps: int) -> Path:
        key = cache_key(source, fmt, bitrate_kbps)
        return self._dir / f'{key}{FORMATS[fmt].extension}'

    async def get(self, source: Path, fmt: str, bitrate_kbps: int) -> Path:
        """The transcoded copy of *source*, made now if it isn't cached.

        Cancelling the call (the client went away) stops the ffmpeg run
        once nobody else is waiting for it.
        """

        if not self.available:
            raise TranscodeError('ffmpeg is not available')
        if fmt not in FORMATS or bitrate_kbps not in BITRATES:
            raise ValueError('Unsupported format or bitrate')
        cached = self.cached_path(source, fmt, bitrate_kbps)
        if cached is not None:
            return cached
        target = self._target(source, fmt, bitrate_kbps)
        key = target.name
        job = self._jobs.get(key)
        if job is None:
            job = _Job(
                asyncio.ensure_future(
                    self._run(source, target, FORMATS[fmt], bitrate_kbps)
                )
            )
            self._jobs[key] = job
            job.task.add_done_callback(lambda _t: self._jobs.pop(key, None))
        job.waiters += 1
        try:
            return await asyncio.shield(job.task)
        except asyncio.CancelledError:
            job.waiters -= 1
            if job.waiters <= 0 and not job.task.done():
                job.task.cancel()
            raise

    async def _run(
        self, source: Path, target: Path, fmt: Format, bitrate_kbps: int
    ) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + '.part')
        async with self._semaphore:
            if target.is_file():
                return target
            args = ffmpeg_args(
                str(self._ffmpeg), source, partial, fmt, bitrate_kbps
            )
            self.running += 1
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _out, err = await asyncio.wait_for(
                    process.communicate(), TRANSCODE_TIMEOUT
                )
            except BaseException:
                with contextlib.suppress(ProcessLookupError):
                    process.kill()
                with contextlib.suppress(Exception):
                    await process.wait()
                partial.unlink(missing_ok=True)
                raise
            finally:
                self.running -= 1
            if process.returncode != 0 or not partial.is_file():
                partial.unlink(missing_ok=True)
                message = (err or b'').decode(errors='replace').strip()
                logger.warning(
                    'Transcode failed for {}: {}', source.name, message[-300:]
                )
                raise TranscodeError('Transcoding failed')
            partial.replace(target)
        logger.info(
            'Transcoded {} to {} {} kbps', source.name, fmt.name, bitrate_kbps
        )
        await asyncio.to_thread(self.prune)
        return target

    def prune(self) -> int:
        """Delete the least recently used copies until the cache is under
        its size limit. Returns how many were deleted."""

        try:
            files = [
                p
                for p in self._dir.iterdir()
                if p.is_file() and not p.name.endswith('.part')
            ]
        except OSError:
            return 0
        stats = []
        for path in files:
            try:
                st = path.stat()
            except OSError:
                continue
            stats.append((st.st_mtime, st.st_size, path))
        total = sum(size for _m, size, _p in stats)
        removed = 0
        for _mtime, size, path in sorted(stats):
            if total <= self._max_bytes:
                break
            with contextlib.suppress(OSError):
                path.unlink()
                total -= size
                removed += 1
        return removed


def transcoder_from_env(data_dir: Path) -> Transcoder:
    """A :class:`Transcoder` with the limits from the environment:
    ``DOWNTIFY_TRANSCODE_CACHE_MB`` and ``DOWNTIFY_TRANSCODE_CONCURRENCY``."""

    def number(name: str, default: int) -> int:
        try:
            return max(0, int(os.getenv(name, '') or default))
        except ValueError:
            logger.warning('{} is not a number; using {}', name, default)
            return default

    return Transcoder(
        Path(data_dir) / 'transcode_cache',
        max_bytes=number(
            'DOWNTIFY_TRANSCODE_CACHE_MB', DEFAULT_CACHE_BYTES // 1024**2
        )
        * 1024**2,
        max_concurrent=number(
            'DOWNTIFY_TRANSCODE_CONCURRENCY', DEFAULT_MAX_CONCURRENT
        ),
    )
