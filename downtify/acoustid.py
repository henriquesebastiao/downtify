"""AcoustID: knowing a song by its sound (optional, off by default).

A Chromaprint *fingerprint* sums up how a file sounds; AcoustID
(https://acoustid.org) is the free, open database that maps such
fingerprints to MusicBrainz recordings. Downtify uses it to confirm what
a file is when its tags and ISRC can't say for sure, and to find the ISRC
of an older file whose tags Deezer can't place
(:mod:`downtify.library_upgrade`, the ``acoustid`` category).

Rules, the same as for ISRCs (:mod:`downtify.isrc`):

* **Opt-in.** Nothing here runs until an admin turns on
  ``acoustid_enabled`` and enters their own free AcoustID application
  key. The key lives in ``<data>/.acoustid_key`` (:class:`KeyStore`),
  never in ``settings.json``, which ``GET /api/settings`` hands out; the
  API only ever shows its last four characters.
* **Confident or nothing** (:func:`identify`): a result counts only with
  a score of at least :data:`MIN_SCORE`, and a recording only when its
  artist and title are the file's own (as :mod:`downtify.library_songs`
  compares them) and its length is within
  :data:`downtify.isrc.LENGTH_SECONDS`. An ISRC is written only when the
  agreeing recordings name exactly one between them. A file AcoustID
  places as another song, or not at all, is left exactly as it is: many
  niche and regional songs are missing from MusicBrainz or filed under
  another spelling, and a guess would be worse than nothing.
* **No MusicBrainz IDs are written into files.** Navidrome builds its
  track and album IDs from them, so writing them would give songs it
  already knows new IDs. Only the ISRC tag is ever added.
* **Polite.** AcoustID allows three requests a second
  (:data:`_INTERVAL`, shared by every caller in the process); a busy
  answer is retried after a pause. ISRCs come from MusicBrainz through
  :mod:`downtify.musicbrainz`, which keeps its own one-a-second pace and
  retries its ``503``.

The fingerprint comes from ``fpcalc`` (Chromaprint's tool) when it is
installed, else from FFmpeg's ``chromaprint`` muxer when the FFmpeg build
has it (the Docker image's does). :func:`fingerprinter` says which, or
``''`` when neither is there; then the feature says so and does nothing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # noqa: S404  # fpcalc / ffmpeg, never a shell
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx
from loguru import logger

from . import __version__
from . import isrc as isrc_mod

LOOKUP_URL = 'https://api.acoustid.org/v2/lookup'

#: The lowest AcoustID score trusted. Scores run 0-1; the same recording
#: from another source scores 0.9 and above, a near miss well below.
MIN_SCORE = 0.9
#: Seconds of audio fingerprinted (fpcalc's own default).
FINGERPRINT_SECONDS = 120
#: Seconds between two AcoustID requests (it allows three a second).
_INTERVAL = 0.34
#: Tries of a request AcoustID answers with "busy".
_RETRIES = 3
_TIMEOUT = 20
#: Seconds a fingerprinting run may take.
_FINGERPRINT_TIMEOUT = 120
#: Recordings asked about on MusicBrainz per file, at most.
_MAX_RECORDINGS = 3

#: AcoustID's error codes for a fingerprint it can't read and for a
#: wrong application key.
_INVALID_FINGERPRINT = 3
_INVALID_KEY = 4

_lock = threading.Lock()
_last_request = 0.0


class AcoustIDError(RuntimeError):
    """AcoustID couldn't answer (unreachable, busy, refused)."""

    def __init__(self, message: str, code: int = 0) -> None:
        super().__init__(message)
        #: AcoustID's own error code, ``0`` when it sent none.
        self.code = code


class InvalidKey(AcoustIDError):
    """AcoustID refused the application key."""


class NoFingerprinter(AcoustIDError):
    """Neither ``fpcalc`` nor an FFmpeg with Chromaprint is installed."""


# ── The key ─────────────────────────────────────────────────────────────


