"""The Spotify companion: your own version of Spotify's personal mixes.

Spotify builds its "made for you" playlists (Daily Mix, Discover Weekly,
Release Radar, the mood, genre, decade and artist mixes, radios) for
whoever is signed in: one link shows every listener their own songs, and
someone signed out gets a generic list (issue #489). Downtify reads
Spotify signed out, so on its own it can only follow that generic list.

The companion is an optional browser extension
(``downtify/companion_extension``) that runs in a browser *you* are
signed in to Spotify in - your desktop browser, or a browser container
on the server. It asks Downtify what to read, reads that mix the way the
Spotify web player does, and sends the song list back. Your Spotify
sign-in never leaves that browser: Downtify only ever sees song lists,
plus the account's name so it can tell when the browser is signed in to
someone else.

Downtify decides what is read and when, so it never looks like a script
hammering Spotify:

* **Time slots** - reads happen only inside the slots you set (days,
  start and end time), each with a number of **seats**: how many mixes
  it may read. A slot can be limited to some **kinds** of mix (Daily
  Mixes, Discover Weekly and Release Radar, everything else).
* **One at a time, spread out** - one read is out at any moment; the
  next waits until the reads left in the slot are spread evenly over
  what is left of it (with some jitter, never closer than the shortest
  gap). The first read of a slot starts a little after it opens.
* **Only what is due** - a mix is read once its watch's interval has
  passed; Discover Weekly and Release Radar only after Spotify's weekly
  refresh (Monday and Friday). The most overdue go first. "Check now"
  jumps the queue (still one at a time, still with the gap).
* **Never the wrong songs** - while the companion is on, a personal mix
  is never read signed out: if the companion is signed out, signed in to
  another account, or hasn't been heard from, the mixes simply wait
  (they are "on hold"), and a notification says why. It says so again
  when everything is back.

The pure parts (settings, kinds, the plan) are at the top; :class:`Store`
keeps the state in ``spotify_companion/`` beside ``settings.json``.
Nothing here imports the rest of Downtify, so :mod:`downtify.spotify`
can ask it for a mix's songs without an import cycle.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any, Optional

FOLDER_NAME = 'spotify_companion'
STATE_FILE = 'companion.json'
SNAPSHOTS = 'snapshots'

# Spotify gives the playlists it makes for one listener their own id
# prefixes (see frontend/src/lib/spotifyMix.js): ``37i9dQZF1E…`` for the
# mixes and radios, ``37i9dQZEVX…`` for Discover Weekly and Release Radar.
MIX_PREFIX = '37i9dQZF1E'
WEEKLY_PREFIX = '37i9dQZEVX'

#: The kinds of mix a time slot can take.
DAILY = 'daily'
WEEKLY = 'weekly'
MIXES = 'mixes'
KINDS = (DAILY, WEEKLY, MIXES)

#: What the companion says about itself when it asks for work.
READY = 'ready'
SIGNED_OUT = 'signed_out'
NO_PLAYER = 'no_player'
ERROR = 'error'
REPORTED = (READY, SIGNED_OUT, NO_PLAYER, ERROR)
#: What Downtify makes of it (besides the above).
OFF = 'off'
NEVER = 'never_connected'
AWAY = 'away'
OTHER_ACCOUNT = 'other_account'

#: A read Spotify answered with "slow down" (HTTP 429): no reads for
#: this long.
RATE_LIMITED = 'rate_limited'
RATE_LIMIT_PAUSE = timedelta(hours=1)
#: Not heard from for this long: shown as away (mixes wait anyway, since
#: nobody is asking for them).
AWAY_AFTER = timedelta(minutes=5)
#: A read not answered in this long is given up (its seat stays used).
JOB_TIMEOUT = timedelta(minutes=15)
#: Reads remembered for the seat counts and the page.
KEEP_READS = timedelta(days=8)
#: Longest wait between two reads, however few are left in a slot.
MAX_GAP_SECONDS = 30 * 60
#: Spotify refreshes Discover Weekly on Mondays and Release Radar on
#: Fridays, early in the morning; read them after this hour.
WEEKLY_REFRESH_HOUR = 6
_REFRESH_DAYS = {'discover weekly': 0, 'release radar': 4}

MAX_SLOTS = 12
MAX_SEATS = 500
DEFAULT_MIN_GAP = 45
DEFAULT_AWAY_ALERT_HOURS = 6

DEFAULT_CONFIG: dict[str, Any] = {
    'enabled': False,
    'slots': [
        {
            'id': 'morning',
            'name': 'Morning',
            'days': [0, 1, 2, 3, 4, 5, 6],
            'start': '09:00',
            'end': '12:00',
            'seats': 40,
            'kinds': list(KINDS),
        },
        {
            'id': 'evening',
            'name': 'Evening',
            'days': [0, 1, 2, 3, 4, 5, 6],
            'start': '18:00',
            'end': '23:00',
            'seats': 60,
            'kinds': list(KINDS),
        },
    ],
    'min_gap_seconds': DEFAULT_MIN_GAP,
    'away_alert_hours': DEFAULT_AWAY_ALERT_HOURS,
}


class CompanionWaiting(RuntimeError):
    """A personal mix the companion hasn't read yet: Downtify waits for
    it rather than reading the signed-out version."""


class UnknownJob(LookupError):
    """A result for a read that isn't the one out (or has timed out)."""


