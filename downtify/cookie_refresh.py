"""Keep the YouTube ``cookies.txt`` signed in without the user's help.

Why exported cookies "expire" after a few hours (henriquesebastiao/downtify
issue on VPN users re-uploading cookies): Google's session is not one static
token. ``__Secure-1PSIDTS`` / ``__Secure-3PSIDTS`` and ``SIDCC`` are rotated
by the browser every few minutes (``POST /RotateCookies``) and by the
``Set-Cookie`` headers of ordinary page loads. A jar that never learns the
new values is eventually refused, and yt-dlp then reports "The provided
YouTube account cookies are no longer valid". The more suspicious the IP
(VPNs, datacenters), the sooner that happens.

Logging in to Google automatically is not an option: Google blocks
scripted and headless sign-ins ("This browser or app may not be secure"),
asks for 2FA / device prompts, and OAuth for YouTube was shut off for
third-party clients. What *is* possible is to behave like the browser
tab the cookies came from - so this module, every
``DOWNTIFY_COOKIES_REFRESH_MINUTES`` (default 15, ``0`` turns it off):

1. asks Google to rotate the session cookies (the same undocumented
   ``RotateCookies`` call the browser makes - best effort, a failure is
   only logged);
2. loads ``https://www.youtube.com/`` with the jar, which both refreshes
   the YouTube cookies and tells whether the session is still signed in
   (``"LOGGED_IN":true`` in the page's config);
3. merges every cookie that changed back into the stored file
   (:func:`downtify.cookies.merge_into`).

The result is kept as the store's ``health`` (``GET /api/cookies``) so the
settings page can say "signed in, checked 3 min ago" or "YouTube signed
these cookies out - upload new ones" instead of downloads failing
silently. yt-dlp's own warnings feed the same state
(:func:`note_ytdlp_message`), so a download that hits a dead session or a
bot check shows up there too.
"""

from __future__ import annotations

import asyncio
import os
import re
import threading
from datetime import datetime, timezone
from typing import Any, Optional

import requests
from loguru import logger

from .cookies import (
    UNKNOWN_HEALTH,
    CookiesStore,
    changed_cookies,
    load_jar,
    merge_into,
)

#: Minutes between two keep-alive runs; ``0`` disables the loop.
ENV_INTERVAL = 'DOWNTIFY_COOKIES_REFRESH_MINUTES'
DEFAULT_INTERVAL_MINUTES = 15
#: Delay before the first run after start, so boot isn't slowed down.
_STARTUP_DELAY_SECONDS = 30

_TIMEOUT = 20
_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
)
#: Google's own rotation request: a fixed body, the answer is Set-Cookie.
_ROTATE_BODY = '[000,"-0000000000000000000"]'
#: Cookie names that mean "this jar belongs to a signed-in account".
_ACCOUNT_COOKIES = frozenset({
    'SID',
    '__Secure-1PSID',
    '__Secure-3PSID',
    'SAPISID',
    'LOGIN_INFO',
})
_LOGGED_IN_RE = re.compile(r'"LOGGED_IN"\s*:\s*(true|false)')

#: Fragments of yt-dlp messages that mean the session itself is dead.
_SIGNED_OUT_FRAGMENTS = (
    'cookies are no longer valid',
    'have likely been rotated in the browser',
)
#: Fragments of yt-dlp messages that mean YouTube wants a signed-in
#: (or less suspicious) client: the VPN / datacenter bot wall.
_BOT_CHECK_FRAGMENTS = ("confirm you're not a bot", 'confirm you’re not a bot')

#: The store :func:`note_ytdlp_message` reports into (one per process).
_bound: dict[str, Optional[CookiesStore]] = {'store': None}
_run_lock = threading.Lock()


def bind_store(store: Optional[CookiesStore]) -> None:
    """Make *store* the one :func:`note_ytdlp_message` reports into."""

    _bound['store'] = store


def interval_minutes() -> int:
    """``DOWNTIFY_COOKIES_REFRESH_MINUTES``, clamped to 0 or 5..1440."""

    raw = os.getenv(ENV_INTERVAL, '').strip()
    if not raw:
        return DEFAULT_INTERVAL_MINUTES
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            '{}={!r} is not a number; using {} minutes',
            ENV_INTERVAL,
            raw,
            DEFAULT_INTERVAL_MINUTES,
        )
        return DEFAULT_INTERVAL_MINUTES
    if value <= 0:
        return 0
    return max(5, min(value, 1440))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_health(store: CookiesStore, **changes: Any) -> None:
    previous = store.health.get('state')
    store.health = {**store.health, **changes}
    state = store.health.get('state')
    if state == 'signed_out' and previous != 'signed_out':
        logger.warning(
            'YouTube cookies are signed out: {}. Upload a fresh '
            'cookies.txt in Settings > YouTube cookies.',
            store.health.get('message') or 'session refused',
        )
    elif state == 'valid' and previous == 'signed_out':
        logger.info('YouTube cookies are signed in again')


