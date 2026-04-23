"""YouTube Music search/match helpers, the audio source for downloads."""

from __future__ import annotations

import logging
import re
from threading import Lock
from typing import Any, Optional

from ytmusicapi import YTMusic

logger = logging.getLogger(__name__)

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


def find_match(song: dict[str, Any]) -> Optional[str]:
    """Return the YouTube Music ``videoId`` that best matches ``song``."""

    artists = ' '.join(song.get('artists') or [])
    title = song.get('name', '')
    query = f'{artists} {title}'.strip()
    if not query:
        return None
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
    best = _pick_best(results, duration)
    if best:
        return best
    for result in results:
        if result.get('videoId'):
            return result['videoId']
    return None


def _pick_best(
    results: list[dict[str, Any]], target_duration: int
) -> Optional[str]:
    best_id: Optional[str] = None
    best_score: float = float('inf')
    for result in results:
        video_id = result.get('videoId')
        if not video_id:
            continue
        candidate_duration = result.get('duration_seconds') or _parse_duration(
            result.get('duration')
        )
        if target_duration and candidate_duration:
            score = abs(candidate_duration - target_duration)
        else:
            score = 5
        if score < best_score:
            best_score = score
            best_id = video_id
    return best_id


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