class KeyStore:
    """The AcoustID application key, kept in a file of its own."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def get(self) -> str:
        try:
            return self.path.read_text(encoding='utf-8').strip()
        except OSError:
            return ''

    def set(self, key: str) -> None:
        """Save *key* (an empty one removes the file)."""

        key = clean_key(key)
        if not key:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + '.tmp')
        tmp.write_text(key, encoding='utf-8')
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, self.path)

    def hint(self) -> str:
        """The key's last four characters behind dots, ``''`` without
        one."""

        return mask(self.get())


def clean_key(value: Any) -> str:
    """*value* as a key: trimmed, and only when it looks like one (letters,
    digits, ``-`` and ``_``, 4-64 characters); ``''`` otherwise."""

    key = str(value or '').strip()
    if not 4 <= len(key) <= 64:
        return ''
    if not all(ch.isascii() and (ch.isalnum() or ch in '-_') for ch in key):
        return ''
    return key


def mask(key: str) -> str:
    return f'••••{key[-4:]}' if key else ''


# ── Fingerprints ────────────────────────────────────────────────────────


def _fpcalc() -> str:
    return os.environ.get('DOWNTIFY_FPCALC', '').strip() or (
        shutil.which('fpcalc') or ''
    )


_ffmpeg_checked: dict[str, bool] = {}


def _ffmpeg_has_chromaprint(ffmpeg: str) -> bool:
    if ffmpeg not in _ffmpeg_checked:
        try:
            out = subprocess.run(  # noqa: S603
                [ffmpeg, '-hide_banner', '-muxers'],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            ).stdout
        except (OSError, subprocess.SubprocessError):
            out = ''
        _ffmpeg_checked[ffmpeg] = any(
            line.split()[1:2] == ['chromaprint']
            for line in out.splitlines()
            if line.strip()
        )
    return _ffmpeg_checked[ffmpeg]


def fingerprinter() -> str:
    """``'fpcalc'``, ``'ffmpeg'`` or ``''``: what makes fingerprints
    here."""

    if _fpcalc():
        return 'fpcalc'
    ffmpeg = shutil.which('ffmpeg') or ''
    if ffmpeg and _ffmpeg_has_chromaprint(ffmpeg):
        return 'ffmpeg'
    return ''


def _length(path: Path) -> float:
    from mutagen import File as MutagenFile  # noqa: PLC0415

    try:
        audio = MutagenFile(str(path))
    except Exception:
        return 0.0
    info = getattr(audio, 'info', None)
    return float(getattr(info, 'length', 0.0) or 0.0)


def fingerprint(path: Path) -> tuple[int, str]:
    """``(duration in seconds, fingerprint)`` of the audio at *path*.

    Raises :class:`NoFingerprinter` without a tool to make one and
    :class:`AcoustIDError` when the file can't be read.
    """

    tool = fingerprinter()
    if not tool:
        raise NoFingerprinter(
            'Fingerprinting needs fpcalc (Chromaprint) or an FFmpeg built '
            'with Chromaprint'
        )
    try:
        if tool == 'fpcalc':
            run = subprocess.run(  # noqa: S603
                [
                    _fpcalc(),
                    '-json',
                    '-length',
                    str(FINGERPRINT_SECONDS),
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=_FINGERPRINT_TIMEOUT,
                check=False,
            )
            data = json.loads(run.stdout or '{}')
            duration = float(data.get('duration') or 0)
            print_ = str(data.get('fingerprint') or '').strip()
        else:
            run = subprocess.run(  # noqa: S603
                [
                    shutil.which('ffmpeg') or 'ffmpeg',
                    '-v',
                    'error',
                    '-nostdin',
                    '-i',
                    str(path),
                    '-t',
                    str(FINGERPRINT_SECONDS),
                    '-f',
                    'chromaprint',
                    '-fp_format',
                    'base64',
                    '-',
                ],
                capture_output=True,
                text=True,
                timeout=_FINGERPRINT_TIMEOUT,
                check=False,
            )
            duration = _length(path)
            print_ = (run.stdout or '').strip()
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise AcoustIDError('Could not fingerprint the file') from exc
    if run.returncode != 0 or not print_ or duration <= 0:
        raise AcoustIDError('Could not fingerprint the file')
    return int(round(duration)), print_


# ── AcoustID ────────────────────────────────────────────────────────────


def _post(data: dict[str, Any]) -> dict[str, Any]:
    """An AcoustID request as JSON, at most three a second process-wide."""

    global _last_request  # noqa: PLW0603  # the shared request clock
    for attempt in range(_RETRIES):
        with _lock:
            wait = _INTERVAL - (time.monotonic() - _last_request)
            if wait > 0:
                time.sleep(wait)
            try:
                resp = httpx.post(
                    LOOKUP_URL,
                    data=data,
                    headers={'User-Agent': f'Downtify/{__version__}'},
                    timeout=_TIMEOUT,
                )
            except httpx.HTTPError as exc:
                if attempt + 1 < _RETRIES:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise AcoustIDError('Could not reach AcoustID') from exc
            finally:
                _last_request = time.monotonic()
        try:
            body = resp.json()
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            body = {}
        error = (
            body.get('error') if isinstance(body.get('error'), dict) else {}
        )
        if error.get('code') == _INVALID_KEY:
            raise InvalidKey('AcoustID refused the API key')
        if resp.status_code in {429, 500, 502, 503, 504} or (
            'rate' in str(error.get('message') or '').lower()
        ):
            logger.debug('AcoustID asked to slow down')
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code >= 400 or body.get('status') != 'ok':
            raise AcoustIDError(
                str(error.get('message') or '')
                or f'AcoustID refused the request ({resp.status_code})',
                int(error.get('code') or 0),
            )
        return body
    raise AcoustIDError('AcoustID is busy; try again later')


def lookup(key: str, duration: int, print_: str) -> list[dict[str, Any]]:
    """AcoustID's results for one fingerprint, best first."""

    body = _post({
        'client': key,
        'format': 'json',
        'duration': str(int(duration)),
        'fingerprint': print_,
        'meta': 'recordings',
    })
    rows = [r for r in body.get('results') or [] if isinstance(r, dict)]
    return sorted(rows, key=lambda r: -float(r.get('score') or 0))