def note_ytdlp_message(message: str) -> None:
    """Record what a yt-dlp warning/error says about the cookies."""

    store = _bound['store']
    if store is None or not message:
        return
    lowered = message.lower()
    if any(fragment in lowered for fragment in _SIGNED_OUT_FRAGMENTS):
        _set_health(
            store,
            state='signed_out',
            checked_at=_now(),
            message='yt-dlp: YouTube no longer accepts these cookies',
        )
    elif any(fragment in lowered for fragment in _BOT_CHECK_FRAGMENTS):
        store.health = {**store.health, 'bot_check_at': _now()}


def _new_session() -> requests.Session:
    """The HTTP session one keep-alive pass runs on (a seam for tests)."""

    return requests.Session()


def _rotate(session: requests.Session, host: str) -> None:
    """Ask ``https://<host>/RotateCookies`` for fresh session cookies."""

    try:
        response = session.post(
            f'https://{host}/RotateCookies',
            data=_ROTATE_BODY,
            headers={
                'Content-Type': 'application/json',
                'Origin': f'https://{host}',
            },
            timeout=_TIMEOUT,
        )
        logger.debug(
            'Cookie rotation at {}: HTTP {}', host, response.status_code
        )
    except requests.RequestException as exc:
        logger.debug('Cookie rotation at {} failed: {}', host, exc)


def _has_account_cookie(jar: dict, domain: str) -> bool:
    return any(
        name in _ACCOUNT_COOKIES and cookie_domain.lstrip('.').endswith(domain)
        for (cookie_domain, _path, name) in jar
    )


def refresh_cookies(store: CookiesStore) -> dict[str, Any]:
    """Run one keep-alive pass on the active jar and return its health.

    Never raises: a network failure becomes ``state='error'``.
    """

    with _run_lock:
        return _refresh_locked(store)


def _refresh_locked(store: CookiesStore) -> dict[str, Any]:
    path = store.active_path()
    if path is None or not path.is_file():
        store.health = dict(UNKNOWN_HEALTH)
        return dict(store.health)

    before = load_jar(path)
    if not _has_account_cookie(before, 'youtube.com') and not (
        _has_account_cookie(before, 'google.com')
    ):
        _set_health(
            store,
            state='no_account',
            checked_at=_now(),
            message='No signed-in Google session in this cookies.txt',
        )
        return dict(store.health)

    session = _new_session()
    session.headers.update({
        'User-Agent': _USER_AGENT,
        'Accept-Language': 'en-US,en;q=0.9',
    })
    for cookie in before.values():
        session.cookies.set_cookie(cookie)

    if _has_account_cookie(before, 'google.com'):
        _rotate(session, 'accounts.google.com')
    if _has_account_cookie(before, 'youtube.com'):
        _rotate(session, 'accounts.youtube.com')

    try:
        response = session.get('https://www.youtube.com/', timeout=_TIMEOUT)
        page = response.text
    except requests.RequestException as exc:
        _set_health(
            store,
            state='error',
            checked_at=_now(),
            message=f'YouTube could not be reached: {type(exc).__name__}',
        )
        return dict(store.health)

    after = {(c.domain, c.path, c.name): c for c in session.cookies}
    saved = merge_into(path, changed_cookies(before, after))
    changes: dict[str, Any] = {'checked_at': _now()}
    if saved:
        changes['refreshed_at'] = changes['checked_at']

    match = _LOGGED_IN_RE.search(page)
    if match is None:
        changes |= {
            'state': 'error',
            'message': (
                f'YouTube answered HTTP {response.status_code} without '
                'its usual page'
            ),
        }
    elif match.group(1) == 'true':
        changes |= {'state': 'valid', 'message': None}
    else:
        changes |= {
            'state': 'signed_out',
            'message': 'YouTube signed this session out',
        }
    _set_health(store, **changes)
    return dict(store.health)


async def cookie_refresh_loop(store: CookiesStore) -> None:
    """Background task: :func:`refresh_cookies` every few minutes."""

    minutes = interval_minutes()
    if minutes == 0:
        logger.info('YouTube cookie keep-alive disabled ({}=0)', ENV_INTERVAL)
        return
    await asyncio.sleep(_STARTUP_DELAY_SECONDS)
    while True:
        try:
            if store.active_path() is not None:
                await asyncio.to_thread(refresh_cookies, store)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.opt(exception=True).warning('Cookie keep-alive failed')
        await asyncio.sleep(minutes * 60)
