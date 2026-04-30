"""YouTube Music search/match helpers, the audio source for downloads."""

from __future__ import annotations

import re
from threading import Lock
from typing import Any, Optional

from loguru import logger
from ytmusicapi import YTMusic

_client: Optional[YTMusic] = None
_lock = Lock()


def _ytm() -> YTMusic:
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = YTMusic()
    return _client


def _upgrade_thumbnail(url: str) -> str:
    """Replace the size suffix on a YT thumbnail with a larger one."""

    if not url:
        return url
    return re.sub(r'=w\d+-h\d+.*$', '=w600-h600-l90-rj', url)


def _parse_duration(value: Any) -> int:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return 0
    parts = value.split(':')
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return 0
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return 0


def _result_to_song(result: dict[str, Any]) -> Optional[dict[str, Any]]:
    video_id = result.get('videoId')
    if not video_id:
        return None
    artists = [
        a.get('name', '')
        for a in (result.get('artists') or [])
        if isinstance(a, dict) and a.get('name')
    ]
    thumbs = result.get('thumbnails') or []
    cover = thumbs[-1].get('url', '') if thumbs else ''
    cover = _upgrade_thumbnail(cover)
    album = result.get('album') or {}
    album_name = album.get('name', '') if isinstance(album, dict) else ''
    duration = result.get('duration_seconds') or _parse_duration(
        result.get('duration')
    )
    return {
        'song_id': video_id,
        'name': result.get('title', ''),
        'artists': artists,
        'album_name': album_name,
        'cover_url': cover,
        'duration': duration,
        'url': f'https://music.youtube.com/watch?v={video_id}',
        'explicit': bool(result.get('isExplicit')),
        'year': str(result.get('year') or ''),
        'source': 'youtube',
    }


def search_songs(query: str, limit: int = 20) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    try:
        results = _ytm().search(query, filter='songs', limit=limit)
    except Exception:
        logger.exception('YouTube Music search failed')
        return []
    songs: list[dict[str, Any]] = []
    for result in results:
        song = _result_to_song(result)
        if song:
            songs.append(song)
    return songs


def find_match(
    song: dict[str, Any],
) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    """Return ``(videoId, full_result)`` that best matches ``song``.

    The full result is the raw ytmusicapi search hit and is useful for
    enrichment (album name, fallback cover, etc.). Either element may be
    ``None`` if no acceptable match is found.
    """

    artists = song.get('artists') or []
    artists_q = ' '.join(artists)
    title = song.get('name', '')
    query = f'{artists_q} {title}'.strip()
    if not query:
        return None, None
    duration = song.get('duration') or 0
    try:
        results = _ytm().search(query, filter='songs', limit=10)
    except Exception:
        logger.exception('YouTube Music match search failed')
        results = []
    if not results:
        try:
            results = _ytm().search(query, filter='videos', limit=10)
        except Exception:
            results = []
    best = _pick_best(results, duration, title, artists)
    if best is not None:
        return best.get('videoId'), best
    for result in results:
        if result.get('videoId'):
            return result['videoId'], result
    return None, None


def find_match_for_video(
    song: dict[str, Any], video_id: str
) -> Optional[dict[str, Any]]:
    """Find the ytmusicapi search result that matches a known videoId.

    Used when the caller already has a target video and wants to enrich
    metadata without risking switching to a different track.
    """

    artists = ' '.join(song.get('artists') or [])
    title = song.get('name', '')
    query = f'{artists} {title}'.strip()
    if not query:
        return None
    try:
        results = _ytm().search(query, filter='songs', limit=10)
    except Exception:
        logger.opt(exception=True).debug('match-by-video search failed')
        return None
    for result in results:
        if result.get('videoId') == video_id:
            return result
    return None


def enrich_from_match(
    song: dict[str, Any], match: Optional[dict[str, Any]]
) -> dict[str, Any]:
    """Fill in metadata gaps from a ytmusicapi match. Existing values win."""

    if not match:
        return song
    enriched = dict(song)
    if not enriched.get('album_name'):
        album = match.get('album') or {}
        if isinstance(album, dict) and album.get('name'):
            enriched['album_name'] = album['name']
    if not enriched.get('cover_url'):
        thumbs = match.get('thumbnails') or []
        if thumbs:
            enriched['cover_url'] = _upgrade_thumbnail(
                thumbs[-1].get('url', '')
            )
    if not enriched.get('year') and match.get('year'):
        enriched['year'] = str(match['year'])
    return enriched


_NEGATIVE_KEYWORDS = (
    'karaoke',
    'instrumental',
    'cover ',
    'cover)',
    'tribute',
    'guitar lesson',
    'sped up',
    'slowed',
    'reverb',
    'nightcore',
    '8d audio',
    '1 hour',
    'bass boosted',
)


def _pick_best(
    results: list[dict[str, Any]],
    target_duration: int,
    target_title: str = '',
    target_artists: Optional[list[str]] = None,
) -> Optional[dict[str, Any]]:
    target_title_l = (target_title or '').lower()
    target_artist_set = {
        (a or '').lower() for a in (target_artists or []) if a
    }

    best: Optional[dict[str, Any]] = None
    best_score: float = float('inf')
    for result in results:
        if not result.get('videoId'):
            continue

        candidate_title = (result.get('title') or '').lower()
        # Skip results that add a "karaoke"/"instrumental"/etc. modifier
        # which the source song does not have. Catches the most common
        # source of wrong-audio matches.
        if any(
            kw in candidate_title and kw not in target_title_l
            for kw in _NEGATIVE_KEYWORDS
        ):
            continue

        candidate_duration = result.get('duration_seconds') or _parse_duration(
            result.get('duration')
        )
        if target_duration and candidate_duration:
            score = abs(candidate_duration - target_duration)
        else:
            score = 5

        # Reward results whose artist list overlaps the source artists.
        candidate_artists = {
            (a.get('name') or '').lower()
            for a in (result.get('artists') or [])
            if isinstance(a, dict)
        }
        if target_artist_set and not (target_artist_set & candidate_artists):
            score += 30  # heavy penalty for wrong artist

        # Reward exact title matches over loosely-related ones.
        if candidate_title and target_title_l:
            if candidate_title.split('(')[0].strip() == (
                target_title_l.split('(')[0].strip()
            ):
                score -= 2

        if score < best_score:
            best_score = score
            best = result
    return best


def song_from_video_id(video_id: str) -> dict[str, Any]:
    """Look up basic song info for a YouTube videoId via YT Music."""

    try:
        info = _ytm().get_song(video_id)
    except Exception:
        logger.exception('YouTube Music get_song failed')
        info = {}
    details = (info or {}).get('videoDetails') or {}
    thumbnails = (details.get('thumbnail') or {}).get('thumbnails') or []
    cover = thumbnails[-1].get('url', '') if thumbnails else ''
    duration = 0
    try:
        duration = int(details.get('lengthSeconds') or 0)
    except (TypeError, ValueError):
        duration = 0
    author = details.get('author', '')
    artists = [author] if author else []
    return {
        'song_id': video_id,
        'name': details.get('title', ''),
        'artists': artists,
        'album_name': '',
        'cover_url': cover,
        'duration': duration,
        'url': f'https://music.youtube.com/watch?v={video_id}',
        'explicit': False,
        'year': '',
        'source': 'youtube',
    }
