"""Notice watches whose playlist or artist can't be read any more.

A watch check starts by reading the playlist's songs (or the artist's
releases). When that failed - the playlist was deleted or made private,
the service changed, the network was down - the check only wrote the
error to the log and marked the watch as checked. Nothing on screen
said so, and a watch could get no songs for months.

:class:`WatchReads` counts the failed reads in a row per watch and
keeps them in ``<data>/watch_reads.json`` (beside the databases, so no
schema change; it is only a health note and can be lost safely):

- after :data:`ALERT_AFTER` failed checks in a row, the Monitor page
  shows the watch as "Can't read" with the reason, and the
  ``watch_failing`` notification says so - once;
- the first read that works clears it, with a "working again" message
  when the alert went out.
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger

from . import notifications

FILE_NAME = 'watch_reads.json'
#: Failed checks in a row before the watch shows as failing.
ALERT_AFTER = 3

_NOT_FOUND = re.compile(
    r'\b404\b|not found|does not exist|no longer available|'
    r'unavailable|private|nonexistent|unable to find',
    re.IGNORECASE,
)
_NETWORK = re.compile(
    r'timed out|timeout|name resolution|connection (refused|reset)|'
    r'network is unreachable|getaddrinfo|eai_again|\b50[234]\b',
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def reason(error: str, kind: str = 'playlist') -> str:
    """What a read error most likely means, in words."""

    text = error or ''
    thing = 'artist' if kind == 'artist' else 'playlist'
    if 'PersistedQueryNotFound' in text:
        return 'Spotify changed its player and the playlist could not be read'
    if _NETWORK.search(text):
        return f'The service did not answer when reading the {thing}'
    if _NOT_FOUND.search(text):
        return (
            f'The {thing} was not found: it may have been deleted or '
            'made private'
        )
    return f'The {thing} could not be read'


def _short(error: str, limit: int = 200) -> str:
    line = ' '.join((error or '').split())
    return line if len(line) <= limit else line[: limit - 1] + '…'


class WatchReads:
    """Failed reads in a row per watch id."""

    def __init__(
        self,
        emit: Callable[[str, str, str], None] = notifications.emit,
    ) -> None:
        self.emit = emit
        self.path: Optional[Path] = None
        self._lock = threading.Lock()
        self._rows: dict[str, dict[str, Any]] = {}

    def configure(self, path: Optional[Path]) -> None:
        self.path = Path(path) if path else None
        self._rows = {}
        if self.path is None:
            return
        try:
            raw = json.loads(self.path.read_text('utf-8'))
        except (OSError, ValueError):
            return
        rows = raw.get('watches') if isinstance(raw, dict) else None
        if isinstance(rows, dict):
            self._rows = {
                str(k): v for k, v in rows.items() if isinstance(v, dict)
            }

    def _save(self) -> None:
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix('.tmp')
            tmp.write_text(json.dumps({'watches': self._rows}), 'utf-8')
            tmp.replace(self.path)
        except OSError:
            logger.opt(exception=True).debug('Could not save watch reads')

    def failed(
        self, watch_id: int, name: str, error: str, kind: str = 'playlist'
    ) -> bool:
        """Count one failed read; ``True`` when this one makes the watch
        show as failing (the alert is sent then)."""

        why = reason(error, kind)
        with self._lock:
            row = self._rows.setdefault(
                str(watch_id), {'failures': 0, 'since': _now()}
            )
            row['failures'] = int(row.get('failures') or 0) + 1
            row['last_at'] = _now()
            row['reason'] = why
            row['error'] = _short(error)
            newly = row['failures'] >= ALERT_AFTER and not row.get('alerted')
            if newly:
                row['alerted'] = True
            count = row['failures']
            self._save()
        if newly:
            logger.warning(
                'Watch "{}" could not be read {} times in a row: {}',
                name,
                count,
                why,
            )
            self.emit(
                'watch_failing',
                f"{name} can't be read",
                f'{why}. {count} checks in a row failed; the watch gets '
                f'no new songs until it can be read. ({_short(error, 120)})',
            )
        return newly

    def ok(self, watch_id: int, name: str) -> bool:
        """A read worked; ``True`` when the watch was shown as failing."""

        with self._lock:
            row = self._rows.pop(str(watch_id), None)
            if row is None:
                return False
            self._save()
        if not row.get('alerted'):
            return False
        logger.info('Watch "{}" can be read again', name)
        self.emit(
            'watch_failing',
            f'{name} works again',
            'It can be read again; new songs download as before.',
        )
        return True

    def forget(self, watch_id: int) -> None:
        with self._lock:
            if self._rows.pop(str(watch_id), None) is not None:
                self._save()

    def status(self, watch_id: int) -> Optional[dict[str, Any]]:
        """``{failures, since, last_at, reason, error}`` once the watch
        shows as failing, else ``None``."""

        row = self._rows.get(str(watch_id))
        if not row or int(row.get('failures') or 0) < ALERT_AFTER:
            return None
        return {
            k: row.get(k)
            for k in ('failures', 'since', 'last_at', 'reason', 'error')
        }


#: The one of this process.
reads = WatchReads()


def configure(path: Optional[Path]) -> None:
    reads.configure(path)


def note_failure(watch: Any, error: BaseException | str) -> None:
    try:
        reads.failed(
            int(watch.id),
            str(watch.name or ''),
            str(error) or type(error).__name__,
            str(getattr(watch, 'kind', 'playlist') or 'playlist'),
        )
    except Exception:
        logger.opt(exception=True).debug('watch reads: failure')


def note_ok(watch: Any) -> None:
    try:
        reads.ok(int(watch.id), str(watch.name or ''))
    except Exception:
        logger.opt(exception=True).debug('watch reads: ok')