# ── Mixes and their kinds ───────────────────────────────────────────


def is_personal_mix(playlist_id: Any) -> bool:
    """Whether *playlist_id* is a Spotify playlist made for one listener."""

    text = str(playlist_id or '')
    return text.startswith(MIX_PREFIX) or text.startswith(WEEKLY_PREFIX)


def refresh_weekday(name: Any) -> Optional[int]:
    """Monday 0 … Sunday 6: the day Spotify refreshes a weekly playlist
    called *name*, or ``None``."""

    return _REFRESH_DAYS.get(str(name or '').strip().lower())


def kind_of(playlist_id: str, name: str) -> str:
    """Which kind of mix (:data:`KINDS`) a personal mix is."""

    if (
        playlist_id.startswith(WEEKLY_PREFIX)
        or refresh_weekday(name) is not None
    ):
        return WEEKLY
    if re.match(r'\s*daily mix\b', name or '', re.IGNORECASE):
        return DAILY
    return MIXES


# ── Settings ────────────────────────────────────────────────────────

_TIME = re.compile(r'^([01]\d|2[0-3]):([0-5]\d)$')


def _clock(value: Any, fallback: str) -> str:
    text = str(value or '').strip()
    if re.match(r'^\d:\d\d$', text):
        text = '0' + text
    return text if _TIME.match(text) else fallback


def _int(value: Any, low: int, high: int, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, number))


