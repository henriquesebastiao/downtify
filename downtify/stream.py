"""Fresh direct-audio URLs and 20-second audio chunks for streaming.

A track the library doesn't have yet still plays in full, in the
built-in player, without downloading first: the frontend resolves it
to a YouTube video id and plays it back piece by piece - ``GET
/api/stream/chunk`` cuts a 20-second MP3 out of the video's current
audio with ffmpeg, and the player stitches the pieces together with
the Media Source Extensions, fetching ahead so playback never waits.
A start or a seek into a part that isn't loaded yet only costs one
small chunk fetch. Nothing is downloaded, tagged or stored.

Direct URLs are short-lived and IP-bound, so they live only in a
short in-memory cache (never on disk); chunks are transcoded on every
request. Failures surface as :class:`ValueError` (same convention as
:mod:`downtify.deezer`), so the endpoints map them to ``503``.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from typing import Any, Optional

import yt_dlp
from loguru import logger

from .downloader import (
    _yt_player_clients,
    _YtdlpLogger,
    is_age_restricted_error,
)

#: What a YouTube video id looks like — anything else is rejected
#: without touching the network.
VIDEO_ID_RE = re.compile(r'^[A-Za-z0-9_-]{11}$')

#: One player piece, in seconds: small enough to arrive fast, big enough
#: that junctions (every MP3 chunk carries encoder padding) stay rare.
CHUNK_SECONDS = 20

#: How long a resolved direct URL is reused from memory (seconds).
#: Well inside the few hours YouTube signs them for.
_URL_TTL_SECONDS = 2 * 3600

#: How long one chunk transcode may take (seconds).
_CHUNK_TIMEOUT = 60

_TIMEOUT = 30

# video_id + cookies -> (direct url, total seconds, ext, resolved at).
# Memory only: the URLs expire on their own and must never be written
# anywhere, or a stored one quietly stops working hours later.
_url_cache: dict[str, tuple[str, float, str, float]] = {}


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


def _resolve_direct(vid: str, cookies_file: str) -> tuple[str, float, str]:
    """``(direct url, total seconds, ext)``, from cache when fresh."""

    key = f'{vid}|{cookies_file}'
    cached = _url_cache.get(key)
    if cached is not None and time.monotonic() - cached[3] < _URL_TTL_SECONDS:
        return cached[0], cached[1], cached[2]
    opts = _ydl_options()
    if cookies_file:
        opts['cookiefile'] = cookies_file
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
    try:
        total = max(0.0, float(info.get('duration') or 0))
    except (TypeError, ValueError):
        total = 0.0
    ext = str(info.get('ext') or '')
    _url_cache[key] = (direct, total, ext, time.monotonic())
    logger.info('Stream URL resolved for videoId={} ext={!r}', vid, ext)
    return direct, total, ext


def stream_url_for_video(
    video_id: str, *, cookies_file: str = ''
) -> dict[str, Any]:
    """The current direct-audio URL of the YouTube video *video_id*.

    Returns ``{url, ext, duration}`` — ``ext`` is ``m4a`` when YouTube
    served AAC (plays in every browser) and whatever ``bestaudio`` was
    otherwise; ``duration`` is the whole track in seconds (``0`` when
    YouTube didn't say). Raises :class:`ValueError` when the id is
    malformed, age-gated without usable cookies, or YouTube can't be
    reached. The URL itself is never logged: it carries a signature.
    """

    vid = clean_video_id(video_id)
    direct, total, ext = _resolve_direct(vid, str(cookies_file or '').strip())
    return {'url': direct, 'ext': ext, 'duration': total}


def audio_chunk(
    video_id: str, start: float, *, cookies_file: str = ''
) -> dict[str, Any]:
    """``CHUNK_SECONDS`` of MP3 audio from *start* seconds in.

    Returns ``{data, start, duration}`` — ``data`` a self-contained
    MP3 piece the player appends to its Media Source buffer (every
    browser plays it, and junctions stay ~20 s apart), ``duration``
    the whole track in seconds when known. Raises
    :class:`ValueError` when ffmpeg is missing, the range is past the
    end, or the audio can't be read.
    """

    vid = clean_video_id(video_id)
    if start < 0:
        raise ValueError('Chunk start is negative')
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise ValueError('ffmpeg is not available for streaming')
    direct, total, _ = _resolve_direct(vid, str(cookies_file or '').strip())
    if total and start >= total:
        raise ValueError('Chunk start is past the end of the track')
    cmd = [
        ffmpeg,
        '-hide_banner',
        '-loglevel',
        'error',
        '-ss',
        str(max(0.0, start)),
        '-i',
        direct,
        '-t',
        str(CHUNK_SECONDS),
        '-vn',
        '-c:a',
        'libmp3lame',
        '-b:a',
        '160k',
        '-ar',
        '44100',
        '-f',
        'mp3',
        'pipe:1',
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, timeout=_CHUNK_TIMEOUT, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError('Chunk transcode timed out') from exc
    except OSError as exc:
        raise ValueError(f'ffmpeg could not run: {exc}') from exc
    if proc.returncode != 0 or not proc.stdout:
        detail = (proc.stderr or b'').decode('utf-8', 'ignore').strip()[:200]
        raise ValueError(
            'Chunk transcode failed' + (f': {detail}' if detail else '')
        )
    return {'data': proc.stdout, 'start': max(0.0, start), 'duration': total}


def resolve_cookies_file(store: Optional[Any]) -> str:
    """The cookies.txt streaming should use (UI upload wins, env next)."""

    try:
        active = store.active_path() if store is not None else None
    except Exception:
        active = None
    if active:
        return str(active)
    return os.getenv('DOWNTIFY_COOKIES_FILE', '').strip()
