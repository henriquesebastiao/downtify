"""Full-track streaming, served from this server.

A track the library doesn't have yet still plays in full, in the
built-in player, without a library download: the frontend resolves it
to a YouTube video id and plays ``GET /api/stream/file``, which the
:class:`StreamCache` below downloads once (via yt-dlp, with the same
anti-bot posture as a real download) into ``/data/stream_cache`` and
then serves with seeking support. This is what makes streaming work
where the browser itself can't reach YouTube (or only slowly): the
only YouTube traffic is server-side, and the second play of a track
never touches YouTube at all.

Two endpoints share this module: ``GET /api/stream`` hands out a
fresh direct-audio URL for third-party clients, ``GET
/api/stream/file`` serves the cached file to the web player.

Failures surface as :class:`ValueError` (same convention as
:mod:`downtify.deezer`), so the endpoints map them to ``503``.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import re
from pathlib import Path
from typing import Any, Optional

import yt_dlp
from loguru import logger

from .downloader import (
    _yt_player_clients,
    _YtdlpLogger,
    is_age_restricted_error,
)

#: What a YouTube video id looks like тАФ anything else is rejected
#: without touching the network.
VIDEO_ID_RE = re.compile(r'^[A-Za-z0-9_-]{11}$')

_TIMEOUT = 30


def clean_video_id(video_id: str) -> str:
    """*video_id* when it is shaped like a YouTube video id."""

    candidate = str(video_id or '').strip()
    if not VIDEO_ID_RE.fullmatch(candidate):
        raise ValueError(f'Not a YouTube video id: {candidate[:32]!r}')
    return candidate


def _ydl_options() -> dict[str, Any]:
    """yt-dlp options for reading (not downloading) one audio URL.

    Mirrors the anti-bot posture of a real download (see
    ``Downloader._ydl_options``): the TV/mobile player clients that
    bypass "Sign in to confirm you're not a bot", the EJS challenge
    solver, IPv4 when asked, and the same cookies.
    """

    opts: dict[str, Any] = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'quiet': True,
        'noprogress': True,
        'logger': _YtdlpLogger(),
        'noplaylist': True,
        'nocheckcertificate': True,
        'socket_timeout': _TIMEOUT,
        'extractor_args': {'youtube': {'player_client': _yt_player_clients()}},
        'remote_components': ['ejs:github'],
    }
    if os.getenv('DOWNTIFY_FORCE_IPV4', '').strip() in {'1', 'true', 'yes'}:
        opts['source_address'] = '0.0.0.0'
    return opts


def stream_url_for_video(
    video_id: str, *, cookies_file: str = ''
) -> dict[str, Any]:
    """The current direct-audio URL of the YouTube video *video_id*.

    Returns ``{url, ext}`` тАФ ``ext`` is ``m4a`` when YouTube served
    AAC (plays in every browser) and whatever ``bestaudio`` was
    otherwise. Raises :class:`ValueError` when the id is malformed,
    age-gated without usable cookies, or YouTube can't be reached.
    The URL itself is never logged: it carries a signature.
    """

    vid = clean_video_id(video_id)
    opts = _ydl_options()
    resolved = str(cookies_file or '').strip()
    if resolved:
        opts['cookiefile'] = resolved
    cookies_browser = os.getenv('DOWNTIFY_COOKIES_FROM_BROWSER', '').strip()
    if cookies_browser:
        parts = cookies_browser.split(':', 1)
        opts['cookiesfrombrowser'] = (
            (parts[0],) if len(parts) == 1 else (parts[0], parts[1])
        )
    url = f'https://www.youtube.com/watch?v={vid}'
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        if is_age_restricted_error(str(exc)):
            raise ValueError(
                'This track is age-restricted on YouTube: upload a '
                'YouTube cookies.txt in Settings > YouTube cookies '
                'to stream it.'
            ) from exc
        raise ValueError(
            f'YouTube did not answer: {type(exc).__name__}'
        ) from exc
    if not isinstance(info, dict) or not info.get('url'):
        raise ValueError('YouTube answered with an unreadable reply')
    direct = str(info['url'])
    logger.info(
        'Stream URL resolved for videoId={} ext={!r}', vid, info.get('ext')
    )
    return {'url': direct, 'ext': str(info.get('ext') or '')}


def resolve_cookies_file(store: Optional[Any]) -> str:
    """The cookies.txt streaming should use (UI upload wins, env next)."""

    try:
        active = store.active_path() if store is not None else None
    except Exception:
        active = None
    if active:
        return str(active)
    return os.getenv('DOWNTIFY_COOKIES_FILE', '').strip()


#: Default cap of the on-disk stream cache (see ``stream_cache_from_env``).
DEFAULT_STREAM_CACHE_MB = 1024
#: How many stream downloads may run at once (they are heavier than
#: metadata lookups but lighter than full tagged downloads).
DEFAULT_STREAM_CONCURRENCY = 2

_MEDIA_TYPES = {
    'm4a': 'audio/mp4',
    'mp4': 'audio/mp4',
    'aac': 'audio/aac',
    'mp3': 'audio/mpeg',
    'webm': 'audio/webm',
    'opus': 'audio/ogg',
    'ogg': 'audio/ogg',
    'flac': 'audio/flac',
    'wav': 'audio/wav',
}


def media_type_for(path: Any) -> str:
    """The ``Content-Type`` a cached stream file is served with."""

    ext = str(getattr(path, 'suffix', '') or '').lower().lstrip('.')
    return _MEDIA_TYPES.get(ext, 'application/octet-stream')


class _StreamJob:
    """One cache download, shared by every request waiting for it."""

    def __init__(self, task: asyncio.Task[Path]) -> None:
        self.task = task
        self.waiters = 0


class StreamCache:
    """On-disk cache of streamed audio (see the module docstring).

    ``get`` downloads a video's audio once no matter how many requests
    arrive together, serves the finished file afterwards, and prunes
    the least recently used files past the size limit. Files are named
    ``<video_id>.<ext>`` with ``.part`` left to yt-dlp while a download
    is in flight (never served: only finished files match).
    """

    def __init__(
        self,
        cache_dir: Any,
        *,
        max_bytes: int = DEFAULT_STREAM_CACHE_MB * 1024**2,
        max_concurrent: int = DEFAULT_STREAM_CONCURRENCY,
    ) -> None:
        self._dir = (
            Path(cache_dir) if not isinstance(cache_dir, Path) else cache_dir
        )
        self._max_bytes = max(0, int(max_bytes))
        self._semaphore = asyncio.Semaphore(max(1, int(max_concurrent)))
        self._jobs: dict[str, _StreamJob] = {}
        self.running = 0

    def cached_path(self, video_id: str) -> Optional[Path]:
        """The finished cached file for *video_id*, if one is stored."""

        try:
            vid = clean_video_id(video_id)
        except ValueError:
            return None
        for path in sorted(self._dir.glob(f'{vid}.*')):
            if path.name.endswith('.part') or not path.is_file():
                continue
            try:
                if path.stat().st_size <= 0:
                    continue
                with contextlib.suppress(OSError):
                    os.utime(path)
            except OSError:
                continue
            return path
        return None

    async def get(self, video_id: str, *, cookies_file: str = '') -> Path:
        """The cached audio file for *video_id*, downloading it first.

        Concurrent callers share one download; cancelling (the player
        moved on) only stops the download once nobody else waits for
        it. Raises :class:`ValueError` when there is nothing to serve.
        """

        vid = clean_video_id(video_id)
        cached = self.cached_path(vid)
        if cached is not None:
            return cached
        job = self._jobs.get(vid)
        if job is None:
            job = _StreamJob(
                asyncio.ensure_future(self._run(vid, cookies_file))
            )
            self._jobs[vid] = job
            job.task.add_done_callback(lambda _t: self._jobs.pop(vid, None))
        job.waiters += 1
        try:
            return await asyncio.shield(job.task)
        except asyncio.CancelledError:
            job.waiters -= 1
            if job.waiters <= 0 and not job.task.done():
                job.task.cancel()
            raise

    async def _run(self, video_id: str, cookies_file: str) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        async with self._semaphore:
            cached = self.cached_path(video_id)
            if cached is not None:
                return cached
            self.running += 1
            try:
                await asyncio.to_thread(self._fetch, video_id, cookies_file)
            finally:
                self.running -= 1
            found = self.cached_path(video_id)
            if found is None:
                raise ValueError(
                    'YouTube gave nothing to stream for this track'
                )
            await asyncio.to_thread(self.prune)
            return found

    def _fetch(self, video_id: str, cookies_file: str) -> None:
        """Download *video_id*'s audio into the cache dir (blocking)."""

        opts: dict[str, Any] = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': str(self._dir / f'{video_id}.%(ext)s'),
            'quiet': True,
            'noprogress': True,
            'logger': _YtdlpLogger(),
            'noplaylist': True,
            'nocheckcertificate': True,
            'socket_timeout': _TIMEOUT,
            'retries': 10,
            'extractor_retries': 3,
            'extractor_args': {
                'youtube': {'player_client': _yt_player_clients()}
            },
            'remote_components': ['ejs:github'],
        }
        if os.getenv('DOWNTIFY_FORCE_IPV4', '').strip() in {
            '1',
            'true',
            'yes',
        }:
            opts['source_address'] = '0.0.0.0'
        resolved = str(cookies_file or '').strip()
        if resolved:
            opts['cookiefile'] = resolved
        cookies_browser = os.getenv(
            'DOWNTIFY_COOKIES_FROM_BROWSER', ''
        ).strip()
        if cookies_browser:
            parts = cookies_browser.split(':', 1)
            opts['cookiesfrombrowser'] = (
                (parts[0],) if len(parts) == 1 else (parts[0], parts[1])
            )
        url = f'https://www.youtube.com/watch?v={video_id}'
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except Exception as exc:
            if is_age_restricted_error(str(exc)):
                raise ValueError(
                    'This track is age-restricted on YouTube: upload a '
                    'YouTube cookies.txt in Settings > YouTube cookies '
                    'to stream it.'
                ) from exc
            raise ValueError(
                f'YouTube did not answer: {type(exc).__name__}'
            ) from exc
        logger.info('Stream cached for videoId={}', video_id)

    def prune(self) -> int:
        """Delete the least recently used files past the size limit."""

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
            if st.st_size <= 0:
                with contextlib.suppress(OSError):
                    path.unlink()
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


def stream_cache_from_env(data_dir: Any) -> StreamCache:
    """A :class:`StreamCache` under ``<data_dir>/stream_cache``.

    Limits come from ``DOWNTIFY_STREAM_CACHE_MB`` (default 1024) and
    ``DOWNTIFY_STREAM_CONCURRENCY`` (default 2).
    """

    def _int(name: str, default: int) -> int:
        try:
            return max(0, int(os.getenv(name, '') or default))
        except (TypeError, ValueError):
            return default

    base = Path(data_dir) if not isinstance(data_dir, Path) else data_dir
    return StreamCache(
        base / 'stream_cache',
        max_bytes=_int('DOWNTIFY_STREAM_CACHE_MB', DEFAULT_STREAM_CACHE_MB)
        * 1024**2,
        max_concurrent=_int(
            'DOWNTIFY_STREAM_CONCURRENCY', DEFAULT_STREAM_CONCURRENCY
        )
        or DEFAULT_STREAM_CONCURRENCY,
    )