def _slot(raw: Any, index: int) -> Optional[dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    days = raw.get('days')
    days = sorted({
        d for d in (days if isinstance(days, list) else []) if d in range(7)
    })
    kinds = raw.get('kinds')
    kinds = [k for k in KINDS if isinstance(kinds, list) and k in kinds]
    start = _clock(raw.get('start'), '')
    end = _clock(raw.get('end'), '')
    if not days or not kinds or not start or not end or start == end:
        return None
    slot_id = re.sub(r'[^a-z0-9_-]', '', str(raw.get('id') or '').lower())
    return {
        'id': slot_id[:32] or f'slot{index + 1}',
        'name': str(raw.get('name') or '').strip()[:40] or f'Slot {index + 1}',
        'days': days,
        'start': start,
        'end': end,
        'seats': _int(raw.get('seats'), 1, MAX_SEATS, 20),
        'kinds': kinds,
    }


def effective(raw: Any) -> dict[str, Any]:
    """A complete, valid config. Slots that make no sense are dropped;
    other bad values fall back to their defaults."""

    data = raw if isinstance(raw, dict) else {}
    slots_raw = data.get('slots')
    if isinstance(slots_raw, list):
        slots = []
        seen: set[str] = set()
        for index, item in enumerate(slots_raw[:MAX_SLOTS]):
            slot = _slot(item, index)
            if slot is None:
                continue
            while slot['id'] in seen:
                slot['id'] = f'{slot["id"][:28]}-{len(seen) + 1}'
            seen.add(slot['id'])
            slots.append(slot)
    else:
        slots = [dict(s) for s in DEFAULT_CONFIG['slots']]
    return {
        'enabled': bool(data.get('enabled', False)),
        'slots': slots,
        'min_gap_seconds': _int(
            data.get('min_gap_seconds'), 20, 3600, DEFAULT_MIN_GAP
        ),
        'away_alert_hours': _int(
            data.get('away_alert_hours'), 1, 72, DEFAULT_AWAY_ALERT_HOURS
        ),
    }


# ── Time slots ──────────────────────────────────────────────────────


def _at(day: datetime, clock: str) -> datetime:
    hours, minutes = (int(p) for p in clock.split(':'))
    return day.replace(hour=hours, minute=minutes, second=0, microsecond=0)


def _windows(
    slot: dict[str, Any], local: datetime, days_ahead: int = 0
) -> list[tuple[datetime, datetime]]:
    """The slot's windows that start between yesterday and
    *days_ahead* days from *local*'s date (a window may run past
    midnight)."""

    found = []
    for offset in range(-1, days_ahead + 1):
        day = local + timedelta(days=offset)
        if day.weekday() not in slot['days']:
            continue
        start = _at(day, slot['start'])
        end = _at(day, slot['end'])
        if end <= start:
            end += timedelta(days=1)
        found.append((start, end))
    return found


def open_windows(
    slots: list[dict[str, Any]], local: datetime
) -> list[tuple[dict[str, Any], datetime, datetime, str]]:
    """``(slot, start, end, key)`` for every slot open at *local*. The
    key names that one opening, for counting its seats."""

    found = []
    for slot in slots:
        for start, end in _windows(slot, local):
            if start <= local < end:
                key = f'{slot["id"]}@{start.date().isoformat()}'
                found.append((slot, start, end, key))
    return found


def next_opening(
    slots: list[dict[str, Any]], local: datetime
) -> Optional[tuple[dict[str, Any], datetime]]:
    """The next slot to open after *local*, and when."""

    best = None
    for slot in slots:
        for start, _end in _windows(slot, local, days_ahead=7):
            if start > local and (best is None or start < best[1]):
                best = (slot, start)
    return best


def _first_offset(key: str, start: datetime, end: datetime, gap: int) -> int:
    """Seconds after a slot opens before its first read: the same for
    one opening, different from day to day, within the first quarter."""

    span = max(1, min(gap * 3, int((end - start).total_seconds() / 4)))
    digest = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(digest[:4], 'big') % span


# ── Watches ─────────────────────────────────────────────────────────


@dataclass
class Watch:
    """What the plan needs from a playlist watch."""

    id: int
    playlist_id: str
    name: str
    interval_minutes: int
    last_checked: Optional[str]
    enabled: bool = True

    @property
    def kind(self) -> str:
        return kind_of(self.playlist_id, self.name)


def _when(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        found = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return found if found.tzinfo else found.replace(tzinfo=timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def due_at(watch: Watch, last: Optional[datetime], tz: Optional[tzinfo]):
    """When *watch* is next due to be read (``None``: now, never read)."""

    if last is None:
        return None
    weekday = refresh_weekday(watch.name)
    if weekday is not None:
        # The first refresh after the last read.
        local = last.astimezone(tz)
        refresh = _at(local, f'{WEEKLY_REFRESH_HOUR:02d}:00')
        refresh += timedelta(days=(weekday - local.weekday()) % 7)
        if refresh <= local:
            refresh += timedelta(days=7)
        return refresh
    return last + timedelta(minutes=max(1, watch.interval_minutes))


# ── State ───────────────────────────────────────────────────────────


def _blank_state() -> dict[str, Any]:
    return {
        # The Spotify account the companion read for first: another one
        # later puts everything on hold (so nobody's mixes get mixed).
        'account': None,
        # The companion's last report: status, account, version, at.
        'seen': None,
        # What the last notification was about (None: all is well).
        'incident': None,
        'in_flight': None,
        'not_before': None,
        'reads': [],
        'requests': [],
        'errors': {},
    }


def _snapshot_name(playlist_id: str) -> str:
    return re.sub(r'[^A-Za-z0-9]', '', playlist_id)[:64] + '.json'


class Store:
    """The companion's settings and state, saved in *root*."""

    def __init__(
        self,
        root: Path,
        *,
        tz: Optional[tzinfo] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.root = Path(root)
        self.tz = tz
        self.rng = rng or random.Random()
        self._lock = threading.RLock()
        self.config = effective(None)
        self.state = _blank_state()
        self._load()

    # ── Files ──

    def _load(self) -> None:
        path = self.root / STATE_FILE
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        self.config = effective(data.get('config'))
        state = data.get('state')
        if isinstance(state, dict):
            self.state = {**_blank_state(), **state}

    def _save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / STATE_FILE
        tmp = path.with_suffix('.tmp')
        tmp.write_text(
            json.dumps({'config': self.config, 'state': self.state}),
            encoding='utf-8',
        )
        os.replace(tmp, path)

    # ── Settings ──

    @property
    def enabled(self) -> bool:
        return bool(self.config['enabled'])

    def set_config(self, raw: Any) -> dict[str, Any]:
        with self._lock:
            merged = {**self.config, **(raw if isinstance(raw, dict) else {})}
            self.config = effective(merged)
            if not self.enabled:
                self.state['in_flight'] = None
                self.state['requests'] = []
            self._save()
            return self.config

    def accept_account(self) -> None:
        """Make the account the companion is signed in to now the one
        to read for (after "signed in to another account")."""

        with self._lock:
            seen = self.state.get('seen') or {}
            self.state['account'] = seen.get('account')
            self._save()

    # ── Health ──

    def health(self, now: datetime) -> dict[str, Any]:
        """``status`` (:data:`READY` when mixes can be read) and what is
        known about the companion."""

        seen = self.state.get('seen') or {}
        account = seen.get('account')
        expected = self.state.get('account')
        at = _when(seen.get('at'))
        if not self.enabled:
            status = OFF
        elif at is None:
            status = NEVER
        elif now - at > AWAY_AFTER:
            status = AWAY
        else:
            status = seen.get('status') or ERROR
            if (
                status == READY
                and expected
                and account
                and account.get('id') != expected.get('id')
            ):
                status = OTHER_ACCOUNT
        return {
            'status': status,
            'seen_at': seen.get('at'),
            'reported': seen.get('status'),
            'message': seen.get('message') or '',
            'version': seen.get('version') or '',
            'account': account,
            'expected_account': expected,
        }

    def _incident(self, now: datetime) -> Optional[str]:
        health = self.health(now)
        status = health['status']
        if status in {SIGNED_OUT, OTHER_ACCOUNT}:
            return status
        at = _when(health['seen_at'])
        if (
            status == AWAY
            and at is not None
            and now - at >= timedelta(hours=self.config['away_alert_hours'])
        ):
            return AWAY
        return None

    def _notices(self, now: datetime) -> list[tuple[str, str]]:
        """What changed worth a notification (``(title, text)``), and
        remember it."""

        before = self.state.get('incident')
        if not self.enabled:
            # Turned off: nothing to report, and nothing "back" either.
            self.state['incident'] = None
            return []
        after = self._incident(now)
        if before == after:
            return []
        self.state['incident'] = after
        if after is None:
            return [
                (
                    'back',
                    'Spotify mixes made for you are being read again.',
                )
            ]
        health = self.health(now)
        if after == SIGNED_OUT:
            text = (
                'Sign in to Spotify again in the browser the companion '
                'runs in. Your personal mix watches are on hold until then.'
            )
            return [('signed out of Spotify', text)]
        if after == OTHER_ACCOUNT:
            name = (health['account'] or {}).get('name') or 'another account'
            want = (health['expected_account'] or {}).get('name') or 'yours'
            text = (
                f'It is signed in to {name}, not {want}. Your personal mix '
                'watches are on hold: sign back in, or use the new account '
                'from Settings > Apps > Spotify companion.'
            )
            return [('signed in to another Spotify account', text)]
        hours = self.config['away_alert_hours']
        text = (
            f'Nothing heard from it for {hours} hours: is its browser '
            'running? Your personal mix watches are on hold until it is '
            'back.'
        )
        return [('not heard from', text)]

    def report(self, now: datetime, raw: Any) -> list[tuple[str, str]]:
        """The companion checked in with *raw* (``status``, ``account``
        ``{id, name}``, ``version``, ``message``). Returns notifications."""

        data = raw if isinstance(raw, dict) else {}
        status = data.get('status')
        status = status if status in REPORTED else ERROR
        account = data.get('account')
        if isinstance(account, dict) and account.get('id'):
            account = {
                'id': str(account['id'])[:100],
                'name': str(account.get('name') or account['id'])[:100],
            }
        else:
            account = None
        with self._lock:
            if status == READY and account is None:
                status = SIGNED_OUT
            self.state['seen'] = {
                'status': status,
                'account': account,
                'version': str(data.get('version') or '')[:20],
                'message': str(data.get('message') or '')[:300],
                'at': _iso(now),
            }
            if (
                self.enabled
                and status == READY
                and self.state.get('account') is None
            ):
                self.state['account'] = account
            notices = self._notices(now)
            self._save()
            return notices

    def tick(self, now: datetime) -> list[tuple[str, str]]:
        """Run now and then: notices the companion going quiet, and gives
        up a read nobody answered."""

        with self._lock:
            changed = self._expire(now)
            notices = self._notices(now)
            if changed or notices:
                self._save()
            return notices

    # ── Reads ──

    def _expire(self, now: datetime) -> bool:
        changed = False
        flight = self.state.get('in_flight')
        if flight and now - (_when(flight['at']) or now) > JOB_TIMEOUT:
            self.state['in_flight'] = None
            self.state['errors'][str(flight['watch_id'])] = {
                'at': _iso(now),
                'error': 'The companion never answered',
            }
            changed = True
        cutoff = now - KEEP_READS
        reads = [
            r
            for r in self.state['reads']
            if (_when(r.get('at')) or now) >= cutoff
        ]
        if len(reads) != len(self.state['reads']):
            self.state['reads'] = reads
            changed = True
        return changed

    def last_read(self, watch: Watch) -> Optional[datetime]:
        times = [
            _when(r['at'])
            for r in self.state['reads']
            if r.get('watch_id') == watch.id and r.get('ok', True)
        ]
        times.append(_when(watch.last_checked))
        found = [t for t in times if t is not None]
        return max(found) if found else None

    def request(self, watch_id: int) -> None:
        """ "Check now": read *watch_id* next, outside the slots."""

        with self._lock:
            if watch_id not in self.state['requests']:
                self.state['requests'].append(watch_id)
                self._save()

    def plan(
        self, now: datetime, watches: list[Watch], query_hash: str = ''
    ) -> dict[str, Any]:
        """The companion asks for work: ``{'job': {...}}`` or
        ``{'wait_seconds': n, 'reason': ...}``."""

        with self._lock:
            self._expire(now)
            decision = self._plan(now, watches, query_hash)
            self._save()
            return decision

    def _plan(  # noqa: PLR0911  # one early answer per reason to wait
        self, now: datetime, watches: list[Watch], query_hash: str
    ) -> dict[str, Any]:
        if not self.enabled:
            return _wait(600, OFF)
        status = self.health(now)['status']
        if status != READY:
            return _wait(120, status)
        if self.state.get('in_flight'):
            return _wait(30, 'busy')
        not_before = _when(self.state.get('not_before'))
        if not_before is not None and now < not_before:
            return _wait((not_before - now).total_seconds(), 'gap')
        mine = {
            w.id: w
            for w in watches
            if w.enabled and is_personal_mix(w.playlist_id)
        }
        gap = self.config['min_gap_seconds']
        # "Check now" first.
        while self.state['requests']:
            watch = mine.get(self.state['requests'][0])
            self.state['requests'].pop(0)
            if watch is not None:
                return self._hand_out(now, watch, 'now', gap, query_hash)
        local = now.astimezone(self.tz)
        windows = open_windows(self.config['slots'], local)
        if not windows:
            upcoming = next_opening(self.config['slots'], local)
            if upcoming is None:
                return _wait(3600, 'no_slots')
            seconds = (upcoming[1] - local).total_seconds()
            return _wait(min(3600, seconds), 'between_slots')
        return self._from_slots(now, local, windows, mine, query_hash)

    def _from_slots(
        self,
        now: datetime,
        local: datetime,
        windows: list[tuple[dict[str, Any], datetime, datetime, str]],
        mine: dict[int, Watch],
        query_hash: str,
    ) -> dict[str, Any]:
        """The next read from the open slots: the most overdue mix of a
        kind a slot with a free seat takes."""

        gap = self.config['min_gap_seconds']
        waits = []
        for slot, start, end, key in windows:
            used = sum(1 for r in self.state['reads'] if r.get('slot') == key)
            left = slot['seats'] - used
            if left <= 0:
                continue
            candidates = []
            for watch in mine.values():
                if watch.kind not in slot['kinds']:
                    continue
                due = due_at(watch, self.last_read(watch), self.tz)
                if due is None or due <= now:
                    candidates.append((
                        due or datetime.min.replace(tzinfo=timezone.utc),
                        watch,
                    ))
            if not candidates:
                continue
            if used == 0:
                first = start + timedelta(
                    seconds=_first_offset(key, start, end, gap)
                )
                if local < first:
                    waits.append((first - local).total_seconds())
                    continue
            candidates.sort(key=lambda pair: (pair[0], pair[1].id))
            remaining = (end - local).total_seconds()
            spread = remaining / min(left, len(candidates))
            pause = min(
                MAX_GAP_SECONDS,
                max(gap, spread * self.rng.uniform(0.7, 1.3)),
            )
            return self._hand_out(
                now, candidates[0][1], key, pause, query_hash
            )
        if waits:
            return _wait(min(waits), 'slot_opening')
        return _wait(300, 'nothing_due')

    def _hand_out(
        self,
        now: datetime,
        watch: Watch,
        slot: str,
        pause: float,
        query_hash: str,
    ) -> dict[str, Any]:
        job = {
            'id': uuid.uuid4().hex,
            'watch_id': watch.id,
            'playlist_id': watch.playlist_id,
            'name': watch.name,
            'hash': query_hash,
            'page_size': 100,
        }
        self.state['in_flight'] = {**job, 'slot': slot, 'at': _iso(now)}
        self.state['not_before'] = _iso(now + timedelta(seconds=pause))
        return {'job': job}

    def finish(
        self,
        now: datetime,
        job_id: str,
        *,
        tracks: Optional[list[dict[str, Any]]] = None,
        name: str = '',
        error: str = '',
    ) -> tuple[dict[str, Any], list[tuple[str, str]]]:
        """The answer to a read: its songs, or why it failed. Returns the
        job and any notifications."""

        with self._lock:
            flight = self.state.get('in_flight')
            if not flight or flight.get('id') != job_id:
                raise UnknownJob(job_id)
            self.state['in_flight'] = None
            ok = tracks is not None and not error
            self.state['reads'].append({
                'watch_id': flight['watch_id'],
                'slot': flight['slot'],
                'at': _iso(now),
                'ok': ok,
            })
            key = str(flight['watch_id'])
            if ok:
                self.state['errors'].pop(key, None)
                self._write_snapshot(
                    flight['playlist_id'], name or flight['name'], tracks or []
                )
            else:
                self.state['errors'][key] = {
                    'at': _iso(now),
                    'error': (error or 'The read failed')[:300],
                }
                if error == SIGNED_OUT and self.state.get('seen'):
                    self.state['seen']['status'] = SIGNED_OUT
                if error == RATE_LIMITED:
                    # Spotify asked to slow down: an hour off.
                    self.state['not_before'] = _iso(now + RATE_LIMIT_PAUSE)
            notices = self._notices(now)
            self._save()
            return flight, notices

    # ── Snapshots ──

    def _write_snapshot(
        self, playlist_id: str, name: str, tracks: list[dict[str, Any]]
    ) -> None:
        folder = self.root / SNAPSHOTS
        folder.mkdir(parents=True, exist_ok=True)
        account = (self.state.get('seen') or {}).get('account')
        path = folder / _snapshot_name(playlist_id)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(
            json.dumps({
                'playlist_id': playlist_id,
                'name': name,
                'tracks': tracks,
                'account': account,
                'at': _iso(datetime.now(timezone.utc)),
            }),
            encoding='utf-8',
        )
        os.replace(tmp, path)

    def snapshot(
        self, playlist_id: str
    ) -> Optional[tuple[str, list[dict[str, Any]]]]:
        """``(name, tracks)`` from the companion's last read of a mix."""

        path = self.root / SNAPSHOTS / _snapshot_name(playlist_id)
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None
        tracks = data.get('tracks')
        if not isinstance(tracks, list):
            return None
        return str(data.get('name') or ''), tracks

    # ── The page ──

    def summary(self, now: datetime, watches: list[Watch]) -> dict[str, Any]:
        with self._lock:
            mine = [
                w
                for w in watches
                if w.enabled and is_personal_mix(w.playlist_id)
            ]
            local = now.astimezone(self.tz)
            today = local.date()
            reads_today = [
                r
                for r in self.state['reads']
                if (_when(r['at']) or now).astimezone(self.tz).date() == today
            ]
            slots = []
            for slot in self.config['slots']:
                windows = open_windows([slot], local)
                key = windows[0][3] if windows else None
                slots.append({
                    'id': slot['id'],
                    'open': key is not None,
                    'used': sum(
                        1
                        for r in self.state['reads']
                        if key and r['slot'] == key
                    ),
                })
            upcoming = next_opening(self.config['slots'], local)
            per_watch = {}
            for watch in mine:
                last = self.last_read(watch)
                due = due_at(watch, last, self.tz)
                per_watch[watch.id] = {
                    'kind': watch.kind,
                    'last_read': _iso(last) if last else None,
                    'due': due is None or due <= now,
                    'next_due': _iso(due) if due else None,
                    'requested': watch.id in self.state['requests'],
                    'error': self.state['errors'].get(str(watch.id)),
                    'has_snapshot': self.snapshot(watch.playlist_id)
                    is not None,
                }
            flight = self.state.get('in_flight')
            return {
                'health': self.health(now),
                'mixes': len(mine),
                'due': sum(1 for w in per_watch.values() if w['due']),
                'reads_today': len(reads_today),
                'failed_today': sum(
                    1 for r in reads_today if not r.get('ok', True)
                ),
                'slots': slots,
                'next_opening': (
                    {'id': upcoming[0]['id'], 'at': _iso(upcoming[1])}
                    if upcoming and not any(s['open'] for s in slots)
                    else None
                ),
                'reading': (
                    {'watch_id': flight['watch_id'], 'name': flight['name']}
                    if flight
                    else None
                ),
                'watches': per_watch,
            }


def _wait(seconds: float, reason: str) -> dict[str, Any]:
    return {'wait_seconds': max(15, int(seconds)), 'reason': reason}


# ── The one store of this process ───────────────────────────────────

_current: Optional[Store] = None


def set_current(store: Optional[Store]) -> None:
    global _current
    _current = store


def current() -> Optional[Store]:
    return _current


def manages(playlist_id: Any) -> bool:
    """Whether the companion, not a signed-out read, supplies the songs
    of Spotify playlist *playlist_id*."""

    store = _current
    return store is not None and store.enabled and is_personal_mix(playlist_id)


def personal_playlist(
    playlist_id: str,
) -> Optional[tuple[str, list[dict[str, Any]]]]:
    """For :mod:`downtify.spotify`: ``None`` to read *playlist_id* as
    usual, else ``(name, tracks)`` from the companion. Raises
    :class:`CompanionWaiting` for a mix it hasn't read yet."""

    if not manages(playlist_id):
        return None
    found = _current.snapshot(playlist_id) if _current else None
    if found is None:
        raise CompanionWaiting(
            'This Spotify mix is made for whoever is signed in. The '
            'Spotify companion has not read your version of it yet, so it '
            'is waiting (Settings > Apps > Spotify companion).'
        )
    # Copies, so a caller can't change the saved list.
    return found[0], [dict(t) for t in found[1]]
