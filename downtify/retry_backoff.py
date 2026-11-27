"""How often a watch tries again a song it keeps failing to download.

A watch's check downloads every song of the playlist (or every song of
an artist's unfinished releases) it doesn't hold yet - a song that
failed included. Without a wait, a song no source has is searched for
again on every check: on slskd, YouTube Music and the rest, each hour,
for weeks.

So a failing song (``watch_failures``, see :mod:`downtify.watch_history`)
waits before its next try: a quarter of the time it has been failing,
at least :data:`MIN_WAIT` and at most :data:`MAX_WAIT`. A song that just
failed is tried again in an hour, one failing for four days once a day,
one failing for a month once a week. It is never given up on.

The waits start over (every failing song is tried on the next check)
when what could make a try succeed changes: another Downtify or yt-dlp
version, or other audio sources (:func:`start_over`). A watch's **Check
now** tries every failing song of that watch (:func:`every_failure`);
**Forget failures** drops the rows, and with them the waits.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import Iterator
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from yt_dlp.version import __version__ as yt_dlp_version

from . import __version__

#: The shortest and the longest wait between two tries of a song.
MIN_WAIT = timedelta(hours=1)
MAX_WAIT = timedelta(days=7)
#: The wait is the time the song has been failing, divided by this.
WAIT_SHARE = 4

#: When the waits last started over (``None``: never).
_started_over: Optional[datetime] = None
#: Set while a check tries every failing song (**Check now**).
_every_failure: ContextVar[bool] = ContextVar(
    'retry_every_failure', default=False
)


def _parse(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        found = value
    else:
        try:
            found = datetime.fromisoformat(str(value or ''))
        except ValueError:
            return None
    if found.tzinfo is None:
        found = found.replace(tzinfo=timezone.utc)
    return found


def started_over() -> Optional[datetime]:
    return _started_over


def set_started_over(value: Any) -> None:
    """Take *value* (a datetime or an ISO string) as when the waits last
    started over; ``None`` or an unreadable value: never."""

    global _started_over
    _started_over = None if value is None else _parse(value)


def start_over(now: Optional[datetime] = None) -> datetime:
    """Every failing song is tried on its watch's next check; returns the
    moment, for the caller to save."""

    moment = now or datetime.now(timezone.utc)
    set_started_over(moment)
    return moment


@contextlib.contextmanager
def every_failure() -> Iterator[None]:
    """Within: a check tries every failing song, waiting or not."""

    token = _every_failure.set(True)
    try:
        yield
    finally:
        _every_failure.reset(token)


def next_try(
    first_failed_at: Any,
    last_failed_at: Any,
    since: Optional[datetime] = None,
) -> Optional[datetime]:
    """When a song failing since *first_failed_at* (last at
    *last_failed_at*) is tried again; ``None``: on the next check.

    A failure from before the waits started over (*since*) counts as
    none: the song is tried right away and, failing again, waits as one
    that only just started failing.
    """

    last = _parse(last_failed_at)
    if last is None:
        return None
    if since is not None and last < since:
        return None
    first = _parse(first_failed_at) or last
    if since is not None and first < since:
        first = since
    failing = max(last - first, timedelta(0))
    wait = min(max(failing / WAIT_SHARE, MIN_WAIT), MAX_WAIT)
    return last + wait


def waiting(
    failures: list[dict[str, Any]], now: Optional[datetime] = None
) -> dict[str, datetime]:
    """``{track id: next try}`` of the *failures* (rows of
    ``watch_failures``) not to try yet."""

    if _every_failure.get():
        return {}
    now = now or datetime.now(timezone.utc)
    out: dict[str, datetime] = {}
    for row in failures:
        track_id = str(row.get('track_id') or '')
        when = next_try(
            row.get('first_failed_at'),
            row.get('last_failed_at'),
            _started_over,
        )
        if track_id and when is not None and when > now:
            out[track_id] = when
    return out


def waiting_for_watch(history: Any, playlist_id: int) -> dict[str, datetime]:
    """:func:`waiting` for one watch's failures (best effort: a failure
    list that can't be read waits for nothing)."""

    if _every_failure.get() or history is None:
        return {}
    try:
        failures = history.failures(playlist_id)
    except Exception:
        return {}
    return waiting(failures)


def fingerprint() -> str:
    """What a try's outcome depends on besides the song and the settings:
    Downtify's and yt-dlp's versions."""

    return json.dumps(
        {'downtify': __version__, 'yt_dlp': yt_dlp_version}, sort_keys=True
    )
