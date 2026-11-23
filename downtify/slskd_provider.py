"""slskd provider integration for track search and download handoff."""

from __future__ import annotations

import hashlib
import os
import re
import threading
import time
import unicodedata
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import quote

import httpx
from loguru import logger

from .audio_formats import extensions_of
from .library_metadata import read_audio_metadata
from .track_tag_match import (
    MIX_VARIANT_REMOTE_SKIP_KEYWORDS,
    duration_tolerances_from_settings,
    media_duration_matches_mix_variant,
    media_duration_matches_song,
    remote_text_unacceptable,
    snapshot_spotify_metadata,
    spotify_file_tag_mismatch_label,
    strip_mix_suffix,
    verify_downloaded_file_matches_spotify,
)
from .track_tag_match import fold_accents as _fold_accents
from .track_tag_match import plain_name as _plain_name

ProgressCallback = Callable[[float, str], None]

_SLSKD_SEM: Optional[threading.Semaphore] = None
_SLSKD_SEM_LIMIT = 0


def _slskd_parallel_limit(settings: dict[str, Any]) -> int:
    return _int_setting(
        settings,
        'max_parallel_downloads',
        3,
        minimum=1,
        maximum=8,
    )


def reset_slskd_parallelism(settings: dict[str, Any]) -> None:
    """Apply a new parallel limit after settings change (call on save)."""
    global _SLSKD_SEM, _SLSKD_SEM_LIMIT
    limit = _slskd_parallel_limit(settings)
    _SLSKD_SEM = threading.Semaphore(limit)
    _SLSKD_SEM_LIMIT = limit


def _slskd_semaphore(settings: dict[str, Any]) -> threading.Semaphore:
    """Match Downtify parallel download setting; do not serialize all slskd work."""
    limit = _slskd_parallel_limit(settings)
    if _SLSKD_SEM is None or _SLSKD_SEM_LIMIT != limit:
        reset_slskd_parallelism(settings)
    return _SLSKD_SEM


_DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 600
_DEFAULT_QUEUED_TIMEOUT_SECONDS = 180
_TRANSFERS_LOCK = threading.Lock()
_TRANSFERS_CACHE: OrderedDict[
    tuple[str, bytes], tuple[float, list[dict[str, Any]]]
] = OrderedDict()
_TRANSFERS_CACHE_LIMIT = 32

# ── Peers and files that just failed ───────────────────────────────────
# A watch retries a missing song on every check, and the search ranks the
# same file first each time: a peer whose copy changed size (slskd:
# "remote size ... does not match expected size") or who stopped sharing
# it ("File not shared") was asked again and again. A failed file is
# skipped for a while, and a peer that says it is overwhelmed is tried
# last for a while. Kept in memory: a restart forgets it.

#: Seconds a file is skipped after slskd says the peer can't serve it.
BAD_FILE_SECONDS = 24 * 3600
#: Seconds a file is skipped after it stalled or timed out.
SLOW_FILE_SECONDS = 3600
#: Seconds a peer that said it is overwhelmed is tried last.
BUSY_PEER_SECONDS = 15 * 60

#: Words in slskd's transfer error that mean this file won't come from
#: this peer however often it is asked.
_BAD_FILE_ERRORS = (
    'not shared',
    'does not match expected size',
    'file read error',
    'rejected',
)
_BUSY_PEER_ERRORS = ('overwhelmed', 'too many')

_FAILED_LOCK = threading.Lock()
_FAILED_FILES: dict[tuple[str, str], float] = {}
_BUSY_PEERS: dict[str, float] = {}


def _transfer_error(transfer: Optional[dict[str, Any]]) -> str:
    """slskd's reason a transfer ended, lower-cased (``''`` without one)."""

    if not transfer:
        return ''
    parts = [
        str(transfer.get(key) or '')
        for key in ('exception', 'state', 'stateDescription')
    ]
    return ' '.join(p for p in parts if p).lower()


def remember_failure(
    username: str,
    filename: str,
    transfer: Optional[dict[str, Any]],
    *,
    now: Optional[float] = None,
) -> str:
    """Remember a candidate that failed; returns how (``bad_file``,
    ``busy_peer`` or ``slow``)."""

    now = time.monotonic() if now is None else now
    error = _transfer_error(transfer)
    key = (username, filename)
    with _FAILED_LOCK:
        if any(word in error for word in _BUSY_PEER_ERRORS):
            _BUSY_PEERS[username] = now + BUSY_PEER_SECONDS
            return 'busy_peer'
        if any(word in error for word in _BAD_FILE_ERRORS):
            _FAILED_FILES[key] = now + BAD_FILE_SECONDS
            return 'bad_file'
        _FAILED_FILES[key] = max(
            _FAILED_FILES.get(key, 0.0), now + SLOW_FILE_SECONDS
        )
        return 'slow'


def _recently_failed(
    username: str, filename: str, *, now: Optional[float] = None
) -> bool:
    now = time.monotonic() if now is None else now
    with _FAILED_LOCK:
        until = _FAILED_FILES.get((username, filename))
        if until is not None and until <= now:
            del _FAILED_FILES[(username, filename)]
            return False
        return until is not None


def _peer_busy(username: str, *, now: Optional[float] = None) -> bool:
    now = time.monotonic() if now is None else now
    with _FAILED_LOCK:
        until = _BUSY_PEERS.get(username)
        if until is not None and until <= now:
            del _BUSY_PEERS[username]
            return False
        return until is not None


def order_by_past_failures(
    files: list[dict[str, Any]], *, now: Optional[float] = None
) -> list[dict[str, Any]]:
    """*files* without the ones that failed recently, with files of peers
    that said they are overwhelmed moved to the end."""

    kept = [
        row
        for row in files
        if not _recently_failed(
            str(row.get('username') or ''),
            str(row.get('filename') or ''),
            now=now,
        )
    ]
    return sorted(
        kept,
        key=lambda row: _peer_busy(str(row.get('username') or ''), now=now),
    )


def forget_failures() -> None:
    """Forget every remembered failure (tests, and settings changes)."""

    with _FAILED_LOCK:
        _FAILED_FILES.clear()
        _BUSY_PEERS.clear()


def _poll_env(name: str, default: int, minimum: int, maximum: int) -> int:
    return _int_setting(
        {name: os.getenv(name)},
        name,
        default,
        minimum=minimum,
        maximum=maximum,
    )


def _poll_sleep(
    seconds: float, cancel_check: Optional[Callable[[], None]]
) -> None:
    """Keep cancellation responsive without extra HTTP or filesystem polls."""
    if cancel_check is None:
        time.sleep(seconds)
        return
    remaining = seconds
    while remaining > 0:
        cancel_check()
        step = min(1.0, remaining)
        time.sleep(step)
        remaining -= step


class _PollSchedule:
    """Bound expensive polls while retaining the original wait budget."""

    def __init__(self, settings: dict[str, Any]) -> None:
        self.interval = _poll_env(
            'DOWNTIFY_POLL_INTERVAL',
            _int_setting(
                settings, 'poll_interval_seconds', 5, minimum=1, maximum=30
            ),
            1,
            30,
        )
        self.idle_interval = _poll_env(
            'DOWNTIFY_POLL_IDLE_INTERVAL', 60, 1, 60
        )
        self.deep_scan_every = _poll_env(
            'DOWNTIFY_POLL_DEEP_SCAN_EVERY', 12, 1, 300
        )
        self.attempts = _int_setting(
            settings, 'poll_max_attempts', 60, minimum=1, maximum=300
        )
        self.started = time.monotonic()
        self.remaining_sleep = float(self.attempts * self.interval)
        self.last_deep_scan = self.started - 60

    def should_scan(
        self, attempt: int, transfer: Optional[dict[str, Any]]
    ) -> bool:
        now = time.monotonic()
        scan = (
            attempt % self.deep_scan_every == 0
            or bool(transfer)
            or now - self.last_deep_scan >= 60
        )
        if scan:
            self.last_deep_scan = now
        return scan

    def sleep(
        self,
        transfer: Optional[dict[str, Any]],
        last_progress: float,
        queued_timeout: int,
        deadline: Optional[float],
        cancel_check: Optional[Callable[[], None]],
    ) -> None:
        now = time.monotonic()
        timeout_at = (
            last_progress if transfer else self.started
        ) + queued_timeout
        seconds = min(
            self.interval if transfer else self.idle_interval,
            max(1.0, timeout_at - now),
            self.remaining_sleep,
        )
        if deadline is not None:
            seconds = min(seconds, max(0.0, deadline - now))
        _poll_sleep(seconds, cancel_check)
        self.remaining_sleep -= seconds


