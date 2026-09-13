"""Checks GitHub Releases for a newer Downtify version than the one
running, on an hourly background loop.

The web UI only ever reads whatever the last check found (see
``GET /api/check_update`` in ``downtify/api.py``) — the actual HTTP call
to GitHub happens here, in the background, so loading the app never
waits on it.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any, Optional

import requests
from loguru import logger

GITHUB_REPO = 'henriquesebastiao/downtify'
RELEASES_API_URL = (
    f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest'
)
DEFAULT_RELEASES_PAGE_URL = f'https://github.com/{GITHUB_REPO}/releases/latest'

#: Seconds between checks — "every hour", per the feature request.
CHECK_INTERVAL_SECONDS = 3600
REQUEST_TIMEOUT = 10

_VERSION_RE = re.compile(r'\d+(?:\.\d+)*')


def _parse_version(raw: str) -> tuple[int, ...]:
    """Turn ``'2.11.0'``, ``'v2.11.0'`` or ``'Downtify 2.11.0'`` into
    ``(2, 11, 0)``.

    Falls back to an empty tuple for anything unparseable, which always
    compares as "not newer" in :func:`is_newer` rather than raising.
    """
    match = _VERSION_RE.search(raw or '')
    if not match:
        return ()
    return tuple(int(part) for part in match.group().split('.'))


def is_newer(latest: str, current: str) -> bool:
    """Whether ``latest`` is a strictly newer version than ``current``."""
    latest_version = _parse_version(latest)
    return bool(latest_version) and latest_version > _parse_version(current)


class UpdateChecker:
    """Caches the result of the last GitHub Releases check.

    ``check_now()`` does the (blocking) network call and is meant to be
    run via ``asyncio.to_thread`` from :func:`update_check_loop`;
    :meth:`status` is cheap and safe to call from a request handler.
    """

    def __init__(self, repo: str = GITHUB_REPO) -> None:
        self._repo = repo
        self._latest_version: Optional[str] = None
        self._release_url = DEFAULT_RELEASES_PAGE_URL
        self._last_checked: Optional[str] = None
        self._last_error: Optional[str] = None

    def check_now(self) -> None:
        """Fetch the latest release from GitHub. Never raises — a
        network hiccup or GitHub's (unauthenticated) rate limit just
        means the previous result carries over until the next hourly
        check, rather than crashing the background loop.
        """
        url = f'https://api.github.com/repos/{self._repo}/releases/latest'
        try:
            response = requests.get(
                url,
                headers={'Accept': 'application/vnd.github+json'},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            tag = str(data.get('tag_name') or '').strip()
            if not tag:
                raise ValueError('release response has no tag_name')
            self._latest_version = tag
            self._release_url = data.get('html_url') or self._release_url
            self._last_error = None
        except Exception as exc:
            logger.opt(exception=True).warning(
                'Update check against GitHub Releases failed: {}', exc
            )
            self._last_error = str(exc)
        finally:
            self._last_checked = datetime.now(timezone.utc).isoformat()

    def status(self, current_version: str) -> dict[str, Any]:
        """Shape returned by ``GET /api/check_update``."""
        update_available = bool(
            self._latest_version
            and is_newer(self._latest_version, current_version)
        )
        return {
            'current_version': current_version,
            'latest_version': self._latest_version,
            'update_available': update_available,
            'release_url': self._release_url,
            'last_checked': self._last_checked,
        }


async def update_check_loop(
    checker: UpdateChecker,
    interval_seconds: int = CHECK_INTERVAL_SECONDS,
) -> None:
    """Background task: check GitHub Releases once immediately, then
    every ``interval_seconds`` (an hour by default).
    """
    while True:
        try:
            await asyncio.to_thread(checker.check_now)
        except Exception:
            logger.exception('Unexpected error in update check loop')
        await asyncio.sleep(interval_seconds)
