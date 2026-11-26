"""Pause the download queue while slskd can't search.

When slskd loses the Soulseek network (the server is down, or slskd was
kicked off it), slskd's own web API still answers but every search is
refused. Each song then falls through to the next source (YouTube Music,
YouTube...), which picks wrong versions far more often - thousands of
them, for a long queue or a batch of new artist watches.

:class:`OutageWatch` counts the downloads in a row that slskd could not
even search for (:data:`OUTAGE_REASONS`). Any download slskd did search
for - found or not - starts the count over. When the count reaches
``slskd.outage_pause_after`` (0 = never), the caller pauses the queue
and says so on the notification channels; :meth:`OutageWatch.tripped`
returns ``True`` once per outage.

While the queue is paused for an outage, the API checks slskd every
:data:`CHECK_SECONDS` and resumes it once slskd is logged in again
(``downtify.api._watch_slskd_outage``). Resuming or pausing by hand
ends that watch: the admin decides from then on.
"""

from __future__ import annotations

import threading

#: slskd miss reasons (``slskd_provider.MISS_REASONS``) that mean slskd
#: could not search at all, as opposed to searching and finding nothing.
OUTAGE_REASONS = frozenset({'unreachable', 'offline', 'search_failed'})
#: The default for ``slskd.outage_pause_after``.
DEFAULT_PAUSE_AFTER = 25
#: Seconds between two looks at slskd while the queue waits for it.
CHECK_SECONDS = 60


class OutageWatch:
    """Counts the downloads in a row slskd couldn't search for."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._streak = 0
        self._tripped = False
        #: The queue is paused because of an outage (not by an admin).
        self.paused_by_outage = False
        #: The last reason counted, for the message.
        self.last_reason = ''

    @property
    def streak(self) -> int:
        return self._streak

    def reset(self) -> None:
        """slskd searched again: the outage (if any) is over."""

        with self._lock:
            self._streak = 0
            self._tripped = False

    def note(self, reason: str, pause_after: int) -> bool:
        """Count one download slskd missed for *reason*; ``True`` when
        this one reaches *pause_after* (once per outage)."""

        with self._lock:
            if reason not in OUTAGE_REASONS:
                self._streak = 0
                self._tripped = False
                return False
            self._streak += 1
            self.last_reason = reason
            if pause_after <= 0 or self._tripped:
                return False
            if self._streak >= pause_after:
                self._tripped = True
                return True
            return False

    def admin_took_over(self) -> None:
        """An admin paused or resumed the queue by hand."""

        with self._lock:
            self.paused_by_outage = False
            self._streak = 0
            self._tripped = False


#: The one watch of this process.
watch = OutageWatch()


def pause_after(slskd_settings: dict) -> int:
    """``slskd.outage_pause_after`` as a whole number, 0 = never."""

    raw = slskd_settings.get('outage_pause_after')
    if raw is None or raw == '':
        return DEFAULT_PAUSE_AFTER
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = DEFAULT_PAUSE_AFTER
    return min(1000, max(0, value))


_REASON_TEXT = {
    'unreachable': "slskd's web API did not answer",
    'offline': 'slskd is not logged in to the Soulseek network',
    'search_failed': 'slskd refused the searches',
}


def reason_text(reason: str) -> str:
    return _REASON_TEXT.get(reason, 'slskd could not search')
