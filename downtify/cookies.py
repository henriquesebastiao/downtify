"""Managed storage for the YouTube ``cookies.txt`` used by yt-dlp.

Cookies are what get age-restricted (explicit) tracks and bot-challenged
downloads working, but until now the only way to supply them was the
``DOWNTIFY_COOKIES_FILE`` environment variable plus a bind mount — a
non-starter on Docker Desktop for Windows, and a frequent source of
"downloads just fail" reports (henriquesebastiao/downtify#280).

This module keeps an uploaded ``cookies.txt`` inside the ``/data``
volume, so it survives container updates the same way ``settings.json``
and the Playlist Monitor database do. The environment variable still
wins when it's set: a deployment that mounts its own cookie file stays
in charge, and the web UI shows the upload controls as locked.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import tempfile
import threading
from collections.abc import Iterator
from datetime import datetime, timezone
from http.cookiejar import Cookie
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from yt_dlp.cookies import YoutubeDLCookieJar

#: Environment variable that pins a cookie file, bypassing this store.
ENV_VAR = 'DOWNTIFY_COOKIES_FILE'

#: Cookie jars are a few KB at most; anything larger isn't a cookies.txt.
MAX_COOKIES_BYTES = 2 * 1024 * 1024

#: Netscape cookie lines have exactly these 7 tab-separated fields.
_NETSCAPE_FIELD_COUNT = 7

_USEFUL_DOMAINS = ('youtube.com', 'google.com')

#: ``health`` before any check ran (or after the jar was removed).
UNKNOWN_HEALTH: dict[str, Any] = {
    'state': 'unknown',
    'checked_at': None,
    'message': None,
    'refreshed_at': None,
    'bot_check_at': None,
}


#: One cookie's identity in a jar: ``(domain, path, name)``.
CookieKey = tuple[str, str, str]

#: Serializes every write of a shared cookies.txt in this process, so two
#: downloads finishing together can't interleave their merges.
_WRITE_LOCK = threading.Lock()


class InvalidCookiesFile(ValueError):
    """Raised when an upload isn't a usable Netscape cookies.txt."""


