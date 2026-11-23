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

The first half of the module is pure: the star tables, the options
sanitiser and the repeat-schedule rule. :class:`RatingRun` walks the
library and rates songs from Deezer.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from . import deezer
from .navidrome import SubsonicError

#: Subsonic error code for "not found" (a song or album removed mid-run).
SUBSONIC_NOT_FOUND = 70

#: Deezer error codes worth a retry: quota exceeded, service busy.
DEEZER_RETRY_CODES = (4, 700)

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

#: Seconds to wait between Deezer calls.
DEEZER_PAUSE = 0.2
#: Seconds to wait before each retry of a failed Deezer call. A blip on a
#: big library used to end the whole run after one retry; now Deezer gets
#: about four minutes to answer again before the run gives up.
RETRY_PAUSES = (5.0, 15.0, 30.0, 60.0, 120.0)
#: After this many Deezer calls, rest for BATCH_PAUSE seconds: long runs
#: go in small batches, well under Deezer's 50 calls per 5 seconds.
BATCH_SIZE = 100
BATCH_PAUSE = 10.0
#: Longest single sleep, so Stop is noticed during a long wait.
_WAIT_STEP = 5.0

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


_DEEZER_API = 'https://api.deezer.com'


class DeezerUnavailable(RuntimeError):
    """Deezer failed twice in a row; the run cannot go on."""


def _never() -> bool:
    return False


def _ignore(done: int, total: int, step: str) -> None:
    """Default progress callback: nothing listens."""


