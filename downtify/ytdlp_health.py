"""Notice when YouTube downloads keep failing because of yt-dlp.

Each YouTube download reports here (:func:`downtify.downloader.Downloader.fetch_audio`).
Failures that belong to one song (removed, private, region-locked,
age-restricted, members only) or to the network (no DNS, timed out)
don't count: those say nothing about yt-dlp. When
:data:`BROKEN_AFTER` of the rest come in a row, spread over at least
:data:`MIN_SONGS` different videos, with no YouTube download working in
between, YouTube is marked as failing:

- the ``ytdlp`` notification says so, with the yt-dlp in use;
- the updater (:mod:`downtify.ytdlp_update`) is asked to check PyPI
  soon instead of waiting for its daily check.

The first YouTube download that works again sends "working again".
YouTube's bot check ("confirm you're not a bot") counts too, but the
message points at the cookies instead of yt-dlp.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional

from loguru import logger

from . import notifications

#: Failures in a row (no success between) that mark YouTube as failing.
BROKEN_AFTER = 10
#: ... spread over at least this many different videos.
MIN_SONGS = 3

#: Errors about one song, not yt-dlp.
_SONG_FRAGMENTS = (
    'video unavailable',
    'private video',
    'has been removed',
    'been terminated',
    'no longer available',
    'not available in your country',
    'not made this video available',
    'blocked it in your country',
    'copyright',
    'members-only',
    'join this channel',
    'premieres in',
    'live event will begin',
    'this live event',
    'sign in to confirm your age',
    'age-restricted',
    'inappropriate for some users',
    'only streams a 30-second preview',
    'is not a valid url',
)
#: Errors from the network, not yt-dlp.
_NETWORK_FRAGMENTS = (
    'timed out',
    'temporary failure in name resolution',
    'name or service not known',
    'nodename nor servname',
    'network is unreachable',
    'connection refused',
    'connection reset',
    'no route to host',
    'eai_again',
    'getaddrinfo failed',
)
_BOT_FRAGMENTS = ("confirm you're not a bot", 'confirm you’re not a bot')


def classify(message: str) -> str:
    """``song``, ``network``, ``bot`` or ``ytdlp`` for a failure."""

    text = (message or '').lower()
    if any(f in text for f in _BOT_FRAGMENTS):
        return 'bot'
    if any(f in text for f in _SONG_FRAGMENTS):
        return 'song'
    if any(f in text for f in _NETWORK_FRAGMENTS):
        return 'network'
    return 'ytdlp'


def _short(message: str, limit: int = 160) -> str:
    line = ' '.join((message or '').split())
    if line.lower().startswith('error: '):
        line = line[7:]
    return line if len(line) <= limit else line[: limit - 1] + '…'


class YoutubeHealth:
    """The streak of failed YouTube downloads in this process."""

    def __init__(
        self,
        emit: Callable[[str, str, str], None] = notifications.emit,
        version: Callable[[], Optional[str]] = lambda: None,
        on_broken: Callable[[], None] = lambda: None,
        update_hint: Callable[[], str] = lambda: '',
    ) -> None:
        self.emit = emit
        self.version = version
        self.on_broken = on_broken
        self.update_hint = update_hint
        self._lock = threading.Lock()
        self._streak = 0
        self._videos: set[str] = set()
        self._kinds: dict[str, int] = {}
        self._last_error = ''
        self.broken = False

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                'failing': self.broken,
                'streak': self._streak,
                'last_error': self._last_error or None,
            }

    def success(self) -> None:
        with self._lock:
            was_broken = self.broken
            self._streak = 0
            self._videos.clear()
            self._kinds.clear()
            self.broken = False
        if was_broken:
            logger.info('YouTube downloads work again')
            self._send(
                'YouTube downloads work again',
                f'yt-dlp {self.version() or ""}'.strip() + ' is downloading.',
            )

    def failure(self, video_id: str, message: str) -> None:
        kind = classify(message)
        if kind in {'song', 'network'}:
            return
        with self._lock:
            self._streak += 1
            self._videos.add(str(video_id))
            self._kinds[kind] = self._kinds.get(kind, 0) + 1
            self._last_error = _short(message)
            newly = (
                not self.broken
                and self._streak >= BROKEN_AFTER
                and len(self._videos) >= MIN_SONGS
            )
            if newly:
                self.broken = True
            bot = self._kinds.get('bot', 0) * 2 >= self._streak
            streak, last = self._streak, self._last_error
        if not newly:
            return
        logger.warning(
            'YouTube downloads keep failing ({} in a row): {}', streak, last
        )
        if bot:
            self._send(
                'YouTube wants a sign-in',
                event='youtube_cookies',
                text=f"{streak} YouTube downloads in a row hit YouTube's bot "
                'check. Upload fresh cookies in Settings > Sources > '
                f'YouTube cookies. Last error: {last}',
            )
        else:
            hint = ''
            try:
                hint = self.update_hint()
            except Exception:
                logger.opt(exception=True).debug('yt-dlp hint failed')
            self._send(
                'YouTube downloads keep failing',
                f'{streak} in a row with yt-dlp {self.version() or "?"}. '
                f'{hint}Last error: {last}'.replace('  ', ' '),
            )
        try:
            self.on_broken()
        except Exception:
            logger.opt(exception=True).debug('yt-dlp: on_broken failed')

    def _send(self, title: str, text: str, event: str = 'ytdlp') -> None:
        try:
            self.emit(event, title, text)
        except Exception:
            logger.opt(exception=True).debug('yt-dlp: notify failed')


#: The one of this process; ``main.py`` wires its callbacks.
monitor = YoutubeHealth()


def report_success() -> None:
    try:
        monitor.success()
    except Exception:
        logger.opt(exception=True).debug('yt-dlp health: success')


def report_failure(video_id: str, message: str) -> None:
    try:
        monitor.failure(video_id, message)
    except Exception:
        logger.opt(exception=True).debug('yt-dlp health: failure')