def _cookie_lines(text: str) -> list[list[str]]:
    """Split *text* into its Netscape cookie records.

    Comments and blank lines are dropped. ``#HttpOnly_`` is a real
    prefix browsers' export extensions write on otherwise normal
    records, so it's unwrapped rather than treated as a comment.
    """

    records: list[list[str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('#HttpOnly_'):
            line = line[len('#HttpOnly_') :]
        elif line.startswith('#'):
            continue
        fields = line.split('\t')
        if len(fields) == _NETSCAPE_FIELD_COUNT:
            records.append(fields)
    return records


def validate_cookies(content: bytes) -> list[str]:
    """Validate an uploaded cookie jar, returning non-fatal warnings.

    Raises :class:`InvalidCookiesFile` when the upload can't work at all
    — that's far kinder than accepting it and letting every download
    fail later with an opaque yt-dlp error.
    """

    if not content.strip():
        raise InvalidCookiesFile('The file is empty.')
    if len(content) > MAX_COOKIES_BYTES:
        raise InvalidCookiesFile(
            f'The file is larger than '
            f'{MAX_COOKIES_BYTES // (1024 * 1024)} MB, so it is not a '
            f'cookies.txt.'
        )
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise InvalidCookiesFile(
            'The file is not UTF-8 text. Export it as a Netscape '
            'cookies.txt, not as a binary or spreadsheet file.'
        ) from exc

    records = _cookie_lines(text)
    if not records:
        raise InvalidCookiesFile(
            'No cookies found. The file must be in Netscape format — one '
            'cookie per line, fields separated by tabs. Use a browser '
            'extension such as "Get cookies.txt LOCALLY" to export it.'
        )

    warnings: list[str] = []
    domains = {fields[0].lstrip('.').lower() for fields in records}
    if not any(
        domain.endswith(useful)
        for domain in domains
        for useful in _USEFUL_DOMAINS
    ):
        warnings.append(
            'No youtube.com or google.com cookies found in this file. '
            'Export it from a tab logged into YouTube, otherwise it '
            "won't help with age-restricted tracks."
        )
    return warnings


def load_jar(path: Path | str) -> dict[CookieKey, Cookie]:
    """Every cookie in the Netscape file at *path*, keyed by identity.

    An unreadable or malformed file reads as empty: callers use this to
    diff and merge, never to decide whether cookies are configured.
    """

    jar = YoutubeDLCookieJar(str(path))
    try:
        jar.load()
    except (OSError, ValueError) as exc:
        logger.debug('Could not read cookie jar {}: {}', path, exc)
        return {}
    return {(c.domain, c.path, c.name): c for c in jar}


def changed_cookies(
    before: dict[CookieKey, Cookie], after: dict[CookieKey, Cookie]
) -> list[Cookie]:
    """Cookies of *after* that are new or carry a new value or expiry.

    Cookies missing from *after* are deliberately not reported: a merge
    only ever adds or refreshes, so a client that dropped a cookie can't
    take it away from the shared file.
    """

    changed: list[Cookie] = []
    for key, cookie in after.items():
        old = before.get(key)
        if (
            old is None
            or old.value != cookie.value
            or old.expires != cookie.expires
        ):
            changed.append(cookie)
    return changed


def merge_into(path: Path | str, cookies: list[Cookie]) -> int:
    """Write *cookies* into the shared jar at *path*, keeping the rest.

    YouTube and Google rotate their session cookies (``__Secure-*PSIDTS``,
    ``SIDCC`` and friends) as they're used; a jar that never learns the
    new values is eventually refused ("cookies are no longer valid").
    Only the changed cookies are applied, on top of the file as it is
    *now*, so a slow download can't roll back a newer value another one
    already saved. Returns how many cookies were written; 0 when the
    file is gone or can't be written (a read-only bind mount stays
    exactly as it was).
    """

    target = Path(path)
    if not cookies or not target.is_file():
        return 0
    with _WRITE_LOCK:
        jar = YoutubeDLCookieJar(str(target))
        try:
            jar.load()
        except (OSError, ValueError) as exc:
            logger.debug(
                'Cookie merge skipped, {} unreadable: {}', target, exc
            )
            return 0
        for cookie in cookies:
            jar.set_cookie(cookie)
        if not _save_jar(jar, target):
            return 0
    logger.debug('Saved {} refreshed cookie(s) to {}', len(cookies), target)
    return len(cookies)


def _save_jar(jar: YoutubeDLCookieJar, target: Path) -> bool:
    """Write *jar* over *target*: atomically when the folder allows it,
    in place when *target* is a single-file bind mount (renaming over a
    mount point fails with ``EBUSY``). Callers hold ``_WRITE_LOCK``."""

    tmp_path = target.with_name(f'{target.name}.merge.tmp')
    try:
        jar.save(str(tmp_path))
        with contextlib.suppress(OSError):
            tmp_path.chmod(0o600)
        tmp_path.replace(target)
        return True
    except OSError:
        with contextlib.suppress(OSError):
            tmp_path.unlink()
    try:
        jar.save(str(target))
        return True
    except OSError as exc:
        logger.debug('Cookie merge skipped, {} not writable: {}', target, exc)
        return False


@contextlib.contextmanager
def private_cookiefile(ydl_opts: dict[str, Any]) -> Iterator[None]:
    """Point ``cookiefile`` at a per-run copy of the cookie jar.

    yt-dlp rewrites ``cookiefile`` on exit (truncate then write), so
    parallel downloads sharing one cookies.txt clobber it and a
    concurrent reader hits a half-written file ("does not look like a
    Netscape format cookies file"). The copy keeps that write off the
    shared path; once yt-dlp is done, the cookies YouTube rotated during
    the run are merged back (:func:`merge_into`) so the shared jar stays
    signed in instead of going stale after a few hours.
    """

    shared = ydl_opts.get('cookiefile')
    if not shared or not os.path.isfile(shared):
        yield
        return
    fd, tmp = tempfile.mkstemp(prefix='cookies-', suffix='.txt')
    os.close(fd)
    before: dict[CookieKey, Cookie] = {}
    try:
        # Under the write lock: an in-place save (see _save_jar) must
        # not be copied half-written.
        with _WRITE_LOCK:
            shutil.copyfile(shared, tmp)
        before = load_jar(tmp)
        ydl_opts['cookiefile'] = tmp
        yield
    finally:
        ydl_opts['cookiefile'] = shared
        try:
            merge_into(shared, changed_cookies(before, load_jar(tmp)))
        except Exception:
            logger.opt(exception=True).debug('Cookie merge-back failed')
        with contextlib.suppress(OSError):
            os.remove(tmp)


class CookiesStore:
    """The uploaded ``cookies.txt``, plus the env var that overrides it."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        #: Last result of the keep-alive check (downtify/cookie_refresh.py),
        #: surfaced as ``health`` by :meth:`status`.
        self.health: dict[str, Any] = dict(UNKNOWN_HEALTH)

    @property
    def path(self) -> Path:
        return self._path

    @staticmethod
    def env_override() -> str:
        """``DOWNTIFY_COOKIES_FILE``, or ``''`` when unset."""
        return os.getenv(ENV_VAR, '').strip()

    def is_locked(self) -> bool:
        """Whether the env var owns cookie configuration (UI read-only)."""
        return bool(self.env_override())

    def active_path(self) -> Optional[Path]:
        """The cookie file yt-dlp should use, if any.

        The environment variable wins so an existing deployment's bind
        mount keeps working exactly as before.
        """
        env_path = self.env_override()
        if env_path:
            return Path(env_path)
        return self._path if self._path.is_file() else None

    def status(self) -> dict[str, Any]:
        """Shape consumed by ``GET /api/cookies`` and the settings UI."""
        return {**self._file_status(), 'health': dict(self.health)}

    def _file_status(self) -> dict[str, Any]:
        env_path = self.env_override()
        if env_path:
            return {
                'configured': Path(env_path).is_file(),
                'source': 'env',
                'locked': True,
                'path': env_path,
                'size': None,
                'updated_at': None,
            }
        if self._path.is_file():
            stat = self._path.stat()
            return {
                'configured': True,
                'source': 'upload',
                'locked': False,
                'path': str(self._path),
                'size': stat.st_size,
                'updated_at': datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
            }
        return {
            'configured': False,
            'source': None,
            'locked': False,
            'path': None,
            'size': None,
            'updated_at': None,
        }

    def save(self, content: bytes) -> list[str]:
        """Validate and persist *content*, replacing any previous file.

        Returns the non-fatal warnings from :func:`validate_cookies`.
        """

        warnings = validate_cookies(content)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Write-then-replace so a failed write can't leave a truncated
        # jar behind that would break every subsequent download.
        tmp_path = self._path.with_name(f'{self._path.name}.tmp')
        tmp_path.write_bytes(content)
        # Session tokens: keep it out of reach of other users on the host.
        # Best-effort — filesystems without POSIX permissions (a Windows
        # bind mount, most notably) must not fail the upload itself.
        with contextlib.suppress(OSError):
            tmp_path.chmod(0o600)
        tmp_path.replace(self._path)
        self.health = dict(UNKNOWN_HEALTH)
        logger.info('Stored uploaded cookies file at {}', self._path)
        return warnings

    def delete(self) -> bool:
        """Remove the uploaded file. ``False`` when there was none."""
        if not self._path.is_file():
            return False
        self._path.unlink()
        self.health = dict(UNKNOWN_HEALTH)
        logger.info('Removed uploaded cookies file at {}', self._path)
        return True
