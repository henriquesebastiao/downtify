"""Fresh direct-audio URLs for instant full-track streaming.

A track the library doesn't have yet still plays in full, in the
built-in player, without downloading first: the frontend resolves it
to a YouTube video id, asks ``GET /api/stream`` for that video's
current audio URL, and hands it to the player as a transient (never
stored) track. The URL is short-lived and IP-bound, so it is fetched
on demand and never cached or persisted.

Failures surface as :class:`ValueError` (same convention as
:mod:`downtify.deezer`), so the endpoint maps them to ``503``.
"""

from __future__ import annotations

import os
import re
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

    Returns ``{url, ext}`` — ``ext`` is ``m4a`` when YouTube served
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
