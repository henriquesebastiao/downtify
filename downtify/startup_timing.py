"""How long each start-up step takes, in the log.

The web page answers only once every step before ``yield`` in
``main.py``'s lifespan is done. On a big library one of them can take
minutes, and without timings the log only shows a long silence. Each
step is timed here: a slow one gets its own line as it finishes, and one
summary line names the slowest steps when the server is ready.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from loguru import logger

#: A step that takes at least this long gets its own log line.
SLOW_STEP_SECONDS = 1.0
#: How many of the slowest steps the summary line names.
SUMMARY_STEPS = 5
#: Steps shorter than this are left out of the summary line.
SUMMARY_MIN_SECONDS = 0.05


class StartupTimings:
    """Time the named steps of one start, then log a summary."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self.started = clock()
        self.steps: list[tuple[str, float]] = []

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        """Time the block. A step that raises is still timed and logged
        (``failed``); the exception goes on to the caller."""

        began = self._clock()
        failed = True
        try:
            yield
            failed = False
        finally:
            self.record(name, self._clock() - began, failed=failed)

    def since(self, name: str, began: float) -> None:
        """Record a step that started at *began* (this timer's clock)
        and ends now: for a long block that a ``with`` would re-indent."""

        self.record(name, self._clock() - began)

    def record(self, name: str, seconds: float, *, failed: bool = False):
        self.steps.append((name, seconds))
        if failed:
            logger.info('Start-up: {} failed after {:.1f} s', name, seconds)
        elif seconds >= SLOW_STEP_SECONDS:
            logger.info('Start-up: {} took {:.1f} s', name, seconds)

    def summary(self) -> str:
        """The line :meth:`log_ready` writes."""

        total = self._clock() - self.started
        slowest = sorted(
            (s for s in self.steps if s[1] >= SUMMARY_MIN_SECONDS),
            key=lambda s: s[1],
            reverse=True,
        )[:SUMMARY_STEPS]
        line = f'Start-up finished in {total:.1f} s'
        if slowest:
            line += '; slowest: ' + ', '.join(
                f'{name} {seconds:.1f} s' for name, seconds in slowest
            )
        return line

    def log_ready(self) -> None:
        logger.info(self.summary())
