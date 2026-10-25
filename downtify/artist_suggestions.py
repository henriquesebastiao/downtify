"""Local, personal suggestions for the existing artist monitor."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import urlsplit

from .discover import LISTEN_HALF_LIFE_DAYS, artist_key


def artist_suggestions(
    library: Iterable[dict[str, Any]],
    listens: Iterable[dict[str, Any]],
    watches: Iterable[Any],
    *,
    listening_offset: int = 0,
    library_offset: int = 0,
    limit: int = 20,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Rank existing signals; never resolve artists or scan audio files.

    Listening counts are lifetime aggregates weighted by last activity,
    not a reconstructed time-window history. Callers must scope all three
    inputs to the requesting user before entering this function.
    """
    now = now or datetime.now(timezone.utc)
    watched = {artist_key(w.name) for w in watches if w.kind == 'artist'}
    watched.update(
        artist_key(n)
        for n in ('Various Artists', 'Various Artist', 'Artistes divers')
    )
    by_name: dict[str, dict[str, Any]] = {}
    for row in library:
        name = str(row.get('name') or '').strip()
        key = artist_key(name)
        if not key or key in watched:
            continue
        bucket = by_name.setdefault(
            key, {'name': name, 'track_count': 0, 'album_count': 0}
        )
        bucket['track_count'] += int(row.get('track_count') or 0)
        bucket['album_count'] += int(row.get('album_count') or 0)
    library_rows = sorted(
        (r for r in by_name.values() if r['track_count'] > 0),
        key=lambda r: (
            -r['track_count'],
            -r['album_count'],
            r['name'].casefold(),
        ),
    )
    listening: dict[str, dict[str, Any]] = {}
    for row in listens:
        name = str(row.get('name') or '').strip()
        key = artist_key(name)
        plays = max(0, int(row.get('plays') or 0))
        if not key or key in watched or not plays:
            continue
        try:
            last = datetime.fromisoformat(str(row.get('last_played')))
            last = (
                last.replace(tzinfo=timezone.utc)
                if last.tzinfo is None
                else last
            )
        except (TypeError, ValueError):
            continue
        last = last.astimezone(timezone.utc)
        age = max(0, (now - last).total_seconds() / 86400)
        bucket = listening.setdefault(
            key,
            {
                **by_name.get(
                    key, {'name': name, 'track_count': 0, 'album_count': 0}
                ),
                'plays': 0,
                'score': 0.0,
                'last_played': last.isoformat(),
            },
        )
        bucket['plays'] += plays
        bucket['score'] += plays * 0.5 ** (age / LISTEN_HALF_LIFE_DAYS)
        bucket['last_played'] = max(
            bucket['last_played'], last.astimezone(timezone.utc).isoformat()
        )
    listening_rows = sorted(
        listening.values(), key=lambda r: (-r['score'], r['name'].casefold())
    )

    def page(rows: list[dict[str, Any]], offset: int) -> dict[str, Any]:
        end = offset + limit
        return {
            'items': rows[offset:end],
            'total': len(rows),
            'next_offset': end if end < len(rows) else None,
        }

    return {
        'listening': page(listening_rows, listening_offset),
        'library': page(library_rows, library_offset),
        'half_life_days': LISTEN_HALF_LIFE_DAYS,
    }


def _artist_image(row: dict[str, Any]) -> str:
    value = str(row.get('image_url') or row.get('cover_url') or '')
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ''
        allowed = host in {
            'i.scdn.co',
            'yt3.ggpht.com',
            'yt3.googleusercontent.com',
            'lh3.googleusercontent.com',
        } or host.endswith('.spotifycdn.com')
        if (
            parsed.scheme == 'https'
            and allowed
            and not parsed.username
            and not parsed.password
            and parsed.port in {None, 443}
        ):
            return value
    except ValueError:
        pass
    return ''


def artist_candidates(
    name: str, results: list[dict[str, Any]], *, source: str = 'youtube-music'
) -> dict[str, Any]:
    """Only a unique exact-name result can prefill the native form.

    A homonym remains an explicit choice, even when the provider ranked
    one candidate first. Channel URLs are constructed from validated IDs.
    """
    candidates: dict[str, dict[str, str]] = {}
    for row in results:
        channel = str(row.get('artist_id') or '')
        pattern = (
            r'[A-Za-z0-9]{22}'
            if source == 'spotify'
            else r'UC[A-Za-z0-9_-]{22}'
        )
        if not re.fullmatch(pattern, channel):
            continue
        candidates[channel] = {
            'name': str(row.get('name') or '').strip(),
            'url': f'https://open.spotify.com/artist/{channel}'
            if source == 'spotify'
            else f'https://music.youtube.com/channel/{channel}',
            'artist_id': channel,
            'source': 'spotify' if source == 'spotify' else 'youtube_music',
            'image_url': _artist_image(row),
        }
    exact = [
        r
        for r in candidates.values()
        if r['name'].casefold() == name.strip().casefold()
    ]
    return {
        'candidates': list(candidates.values()),
        'url': exact[0]['url'] if len(exact) == 1 else None,
    }
