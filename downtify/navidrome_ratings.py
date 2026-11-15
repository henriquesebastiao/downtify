"""Gives Navidrome songs 0-5 stars from their Deezer popularity.

The star scale and the options are ported from dztnr
(https://github.com/scatolo/dztnr), itself a fork of sptnr
(https://github.com/krestaino/sptnr). Their MIT licence follows.

MIT License

Copyright (c) 2024 Kevin Restaino

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

This part of the module is pure: the star tables, the options sanitiser
and the repeat-schedule rule.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

#: The options a rating run takes, with their defaults.
DEFAULTS: dict[str, Any] = {
    'repeat': 'off',
    'skip_rated': True,
    'skip_starred': False,
    'grading': 'absolute',
}

#: Repeat choice -> days between runs (0 means never repeat).
REPEAT_DAYS = {'off': 0, 'daily': 1, 'weekly': 7, 'monthly': 30}

#: How a song's Deezer rank is turned into stars.
GRADINGS = ('absolute', 'artist', 'album')

#: Seconds to wait between Deezer calls, and before retrying one.
DEEZER_PAUSE = 0.2
RETRY_PAUSE = 5.0

#: A failed run is retried after this long, whatever the repeat is.
RETRY_AFTER_FAILURE = timedelta(hours=6)

#: How many songs a preview lists.
EXAMPLES = 500

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def effective_settings(raw: Any) -> dict[str, Any]:
    """Return a fresh dict holding exactly the known options.

    Anything missing or invalid falls back to its default.
    """
    data = raw if isinstance(raw, dict) else {}
    repeat = data.get('repeat')
    grading = data.get('grading')
    return {
        'repeat': repeat
        if repeat in tuple(REPEAT_DAYS)
        else DEFAULTS['repeat'],
        'skip_rated': bool(data.get('skip_rated', DEFAULTS['skip_rated'])),
        'skip_starred': bool(
            data.get('skip_starred', DEFAULTS['skip_starred'])
        ),
        'grading': grading if grading in GRADINGS else DEFAULTS['grading'],
    }


def stars_from_rank(rank: int) -> int:
    """Stars for a Deezer rank (dztnr's ``get_rating_from_rank``)."""
    rank = int(rank)
    if rank < 10_000:
        return 0
    if rank < 100_000:
        return 1
    if rank < 300_000:
        return 2
    if rank < 600_000:
        return 3
    if rank < 850_000:
        return 4
    return 5


def stars_from_relative_rank(rank: int, top: Optional[int]) -> int:
    """Stars for a rank relative to the highest one (dztnr's
    ``get_rating_from_relative_rank``)."""
    rank = int(rank)
    if rank <= 0 or top is None or int(top) <= 0:
        return 0
    ratio = rank / int(top)
    if ratio >= 0.80:
        return 5
    if ratio >= 0.60:
        return 4
    if ratio >= 0.40:
        return 3
    if ratio >= 0.20:
        return 2
    return 1


def _started_at(
    last_rating_run: Optional[dict[str, Any]],
) -> Optional[datetime]:
    if not isinstance(last_rating_run, dict):
        return None
    try:
        started = datetime.fromisoformat(last_rating_run['started_at'])
    except (KeyError, TypeError, ValueError):
        return None
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return started.astimezone(timezone.utc)


def next_run_at(
    settings: dict[str, Any], last_rating_run: Optional[dict[str, Any]]
) -> Optional[datetime]:
    """When the next scheduled run is due, as an aware UTC datetime.

    ``None`` when repeat is off. The Unix epoch (so, due now) when there
    is no usable last run. A failed run is retried after
    ``RETRY_AFTER_FAILURE``, any other after the repeat interval.
    """
    repeat = settings.get('repeat')
    days = REPEAT_DAYS[repeat] if repeat in tuple(REPEAT_DAYS) else 0
    if not days:
        return None
    started = _started_at(last_rating_run)
    if started is None:
        return _EPOCH
    if last_rating_run.get('state') == 'failed':
        return started + RETRY_AFTER_FAILURE
    return started + timedelta(days=days)