def _int_setting(
    settings: dict[str, Any],
    key: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int(settings.get(key) or default)
    except (TypeError, ValueError):
        value = default
    return min(maximum, max(minimum, value))


SLSKD_UNKNOWN_BITRATE_MODES = ('auto', 'allow', 'reject')


def _bitrate_value(value: Any) -> int:
    """A kbps value clamped to 0-10000; anything unreadable is 0 (off)."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return min(10000, max(0, number))


def normalize_slskd_quality(raw: dict[str, Any]) -> dict[str, Any]:
    """The fine-tune quality fields of the slskd settings, normalized.

    ``advanced`` switches them on; while it is off, candidate selection
    ignores them, so turning it off restores the basic behaviour without
    losing what was set. ``unknown_bitrate`` decides files that report no
    bitrate (``auto`` keeps the basic rule: rejected in strict mode with a
    minimum, allowed otherwise). ``format_min_bitrate`` overrides the
    minimum per extension, ``max_bitrate`` (0 = off) skips files above it,
    such as lossless audio in an ``.m4a``, and ``prefer_bitrate`` tries the
    highest bitrate first among files that match well enough.
    """

    floors_raw = raw.get('format_min_bitrate')
    floors: dict[str, int] = {}
    if isinstance(floors_raw, dict):
        for ext, value in floors_raw.items():
            key = str(ext or '').strip().lower().lstrip('.')
            if key and value not in {None, ''}:
                floors[key] = _bitrate_value(value)
    unknown = str(raw.get('unknown_bitrate') or 'auto').strip().lower()
    if unknown not in SLSKD_UNKNOWN_BITRATE_MODES:
        unknown = 'auto'
    return {
        'advanced': bool(raw.get('advanced', False)),
        'unknown_bitrate': unknown,
        'format_min_bitrate': floors,
        'max_bitrate': _bitrate_value(raw.get('max_bitrate')),
        'prefer_bitrate': bool(raw.get('prefer_bitrate', False)),
    }


def _slskd_deadline(settings: dict[str, Any]) -> float:
    seconds = _int_setting(
        settings,
        'download_timeout_seconds',
        _DEFAULT_DOWNLOAD_TIMEOUT_SECONDS,
        minimum=30,
        maximum=3600,
    )
    return time.monotonic() + seconds


def _past_deadline(deadline: float) -> bool:
    return time.monotonic() >= deadline


_AUDIO_EXTENSIONS = frozenset({'mp3', 'flac', 'm4a', 'ogg', 'opus'})
#: A file the deep scan takes for a transfer may be at most this much
#: bigger than slskd said the transfer is (it is the same file).
_DISK_SCAN_MAX_SIZE_SHARE = 1.05
_PATH_PENALTY_KEYWORDS = (
    'unreleased',
    'bootleg',
    'mixtape',
    'discography',
)
_AMBIGUOUS_TITLE_ALNUM_LEN = 5
# Share of the minimum bitrate a variable-bitrate file's average must reach.
_VBR_FLOOR_SHARE = 0.85
_DEFAULT_MATCH_MIN_SCORE = 5
_STRICT_DURATION_SECONDS = 3


class SlskdClient:
    def __init__(self, settings: dict[str, Any]):
        self.base_url = str(settings.get('base_url') or '').strip().rstrip('/')
        self.api_key = str(settings.get('api_key') or '').strip()
        self.timeout = int(settings.get('timeout_seconds') or 20)
        self.search_retries = int(settings.get('search_retries') or 5)
        self.search_poll_seconds = int(
            settings.get('search_poll_seconds') or 15
        )
        self.download_attempts = int(settings.get('download_attempts') or 5)
        self.session = httpx.Client(follow_redirects=True)
        if self.api_key:
            self.session.headers.update({'X-API-Key': self.api_key})

    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def can_connect(self) -> bool:
        for ep in (
            '/api/v0/application',
            '/api/v0/options',
            '/api/v0/transfers/downloads',
        ):
            try:
                self._request('GET', ep)
                return True
            except Exception:
                continue
        return False

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Any] = None,
    ) -> Any:
        url = f'{self.base_url}{path}'
        kwargs: dict[str, Any] = {'timeout': self.timeout}
        if json_body is not None:
            kwargs['json'] = json_body
        resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        if not resp.content:
            return {}
        return resp.json()

    def start_search(self, query: str) -> Optional[str]:
        body = {
            'searchText': query,
            'filterResponses': True,
            'minimumResponseFileCount': 1,
            'minimumPeerUploadSpeed': 1,
        }
        try:
            data = self._request('POST', '/api/v0/searches', json_body=body)
        except Exception as exc:
            logger.info(
                'slskd: search POST failed q={!r} err={}', query[:120], exc
            )
            return None
        if isinstance(data, dict):
            for key in ('id', 'searchId'):
                raw = data.get(key)
                if isinstance(raw, (int, str)) and str(raw).strip():
                    return str(raw).strip()
        return None

    def wait_search_complete(
        self,
        search_id: str,
        label: str,
        *,
        on_poll: Optional[Callable[[float], None]] = None,
        deadline: Optional[float] = None,
        cancel_check: Optional[Callable[[], None]] = None,
    ) -> bool:
        max_attempts = max(1, self.search_retries)
        for attempt in range(max_attempts):
            if cancel_check:
                cancel_check()
            if deadline is not None and _past_deadline(deadline):
                return False
            if on_poll is not None:
                try:
                    on_poll(5.0 + (attempt / max_attempts) * 30.0)
                except Exception:
                    logger.opt(exception=True).debug(
                        'slskd search progress callback error'
                    )
            try:
                status = self._request('GET', f'/api/v0/searches/{search_id}')
            except Exception as exc:
                logger.info(
                    'slskd: search status failed id={} err={}', search_id, exc
                )
                return False
            if not isinstance(status, dict):
                return False
            file_count = int(status.get('fileCount') or 0)
            locked = int(status.get('lockedFileCount') or 0)
            if status.get('isComplete'):
                if file_count > 0 and file_count != locked:
                    return True
                logger.info(
                    'slskd: search complete but no free files label={!r} '
                    'fileCount={} locked={}',
                    label[:120],
                    file_count,
                    locked,
                )
                return False
            if attempt + 1 < self.search_retries:
                time.sleep(max(1, self.search_poll_seconds))
        logger.info(
            'slskd: search timed out label={!r} retries={}',
            label[:120],
            self.search_retries,
        )
        return False

    def search_responses(self, search_id: str) -> list[dict[str, Any]]:
        try:
            data = self._request(
                'GET', f'/api/v0/searches/{search_id}/responses'
            )
        except Exception:
            return []
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
        return []

    def delete_search(self, search_id: str) -> None:
        try:
            self._request('DELETE', f'/api/v0/searches/{search_id}')
        except Exception:
            pass

    def enqueue_download(self, row: dict[str, Any]) -> bool:
        username = str(
            row.get('username') or row.get('userName') or row.get('user') or ''
        ).strip()
        filename = str(
            row.get('filename')
            or row.get('fileName')
            or row.get('path')
            or row.get('fullPath')
            or ''
        ).strip()
        if not username or not filename:
            return False
        try:
            size = int(row.get('size') or 0)
        except (TypeError, ValueError):
            size = 0
        endpoint = f'/api/v0/transfers/downloads/{quote(username)}'
        body = [{'filename': filename, 'size': max(0, size)}]
        try:
            self._request('POST', endpoint, json_body=body)
            with _TRANSFERS_LOCK:
                _TRANSFERS_CACHE.pop(self._transfers_cache_key(), None)
            return True
        except Exception as exc:
            logger.info(
                'slskd: enqueue failed user={!r} file={!r} err={}',
                username,
                filename[:120],
                exc,
            )
            return False

    def cancel_download(self, username: str, transfer_id: str) -> bool:
        """Cancel a download Downtify gave up on, so the peer doesn't
        deliver it later and it doesn't linger in slskd's queue (where a
        restart of slskd ends it as "Application shut down"). The
        transfer stays in slskd's history; only its state changes."""

        if not username or not transfer_id:
            return False
        endpoint = (
            f'/api/v0/transfers/downloads/{quote(username)}/'
            f'{quote(transfer_id)}'
        )
        try:
            self._request('DELETE', endpoint)
        except Exception as exc:
            logger.info(
                'slskd: cancel failed user={!r} id={} err={}',
                username,
                transfer_id,
                exc,
            )
            return False
        with _TRANSFERS_LOCK:
            _TRANSFERS_CACHE.pop(self._transfers_cache_key(), None)
        return True

    def list_download_transfers(self) -> list[dict[str, Any]]:
        ttl = _poll_env('DOWNTIFY_TRANSFERS_TTL', 3, 0, 60)
        if ttl == 0:
            return self._fetch_download_transfers() or []
        # Single-flight across workers using the same endpoint/credentials.
        # Never share another API key's snapshot or cache a failed request.
        with _TRANSFERS_LOCK:
            key = self._transfers_cache_key()
            cached = _TRANSFERS_CACHE.get(key)
            if cached and 0 <= time.monotonic() - cached[0] < ttl:
                _TRANSFERS_CACHE.move_to_end(key)
                return cached[1]
            data = self._fetch_download_transfers()
            if data is None:
                return []
            _TRANSFERS_CACHE[key] = (time.monotonic(), data)
            _TRANSFERS_CACHE.move_to_end(key)
            while len(_TRANSFERS_CACHE) > _TRANSFERS_CACHE_LIMIT:
                _TRANSFERS_CACHE.popitem(last=False)
            return data

    def _transfers_cache_key(self) -> tuple[str, bytes]:
        return self.base_url, hashlib.sha256(self.api_key.encode()).digest()

    def _fetch_download_transfers(self) -> Optional[list[dict[str, Any]]]:
        try:
            data = self._request('GET', '/api/v0/transfers/downloads')
        except Exception:
            return None
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        return []

    def find_transfer(
        self, username: str, filename: str
    ) -> Optional[dict[str, Any]]:
        transfers = self.list_download_transfers()
        for peer_filter in (username, ''):
            for peer in transfers:
                if (
                    peer_filter
                    and str(peer.get('username') or '') != peer_filter
                ):
                    continue
                for directory in peer.get('directories') or []:
                    if not isinstance(directory, dict):
                        continue
                    for file_row in directory.get('files') or []:
                        if not isinstance(file_row, dict):
                            continue
                        name = str(
                            file_row.get('filename')
                            or file_row.get('fileName')
                            or ''
                        )
                        if _paths_match(name, filename):
                            return file_row
        return None

    def remote_download_directories(self) -> list[str]:
        """Best-effort read of slskd's configured download/incomplete dirs."""
        for endpoint in ('/api/v0/options', '/api/v0/application'):
            try:
                data = self._request('GET', endpoint)
            except Exception:
                continue
            paths = _extract_directory_paths(data)
            if paths:
                return paths
        return []


def _flatten_slskd_responses(data: Any) -> list[dict[str, Any]]:
    responses = data if isinstance(data, list) else []
    rows: list[dict[str, Any]] = []
    for resp in responses:
        if not isinstance(resp, dict):
            continue
        username = str(
            resp.get('username')
            or resp.get('userName')
            or resp.get('user')
            or ''
        ).strip()
        for file_row in resp.get('files') or []:
            if not isinstance(file_row, dict):
                continue
            filename = str(
                file_row.get('filename')
                or file_row.get('fileName')
                or file_row.get('path')
                or ''
            ).strip()
            if not filename:
                continue
            rows.append({**file_row, 'username': username})
    return rows


def _normalize_search_text(text: str) -> str:
    folded = unicodedata.normalize('NFKC', text)
    folded = re.sub(r"[''`\u2019]", '', folded)
    return re.sub(r'\s+', ' ', folded).strip()


# "&", "+" and "and" join names the same way ("Earth, Wind & Fire" is
# often filed as "Earth Wind and Fire"), so a comparison leaves them out.
_JOINER = re.compile(r'(?<!\w)(?:and|&|\+)(?!\w)', re.IGNORECASE)
# "Pt. II" / "Part 2" / "pt 2" are one spelling to a comparison.
_PART_NUMBER = re.compile(
    r'\b(?:pt|part|vol|volume|chapter)\b\.?\s*([ivx]+|\d+)\b', re.IGNORECASE
)
_ROMAN = {
    'i': '1',
    'ii': '2',
    'iii': '3',
    'iv': '4',
    'v': '5',
    'vi': '6',
    'vii': '7',
    'viii': '8',
    'ix': '9',
    'x': '10',
}


def _part_number(match: re.Match) -> str:
    number = match.group(1).casefold()
    return f' pt {_ROMAN.get(number, number)} '


def _alnum_only(text: str) -> str:
    """*text* as names are compared: letters and digits only (any script,
    so ``夜に駆ける`` is still a title), no accents, no case, without
    ``&``/``+``/``and``, and ``Part II`` spelled ``pt 2``."""

    folded = _fold_accents(_normalize_search_text(text)).casefold()
    folded = _PART_NUMBER.sub(_part_number, _JOINER.sub(' ', folded))
    return re.sub(r'[\W_]+', '', folded)


def _primary_title(title: str) -> str:
    text = strip_mix_suffix(str(title or '').strip())
    if ' - ' in text:
        head = text.split(' - ', 1)[0].strip()
        if head:
            return head
    return text


# "(feat. X)", "[with X]", "(from GTAVI: The Album)": credits and where a
# song comes from, which Spotify puts in the title and a shared file's name
# usually leaves out, words differently or moves in front of the title.
_CREDIT_PART = re.compile(
    r'\s*[\(\[]\s*(?:feat\.?|ft\.?|featuring|with|from)\s[^\)\]]*[\)\]]',
    re.IGNORECASE,
)
_CREDIT_TAIL = re.compile(
    r'\s+(?:feat\.?|ft\.?|featuring)\s.*$', re.IGNORECASE
)


def _core_title(title: str) -> str:
    """The song's own name, as a shared file names it: :func:`_primary_title`
    without featured artists or a "(from …)" note - ``That's It (feat.
    Future & Metro Boomin)`` -> ``That's It``."""

    primary = _primary_title(title)
    core = _CREDIT_TAIL.sub('', _CREDIT_PART.sub('', primary)).strip()
    return core or primary


# Words that make a recording a different version of the song. One that
# is in Spotify's title must be in the file's path too, so "Despacito -
# Remix" never gets the original and "Jóga - Live" never the studio take.
_VERSION_WORDS = (
    'remix',
    'live',
    'acoustic',
    'instrumental',
    'demo',
    'unplugged',
    'karaoke',
    'acapella',
    'a cappella',
    'sped up',
    'slowed',
    'nightcore',
    'reprise',
    'orchestral',
)


def _version_words(text: str) -> list[str]:
    folded = ' '.join(re.split(r'[\W_]+', _fold_accents(text).casefold()))
    return [
        word for word in _VERSION_WORDS if re.search(rf'\b{word}\b', folded)
    ]


def _missing_version_word(song: dict[str, Any], filename: str) -> bool:
    title = str(song.get('name') or '')
    album = str(song.get('album_name') or '')
    wanted = [
        w for w in _version_words(title) if w not in _version_words(album)
    ] + [w for w in _version_words(album) if w in _version_words(title)]
    if not wanted:
        return False
    path = ' '.join(re.split(r'[\W_]+', _fold_accents(filename).casefold()))
    return any(word not in path for word in wanted)


_BRACKETED = re.compile(r'\s*[\(\[][^\)\]]*[\)\]]')


def _bare_title(title: str) -> str:
    """:func:`_core_title` without bracketed extras that don't make it a
    different version - ``Gangnam Style (강남스타일)`` -> ``Gangnam Style``,
    ``Superhero (Heroes & Villains)`` -> ``Superhero`` - or ``""`` when
    there are none, or one names a version (``(Taylor's Version)``,
    ``(Remix)``)."""

    core = _core_title(title)
    parts = _BRACKETED.findall(core)
    if not parts:
        return ''
    if any(
        _version_words(part) or re.search(r'version|mix|edit', part, re.I)
        for part in parts
    ):
        return ''
    return _BRACKETED.sub('', core).strip()


def _duo_surnames_in(artist: str, path_alnum: str) -> str:
    """For a duo or group credited by full names (``Daryl Hall & John
    Oates``), the first surname when every member's surname is in
    *path_alnum* - files often say ``Hall & Oates`` - else ``""``."""

    parts = [
        p
        for p in re.split(r'\s*(?:,|&|\+|\band\b)\s*', artist, flags=re.I)
        if p.strip()
    ]
    if len(parts) < 2:
        return ''
    surnames = [_alnum_only(part.split()[-1]) for part in parts]
    if all(len(name) >= 3 and name in path_alnum for name in surnames):
        return surnames[0]
    return ''


def _artist_key(artist: str) -> str:
    """*artist* as a file name is compared with it: :func:`_alnum_only`,
    without a leading "The" (``The Killers`` is often filed as ``Killers``)."""

    name = re.sub(r'^\s*the\s+', '', str(artist or ''), flags=re.IGNORECASE)
    return _alnum_only(name) or _alnum_only(artist)


def _soulseek_words(text: str, *, join_apostrophes: bool = False) -> str:
    """*text* as Soulseek search words. Peers match whole words of a shared
    path, split at punctuation, so ``That's It (feat. A & B)`` is searched
    as ``That s It feat A B`` - the way Nicotine+ sends it - since
    ``Thats`` or ``(feat.`` match no file. *join_apostrophes* gives the
    ``Thats It`` spelling instead, for files named without the apostrophe."""

    folded = unicodedata.normalize('NFKC', str(text or ''))
    # A censored word ("F**kin'") matches no file ("Fuckin"): left out.
    folded = re.sub(r'\S*[^\W\d_]\*+\S*', ' ', folded)
    folded = re.sub(r"['`\u2019]", '' if join_apostrophes else ' ', folded)
    return re.sub(r'[\W_]+', ' ', folded).strip()


def _censored_title_in(title: str, base_alnum: str) -> bool:
    """Whether *title*, censored by Spotify (``F**kin' Problems``), is in a
    file name that spells it out (``Fuckin Problems``): each ``*`` run
    stands for up to four letters, or none (``Fkin``)."""

    if not re.search(r'[^\W\d_]\*', title):
        return False
    pieces = [_alnum_only(piece) for piece in re.split(r'\*+', title)]
    if not any(pieces):
        return False
    pattern = r'\w{0,4}'.join(re.escape(piece) for piece in pieces)
    return re.search(pattern, base_alnum) is not None


def _title_in_basename(filename: str, title_alnum: str) -> bool:
    """Require title as a basename token (avoids folder-only and substring false hits)."""

    if not title_alnum:
        return True
    base = _file_basename(filename)
    base_alnum = _alnum_only(base)
    if title_alnum == base_alnum:
        return True
    folded = _fold_accents(_normalize_search_text(base)).casefold()
    tokens = [
        _alnum_only(part)
        for part in re.split(r'[\W_]+', folded)
        if _alnum_only(part)
    ]
    if title_alnum in tokens:
        return True
    if len(title_alnum) >= 6 and title_alnum in base_alnum:
        return True
    # A short title of several words ("Hey Ya!") is in "OutKast - Hey Ya!"
    # when it covers whole words there, not part of one ("Theyyard").
    joined = ''.join(tokens)
    starts, ends, position = set(), set(), 0
    for token in tokens:
        starts.add(position)
        position += len(token)
        ends.add(position)
    at = joined.find(title_alnum)
    while at >= 0:
        if at in starts and at + len(title_alnum) in ends:
            return True
        at = joined.find(title_alnum, at + 1)
    return False


def _slskd_search_queries(song: dict[str, Any]) -> list[str]:
    """What to search Soulseek for, most likely first, as plain words
    (:func:`_soulseek_words`): the artist and the song's own name
    (:func:`_core_title`, no "(feat. …)"), the same without apostrophes,
    the artist with the full title (``Loud Enough Radio Mix``), the song's
    name alone, and the artist and name without accents. A peer only
    answers when every word is in a file's path, so fewer, plainer words
    find more; the ranking (:func:`_score_slskd_candidate`) decides which
    file is the song."""

    artists = [
        str(a).strip()
        for a in (song.get('artists') or [])[:2]
        if str(a).strip()
    ]
    artist = artists[0] if artists else ''
    title = str(song.get('name') or '').strip()
    core = _core_title(title)
    short_title = _primary_title(title)
    queries: list[str] = []
    seen: set[str] = set()

    def add(q: str, *, join_apostrophes: bool = False) -> None:
        words = _soulseek_words(q, join_apostrophes=join_apostrophes)
        if words and words.casefold() not in seen:
            seen.add(words.casefold())
            queries.append(words)

    if artist and core:
        add(f'{artist} {core}')
        add(f'{artist} {core}', join_apostrophes=True)
    if artist and title:
        add(f'{artist} {_CREDIT_PART.sub("", title)}')
        if short_title != core:
            add(f'{artist} {short_title}')
    plain_artist = _plain_name(artist)
    if artist and core and plain_artist != _soulseek_words(artist):
        add(f'{plain_artist} {core}')
    bare = _bare_title(title)
    if artist and bare:
        add(f'{artist} {bare}')
    if core:
        add(core)
    if artist and core:
        add(_fold_accents(f'{artist} {core}'))
    return queries


# Words that carry little meaning in a search, dropped first when a search
# has to be loosened (see _blocked_phrase_queries).
_FILLER_WORDS = frozenset({
    'a',
    'an',
    'and',
    'at',
    'by',
    'for',
    'from',
    'in',
    'is',
    'it',
    'me',
    'my',
    'of',
    'on',
    'or',
    'the',
    'to',
    'with',
    'you',
    'your',
})
_BLOCKED_PHRASE_TRIES = 3
_BLOCKED_PAIR_TRIES = 2


def _blocked_phrase_queries(
    song: dict[str, Any], tried: list[str]
) -> list[str]:
    """Searches with words left out, for when nobody answered any of
    *tried*. The Soulseek server silently answers nothing to some word
    combinations - artist names such as "Frank Ocean" or "Lady Gaga", and
    some titles such as "Starting From Zero" or "Hold My Hand" - in any
    order, while "Ocean Nights", "Justice Starting Zero" and "Gaga Hold
    Hand" find the files (all measured). Up to three searches leave one
    word out - filler words (``From``) first, then the shortest - then up
    to two leave out two, for when the artist and the title are both
    blocked. At least two words always remain."""

    queries = _slskd_search_queries(song)
    if not queries:
        return []
    words = queries[0].split()
    if len(words) < 3:
        return []
    order = sorted(
        range(len(words)),
        key=lambda i: (
            words[i].casefold() not in _FILLER_WORDS,
            len(words[i]),
        ),
    )
    seen = {q.casefold() for q in tried}
    out: list[str] = []

    def add(dropped: set[int], limit: int) -> None:
        query = ' '.join(w for i, w in enumerate(words) if i not in dropped)
        if (
            len(out) < limit
            and len(words) - len(dropped) >= 2
            and query.casefold() not in seen
        ):
            seen.add(query.casefold())
            out.append(query)

    for index in order:
        add({index}, _BLOCKED_PHRASE_TRIES)
    if len(words) >= 4:
        pairs = [(order[0], order[1]), (order[0], order[2])]
        for pair in pairs:
            add(set(pair), _BLOCKED_PHRASE_TRIES + _BLOCKED_PAIR_TRIES)
    return out


def _file_extension(filename: str) -> str:
    ext = Path(filename.replace('\\', '/')).suffix.lower().lstrip('.')
    return re.sub(r'[^a-z0-9]+', '', ext)


def _path_segments(filename: str) -> list[str]:
    """Parent folders in a Soulseek path (people often encode artist/album there)."""
    normalized = str(filename or '').replace('\\', '/')
    parent = Path(normalized).parent
    return [part for part in parent.parts if part not in {'.', '/'}]


def _contains_keyword(
    song: dict[str, Any],
    filename: str,
    *,
    allow_mix_variants: bool = False,
) -> bool:
    """Filter remix/live/etc. on the file name, not parent folder names."""
    # The album counts too: a track of "Homogenic (Live)" is a live take.
    title = f'{song.get("name") or ""} {song.get("album_name") or ""}'
    artists = [str(a) for a in (song.get('artists') or []) if str(a).strip()]
    basename = _file_basename(filename)
    haystacks = [basename]
    segments = _path_segments(filename)
    if segments:
        # Immediate parent folder (e.g. "Artist - Album") — not the whole tree.
        haystacks.append(segments[-1])
    skip = (
        MIX_VARIANT_REMOTE_SKIP_KEYWORDS if allow_mix_variants else frozenset()
    )
    return any(
        remote_text_unacceptable(
            title,
            haystack,
            spotify_artists=artists,
            skip_variant_keywords=skip,
        )
        for haystack in haystacks
    )


def _parse_duration_seconds(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value or '').strip()
    if not text:
        return 0
    if text.isdigit():
        return int(text)
    parts = text.split(':')
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return 0
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return 0


def _response_has_free_slot(resp: dict[str, Any]) -> bool:
    return resp.get('hasFreeUploadSlot') is True


def _file_is_locked(file_row: dict[str, Any]) -> bool:
    if file_row.get('isLocked') is True:
        return True
    if file_row.get('IsLocked') is True:
        return True
    return False


def _locked_filenames(resp: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for file_row in resp.get('lockedFiles') or []:
        if not isinstance(file_row, dict):
            continue
        filename = str(
            file_row.get('filename')
            or file_row.get('fileName')
            or file_row.get('path')
            or ''
        ).strip()
        if filename:
            names.add(filename.casefold())
    return names


def _filter_slskd_responses(
    responses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Drop peers without a free upload slot (slskd UI: hide no free slots)."""
    return [r for r in responses if _response_has_free_slot(r)]


def _busy_responses(responses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Peers whose upload slots are all taken. A download from one waits in
    its queue (``queued_timeout_seconds``), which still beats YouTube when
    no peer with a free slot has the song."""

    return [
        r
        for r in responses
        if not _response_has_free_slot(r) and int(r.get('fileCount') or 0) > 0
    ]


def _song_duration_seconds(song: dict[str, Any]) -> int:
    target_duration = int(song.get('duration') or 0)
    if target_duration > 1000:
        return target_duration // 1000
    return target_duration


def _title_is_ambiguous(title_alnum: str) -> bool:
    return len(title_alnum) < _AMBIGUOUS_TITLE_ALNUM_LEN


def _match_min_score(settings: dict[str, Any]) -> int:
    try:
        value = int(
            settings.get('match_min_score') or _DEFAULT_MATCH_MIN_SCORE
        )
    except (TypeError, ValueError):
        value = _DEFAULT_MATCH_MIN_SCORE
    return max(0, value)


def _score_slskd_candidate(  # noqa: PLR0914
    song: dict[str, Any],
    filename: str,
    file_row: dict[str, Any],
    *,
    target_duration: int,
    mix_variant_duration: bool = False,
    settings: Optional[dict[str, Any]] = None,
) -> Optional[tuple[int, list[str]]]:
    """Return (score, reasons) or None when hard requirements fail."""
    tol = duration_tolerances_from_settings(settings)
    album = _alnum_only(str(song.get('album_name') or ''))
    raw_name = str(song.get('name') or '')
    title = _alnum_only(_core_title(raw_name))
    full_title = _alnum_only(raw_name)
    sanitized_name = _alnum_only(filename)
    basename = _file_basename(filename)
    base_alnum = _alnum_only(basename)
    path_segments = _path_segments(filename)
    # The first credited artist, or another one when only that one is in
    # the path ("Metro Boomin - …" for a Yung Lean song featuring him).
    artist_keys = [
        key
        for a in (song.get('artists') or [])[:3]
        for key in dict.fromkeys((
            _artist_key(str(a)),
            _artist_key(_plain_name(str(a))),
        ))
        if key
    ]
    artist = next(
        (key for key in artist_keys if key in sanitized_name),
        '',
    ) or next(
        (
            key
            for a in (song.get('artists') or [])[:3]
            if (key := _duo_surnames_in(str(a), sanitized_name))
        ),
        artist_keys[0] if artist_keys else '',
    )

    if not artist and not title and not full_title:
        return None

    # Soulseek paths often include the requested album/title in folders while
    # the leaf file is a different track — require title on the filename itself.
    title_ok = False
    bare = _alnum_only(_bare_title(raw_name))
    if title and _title_in_basename(filename, title):
        title_ok = True
    elif (
        full_title
        and full_title != title
        and _title_in_basename(filename, full_title)
    ):
        title_ok = True
    elif bare and _title_in_basename(filename, bare):
        title_ok = True
        title = bare
    elif _censored_title_in(_core_title(raw_name), base_alnum):
        title_ok = True
        title = ''
    if (title or full_title) and not title_ok:
        return None
    if _missing_version_word(song, filename):
        return None

    artist_in_leaf = bool(artist and artist in base_alnum)
    artist_in_path = bool(
        artist and any(artist in _alnum_only(seg) for seg in path_segments)
    )
    if artist and not (artist_in_leaf or artist_in_path):
        return None

    length = _parse_duration_seconds(
        file_row.get('length') or file_row.get('duration')
    )
    if _title_is_ambiguous(title):
        if not (target_duration and length):
            return None
        if abs(target_duration - length) > _STRICT_DURATION_SECONDS:
            return None
    elif target_duration and length:
        if mix_variant_duration:
            duration_ok = media_duration_matches_mix_variant(
                song,
                length,
                tolerance_percent=tol['mix_percent'],
                normal_tolerance_seconds=tol['seconds'],
                normal_tolerance_percent=tol['percent'],
            )
        else:
            duration_ok = media_duration_matches_song(
                song,
                length,
                tolerance_seconds=tol['seconds'],
                tolerance_percent=tol['percent'],
            )
        if not duration_ok:
            return None

    score = 0
    reasons: list[str] = []

    if artist and (
        base_alnum.startswith(artist) or base_alnum.startswith(f'the{artist}')
    ):
        score += 3
        reasons.append('artist_prefix')
    elif artist and artist in base_alnum:
        score += 1
        reasons.append('artist')
    elif artist and artist in sanitized_name:
        score += 2
        reasons.append('artist_in_path')

    if title and _title_in_basename(filename, title):
        score += 2
        reasons.append('title')
        if artist and base_alnum.find(artist) < base_alnum.find(title):
            score += 2
            reasons.append('artist_before_title')
    elif (
        full_title
        and full_title != title
        and _title_in_basename(filename, full_title)
    ):
        score += 2
        reasons.append('title_full')
    elif title and title in sanitized_name:
        score += 2
        reasons.append('title_in_path')

    for segment in path_segments:
        segment_alnum = _alnum_only(segment)
        if not segment_alnum:
            continue
        if (
            artist
            and title
            and artist in segment_alnum
            and title in segment_alnum
        ):
            score += 2
            reasons.append('folder_segment')
            break
        if album and album in segment_alnum:
            score += 1
            reasons.append('album_folder')
            break

    if target_duration and length:
        delta = abs(target_duration - length)
        if delta <= min(_STRICT_DURATION_SECONDS, tol['seconds']):
            score += 3
            reasons.append('duration_3s')
        elif delta <= tol['seconds']:
            score += 1
            reasons.append('duration_10s')

    if album and album in sanitized_name:
        score += 1
        reasons.append('album')

    # Soft penalty only when the leaf file name lacks title (dump folders).
    path_folded = filename.casefold()
    if (
        title
        and title not in base_alnum
        and any(keyword in path_folded for keyword in _PATH_PENALTY_KEYWORDS)
    ):
        score -= 1
        reasons.append('path_penalty')

    try:
        bitrate = int(file_row.get('bitRate') or file_row.get('bitrate') or 0)
    except (TypeError, ValueError):
        bitrate = 0
    if bitrate >= 320:
        score += 1
        reasons.append('bitrate_320')
    elif bitrate >= 192:
        score += 1
        reasons.append('bitrate_192')

    return score, reasons


def _rank_slskd_candidates(
    song: dict[str, Any],
    responses: list[dict[str, Any]],
    settings: Optional[dict[str, Any]] = None,
    *,
    allow_mix_variants: bool = False,
    include_busy: bool = False,
) -> list[dict[str, Any]]:
    """Score and sort all viable files (highest confidence first); peers
    without a free upload slot only with *include_busy*."""
    target_duration = _song_duration_seconds(song)
    ranked: list[dict[str, Any]] = []

    for resp in (
        responses if include_busy else _filter_slskd_responses(responses)
    ):
        if int(resp.get('fileCount') or 0) <= 0:
            continue
        username = str(resp.get('username') or '').strip()
        locked_names = _locked_filenames(resp)
        for file_row in resp.get('files') or []:
            if not isinstance(file_row, dict):
                continue
            if _file_is_locked(file_row):
                continue
            filename = str(
                file_row.get('filename')
                or file_row.get('fileName')
                or file_row.get('path')
                or ''
            ).strip()
            if not filename:
                continue
            if filename.casefold() in locked_names:
                continue
            ext = _file_extension(filename)
            if ext and ext not in _AUDIO_EXTENSIONS:
                continue
            if _contains_keyword(
                song, filename, allow_mix_variants=allow_mix_variants
            ):
                continue

            scored = _score_slskd_candidate(
                song,
                filename,
                file_row,
                target_duration=target_duration,
                mix_variant_duration=allow_mix_variants,
                settings=settings,
            )
            if scored is None:
                continue
            score, reasons = scored
            ranked.append({
                **file_row,
                'username': username,
                'filename': filename,
                'match_score': score,
                'match_reasons': reasons,
            })

    ranked.sort(
        key=lambda row: (
            -int(row.get('match_score') or 0),
            -int(row.get('bitRate') or row.get('bitrate') or 0),
        )
    )
    return ranked


def _collect_matching_files(
    song: dict[str, Any], responses: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Ranked candidates without applying the minimum score gate (tests)."""
    return _rank_slskd_candidates(song, responses)


def _select_download_candidates(
    ranked: list[dict[str, Any]], settings: dict[str, Any]
) -> list[dict[str, Any]]:
    """Choose candidates by score, or in ordered format tiers when enabled."""
    raw_ext = settings.get('extensions') or ['mp3', 'flac']
    extensions = list(
        dict.fromkeys(
            str(e).strip().lower().lstrip('.')
            for e in raw_ext
            if str(e).strip()
        )
    ) or ['mp3', 'flac']
    min_bitrate = int(settings.get('min_bitrate') or 0)
    max_files = int(settings.get('download_attempts') or 5)
    strict_priority = bool(settings.get('strict_format_priority', False))
    whitelist = bool(settings.get('extensions_whitelist', False))
    quality = normalize_slskd_quality(settings)
    if not quality['advanced']:
        quality = normalize_slskd_quality({})

    def bitrate_of(file_row: dict[str, Any]) -> int:
        try:
            return int(file_row.get('bitRate') or file_row.get('bitrate') or 0)
        except (TypeError, ValueError):
            return 0

    def rank_key(file_row: dict[str, Any]) -> tuple[int, int]:
        score = int(file_row.get('match_score') or 0)
        if quality['prefer_bitrate']:
            return (-bitrate_of(file_row), -score)
        return (-score, -bitrate_of(file_row))

    # Formats to avoid are out whatever the list and the whitelist say.
    avoid = extensions_of(settings.get('avoid_formats') or ())
    extensions = [e for e in extensions if e not in avoid]
    candidates = [
        row
        for row in ranked
        if _file_extension(str(row.get('filename') or '')) not in avoid
        and (
            not whitelist
            or _file_extension(str(row.get('filename') or '')) in extensions
        )
    ]

    def passes_bitrate(file_row: dict[str, Any]) -> bool:
        bitrate = bitrate_of(file_row)
        ext = _file_extension(str(file_row.get('filename') or ''))
        if quality['max_bitrate'] and bitrate > quality['max_bitrate']:
            return False
        if strict_priority and ext == 'flac':
            return True
        floor = quality['format_min_bitrate'].get(ext, min_bitrate)
        if not bitrate:
            if quality['unknown_bitrate'] == 'allow':
                return True
            if quality['unknown_bitrate'] == 'reject':
                return False
            return not (strict_priority and floor)
        if file_row.get('isVariableBitRate') and floor:
            # A VBR file reports its average: LAME V0, as good as 320 CBR,
            # averages ~220-260 kbps, so it passes at 85 % of the floor.
            return bitrate >= floor * _VBR_FLOOR_SHARE
        return bitrate >= floor

    if strict_priority:
        selected: list[dict[str, Any]] = []
        tiers = [
            [
                row
                for row in candidates
                if _file_extension(str(row.get('filename') or '')) == ext
            ]
            for ext in extensions
        ]
        if not whitelist:
            tiers.append([
                row
                for row in candidates
                if _file_extension(str(row.get('filename') or ''))
                not in extensions
            ])

        for tier in tiers:
            accepted = [row for row in tier if passes_bitrate(row)]
            accepted.sort(key=rank_key)
            selected.extend(accepted[:max_files])
        return selected

    # Grouped by match score, so the format order breaks ties; with
    # ``prefer_bitrate`` grouped by bitrate instead (best match first).
    by_group: dict[int, list[dict[str, Any]]] = {}
    for row in sorted(candidates, key=rank_key):
        by_group.setdefault(rank_key(row)[0], []).append(row)

    selected: list[dict[str, Any]] = []
    for group in sorted(by_group.keys()):
        bucket = by_group[group]
        for ext in extensions:
            for file_row in bucket:
                if _file_extension(str(file_row.get('filename') or '')) != ext:
                    continue
                if not passes_bitrate(file_row):
                    continue
                selected.append(file_row)
                if len(selected) >= max_files:
                    return selected
        for file_row in bucket:
            if file_row in selected:
                continue
            if not passes_bitrate(file_row):
                continue
            selected.append(file_row)
            if len(selected) >= max_files:
                return selected
    return selected


def _file_basename(filename: str) -> str:
    return Path(str(filename or '').replace('\\', '/')).name


def _paths_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    return _file_basename(left).casefold() == _file_basename(right).casefold()


def _extract_directory_paths(data: Any) -> list[str]:
    paths: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            directories = node.get('directories')
            if isinstance(directories, dict):
                for key in ('downloads', 'incomplete', 'download'):
                    raw = directories.get(key)
                    if isinstance(raw, str) and raw.strip():
                        paths.append(raw.strip())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    out: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        if raw not in seen:
            seen.add(raw)
            out.append(raw)
    return out


def _search_roots(settings: dict[str, Any], client: SlskdClient) -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()
    for raw in (
        settings.get('source_dir'),
        settings.get('output_dir'),
        settings.get('download_dir'),
        *client.remote_download_directories(),
    ):
        text = str(raw or '').strip()
        if not text or text in seen:
            continue
        seen.add(text)
        roots.append(Path(text))
    return roots


def _parse_soulseek_path(filename: str) -> tuple[str, str]:
    normalized = filename.replace('\\', '/')
    parent = Path(normalized).parent
    parent_name = '' if str(parent) in {'.', '/'} else parent.name
    return Path(normalized).name, parent_name


def _transfer_failed(status: dict[str, Any]) -> bool:
    state = str(status.get('state') or '')
    return any(
        failure in state
        for failure in (
            'Errored',
            'Cancelled',
            'Aborted',
            'Rejected',
            'TimedOut',
        )
    )


def _transfer_succeeded(status: dict[str, Any]) -> bool:
    state = str(status.get('state') or '')
    remaining = int(status.get('bytesRemaining') or 0)
    percent = float(status.get('percentComplete') or 0)
    return (
        remaining == 0
        or percent >= 100
        or 'Succeeded' in state
        or 'Completed' in state
    )


def _slskd_transfer_progress_pct(
    *,
    transfer: Optional[dict[str, Any]] = None,
    on_disk_bytes: int = 0,
    expected_size: int = 0,
    poll_attempt: int = 0,
) -> tuple[float, str]:
    """Map an active slskd transfer to overall job progress (40–92%)."""

    lo, hi = 40.0, 92.0
    span = hi - lo
    if transfer:
        try:
            pct_complete = float(transfer.get('percentComplete') or 0)
        except (TypeError, ValueError):
            pct_complete = 0.0
        if 0 < pct_complete <= 100:
            return lo + span * (pct_complete / 100.0), 'Downloading'
        try:
            transferred = int(transfer.get('bytesTransferred') or 0)
            size = int(transfer.get('size') or 0) or int(expected_size or 0)
        except (TypeError, ValueError):
            transferred = 0
            size = 0
        if size > 0 and transferred >= 0:
            ratio = min(1.0, transferred / size)
            return lo + span * ratio, 'Downloading'
    if expected_size > 0 and on_disk_bytes > 0:
        ratio = min(1.0, on_disk_bytes / expected_size)
        return lo + span * ratio, 'Downloading'
    fallback = lo + min(span * 0.12, max(0, poll_attempt) * 0.4)
    return min(hi - 4.0, fallback), 'Waiting for slskd'


def _normalize_token(text: str) -> str:
    folded = unicodedata.normalize('NFKD', text)
    stripped = ''.join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r'\s+', ' ', stripped).casefold().strip()


def _disk_complete(path: Path, expected_size: int) -> bool:
    try:
        size = path.stat().st_size
    except OSError:
        return False
    if expected_size > 0:
        return size >= int(expected_size * 0.95)
    return size > 50_000


def _find_on_disk(
    roots: list[Path],
    soulseek_filename: str,
    *,
    username: str = '',
    min_size: int = 1,
    deep_scan: bool = True,
) -> Optional[Path]:
    basename, parent = _parse_soulseek_path(soulseek_filename)
    if not basename:
        return None
    relative_candidates: list[Path] = [Path(basename)]
    if parent:
        relative_candidates.append(Path(parent) / basename)
    if username:
        relative_candidates.append(Path(username) / basename)
        if parent:
            relative_candidates.append(Path(username) / parent / basename)

    for root in roots:
        if not root.exists():
            continue
        for rel in relative_candidates:
            candidate = root / rel
            if candidate.is_file() and candidate.stat().st_size >= min_size:
                return candidate

    if not deep_scan:
        return None
    best: Optional[Path] = None
    best_mtime = 0.0
    for root in roots:
        if not root.exists():
            continue
        try:
            matches = list(root.rglob(basename))
        except OSError:
            continue
        for candidate in matches:
            if not candidate.is_file():
                continue
            try:
                size = candidate.stat().st_size
                mtime = candidate.stat().st_mtime
            except OSError:
                continue
            if size < min_size:
                continue
            if mtime >= best_mtime:
                best = candidate
                best_mtime = mtime
    return best


def _find_on_disk_for_song(
    roots: list[Path],
    song: dict[str, Any],
    soulseek_filename: str,
    *,
    username: str = '',
    expected_size: int = 0,
    extensions: Optional[frozenset[str]] = None,
    deep_scan: bool = True,
) -> Optional[Path]:
    min_size = max(1, int(expected_size * 0.95) if expected_size else 1)
    found = _find_on_disk(
        roots,
        soulseek_filename,
        username=username,
        min_size=min_size,
        deep_scan=deep_scan,
    )
    if found is not None:
        return found
    if not deep_scan:
        return None

    title = _normalize_token(str(song.get('name') or ''))
    if len(title) < 3:
        return None
    # The scan looks for the requested transfer saved under another name,
    # so only a file of its format and size will do: another file with
    # the title in its name - a FLAC of the same song left in slskd's
    # folder by an older download or another app, a long mix - would
    # otherwise be imported in its place, whatever formats are allowed.
    requested_ext = _file_extension(soulseek_filename)
    exts = extensions or _AUDIO_EXTENSIONS
    if requested_ext:
        exts = frozenset({requested_ext}) & frozenset(
            e.lower().lstrip('.') for e in exts
        )
    max_size = (
        int(expected_size * _DISK_SCAN_MAX_SIZE_SHARE) if expected_size else 0
    )
    best: Optional[Path] = None
    best_mtime = 0.0
    for root in roots:
        if not root.exists():
            continue
        for ext in exts:
            pattern = ext if ext.startswith('.') else f'.{ext}'
            try:
                matches = list(root.rglob(f'*{pattern}'))
            except OSError:
                continue
            for candidate in matches:
                if not candidate.is_file():
                    continue
                if title not in _normalize_token(candidate.name):
                    continue
                try:
                    size = candidate.stat().st_size
                    mtime = candidate.stat().st_mtime
                except OSError:
                    continue
                if size < min_size or (max_size and size > max_size):
                    continue
                if mtime >= best_mtime:
                    best = candidate
                    best_mtime = mtime
    return best


def _resolve_downloaded_file(
    roots: list[Path],
    song: dict[str, Any],
    soulseek_filename: str,
    *,
    username: str,
    expected_size: int = 0,
) -> Optional[Path]:
    return _find_on_disk_for_song(
        roots,
        song,
        soulseek_filename,
        username=username,
        expected_size=expected_size,
    )


def _finalize_slskd_path(found: Path) -> Path:
    """Return the original transfer; Downloader owns import and cleanup."""

    return found


def _wait_for_slskd_file(
    client: SlskdClient,
    song: dict[str, Any],
    username: str,
    filename: str,
    settings: dict[str, Any],
    roots: list[Path],
    *,
    expected_size: int = 0,
    progress_cb: Optional[ProgressCallback] = None,
    deadline: Optional[float] = None,
    cancel_check: Optional[Callable[[], None]] = None,
) -> Optional[Path]:
    """Wait for slskd to finish, then return the file path on disk (if found)."""
    poll = _PollSchedule(settings)
    queued_timeout = _int_setting(
        settings,
        'queued_timeout_seconds',
        _DEFAULT_QUEUED_TIMEOUT_SECONDS,
        minimum=15,
        maximum=3600,
    )
    last_bytes = -1
    last_progress = poll.started
    last_reported_pct = -1.0

    for attempt in range(poll.attempts):
        if cancel_check:
            cancel_check()
        if deadline is not None and _past_deadline(deadline):
            logger.info(
                'slskd: download timeout while waiting for file title={!r} '
                'user={!r} file={!r}',
                song.get('name'),
                username,
                _file_basename(filename)[:120],
            )
            return None
        if attempt and poll.remaining_sleep <= 0:
            break
        transfer = client.find_transfer(username, filename)
        found = _find_on_disk_for_song(
            roots,
            song,
            filename,
            username=username,
            expected_size=expected_size,
            deep_scan=poll.should_scan(attempt, transfer),
        )
        on_disk_bytes = 0
        if found is not None:
            try:
                on_disk_bytes = found.stat().st_size
            except OSError:
                on_disk_bytes = 0
            if _disk_complete(found, expected_size):
                if progress_cb is not None:
                    progress_cb(92.0, 'slskd · downloading', 'slskd')
                return found

        if transfer:
            try:
                expected_size = max(
                    expected_size, int(transfer.get('size') or 0)
                )
            except (TypeError, ValueError):
                pass
            if _transfer_failed(transfer):
                return None
            transferred = int(transfer.get('bytesTransferred') or 0)
            if transferred > last_bytes:
                last_bytes = transferred
                last_progress = time.monotonic()
            elif time.monotonic() - last_progress > queued_timeout:
                logger.info(
                    'slskd: stalled (no progress) title={!r} user={!r} '
                    'bytes={} state={!r}',
                    song.get('name'),
                    username,
                    transferred,
                    transfer.get('state'),
                )
                return None
        elif time.monotonic() - poll.started > queued_timeout:
            logger.info(
                'slskd: queued timeout (transfer not started) title={!r} '
                'user={!r} file={!r}',
                song.get('name'),
                username,
                _file_basename(filename)[:120],
            )
            return None

        if progress_cb is not None:
            pct, message = _slskd_transfer_progress_pct(
                transfer=transfer,
                on_disk_bytes=on_disk_bytes,
                expected_size=expected_size,
                poll_attempt=attempt,
            )
            if pct > last_reported_pct or attempt == 0:
                last_reported_pct = pct
                progress_cb(pct, message, 'slskd')

        poll.sleep(
            transfer, last_progress, queued_timeout, deadline, cancel_check
        )

    return _find_on_disk_for_song(
        roots,
        song,
        filename,
        username=username,
        expected_size=expected_size,
    )


# ── Why slskd didn't deliver ───────────────────────────────────────────
# A download that slskd can't serve falls through to the next source. The
# reason is kept for the thread that asked (one download per thread), so
# the downloader can say why another source was used (see
# downtify.slskd_misses).

#: Reasons, in the order a download gets further: when several queries
#: fail differently, the one that got furthest is reported.
MISS_REASONS = (
    'not_configured',
    'unreachable',
    'search_failed',
    'search_timeout',
    'no_results',
    'no_match',
    'low_confidence',
    'quality_filtered',
    'timeout',
    'transfer_failed',
    'tag_mismatch',
)

_miss = threading.local()


def take_miss() -> Optional[dict[str, str]]:
    """Why the last :func:`download_from_slskd` on this thread found
    nothing (``{reason, detail}``), once; ``None`` when it didn't fail or
    was never called."""

    found = getattr(_miss, 'value', None)
    _miss.value = None
    return found


def _missed(reason: str, detail: str = '') -> None:
    """Remember why slskd found nothing, unless an earlier query of the
    same download already got further. Returns ``None`` for ``return
    _missed(...)``."""

    current = getattr(_miss, 'value', None)
    if current is None or MISS_REASONS.index(reason) >= MISS_REASONS.index(
        current['reason']
    ):
        _miss.value = {'reason': reason, 'detail': str(detail)[:200]}


def _give_up_on(client: SlskdClient, username: str, filename: str) -> None:
    """A candidate didn't arrive: remember why, and cancel its transfer
    if slskd is still waiting on it (queued, or stalled mid-way)."""

    try:
        transfer = client.find_transfer(username, filename)
    except Exception:
        transfer = None
    how = remember_failure(username, filename, transfer)
    # slskd states every ended transfer "Completed, <how>"; anything else
    # (requested, queued, initializing, in progress) is still waiting.
    if transfer and 'Completed' not in str(transfer.get('state') or ''):
        client.cancel_download(username, str(transfer.get('id') or ''))
    logger.info(
        'slskd: remembered failure ({}) user={!r} file={!r} error={!r}',
        how,
        username,
        _file_basename(filename)[:120],
        _transfer_error(transfer)[:160],
    )


def download_from_slskd(  # noqa: PLR0914  # search, rank, enqueue, poll, finalize
    song: dict[str, Any],
    settings: dict[str, Any],
    progress_cb: Optional[ProgressCallback] = None,
    *,
    cancel_check=None,
) -> Optional[Path]:
    _miss.value = None
    if cancel_check:
        cancel_check()
    if not bool(settings.get('enabled')):
        return None
    client = SlskdClient(settings)
    if not client.configured():
        logger.info(
            'slskd: missing configuration title={!r}', song.get('name')
        )
        return _missed('not_configured')
    if not client.can_connect():
        logger.info(
            'slskd: connectivity check failed base_url={!r}', client.base_url
        )
        return _missed('unreachable')

    output_dir = Path(
        str(
            settings.get('output_dir')
            or settings.get('download_dir')
            or '/downloads'
        )
    )
    source_dir = Path(
        str(
            settings.get('source_dir')
            or settings.get('download_dir')
            or output_dir
        )
    )
    spotify_row = snapshot_spotify_metadata(song)
    queries = _slskd_search_queries(spotify_row)
    if not queries:
        return _missed('no_match', 'no title or artist to search for')

    label = f'{song.get("name")} - {", ".join(song.get("artists") or [])}'

    def report(pct: float, message: str) -> None:
        if progress_cb is not None:
            try:
                text = (
                    message
                    if str(message).lower().startswith('slskd')
                    else f'slskd · {message}'
                )
                progress_cb(pct, text, 'slskd')
            except Exception:
                logger.opt(exception=True).debug(
                    'slskd progress callback error'
                )

    deadline = _slskd_deadline(settings)
    report(2.0, 'searching')

    search_id = ''

    # Hold the parallel slot for search, enqueue, and transfer.
    with _slskd_semaphore(settings):
        used_query = ''
        candidates: list[dict[str, Any]] = []
        files: list[dict[str, Any]] = []
        min_score = _match_min_score(settings)

        # Nobody answering any search may mean the server blocks one of
        # its word combinations: then a few looser searches are added.
        answered = False
        loosened_from: Optional[int] = None
        for index, query in enumerate(queries):
            if (
                loosened_from is not None
                and index >= loosened_from
                and answered
            ):
                break
            if (
                loosened_from is None
                and index == len(queries) - 1
                and not answered
            ):
                loosened_from = len(queries)
                queries.extend(_blocked_phrase_queries(spotify_row, queries))
            if cancel_check:
                cancel_check()
            if _past_deadline(deadline):
                logger.info(
                    'slskd: download timeout during search title={!r}',
                    song.get('name'),
                )
                return _missed('search_timeout')
            report(8.0, 'searching')
            search_id = client.start_search(query) or ''
            if not search_id:
                _missed('search_failed')
                continue
            if not client.wait_search_complete(
                search_id,
                label,
                on_poll=lambda pct: report(pct, 'searching'),
                deadline=deadline,
                **({'cancel_check': cancel_check} if cancel_check else {}),
            ):
                _missed('search_timeout')
                client.delete_search(search_id)
                search_id = ''
                continue
            raw_responses = client.search_responses(search_id)
            if raw_responses:
                answered = True
            responses = _filter_slskd_responses(raw_responses)
            if not responses and not _busy_responses(raw_responses):
                _missed(
                    'no_results',
                    f'{len(raw_responses)} users answered, none with a free '
                    'slot and an unlocked file'
                    if raw_responses
                    else 'nobody had it',
                )
                client.delete_search(search_id)
                search_id = ''
                continue

            ranked = _rank_slskd_candidates(song, responses, settings)
            if not ranked and (busy := _busy_responses(raw_responses)):
                ranked = _rank_slskd_candidates(
                    song, busy, settings, include_busy=True
                )
                if ranked:
                    logger.info(
                        'slskd: only busy peers have {!r}; queueing',
                        song.get('name'),
                    )
            if not ranked:
                ranked = _rank_slskd_candidates(
                    song,
                    responses,
                    settings,
                    allow_mix_variants=True,
                )
                if ranked:
                    logger.info(
                        'slskd: using extended-mix last resort for query={!r} '
                        'title={!r}',
                        query[:120],
                        song.get('name'),
                    )
            if not ranked:
                logger.info(
                    'slskd: no matching audio for query={!r} title={!r} '
                    'responses={}',
                    query[:120],
                    song.get('name'),
                    len(responses),
                )
                _missed('no_match', f'{len(raw_responses)} users answered')
                client.delete_search(search_id)
                search_id = ''
                continue

            qualified = [
                row
                for row in ranked
                if int(row.get('match_score') or 0) >= min_score
            ]
            if not qualified:
                top = ranked[0]
                logger.info(
                    'slskd: low confidence for query={!r} title={!r} '
                    'top_score={} top_file={!r} min_score={}',
                    query[:120],
                    song.get('name'),
                    top.get('match_score'),
                    _file_basename(str(top.get('filename') or '')),
                    min_score,
                )
                _missed(
                    'low_confidence',
                    f'best match {top.get("match_score")}, needs {min_score}: '
                    f'{_file_basename(str(top.get("filename") or ""))}',
                )
                client.delete_search(search_id)
                search_id = ''
                continue

            selected = _select_download_candidates(qualified, settings)
            if not selected:
                _missed(
                    'quality_filtered',
                    f'{len(qualified)} matching files, none passed the '
                    'format and bitrate rules',
                )
                logger.info(
                    'slskd: no files passed quality filters for query={!r} '
                    'title={!r}',
                    query[:120],
                    song.get('name'),
                )
                client.delete_search(search_id)
                search_id = ''
                continue

            used_query = query
            candidates = ranked
            files = selected
            break

        if not files:
            logger.info(
                'slskd: no matching audio files title={!r} queries={}',
                song.get('name'),
                queries[:6],
            )
            if search_id:
                client.delete_search(search_id)
            return None

        pick = files[0]
        logger.info(
            'slskd: picked score={} reasons={} file={!r} user={!r} '
            'query={!r} ranked={} selected={} (download_attempts={})',
            pick.get('match_score'),
            ','.join(pick.get('match_reasons') or []),
            _file_basename(str(pick.get('filename') or '')),
            pick.get('username'),
            used_query[:120],
            len(candidates),
            len(files),
            int(settings.get('download_attempts') or 5),
        )

        if _past_deadline(deadline):
            client.delete_search(search_id)
            logger.info(
                'slskd: download timeout before transfer title={!r}',
                song.get('name'),
            )
            return _missed('timeout')

        roots = _search_roots(settings, client)

        def _root_key(path: Path) -> str:
            try:
                return str(path.resolve())
            except OSError:
                return str(path)

        root_keys = {_root_key(r) for r in roots}
        if _root_key(source_dir) not in root_keys:
            roots.insert(0, source_dir)
        if _root_key(output_dir) not in root_keys:
            roots.append(output_dir)

        before = len(files)
        files = order_by_past_failures(files)
        if len(files) < before:
            logger.info(
                'slskd: skipping {} file(s) that failed recently title={!r}',
                before - len(files),
                song.get('name'),
            )
        for attempt_idx, file_row in enumerate(files, start=1):
            if cancel_check:
                cancel_check()
            if _past_deadline(deadline):
                logger.info(
                    'slskd: download timeout before trying candidate {} title={!r}',
                    attempt_idx,
                    song.get('name'),
                )
                break

            username = str(file_row.get('username') or '')
            filename = str(file_row.get('filename') or '')
            if not client.enqueue_download(file_row):
                logger.info(
                    'slskd: enqueue failed candidate={}/{} title={!r} user={!r} file={!r}',
                    attempt_idx,
                    len(files),
                    song.get('name'),
                    username,
                    _file_basename(filename)[:120],
                )
                continue

            try:
                queued_size = int(file_row.get('size') or 0)
            except (TypeError, ValueError):
                queued_size = 0

            report(36.0, f'queued ({attempt_idx}/{len(files)})')

            found = _wait_for_slskd_file(
                client,
                song,
                username,
                filename,
                settings,
                roots,
                expected_size=queued_size,
                progress_cb=progress_cb,
                **({'cancel_check': cancel_check} if cancel_check else {}),
                deadline=deadline,
            )
            if found is None:
                found = _resolve_downloaded_file(
                    roots,
                    song,
                    filename,
                    username=username,
                    expected_size=queued_size,
                )

            if found is not None:
                if not verify_downloaded_file_matches_spotify(
                    found, spotify_row
                ):
                    meta = read_audio_metadata(found)
                    mismatch_row = {
                        **spotify_row,
                        'name': str(meta.get('title') or ''),
                        'artists': list(meta.get('artists') or []),
                        'library_from_tags': True,
                    }
                    logger.info(
                        'slskd: tags mismatch after download {}; '
                        'retaining source and trying next candidate '
                        '({}/{}) file={!r}',
                        spotify_file_tag_mismatch_label(mismatch_row),
                        attempt_idx,
                        len(files),
                        _file_basename(filename)[:120],
                    )
                    _missed(
                        'tag_mismatch',
                        f'{spotify_file_tag_mismatch_label(mismatch_row)}: '
                        f'{_file_basename(filename)}',
                    )
                    found = None

            if found is not None:
                if search_id:
                    client.delete_search(search_id)
                return _finalize_slskd_path(found)

            _give_up_on(client, username, filename)
            logger.info(
                'slskd: candidate failed candidate={}/{} title={!r} user={!r} file={!r}',
                attempt_idx,
                len(files),
                song.get('name'),
                username,
                _file_basename(filename)[:120],
            )

        if search_id:
            client.delete_search(search_id)

        logger.info(
            'slskd: all candidates failed title={!r} tried={}',
            song.get('name'),
            len(files),
        )
        if _past_deadline(deadline):
            return _missed('timeout', f'{len(files)} files tried')
        return _missed(
            'transfer_failed',
            f'{len(files)} files tried: none arrived complete',
        )
