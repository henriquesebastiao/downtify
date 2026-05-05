"""YouTube Music search/match helpers, the audio source for downloads."""

from __future__ import annotations

import json
import re
from threading import Lock
from typing import Any, Optional

from loguru import logger
from ytmusicapi import YTMusic

from .telemetry import json_log_blob, redact_sensitive_mapping


def _log_ytm_response(label: str, payload: Any) -> None:
    """Full YT Music payloads (truncated); enable DEBUG level to inspect."""

    logger.debug(
        'YouTube Music response {} {} chars: {}',
        label,
        len(json.dumps(payload, default=str)),
        json_log_blob(redact_sensitive_mapping(payload)),
    )


def _log_ytm_summary_search(
    *,
    phase: str,
    query: str,
    filt: str,
    results_len: int,
    first_titles: list[str],
) -> None:
    logger.info(
        'YouTube Music search [{}] filter={!r} q={!r} hits={} first_titles={}',
        phase,
        filt,
        query[:120],
        results_len,
        first_titles,
    )


_client: Optional[YTMusic] = None
_lock = Lock()
# Parsed ``get_album`` payload per browse id — avoids N identical API calls when
# downloading every track off the same LP.
_album_track_cache: dict[
    str,
    tuple[list[dict[str, Any]], Optional[int]],
] = {}
# ``artist|album`` (case-folded hints) → album ``browseId`` from a songs filter.
_album_browse_search_cache: dict[str, str] = {}


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
    year_str = str(result.get('year') or '').strip()
    release_date = (
        year_str if len(year_str) == 4 and year_str.isdigit() else ''
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
        'year': year_str,
        'release_date': release_date,
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
    titles = [
        str(r.get('title') or '')[:60]
        for r in results[:8]
        if isinstance(r, dict)
    ]
    _log_ytm_summary_search(
        phase='browse',
        query=query,
        filt='songs',
        results_len=len(results),
        first_titles=titles,
    )
    _log_ytm_response(f'search songs q={query[:80]!r}', results)
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
    _log_ytm_summary_search(
        phase='match_songs',
        query=query,
        filt='songs',
        results_len=len(results),
        first_titles=[
            str(r.get('title') or '')[:60]
            for r in results[:8]
            if isinstance(r, dict)
        ],
    )
    _log_ytm_response(f'find_match songs q={query[:80]!r}', results)
    if not results:
        try:
            results = _ytm().search(query, filter='videos', limit=10)
        except Exception:
            results = []
        _log_ytm_summary_search(
            phase='match_videos_fallback',
            query=query,
            filt='videos',
            results_len=len(results),
            first_titles=[
                str(r.get('title') or '')[:60]
                for r in results[:8]
                if isinstance(r, dict)
            ],
        )
        _log_ytm_response(f'find_match videos q={query[:80]!r}', results)
    best = _pick_best(results, duration, title, artists)
    if best is not None:
        logger.info(
            'YouTube Music find_match picked videoId={} title={!r} year={!r}',
            best.get('videoId'),
            best.get('title'),
            best.get('year'),
        )
        _log_ytm_response('find_match chosen row', best)
        return best.get('videoId'), best
    for result in results:
        if result.get('videoId'):
            logger.info(
                'YouTube Music find_match fallback first videoId={} title={!r}',
                result.get('videoId'),
                result.get('title'),
            )
            _log_ytm_response('find_match fallback row', result)
            return result['videoId'], result
    logger.info(
        'YouTube Music find_match: no result for query={!r}',
        query[:160],
    )
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
    _log_ytm_response(
        f'find_match_for_video vid={video_id} q={query[:80]!r}', results
    )
    for result in results:
        if result.get('videoId') == video_id:
            logger.info(
                'YouTube Music find_match_for_video hit video={} title={!r}',
                video_id,
                result.get('title'),
            )
            _log_ytm_response(f'YT match row video={video_id}', result)
            return result
    logger.info(
        'YouTube Music find_match_for_video: no hit for {} in {} results',
        video_id,
        len(results),
    )
    return None


def _norm_compact_title(value: Any) -> str:
    """Lowercase collapsed title for forgiving comparisons."""

    return re.sub(r'\s+', ' ', str(value or '').casefold()).strip()


def _album_title_hints(
    match: dict[str, Any], song: Optional[dict[str, Any]]
) -> list[str]:
    hints: list[str] = []
    album = match.get('album')
    if isinstance(album, dict):
        n = str(album.get('name') or '').strip()
        if n:
            hints.append(n)
    if song:
        n = str(song.get('album_name') or '').strip()
        if n not in hints:
            hints.append(n)
    # de-dupe while keeping order
    seen: set[str] = set()
    out: list[str] = []
    for h in hints:
        k = h.casefold()
        if k not in seen:
            seen.add(k)
            out.append(h)
    return out


def _primary_artist_for_search(
    match: dict[str, Any], song: Optional[dict[str, Any]]
) -> str:
    if song:
        artists = song.get('artists') or []
        if isinstance(artists, list) and artists:
            a0 = artists[0]
            if isinstance(a0, str) and a0.strip():
                return a0.strip()
    for a in match.get('artists') or []:
        if isinstance(a, dict):
            nm = str(a.get('name') or '').strip()
            if nm:
                return nm
    return ''


def _album_browse_id_from_search(
    match: dict[str, Any],
    song: Optional[dict[str, Any]],
) -> str:
    titles = _album_title_hints(match, song)
    if not titles:
        return ''
    primary = _primary_artist_for_search(match, song)
    cache_key = f'{primary.casefold()}|{_norm_compact_title(titles[0])}'
    with _lock:
        cached = _album_browse_search_cache.get(cache_key)
    if cached:
        return cached
    q_chunks = []
    if primary:
        q_chunks.append(primary)
    q_chunks.extend(titles)
    query = ' '.join(q_chunks).strip()
    try:
        results = _ytm().search(query, filter='albums', limit=20)
    except Exception:
        logger.opt(exception=True).debug(
            'YouTube Music album search failed',
        )
        return ''
    titles = [
        str(r.get('title') or '')[:60]
        for r in results[:10]
        if isinstance(r, dict)
    ]
    logger.info(
        'YouTube Music album search title_match q={!r} hits={} sample_titles={}',
        query[:120],
        len(results),
        titles,
    )
    _log_ytm_response(f'albums search titles={titles!r}', results)
    want = {_norm_compact_title(t) for t in titles if t.strip()}
    for r in results:
        if not isinstance(r, dict):
            continue
        browse = r.get('browseId')
        if not isinstance(browse, str) or not browse.strip():
            continue
        rt = _norm_compact_title(r.get('title'))
        if rt and rt in want:
            bid = browse.strip()
            with _lock:
                _album_browse_search_cache[cache_key] = bid
            return bid
    return ''


def _album_browse_id(
    match: dict[str, Any],
    song: Optional[dict[str, Any]],
) -> str:
    album = match.get('album')
    if isinstance(album, dict):
        for key in ('id', 'browseId'):
            raw = album.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
    return _album_browse_id_from_search(match, song)


def _row_video_id(row: dict[str, Any]) -> Optional[str]:
    vid = row.get('videoId')
    if isinstance(vid, str) and len(vid.strip()) >= 11:
        return vid.strip()
    return None


def _pick_album_track_row(
    tracks: list[dict[str, Any]],
    video_id: str,
    match: dict[str, Any],
    song: Optional[dict[str, Any]],
) -> tuple[Optional[int], Optional[dict[str, Any]]]:
    """Return ``(list_position 1-based, row)`` for the downloaded video."""

    for position, row in enumerate(tracks, start=1):
        if isinstance(row, dict) and _row_video_id(row) == video_id:
            return position, row
    name_norms: set[str] = {
        _norm_compact_title(match.get('title')),
        _norm_compact_title((song or {}).get('name') if song else ''),
    }
    name_norms.discard('')
    if not name_norms:
        return None, None
    hits = [
        (position, row)
        for position, row in enumerate(tracks, start=1)
        if isinstance(row, dict)
        and _norm_compact_title(row.get('title')) in name_norms
    ]
    if len(hits) == 1:
        return hits[0][0], hits[0][1]
    return None, None


def _normalize_ytm_track_slot(
    *,
    declared: Any,
    position_in_album_list: int,
) -> Optional[int]:
    """Return a 1-based track index for tagging.

    ytmusicapi copies ``trackNumber`` from YouTube's payload (sometimes
    1-based). When it is absent or ``<= 0``, use ordinal position in the
    album's track listing instead.
    """
    if position_in_album_list <= 0:
        return None
    try:
        n = int(declared)
    except (TypeError, ValueError):
        return position_in_album_list
    if n <= 0:
        return position_in_album_list
    return n


def _cached_album_tracks_and_count(
    browse_id: str,
) -> tuple[list[dict[str, Any]], Optional[int]]:
    with _lock:
        hit = _album_track_cache.get(browse_id)
    if hit is not None:
        return hit
    try:
        data = _ytm().get_album(browse_id) or {}
    except Exception:
        logger.opt(exception=True).debug(
            'YouTube Music get_album failed for {}', browse_id
        )
        empty: tuple[list[dict[str, Any]], Optional[int]] = ([], None)
        return empty

    tracks = [t for t in (data.get('tracks') or []) if isinstance(t, dict)]
    logger.info(
        'YouTube Music get_album browseId={!r} title={!r} year={!r} '
        'trackCount={} parsed_tracks_len={}',
        browse_id,
        data.get('title'),
        data.get('year'),
        data.get('trackCount'),
        len(tracks),
    )
    _log_ytm_response(f'get_album {browse_id}', data)
    total_ct: Optional[int] = None
    raw_tc = data.get('trackCount')
    try:
        if raw_tc is not None:
            iv = int(raw_tc)
            if iv > 0:
                total_ct = iv
    except (TypeError, ValueError):
        total_ct = None
    if not total_ct and tracks:
        total_ct = len(tracks)
    tup = (tracks, total_ct)
    with _lock:
        _album_track_cache[browse_id] = tup
    return tup


def youtube_music_track_index_for_match(
    match: Optional[dict[str, Any]],
    song: Optional[dict[str, Any]] = None,
) -> tuple[Optional[int], Optional[int]]:
    """Resolve ``(track_number, album_track_total)`` from YouTube Music.

    Uses ``album.id`` on the search hit when present; otherwise resolves the
    release via an ``albums`` search so ``get_album`` can run anyway.
    """

    if not isinstance(match, dict):
        logger.debug('YTM track_index: match is not a dict')
        return None, None
    video_id = match.get('videoId')
    if not isinstance(video_id, str) or not video_id.strip():
        logger.info(
            'YTM track_index: missing videoId on match title={!r}',
            match.get('title'),
        )
        return None, None
    vid = video_id.strip()
    browse_id = _album_browse_id(match, song)
    if not browse_id:
        logger.info(
            'YTM track_index: cannot resolve album browseId for '
            'video={!r} spotify_title={!r} match_album={!r} '
            'spotify_album_name={!r}',
            vid,
            match.get('title'),
            match.get('album'),
            (song or {}).get('album_name'),
        )
        return None, None
    tracks, total_ct = _cached_album_tracks_and_count(browse_id)
    if not tracks:
        logger.info(
            'YTM track_index: get_album returned zero tracks browseId={!r} '
            'declared_trackCount={}',
            browse_id,
            total_ct,
        )
        return None, total_ct

    fb_total = total_ct if (total_ct and total_ct > 0) else len(tracks)
    position, row = _pick_album_track_row(tracks, vid, match, song)
    if row is None or position is None:
        sample = [_row_video_id(t) or '?' for t in tracks[:6]]
        mtitle = _norm_compact_title(match.get('title'))
        title_matches = sum(
            1
            for t in tracks
            if isinstance(t, dict)
            and _norm_compact_title(t.get('title')) == mtitle
        )
        logger.info(
            'YTM track_index: video {!r} not matched in album {}; '
            'match_title={!r} candidate_videoIds(sample)={} '
            'same_title_row_count={}',
            vid,
            browse_id,
            match.get('title'),
            sample,
            title_matches,
        )
        return None, fb_total
    tn = _normalize_ytm_track_slot(
        declared=row.get('trackNumber'),
        position_in_album_list=position,
    )
    logger.debug(
        'YTM track_index OK video={} browseId={} tn={} total={}',
        vid,
        browse_id,
        tn,
        fb_total,
    )
    return tn, fb_total


def enrich_from_match(
    song: dict[str, Any], match: Optional[dict[str, Any]]
) -> dict[str, Any]:
    """Fill metadata gaps from YT Music hit; resolve track index via get_album."""

    if not match:
        return song
    _log_ytm_response(
        f'enrich_from_match spotify_title={song.get("name")!r}',
        match,
    )
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
    if not enriched.get('release_date'):
        y = str(enriched.get('year') or '').strip()
        if len(y) == 4 and y.isdigit():
            enriched['release_date'] = y
    if not enriched.get('artists'):
        yt_meta = _result_to_song(match)
        if yt_meta and yt_meta.get('artists'):
            enriched['artists'] = yt_meta['artists']
            enriched['artist'] = ', '.join(yt_meta['artists'])
    yt_n, yt_tot = youtube_music_track_index_for_match(match, enriched)
    if yt_n is not None:
        enriched.setdefault('track_number', yt_n)
    if yt_tot is not None:
        enriched.setdefault('album_track_total', yt_tot)
    spotify_tid = enriched.get('song_id')
    if yt_n is None:
        logger.info(
            'YTM enrich: no track_number resolved for Spotify id={} title={!r}',
            spotify_tid,
            enriched.get('name'),
        )
    yr_ok = bool(str(enriched.get('year') or '').strip()) or bool(
        str(enriched.get('release_date') or '').strip()
    )
    match_yr = match.get('year')
    if not yr_ok:
        logger.info(
            'YTM enrich: still no year after match for title={!r} '
            'match.year={!r}',
            enriched.get('name'),
            match_yr,
        )
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
    _log_ytm_response(f'get_song {video_id}', info or {})
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
        'release_date': '',
        'source': 'youtube',
    }