def check_key(key: str) -> None:
    """Ask AcoustID whether *key* works (a lookup of a tiny made-up
    fingerprint: past the key check, AcoustID may call the fingerprint
    itself unreadable, which still means the key is fine). Raises
    :class:`InvalidKey` or :class:`AcoustIDError`."""

    try:
        lookup(key, 30, 'AQAAAA')
    except InvalidKey:
        raise
    except AcoustIDError as exc:
        if exc.code != _INVALID_FINGERPRINT:
            raise


# ── Is it the song its tags say? ────────────────────────────────────────


@dataclass
class Identity:
    """What AcoustID made of one file (see :func:`judge`)."""

    #: ``'confirmed'`` (the tags' own song), ``'different'`` (another
    #: song, confidently) or ``'unknown'`` (no confident match).
    verdict: str
    score: float = 0.0
    artist: str = ''
    title: str = ''
    #: MusicBrainz recordings that agree with the tags (looked up for
    #: ISRCs, never written into a file).
    recordings: list[str] = field(default_factory=list)
    #: The one ISRC those recordings share, else ``''``.
    isrc: str = ''


def _artists(recording: dict[str, Any]) -> list[str]:
    return [
        str(a.get('name') or '')
        for a in recording.get('artists') or []
        if isinstance(a, dict) and a.get('name')
    ]


def _agrees(recording: dict[str, Any], song: dict[str, Any]) -> bool:
    from .library_songs import _key  # noqa: PLC0415  # it imports isrc

    artists = song.get('artists') or [song.get('artist')]
    wanted = _key(artists, song.get('name'))
    if not wanted:
        return False
    title = recording.get('title')
    if not any(_key([name], title) == wanted for name in _artists(recording)):
        return False
    length = float(song.get('duration') or 0)
    other = float(recording.get('duration') or 0)
    # A recording without a length in MusicBrainz still agrees: the
    # fingerprint and the names already do.
    return not (length and other) or (
        abs(length - other) <= isrc_mod.LENGTH_SECONDS
    )


def judge(results: list[dict[str, Any]], song: dict[str, Any]) -> Identity:
    """The verdict on AcoustID's *results* for a file tagged as *song*."""

    sure = [r for r in results if float(r.get('score') or 0) >= MIN_SCORE]
    if not sure:
        return Identity('unknown')
    agreeing: list[str] = []
    first_agreeing: Optional[tuple[float, dict[str, Any]]] = None
    first_other: Optional[tuple[float, dict[str, Any]]] = None
    for row in sure:
        score = float(row.get('score') or 0)
        for rec in row.get('recordings') or []:
            if not isinstance(rec, dict) or not rec.get('title'):
                continue
            if not _agrees(rec, song):
                first_other = first_other or (score, rec)
                continue
            first_agreeing = first_agreeing or (score, rec)
            rec_id = str(rec.get('id') or '')
            if rec_id and rec_id not in agreeing:
                agreeing.append(rec_id)
    best = first_agreeing or first_other
    if best is None:
        # Fingerprints AcoustID knows, linked to no recording yet.
        return Identity('unknown', score=float(sure[0].get('score') or 0))
    score, rec = best
    names = _artists(rec)
    return Identity(
        'confirmed' if agreeing else 'different',
        score=score,
        artist=', '.join(names),
        title=str(rec.get('title') or ''),
        recordings=agreeing,
    )


def _recording_isrcs(recording_id: str) -> set[str]:
    from . import musicbrainz  # noqa: PLC0415

    try:
        data = musicbrainz._get(  # noqa: SLF001
            f'recording/{recording_id}', inc='isrcs'
        )
    except musicbrainz.MusicBrainzError:
        return set()
    codes = {isrc_mod.normalize(c) for c in data.get('isrcs') or []}
    codes.discard('')
    return codes


def identify(path: Path, song: dict[str, Any], key: str) -> Identity:
    """Fingerprint *path*, ask AcoustID, and judge the answer against
    *song* (the file's tags). A confirmed file also gets its ISRC, when
    the agreeing recordings name exactly one.

    Raises :class:`AcoustIDError` (and its kinds) when it can't ask.
    """

    if not key:
        raise InvalidKey('No AcoustID API key is set')
    duration, print_ = fingerprint(path)
    found = judge(lookup(key, duration, print_), song)
    if found.verdict != 'confirmed':
        return found
    codes: set[str] = set()
    for recording_id in found.recordings[:_MAX_RECORDINGS]:
        codes |= _recording_isrcs(recording_id)
        if len(codes) > 1:
            break
    found.isrc = codes.pop() if len(codes) == 1 else ''
    return found


def status(enabled: bool, store: Optional[KeyStore]) -> dict[str, Any]:
    """What the settings page shows about the feature."""

    key = store.get() if store is not None else ''
    tool = fingerprinter()
    return {
        'enabled': bool(enabled),
        'key_set': bool(key),
        'key_hint': mask(key),
        'fingerprinter': tool,
        'ready': bool(enabled and key and tool),
    }
