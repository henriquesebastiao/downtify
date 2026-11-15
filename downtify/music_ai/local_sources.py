"""One bounded daemon slot for potentially slow source metadata I/O."""

from __future__ import annotations

import threading
from typing import Any

from .worker import signature

SOURCE_TIMEOUT = 2.0


class SourceGuard:
    def __init__(self) -> None:
        self._slot = threading.Lock()

    @staticmethod
    def _verify(
        rows: list[dict[str, Any]],
        context: Any,
        expected: dict[str, list[int]],
    ) -> dict[str, str]:
        from ..library_catalog import resolve_library_file

        result = {}
        for row in rows:
            identity = row['id']
            try:
                path = resolve_library_file(row['file'], context)
                if path is None:
                    result[identity] = 'source_unavailable'
                elif list(signature(path)) != expected[identity]:
                    result[identity] = 'source_changed'
                else:
                    result[identity] = 'source_verified'
            except (OSError, ValueError):
                result[identity] = 'source_unavailable'
        return result

    def check(
        self,
        rows: list[dict[str, Any]],
        context: Any,
        expected: dict[str, list[int]],
        *,
        timeout: float = SOURCE_TIMEOUT,
    ) -> dict[str, str]:
        selected = [row.copy() for row in rows if row['id'] in expected]
        if not selected:
            return {}
        if len(selected) > 4:
            raise ValueError('Source verification is bounded to four tracks')
        if not self._slot.acquire(blocking=False):
            return dict.fromkeys(expected, 'source_busy')
        done = threading.Event()
        result = {}

        def work() -> None:
            try:
                result.update(self._verify(selected, context, expected))
            except Exception:
                # Resolver failures are private; do not leak paths or threads.
                result.update(dict.fromkeys(expected, 'source_unavailable'))
            finally:
                self._slot.release()
                done.set()

        worker = threading.Thread(
            target=work, name='local-dj-source-check', daemon=True
        )
        try:
            worker.start()
        except RuntimeError:
            self._slot.release()
            return dict.fromkeys(expected, 'source_unavailable')
        if not done.wait(timeout):
            # The I/O cannot be cancelled safely. Keep its slot until it exits.
            return dict.fromkeys(expected, 'source_timeout')
        return result


guard = SourceGuard()


def attest(result: dict[str, Any], checks: dict[str, str]) -> dict[str, Any]:
    from .local_plans import digest

    tracks = []
    for item in result['tracks']:
        validity = checks.get(item['id'], 'cached_only')
        public = item
        if item['status'] == 'ready' and validity != 'source_verified':
            if validity == 'cached_only':
                validity = 'source_unavailable'
            public = {key: item[key] for key in ('index', 'id', 'revision')}
            public['status'] = 'stale'
        tracks.append({**public, 'validity': validity})
    plans = []
    for item in result['plans']:
        public = item
        reasons = [
            tracks[index]['validity']
            for index in (item['from_index'], item['to_index'])
        ]
        failure = next(
            (
                value
                for value in reasons
                if value not in {'source_verified', 'cached_only'}
            ),
            None,
        )
        if failure is not None:
            public = {
                'from_index': item['from_index'],
                'to_index': item['to_index'],
                'state': 'unavailable',
                'aligned': False,
                'reason': failure,
            }
        plans.append(public)
    value = {**result, 'tracks': tracks, 'plans': plans}
    return {**value, 'revision': digest(value)}
