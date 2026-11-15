"""Navigate published audio without asking a finished renderer to edit its plan."""

from __future__ import annotations

import math
import re
from datetime import datetime


def available(cache, identity, origin, target):
    workspace = cache / identity
    manifest = workspace / 'index.m3u8'
    if (
        cache.is_symlink()
        or workspace.is_symlink()
        or manifest.is_symlink()
        or not manifest.is_file()
        or not manifest.resolve().is_relative_to(cache.resolve())
        or manifest.stat().st_size > 32768
    ):
        return False
    cursor, duration, found = None, None, False
    try:
        for line in manifest.read_text(encoding='utf-8').splitlines():
            if 'URI=' in line:
                return False
            if line.startswith('#EXT-X-PROGRAM-DATE-TIME:'):
                cursor = (
                    datetime.fromisoformat(
                        line.split(':', 1)[1].replace('Z', '+00:00')
                    ).timestamp()
                    - origin
                )
            elif line.startswith('#EXTINF:'):
                duration = float(line.split(':', 1)[1].split(',')[0])
            elif line and not line.startswith('#'):
                if not re.fullmatch(r'segment-[0-9]{8}\.ts', line):
                    return False
                if (
                    cursor is None
                    or duration is None
                    or not math.isfinite(duration)
                    or duration <= 0
                ):
                    return False
                segment = workspace / line
                if cursor - 0.001 <= target < cursor + duration - 0.001:
                    found = segment.is_file() and not segment.is_symlink()
                cursor += duration
                duration = None
    except (OSError, ValueError, OverflowError):
        return False
    return found


def navigation(session, action, payload, cache):
    """None delegates a future Next to the live renderer; a dict is a final receipt."""
    if action not in {'next', 'previous'} or not payload:
        return None
    if set(payload) != {'position'}:
        raise ValueError('Invalid navigation payload')
    try:
        position = float(payload['position'])
    except (TypeError, ValueError):
        raise ValueError('Invalid playback position') from None
    if not math.isfinite(position) or not 0 <= position <= 1_000_000:
        raise ValueError('Invalid playback position')
    if session['state'] not in {'playing', 'paused', 'ready'}:
        raise RuntimeError('DJ stream is not available')
    rows = session.get('timeline', [])
    index = next(
        (
            i
            for i, row in enumerate(rows)
            if row['start'] <= position < row['end']
        ),
        -1,
    )
    target = None
    if index >= 0:

        def start(ordinal):
            return max(
                rows[ordinal]['start'],
                rows[ordinal - 1]['end'] if ordinal else 0,
            )

        ordinal = (
            index + 1
            if action == 'next'
            else (index if position - start(index) > 3 else max(0, index - 1))
        )
        if ordinal < len(rows):
            target = start(ordinal)
    if target is not None and available(
        cache, session['id'], session.get('media_origin', 0), target
    ):
        return {
            'accepted': True,
            'seek_to_seconds': target,
            'effective_after_seconds': 0.0,
        }
    if action == 'next' and session['state'] != 'ready':
        return None
    return {
        'accepted': False,
        'reason': 'Ce repère n’est plus disponible dans la fenêtre du mix.'
        if target is not None
        else 'Aucun titre suivant n’est disponible dans ce mix.',
    }
