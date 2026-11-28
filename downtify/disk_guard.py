"""Pause downloads before the disk is full.

Nothing used to look at free space before downloading. When the library
disk filled up, every download failed ("No space left on device"),
half-written files could be left behind, and the databases next to the
settings could no longer be written either.

:class:`DiskGuard` looks at the free space of the folders Downtify writes
to (the download folder and the data folder) every
:data:`CHECK_SECONDS`. When one has less than ``min_free_space_gb``
(Settings > Downloads & files; ``0`` turns it off):

- the download queue is paused (running downloads finish) and the
  ``disk_space`` notification says which folder and how much is left;
- once every folder has :data:`RESUME_MARGIN_GB` more than the limit
  again, the queue resumes by itself, with a second message.

Pausing or resuming by hand takes over: the guard won't pause again
until free space has gone back above the limit and dropped once more.
"""

from __future__ import annotations

import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

#: The default for ``min_free_space_gb``.
DEFAULT_MIN_FREE_GB = 5
#: Largest limit Settings accepts.
MAX_MIN_FREE_GB = 10_000
#: Seconds between two looks at the disks.
CHECK_SECONDS = 30
#: Free space above the limit needed before resuming, so the queue
#: doesn't flip between paused and running around the limit.
RESUME_MARGIN_GB = 1

GB = 1024**3


def min_free_gb(settings: dict) -> int:
    """``min_free_space_gb`` as a whole number of GB, 0 = off."""

    raw = settings.get('min_free_space_gb')
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return DEFAULT_MIN_FREE_GB
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        return DEFAULT_MIN_FREE_GB
    return min(MAX_MIN_FREE_GB, max(0, value))


def human(size: int) -> str:
    """``12.3 GB`` / ``850 MB``."""

    if size >= GB:
        return f'{size / GB:.1f} GB'
    return f'{size / 1024**2:.0f} MB'


@dataclass
class Low:
    """The folder with the least free space, when below the limit."""

    path: str
    free: int


def _free(path: Path) -> Optional[int]:
    try:
        return shutil.disk_usage(path).free
    except OSError:
        return None


def lowest(
    paths: Iterable[Path],
    free: Callable[[Path], Optional[int]] = _free,
) -> Optional[Low]:
    """The folder of *paths* with the least free space (folders that
    can't be read are skipped)."""

    worst: Optional[Low] = None
    for path in paths:
        space = free(Path(path))
        if space is None:
            continue
        if worst is None or space < worst.free:
            worst = Low(str(path), space)
    return worst


class DiskGuard:
    """Decides when to pause and resume; the caller does it."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        #: The queue is paused because of free space (not by an admin).
        self.paused_by_disk = False
        #: An admin paused or resumed while space was low: leave the
        #: queue to them until space went back above the limit.
        self._held_off = False
        #: Space is low while the queue was already paused: said once.
        self._warned = False
        self.last: Optional[Low] = None

    def admin_took_over(self) -> None:
        with self._lock:
            if self.last is not None and (self.paused_by_disk or self._warned):
                self._held_off = True
            self.paused_by_disk = False

    def decide(
        self,
        worst: Optional[Low],
        limit_gb: int,
        queue_paused: bool,
    ) -> str:
        """What to do about the current reading:

        - ``pause``: pause the queue and say so;
        - ``repause``: pause it again, quietly (something other than an
          admin resumed it while space is still low);
        - ``warn``: space is low but the queue is paused already (by an
          admin, or for slskd): say so, leave the pause alone;
        - ``resume``: space is back, resume what this paused, say so;
        - ``''``: nothing.
        """

        with self._lock:
            self.last = worst
            low = (
                limit_gb > 0
                and worst is not None
                and worst.free < limit_gb * GB
            )
            if low:
                if self._held_off:
                    return ''
                if self.paused_by_disk:
                    return '' if queue_paused else 'repause'
                if queue_paused:
                    if self._warned:
                        return ''
                    self._warned = True
                    return 'warn'
                self.paused_by_disk = True
                return 'pause'
            recovered = (
                limit_gb <= 0
                or worst is None
                or worst.free >= (limit_gb + RESUME_MARGIN_GB) * GB
            )
            if not recovered:
                return ''
            self._held_off = False
            self._warned = False
            if self.paused_by_disk:
                self.paused_by_disk = False
                return 'resume'
            return ''


#: The one guard of this process.
guard = DiskGuard()