class RatingRun:
    """One pass over the Navidrome library, rating songs from Deezer.

    A port of dztnr's walk. ``client`` is a
    :class:`downtify.navidrome.NavidromeClient`; ``options`` are the
    :func:`effective_settings`. Navidrome errors are not caught: they
    reach the caller. With ``preview`` nothing is written.
    """

    def __init__(
        self,
        client: Any,
        options: dict[str, Any],
        *,
        preview: bool = False,
        cancelled: Callable[[], bool] = _never,
        progress: Callable[[int, int, str], None] = _ignore,
        sleep: Callable[[float], None] = time.sleep,
        done_albums: Optional[set[str]] = None,
        album_done: Callable[[str], None] = lambda _album_id: None,
    ) -> None:
        self._client = client
        # Albums a previous run finished before it stopped: skipped, so
        # an interrupted run carries on where it was.
        self._done_albums = set(done_albums or ())
        self._album_done = album_done
        self._calls = 0
        self._options = effective_settings(options)
        self._preview = preview
        self._cancelled = cancelled
        self._progress = progress
        self._sleep = sleep
        self._stopped = False
        self._total = 0
        self._done = 0
        self._rated = 0
        self._skipped = 0
        self._not_found = 0
        self._changes: list[dict[str, Any]] = []
        self._unmatched: list[str] = []
        # Reference ranks, kept even when None so they are not retried.
        self._artist_tops: dict[str, Optional[int]] = {}
        self._album_tops: dict[str, Optional[int]] = {}

    def run(self) -> dict[str, Any]:
        """Walk the library and rate it; return the summary."""
        albums = self._library()
        for artist_name, album_id, song_count in albums:
            if self._stopped:
                break
            if album_id in self._done_albums:
                self._skipped += song_count
                self._done += song_count
                self._progress(
                    self._done, max(self._total, self._done), 'rating'
                )
                continue
            try:
                album = self._client.album(album_id)
            except SubsonicError as exc:
                if exc.code != SUBSONIC_NOT_FOUND:
                    raise
                # Removed since the library pass: skip its songs.
                self._skipped += song_count
                self._done += song_count
                self._progress(
                    self._done, max(self._total, self._done), 'rating'
                )
                continue
            self._rate_album(artist_name, album)
            if not self._stopped:
                self._album_done(album_id)
        return self._summary()

    # -- the library pass ---------------------------------------------

    def _library(self) -> list[tuple[str, str, int]]:
        """Every unique album as ``(navidrome artist name, album id,
        listed song count)``."""
        artists = self._client.artists()
        seen: set[str] = set()
        albums: list[tuple[str, str, int]] = []
        for index, artist in enumerate(artists, start=1):
            if self._cancelled():
                self._stopped = True
                break
            for album in self._client.artist_albums(artist['id']):
                if album['id'] in seen:
                    continue
                seen.add(album['id'])
                count = int(album.get('song_count') or 0)
                albums.append((artist['name'], album['id'], count))
                self._total += count
            self._progress(index, len(artists), 'library')
        return albums

    # -- the rating pass ----------------------------------------------

    def _rate_album(self, artist_name: str, album: dict[str, Any]) -> None:
        for song in album['songs']:
            if self._cancelled():
                self._stopped = True
                return
            self._rate_song(artist_name, album, song)
            self._done += 1
            self._progress(self._done, max(self._total, self._done), 'rating')

    def _wants_skip(self, song: dict[str, Any]) -> bool:
        if self._options['skip_starred'] and song['starred']:
            return True
        return bool(self._options['skip_rated'] and song['rating'] > 0)

    def _rate_song(
        self, artist_name: str, album: dict[str, Any], song: dict[str, Any]
    ) -> None:
        if self._wants_skip(song):
            self._skipped += 1
            return
        top = self._reference(artist_name, album)
        rank = self._song_rank(f'{album["artist"]} {song["title"]}')
        if rank is None:
            self._not_found += 1
            if len(self._unmatched) < EXAMPLES:
                self._unmatched.append(
                    f'{album["artist"]} – {album["name"]} – {song["title"]}'
                )
            return
        stars = (
            stars_from_relative_rank(rank, top)
            if top
            else stars_from_rank(rank)
        )
        if not self._preview and stars != song['rating']:
            try:
                self._client.set_rating(song['id'], stars)
            except SubsonicError as exc:
                if exc.code != SUBSONIC_NOT_FOUND:
                    raise
                # Removed since the album was read.
                self._skipped += 1
                return
        self._rated += 1
        if len(self._changes) < EXAMPLES:
            self._changes.append({
                'artist': album['artist'],
                'album': album['name'],
                'title': song['title'],
                'rank': rank,
                'stars': stars,
                'was': song['rating'],
            })

    # -- Deezer -------------------------------------------------------

    def _wait(self, seconds: float) -> None:
        """Sleep *seconds* in steps, noticing Stop between them."""

        while seconds > 0 and not self._cancelled():
            step = min(seconds, _WAIT_STEP)
            self._sleep(step)
            seconds -= step

    def _call(self, url: str, **params: Any) -> dict[str, Any]:
        """A Deezer GET, paced, in batches.

        A transport failure, quota (4) or busy (700) is retried after
        each of :data:`RETRY_PAUSES`, then :class:`DeezerUnavailable`.
        Any other refusal (such as 800, no data) is final for that item
        and reads as an empty answer.
        """
        self._calls += 1
        if self._calls > 1 and (self._calls - 1) % BATCH_SIZE == 0:
            self._wait(BATCH_PAUSE)
        data: dict[str, Any] = {}
        failure: Optional[ValueError] = None
        for pause in (*RETRY_PAUSES, None):
            try:
                data = deezer._get_json(url, **params)
                failure = None
                break
            except deezer.DeezerRefused as exc:
                if exc.code not in DEEZER_RETRY_CODES:
                    data = {}
                    failure = None
                    break
                failure = exc
            except ValueError as exc:
                failure = exc
            if pause is None or self._cancelled():
                break
            self._wait(pause)
        if failure is not None:
            if self._cancelled():
                # Stopped during the retries: no failure, just a stop.
                self._stopped = True
                return {}
            raise DeezerUnavailable('Deezer is not answering') from failure
        self._sleep(DEEZER_PAUSE)
        return data

    @staticmethod
    def _rows(data: dict[str, Any]) -> list[dict[str, Any]]:
        rows = data.get('data')
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)]

    def _song_rank(self, query: str) -> Optional[int]:
        rows = self._rows(self._call(f'{_DEEZER_API}/search', q=query))
        rank = rows[0].get('rank') if rows else None
        return None if rank is None else int(rank)

    def _top_rank(self, url: str, **params: Any) -> Optional[int]:
        rows = self._rows(self._call(url, **params))
        ranks = [int(r['rank']) for r in rows if r.get('rank') is not None]
        return max(ranks) if ranks else None

    def _reference(
        self, artist_name: str, album: dict[str, Any]
    ) -> Optional[int]:
        """The rank relative grading compares to, or ``None`` (absolute)."""
        grading = self._options['grading']
        if grading == 'artist':
            if artist_name not in self._artist_tops:
                self._artist_tops[artist_name] = self._artist_top(artist_name)
            return self._artist_tops[artist_name]
        if grading == 'album':
            if album['id'] not in self._album_tops:
                self._album_tops[album['id']] = self._album_top(album)
            return self._album_tops[album['id']]
        return None

    def _artist_top(self, artist_name: str) -> Optional[int]:
        # Deezer's first hit is often a namesake with a handful of fans:
        # take the exact name with the most fans instead.
        rows = self._rows(
            self._call(f'{_DEEZER_API}/search/artist', q=artist_name, limit=25)
        )
        match = deezer._most_popular_exact_match(rows, artist_name)
        found = match.get('id') if match else None
        if found is None:
            return None
        return self._top_rank(f'{_DEEZER_API}/artist/{found}/top', limit=100)

    def _album_top(self, album: dict[str, Any]) -> Optional[int]:
        # The album artist on Deezer is often the composer, so only the
        # title has to match exactly (a single or mashup ranks first).
        rows = self._rows(
            self._call(
                f'{_DEEZER_API}/search/album',
                q=f'{album["artist"]} {album["name"]}',
                limit=25,
            )
        )
        wanted = deezer.file_name_key(album['name'])
        found = next(
            (
                row.get('id')
                for row in rows
                if wanted
                and deezer.file_name_key(str(row.get('title') or '')) == wanted
            ),
            None,
        )
        if found is None:
            return None
        return self._top_rank(f'{_DEEZER_API}/album/{found}/tracks')

    def _summary(self) -> dict[str, Any]:
        return {
            'state': 'stopped' if self._stopped else 'done',
            'preview': self._preview,
            'total': self._total,
            'rated': self._rated,
            'skipped': self._skipped,
            'not_found': self._not_found,
            'changes': self._changes,
            'unmatched': self._unmatched,
        }
