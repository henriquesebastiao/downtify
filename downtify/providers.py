"""YouTube Music search/match helpers, the audio source for downloads."""

from __future__ import annotations

import json
import re
from threading import Lock
from typing import Any, Optional

from loguru import logger
from ytmusicapi import YTMusic
from ytmusicapi.continuations import (
    get_continuations,
    get_reloadable_continuation_params,
)
from ytmusicapi.navigation import (
    CONTENT,
    GRID,
    GRID_ITEMS,
    HEADER_SIDE,
    MULTI_SELECT,
    SECTION,
    SECTION_LIST_CONTINUATION,
    SECTION_LIST_ITEM,
    SINGLE_COLUMN_TAB,
    TITLE_TEXT,
    nav,
)
from ytmusicapi.parsers.library import parse_albums as _parse_ytm_albums

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
# Album-level metadata (title/year/thumbnails) per browse id, populated
# alongside ``_album_track_cache`` from the same ``get_album`` call.
_album_meta_cache: dict[str, dict[str, Any]] = {}
# ``artist|album`` (case-folded hints) → album ``browseId`` from a songs filter.
_album_browse_search_cache: dict[str, str] = {}
# Artist names per album browse id, captured from an albums-filter search
# result (``search_albums``) — used as a fallback for the album artist tag
# when the later ``get_album`` call for the same browse id doesn't itself
# return an ``artists`` field.
_album_search_artist_cache: dict[str, list[str]] = {}


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
    artists = _extract_title_featuring_artist(result.get('title', ''), artists)
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


def _album_summary(result: dict[str, Any]) -> Optional[dict[str, Any]]:
    browse_id = result.get('browseId')
    if not isinstance(browse_id, str) or not browse_id.strip():
        return None
    artists = [
        a.get('name', '')
        for a in (result.get('artists') or [])
        if isinstance(a, dict) and a.get('name')
    ]
    if artists:
        with _lock:
            _album_search_artist_cache[browse_id.strip()] = artists
    thumbs = result.get('thumbnails') or []
    cover = _upgrade_thumbnail(thumbs[-1].get('url', '')) if thumbs else ''
    return {
        'album_id': browse_id.strip(),
        'name': result.get('title', ''),
        'artists': artists,
        'artist': ', '.join(artists),
        'cover_url': cover,
        'year': str(result.get('year') or '').strip(),
        'explicit': bool(result.get('isExplicit')),
        'url': f'https://music.youtube.com/browse/{browse_id.strip()}',
        'source': 'youtube',
        # YouTube Music's own release-type classification: 'Album',
        # 'Single', or 'EP'. Not every release is actually an "album" —
        # surface it as-is so callers (UI badge, audio tags) don't have
        # to guess.
        'release_type': result.get('type') or '',
    }


def search_albums(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search YouTube Music for albums matching ``query``.

    Returns lightweight album summaries (not full tracklists) suitable
    for a search-results list; resolve a chosen album's tracks via
    :func:`album_tracks_from_browse_id`.
    """

    if not query.strip():
        return []
    try:
        results = _ytm().search(query, filter='albums', limit=limit)
    except Exception:
        logger.exception('YouTube Music album search failed')
        return []
    titles = [
        str(r.get('title') or '')[:60]
        for r in results[:8]
        if isinstance(r, dict)
    ]
    _log_ytm_summary_search(
        phase='browse_albums',
        query=query,
        filt='albums',
        results_len=len(results),
        first_titles=titles,
    )
    _log_ytm_response(f'search albums q={query[:80]!r}', results)
    albums: list[dict[str, Any]] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        album = _album_summary(result)
        if album:
            albums.append(album)
    return albums


def _artist_summary(result: dict[str, Any]) -> Optional[dict[str, Any]]:
    channel_id = result.get('browseId')
    if not isinstance(channel_id, str) or not channel_id.strip():
        return None
    thumbs = result.get('thumbnails') or []
    cover = _upgrade_thumbnail(thumbs[-1].get('url', '')) if thumbs else ''
    return {
        'artist_id': channel_id.strip(),
        'name': result.get('artist') or '',
        'cover_url': cover,
        'url': f'https://music.youtube.com/channel/{channel_id.strip()}',
        'source': 'youtube',
    }


def search_artists(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search YouTube Music for artists matching ``query``.

    Returns lightweight artist summaries; resolve a chosen artist's full
    discography (every album and single, each with its full tracklist)
    via :func:`artist_discography_from_channel_id`.
    """

    if not query.strip():
        return []
    try:
        results = _ytm().search(query, filter='artists', limit=limit)
    except Exception:
        logger.exception('YouTube Music artist search failed')
        return []
    titles = [
        str(r.get('artist') or '')[:60]
        for r in results[:8]
        if isinstance(r, dict)
    ]
    _log_ytm_summary_search(
        phase='browse_artists',
        query=query,
        filt='artists',
        results_len=len(results),
        first_titles=titles,
    )
    _log_ytm_response(f'search artists q={query[:80]!r}', results)
    artists: list[dict[str, Any]] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        artist = _artist_summary(result)
        if artist:
            artists.append(artist)
    return artists


def _artist_discography_browse_id(channel_id: str) -> str:
    """BrowseId for an artist's full "See all" albums/singles grid page.

    Distinct from the artist's own channelId. YouTube Music's "More"
    button on an artist's Albums/Singles shelf links to this same id
    (``MPAD`` + channelId) — visible directly in the button's own
    navigation endpoint, and in the URL if you click it yourself:
    ``https://music.youtube.com/browse/MPAD<channelId>``.
    """
    return f'MPAD{channel_id}'


def _fetch_full_artist_section(
    channel_id: str, params: str
) -> list[dict[str, Any]]:
    """Fetch every entry of an artist's 'albums' or 'singles' shelf.

    ytmusicapi's own ``get_artist_albums(channelId, params)`` sends the
    artist's own channelId as the browseId, which returns the *artist's
    home page* again (a channel can have several other carousels besides
    Albums/Singles, e.g. "Top songs") instead of the dedicated
    discography grid — its navigation code then assumes the first
    section of that response is the grid it wants, finds an unrelated
    shelf instead, and raises a KeyError. Upstream closed this as "not
    planned": https://github.com/sigma67/ytmusicapi/issues/595. This
    requests the correct discography browseId directly instead (see
    ``_artist_discography_browse_id``), reusing ytmusicapi's own
    lower-level request/parse/continuation helpers.
    """
    body = {
        'browseId': _artist_discography_browse_id(channel_id),
        'params': params,
    }
    ytm = _ytm()
    response = ytm._send_request('browse', body)
    results = nav(response, SINGLE_COLUMN_TAB + SECTION_LIST_ITEM)
    contents = nav(results, GRID_ITEMS, True) or []
    albums = _parse_ytm_albums(contents)
    grid = nav(results, GRID, True) or {}
    if 'continuations' in grid:

        def _request_more(additional_params: Any) -> Any:
            return ytm._send_request('browse', body, additional_params)

        albums.extend(
            get_continuations(
                grid,
                'gridContinuation',
                None,
                _request_more,
                _parse_ytm_albums,
            )
        )
    return albums


def _artist_albums_full_list(
    channel_id: str, section: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return every entry of an artist page's 'albums'/'singles' section.

    The section as returned by ``get_artist`` only ever holds a short
    preview (~10 entries); the ``params`` continuation token it carries
    is used to fetch the complete list from the artist's discography
    browse page (see ``_fetch_full_artist_section``).
    """

    results = [
        r for r in (section.get('results') or []) if isinstance(r, dict)
    ]
    params = section.get('params')
    if not params:
        return results
    try:
        full = _fetch_full_artist_section(channel_id, params)
    except Exception:
        logger.opt(exception=True).debug(
            'Fetching full artist discography failed for {}', channel_id
        )
        return results
    return [r for r in (full or []) if isinstance(r, dict)] or results


def artist_info_from_channel_id(channel_id: str) -> dict[str, Any]:
    """Resolve an artist's own profile info: name, thumbnail, bio.

    Distinct from :func:`artist_albums_from_channel_id` (their releases)
    and :func:`artist_top_songs_from_channel_id`/
    :func:`artist_top_albums_from_channel_id` (their popular tracks/
    albums) - this is just the "About" info for the artist page itself.
    Returns ``{}`` if the artist can't be resolved at all.
    """

    try:
        artist_data = _ytm().get_artist(channel_id)
    except Exception:
        logger.exception('YouTube Music get_artist failed for {}', channel_id)
        return {}

    thumbs = artist_data.get('thumbnails') or []
    cover = _upgrade_thumbnail(thumbs[-1].get('url', '')) if thumbs else ''
    return {
        'artist_id': channel_id,
        'name': str(artist_data.get('name') or '').strip(),
        'cover_url': cover,
        'description': str(artist_data.get('description') or '').strip(),
        'url': f'https://music.youtube.com/channel/{channel_id}',
        'source': 'youtube',
    }


def artist_similar_from_channel_id(channel_id: str) -> list[dict[str, Any]]:
    """Resolve an artist's "Fans might also like" shelf as lightweight
    artist summaries. Same shape as :func:`search_artists` results.

    YouTube Music only ever offers a short, fixed list here (~10 - no
    'params' continuation is offered, unlike the albums/singles shelves).
    """

    try:
        artist_data = _ytm().get_artist(channel_id)
    except Exception:
        logger.exception('YouTube Music get_artist failed for {}', channel_id)
        return []

    section = artist_data.get('related')
    if not isinstance(section, dict):
        return []
    artists = []
    for entry in section.get('results') or []:
        if not isinstance(entry, dict):
            continue
        related_id = entry.get('browseId')
        if not isinstance(related_id, str) or not related_id.strip():
            continue
        thumbs = entry.get('thumbnails') or []
        cover = _upgrade_thumbnail(thumbs[-1].get('url', '')) if thumbs else ''
        artists.append({
            'artist_id': related_id.strip(),
            'name': entry.get('title') or '',
            'cover_url': cover,
            'url': f'https://music.youtube.com/channel/{related_id.strip()}',
            'source': 'youtube',
        })
    return artists


def artist_albums_from_channel_id(channel_id: str) -> list[dict[str, Any]]:
    """Resolve every album and single for an artist as lightweight summaries.

    Same shape as :func:`search_albums` results (no tracklists). This is
    deliberate: listing an artist's releases never needs their tracks - a
    caller that wants a specific release's tracks resolves it separately,
    once the user actually opens it, via :func:`album_tracks_from_browse_id`.
    Resolving every tracklist just to list the discography would mean one
    extra YouTube Music round-trip *per release*, turning a single
    ``get_artist`` call into dozens for a prolific artist. Duplicates (a
    release appearing in both the albums and singles sections) are
    de-duplicated.
    """

    try:
        artist_data = _ytm().get_artist(channel_id)
    except Exception:
        logger.exception('YouTube Music get_artist failed for {}', channel_id)
        return []

    artist_name = str(artist_data.get('name') or '').strip()
    entries: list[tuple[dict[str, Any], str]] = []
    for section_key, release_type in (
        ('albums', 'Album'),
        ('singles', 'Single'),
    ):
        section = artist_data.get(section_key)
        if not isinstance(section, dict):
            continue
        for entry in _artist_albums_full_list(channel_id, section):
            entries.append((entry, release_type))

    # dedupe by browseId (a release occasionally shows up in both sections)
    deduped: dict[str, tuple[dict[str, Any], str]] = {}
    for entry, default_release_type in entries:
        browse_id = entry.get('browseId')
        if not isinstance(browse_id, str) or not browse_id.strip():
            continue
        deduped.setdefault(browse_id.strip(), (entry, default_release_type))

    logger.info(
        'YouTube Music get_artist {!r} channelId={} albums={} singles={} '
        'unique={}',
        artist_name,
        channel_id,
        sum(1 for _, rt in entries if rt == 'Album'),
        sum(1 for _, rt in entries if rt == 'Single'),
        len(deduped),
    )

    return [
        _artist_album_entry_to_summary(
            browse_id, entry, artist_name, default_release_type
        )
        for browse_id, (entry, default_release_type) in deduped.items()
    ]


def _artist_album_entry_to_summary(
    browse_id: str,
    entry: dict[str, Any],
    artist_name: str,
    default_release_type: str,
) -> dict[str, Any]:
    """Build one album summary dict from a raw ``get_artist`` shelf entry.

    Same shape as :func:`search_albums` results (no tracklists) — shared
    by :func:`artist_albums_from_channel_id` (full discography) and
    :func:`artist_top_albums_from_channel_id` (the shelf's own preview,
    unexpanded).
    """
    thumbs = entry.get('thumbnails') or []
    cover = _upgrade_thumbnail(thumbs[-1].get('url', '')) if thumbs else ''
    return {
        'album_id': browse_id,
        'name': entry.get('title') or '',
        'artists': [artist_name] if artist_name else [],
        'artist': artist_name,
        'cover_url': cover,
        'year': str(entry.get('year') or '').strip(),
        'explicit': bool(entry.get('isExplicit')),
        'url': f'https://music.youtube.com/browse/{browse_id}',
        'source': 'youtube',
        # the singles section carries YTM's own 'Single'/'EP' split;
        # the albums section doesn't distinguish further, so it always
        # falls back to the section's own default ('Album').
        'release_type': entry.get('type') or default_release_type,
    }


_TOP_ALBUMS_LIMIT = 5


def _popularity_sort_continuation(
    response: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Find the "Popularity" entry in a discography page's sort-order
    menu and return its reloadable-continuation payload, or ``None`` if
    the page doesn't carry a sort menu at all (e.g. too few releases for
    YouTube Music to bother offering one).
    """
    try:
        sort_options = nav(
            response,
            SINGLE_COLUMN_TAB
            + SECTION
            + HEADER_SIDE
            + [
                'endItems',
                0,
                'musicSortFilterButtonRenderer',
                'menu',
                'musicMultiSelectMenuRenderer',
                'options',
            ],
        )
    except Exception:
        return None
    for option in sort_options:
        title = nav(option, MULTI_SELECT + TITLE_TEXT, True)
        if isinstance(title, str) and title.strip().lower() == 'popularity':
            return nav(
                option,
                [
                    *MULTI_SELECT,
                    'selectedCommand',
                    'commandExecutorCommand',
                    'commands',
                    -1,
                    'browseSectionListReloadEndpoint',
                ],
                True,
            )
    return None


def _fetch_artist_section_by_popularity(
    channel_id: str, params: str, limit: int
) -> list[dict[str, Any]]:
    """Fetch an artist's 'albums'/'singles' shelf sorted by YouTube
    Music's own "Popularity" ordering, truncated to ``limit`` entries.

    This is literally what selecting "Popularity" from the sort dropdown
    on an artist's discography page does — see
    ``_fetch_full_artist_section``'s docstring for why the discography
    browseId, not the artist's channelId itself, is needed to even reach
    that page (and its sort menu) in the first place.
    """
    body = {
        'browseId': _artist_discography_browse_id(channel_id),
        'params': params,
    }
    ytm = _ytm()
    response = ytm._send_request('browse', body)
    continuation = _popularity_sort_continuation(response)
    if not continuation:
        return []
    additional_params = get_reloadable_continuation_params({
        'continuations': [continuation['continuation']]
    })
    response = ytm._send_request('browse', body, additional_params)
    results = nav(response, SECTION_LIST_CONTINUATION + CONTENT)
    contents = nav(results, GRID_ITEMS, True) or []
    return _parse_ytm_albums(contents)[:limit]


def artist_top_albums_from_channel_id(channel_id: str) -> list[dict[str, Any]]:
    """Resolve an artist's most popular albums as lightweight summaries.

    Fetches the discography page sorted by YouTube Music's own
    "Popularity" order and takes the first :data:`_TOP_ALBUMS_LIMIT`.
    Falls back to the "Albums" shelf's own (unsorted) preview when no
    'params' continuation is offered at all, or the popularity fetch
    fails for any reason — an artist with too few releases for YouTube
    Music to paginate doesn't get a sort menu either, so this covers the
    same case that would make the continuation lookup a no-op anyway.
    Singles/EPs are not included, matching the "Albums" shelf itself.
    """

    try:
        artist_data = _ytm().get_artist(channel_id)
    except Exception:
        logger.exception('YouTube Music get_artist failed for {}', channel_id)
        return []

    artist_name = str(artist_data.get('name') or '').strip()
    section = artist_data.get('albums')
    if not isinstance(section, dict):
        return []

    params = section.get('params')
    entries: list[dict[str, Any]] = []
    if params:
        try:
            entries = _fetch_artist_section_by_popularity(
                channel_id, params, _TOP_ALBUMS_LIMIT
            )
        except Exception:
            logger.opt(exception=True).debug(
                'Fetching popularity-sorted albums failed for {}',
                channel_id,
            )
    if not entries:
        entries = [
            r for r in (section.get('results') or []) if isinstance(r, dict)
        ][:_TOP_ALBUMS_LIMIT]

    albums = []
    for entry in entries:
        browse_id = entry.get('browseId')
        if not isinstance(browse_id, str) or not browse_id.strip():
            continue
        albums.append(
            _artist_album_entry_to_summary(
                browse_id.strip(), entry, artist_name, 'Album'
            )
        )
    return albums


def artist_top_songs_from_channel_id(channel_id: str) -> list[dict[str, Any]]:
    """Resolve an artist's 'Top songs' shelf as lightweight song summaries.

    Same shape as :func:`search_songs` results. This is YouTube Music's
    own popularity-ranked preview (~10 entries, no further pagination
    offered) — distinct from the full discography, which is resolved a
    release at a time via :func:`album_tracks_from_browse_id`.
    """

    try:
        artist_data = _ytm().get_artist(channel_id)
    except Exception:
        logger.exception('YouTube Music get_artist failed for {}', channel_id)
        return []

    section = artist_data.get('songs')
    if not isinstance(section, dict):
        return []
    results = [
        r for r in (section.get('results') or []) if isinstance(r, dict)
    ]
    songs: list[dict[str, Any]] = []
    for result in results:
        song = _result_to_song(result)
        if song:
            songs.append(song)
    return songs


_YOUTUBE_URL_HOSTS = ('youtube.com', 'youtu.be', 'music.youtube.com')
_YOUTUBE_VIDEO_ID_RE = re.compile(
    r'(?:[?&]v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{6,})'
)
_YOUTUBE_ALBUM_BROWSE_RE = re.compile(r'/browse/(MPREb_[A-Za-z0-9_-]+)')
_YOUTUBE_ALBUM_PLAYLIST_RE = re.compile(r'[?&]list=(OLAK5uy_[A-Za-z0-9_-]+)')
_YOUTUBE_ARTIST_CHANNEL_RE = re.compile(r'/channel/(UC[A-Za-z0-9_-]+)')


def parse_youtube_url(url: str) -> Optional[tuple[str, str]]:
    """Parse a YouTube/YouTube Music URL into ``(kind, id)``.

    ``kind`` is ``'track'`` (a watchable videoId), ``'album'`` (a
    ``MPREb_`` browse id, or an ``OLAK5uy_`` audio-playlist id — pass
    either straight to :func:`album_tracks_from_browse_id`, which
    resolves the playlist form to a browse id itself), or ``'artist'``
    (a ``UC``-prefixed channel id — pass to
    :func:`artist_discography_from_channel_id`). Returns ``None`` for
    URLs that aren't recognized YouTube links at all.
    """

    if not url or not any(host in url for host in _YOUTUBE_URL_HOSTS):
        return None
    match = _YOUTUBE_ALBUM_BROWSE_RE.search(url)
    if match:
        return 'album', match.group(1)
    match = _YOUTUBE_ALBUM_PLAYLIST_RE.search(url)
    if match:
        return 'album', match.group(1)
    match = _YOUTUBE_ARTIST_CHANNEL_RE.search(url)
    if match:
        return 'artist', match.group(1)
    match = _YOUTUBE_VIDEO_ID_RE.search(url)
    if match:
        return 'track', match.group(1)
    return None


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
    album = song.get('album_name', '')
    query = f'{artists_q} {title}'.strip()
    if not query:
        return None, None
    duration = song.get('duration') or 0

    # Try an unfiltered (default) search first. Unlike the category-
    # filtered searches below, this is the only request that includes
    # YouTube Music's own "Top result" card — its single best guess for
    # the query — and it is empirically far more reliable than the
    # `songs` shelf for tracks the filtered search omits entirely (e.g.
    # "Held Together" and "Fallen Wires (Remastered 2023)" are both absent
    # from `filter='songs'` results for their own artist+title query,
    # yet resolve instantly as the unfiltered Top result).
    try:
        top_results = _ytm().search(query, limit=5)
    except Exception:
        logger.exception('YouTube Music top-result search failed')
        top_results = []
    _log_ytm_summary_search(
        phase='match_top_result',
        query=query,
        filt='default',
        results_len=len(top_results),
        first_titles=[
            str(r.get('title') or '')[:60]
            for r in top_results[:8]
            if isinstance(r, dict)
        ],
    )
    _log_ytm_response(f'find_match top-result q={query[:80]!r}', top_results)
    usable_top_results = [
        r
        for r in top_results
        if isinstance(r, dict) and r.get('resultType') in {'song', 'video'}
    ]
    top_best = _pick_best(usable_top_results, duration, title, artists, album)
    if top_best is not None:
        logger.info(
            'YouTube Music find_match picked videoId={} title={!r} '
            'year={!r} via=top_result',
            top_best.get('videoId'),
            top_best.get('title'),
            top_best.get('year'),
        )
        _log_ytm_response('find_match chosen row (top result)', top_best)
        return top_best.get('videoId'), top_best

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
    best = _pick_best(results, duration, title, artists, album)
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
        # Same hard title/artist requirements as `_pick_best`: never fall
        # back to "the first result" if its title doesn't actually
        # resemble the source track, or if it shares the title but not
        # the artist (title collisions across unrelated artists happen).
        if (
            result.get('videoId')
            and (not title or _titles_match(title, result.get('title')))
            and _artists_overlap(artists, result)
        ):
            logger.info(
                'YouTube Music find_match fallback first videoId={} title={!r}',
                result.get('videoId'),
                result.get('title'),
            )
            _log_ytm_response('find_match fallback row', result)
            return result['videoId'], result
    # Text search sometimes never returns the correct video at all (see
    # `_find_match_via_album`'s docstring) — try resolving it directly
    # off the album's tracklist before giving up.
    album_video_id, album_match = _find_match_via_album(song)
    if album_video_id:
        return album_video_id, album_match
    logger.info(
        'YouTube Music find_match: no title-matching result for '
        'query={!r} target_title={!r}',
        query[:160],
        title,
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


# Qualifiers that mark a genuinely different recording — a different
# performance or edit, not just a different pressing of the same audio.
# When one name is a prefix of the other (e.g. "Amber Field" vs "Local
# Valley (Deluxe)"), the extra text is tolerated *unless* it contains one
# of these — a plain "Fernglow" must never match "Fernglow (DJ Koze Remix)".
# Extend this list as new special cases turn up.
_VERSION_QUALIFIER_WORDS = (
    'live',
    'remix',
    'cover',
    'karaoke',
    'acoustic',
    'unplugged',
    'demo',
    'instrumental',
    'tribute',
)
_VERSION_QUALIFIER_RE = re.compile(
    r'\b(' + '|'.join(_VERSION_QUALIFIER_WORDS) + r')\b'
)


def _names_match(target: Any, candidate: Any) -> bool:
    """True when two free-text names (title or album) refer to the same release.

    An exact normalized match always counts. Otherwise one name may be a
    prefix of the other, tolerating cosmetic edition tags a reissue adds
    without changing the underlying content (``"(Deluxe)"``,
    ``"(Remastered 2023)"``, ``"(Anniversary Edition)"``). The extra
    text is rejected, however, if it names a genuinely different
    recording — see :data:`_VERSION_QUALIFIER_WORDS`. A common prefix
    shorter than 4 characters is never accepted, so short unrelated
    names don't collide (``"U"`` must not match ``"Unplugged"``).
    """

    t = _norm_compact_title(target)
    c = _norm_compact_title(candidate)
    if not t or not c:
        return False
    if t == c:
        return True
    shorter, longer = sorted((t, c), key=len)
    if len(shorter) < 4 or not longer.startswith(shorter):
        return False
    tail = longer[len(shorter) :]
    return not _VERSION_QUALIFIER_RE.search(tail)


def _albums_match(target: Any, candidate: Any) -> bool:
    """True when two album names refer to the same release. See :func:`_names_match`."""

    return _names_match(target, candidate)


def _titles_match(target: Any, candidate: Any) -> bool:
    """True when two song titles refer to the same recording. See :func:`_names_match`."""

    return _names_match(target, candidate)


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
        if n and n not in hints:
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
    result_titles = [
        str(r.get('title') or '')[:60]
        for r in results[:10]
        if isinstance(r, dict)
    ]
    logger.info(
        'YouTube Music album search title_match q={!r} hits={} sample_titles={}',
        query[:120],
        len(results),
        result_titles,
    )
    _log_ytm_response(f'albums search titles={result_titles!r}', results)
    # Match against the *original* title hints we were looking for — not
    # the search results' own titles (that used to shadow `titles` here,
    # making this check a no-op that always accepted the first result
    # regardless of whether it was actually the right album).
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
    artists = [
        a.get('name', '')
        for a in (data.get('artists') or [])
        if isinstance(a, dict) and a.get('name')
    ]
    tup = (tracks, total_ct)
    with _lock:
        _album_track_cache[browse_id] = tup
        if not artists:
            # get_album's own response doesn't always carry an `artists`
            # field — fall back to what the earlier albums-filter search
            # for this same browse id already told us (search_albums /
            # _album_summary), rather than losing it.
            artists = list(_album_search_artist_cache.get(browse_id) or [])
        _album_meta_cache[browse_id] = {
            'title': data.get('title') or '',
            'year': str(data.get('year') or '').strip(),
            'thumbnails': data.get('thumbnails') or [],
            # 'Album' / 'Single' / 'EP' — YouTube Music's own release
            # classification.
            'type': data.get('type') or '',
            'artists': artists,
        }
    return tup


def _cached_album_meta(browse_id: str) -> dict[str, Any]:
    """Album-level metadata for ``browse_id``, if already resolved and cached.

    Only ever a cache read — populated as a side effect of
    :func:`_cached_album_tracks_and_count`, never triggers its own
    ``get_album`` call.
    """

    with _lock:
        return dict(_album_meta_cache.get(browse_id) or {})


def _cached_album_title(browse_id: str) -> str:
    return _cached_album_meta(browse_id).get('title', '')


def _cached_album_release_type(browse_id: str) -> str:
    return _cached_album_meta(browse_id).get('type', '')


# Separators YouTube Music uses when it collapses a featuring artist into
# a single combined-name entry instead of a separate artist dict.
# "and"/","/"with"/"x" are deliberately excluded even though YouTube
# Music uses them too, because they routinely appear inside real band
# names (e.g. a duo named "Harbor and the Wren") and could get mis-split
# if the album's own metadata is ever internally inconsistent about the
# artist name used as the anchor below. "&" carries the same risk but is
# kept anyway since it's the single most common combined-name pattern in
# practice, and the anchor check already guards against the common case.
_FEATURING_ARTIST_SEPARATORS = (
    ' feat. ',
    ' feat ',
    ' featuring ',
    ' ft. ',
    ' ft ',
    ' & ',
)


def _split_combined_featuring_artist(
    artists: list[str], album_artists: list[str]
) -> list[str]:
    """Split a "Primary feat. Featured" combined name YouTube Music
    sometimes returns as a single artist entry (no separate channel id)
    for featuring tracks — instead of the usual one-dict-per-artist list.

    Only splits when the combined name is prefixed by an artist already
    known to be on the album, so genuine band names aren't mistakenly
    split apart.
    """
    if len(artists) != 1:
        return artists
    name = artists[0]
    name_lower = name.lower()
    for album_artist in album_artists:
        for sep in _FEATURING_ARTIST_SEPARATORS:
            prefix = f'{album_artist}{sep}'
            if name_lower.startswith(prefix.lower()):
                featured = name[len(prefix) :].strip()
                if featured:
                    return [album_artist, featured]
    return artists


# Matches a trailing "(feat. X)" / "(ft. X)" / "(featuring X)" — with
# either parenthesis or square-bracket style — at the end of a title.
_TITLE_FEATURING_RE = re.compile(
    r'[\(\[]\s*(?:feat\.?|ft\.?|featuring)\s+(.+?)\s*[\)\]]\s*$',
    re.IGNORECASE,
)


def _extract_title_featuring_artist(
    title: str, artists: list[str]
) -> list[str]:
    """Add a featured artist named in the title's "(feat. X)" suffix to
    ``artists``, for the case where YouTube Music's own artists list
    doesn't credit them at all — e.g. a track titled "Better Way To Live
    (feat. Grian Chatten)" whose ``artists`` is just ``[{"name":
    "KNEECAP"}]``, with no entry whatsoever for the featured artist.
    """
    match = _TITLE_FEATURING_RE.search(title or '')
    if not match:
        return artists
    featured = match.group(1).strip()
    if not featured:
        return artists
    existing = {a.lower() for a in artists}
    if featured.lower() in existing:
        return artists
    return [*artists, featured]


# YouTube Music's own classification of a track's upload (see
# `get_album`/search results' `videoType` field): "ATV" is a studio
# recording uploaded by the artist with static cover art — the actual
# album/single release. "OMV" is a genuine music video, which often uses
# a different edit of the song (extended or spoken intro, alternate
# mix) than the album version, even though it's nominally "the same
# track". ytmusicapi doesn't expose both alternatives on one track
# entry, so swapping requires a follow-up search.
_MUSIC_VIDEO_TYPE_OFFICIAL_AUDIO = 'MUSIC_VIDEO_TYPE_ATV'
_MUSIC_VIDEO_TYPE_MUSIC_VIDEO = 'MUSIC_VIDEO_TYPE_OMV'


def _prefer_official_audio_track(
    video_id: str,
    duration: int,
    title: str,
    artists: list[str],
    video_type: str,
) -> tuple[str, int]:
    """Swap a music-video (OMV) track for its official-audio (ATV)
    counterpart when one can be found, since the video edit sometimes
    differs from the actual album recording. Returns the original
    ``(video_id, duration)`` unchanged when the track isn't an OMV, or
    when no matching ATV alternative turns up.
    """
    if video_type != _MUSIC_VIDEO_TYPE_MUSIC_VIDEO:
        return video_id, duration
    query = f'{" ".join(artists)} {title}'.strip()
    if not query:
        return video_id, duration
    try:
        results = _ytm().search(query, filter='songs', limit=10)
    except Exception:
        logger.opt(exception=True).debug(
            'Official-audio preference search failed for {!r}', title
        )
        return video_id, duration
    for result in results:
        if not isinstance(result, dict):
            continue
        if result.get('videoType') != _MUSIC_VIDEO_TYPE_OFFICIAL_AUDIO:
            continue
        if not _titles_match(title, result.get('title')):
            continue
        if not _artists_overlap(artists, result):
            continue
        candidate = result.get('videoId')
        if not (isinstance(candidate, str) and candidate.strip()):
            continue
        candidate_duration = result.get('duration_seconds') or _parse_duration(
            result.get('duration')
        )
        logger.info(
            'Preferring official-audio (ATV) videoId={} over music-video '
            '(OMV) videoId={} for title={!r}',
            candidate,
            video_id,
            title,
        )
        return candidate.strip(), (candidate_duration or duration)
    return video_id, duration


def _album_track_song(
    track: dict[str, Any],
    video_id: str,
    position: int,
    total: int,
    meta: dict[str, Any],
) -> dict[str, Any]:
    """Build one album-track song dict, given the album's cached metadata."""

    artists = [
        a.get('name', '')
        for a in (track.get('artists') or [])
        if isinstance(a, dict) and a.get('name')
    ]
    artists = _split_combined_featuring_artist(
        artists, meta.get('artists') or []
    )
    artists = _extract_title_featuring_artist(track.get('title', ''), artists)
    title = track.get('title', '')
    duration = track.get('duration_seconds') or _parse_duration(
        track.get('duration')
    )
    video_id, duration = _prefer_official_audio_track(
        video_id, duration, title, artists, track.get('videoType', '')
    )
    year = meta.get('year', '')
    thumbs = meta.get('thumbnails') or []
    cover = _upgrade_thumbnail(thumbs[-1].get('url', '')) if thumbs else ''
    track_number = _normalize_ytm_track_slot(
        declared=track.get('trackNumber'), position_in_album_list=position
    )
    return {
        'song_id': video_id,
        'name': title,
        'artists': artists,
        'artist': ', '.join(artists),
        'album_name': meta.get('title', ''),
        'cover_url': cover,
        'duration': duration,
        'url': f'https://music.youtube.com/watch?v={video_id}',
        'explicit': bool(track.get('isExplicit')),
        'year': year,
        'release_date': year,
        'source': 'youtube',
        'track_number': track_number,
        'album_track_total': total,
        'release_type': meta.get('type', ''),
        # The album's own artist, so every track in the album gets the
        # same "album artist" tag even when a track's own `artists` differs
        # (a feature, a remix credit, ...) — see
        # `downloader._album_artist_for_tags`, which falls back to a
        # per-track heuristic when this isn't set.
        'album_artist': ', '.join(meta.get('artists') or []),
    }


def album_tracks_from_browse_id(
    browse_id_or_playlist_id: str,
) -> list[dict[str, Any]]:
    """Resolve a YouTube Music album into Spotify-shaped song dicts.

    Accepts either a ``MPREb_`` browse id or an ``OLAK5uy_`` audio
    playlist id (converted to a browse id first via
    ``get_album_browse_id``). Mirrors
    :func:`spotify.album_tracks_from_id`'s output shape so the same
    batch-download/M3U frontend code path works unchanged for a
    directly-pasted YouTube Music album URL. Returns ``[]`` if the
    album can't be resolved at all.
    """

    browse_id = browse_id_or_playlist_id
    if browse_id.startswith('OLAK5uy_'):
        try:
            resolved = _ytm().get_album_browse_id(browse_id)
        except Exception:
            logger.exception(
                'YouTube Music get_album_browse_id failed for {}', browse_id
            )
            resolved = None
        if not resolved:
            return []
        browse_id = resolved

    tracks, total_ct = _cached_album_tracks_and_count(browse_id)
    if not tracks:
        return []
    total = total_ct or len(tracks)
    meta = _cached_album_meta(browse_id)

    songs: list[dict[str, Any]] = []
    for position, track in enumerate(tracks, start=1):
        video_id = _row_video_id(track)
        if not video_id:
            continue
        songs.append(_album_track_song(track, video_id, position, total, meta))
    return songs


def _find_match_via_album(
    song: dict[str, Any],
) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    """Resolve a track by scanning its album's tracklist directly.

    YouTube Music's text search occasionally omits the correct video
    from an "artist + title" query's own results entirely — e.g.
    searching "Mica Ferreira Held Together" never surfaces "Held Together" itself,
    while surfacing an unrelated track by the same artist (confirmed by
    inspecting the raw search payload). When the source album is known,
    resolving it via the ``albums`` filter and scanning its full
    :func:`_cached_album_tracks_and_count` listing sidesteps that
    search-relevance quirk entirely, since the tracklist is keyed by
    album rather than by a fuzzy text query.
    """

    title = song.get('name', '')
    album_name = str(song.get('album_name') or '').strip()
    if not title or not album_name:
        return None, None

    browse_id = _album_browse_id_from_search({}, song)
    if not browse_id:
        return None, None

    tracks, _total = _cached_album_tracks_and_count(browse_id)
    for track in tracks:
        if not isinstance(track, dict):
            continue
        video_id = _row_video_id(track)
        if not video_id:
            continue
        if _titles_match(title, track.get('title')):
            logger.info(
                'YouTube Music find_match album-tracklist fallback hit '
                'browseId={!r} videoId={} title={!r}',
                browse_id,
                video_id,
                track.get('title'),
            )
            return video_id, track
    logger.info(
        'YouTube Music find_match album-tracklist fallback: no title '
        'match in browseId={!r} for title={!r}',
        browse_id,
        title,
    )
    return None, None


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
    if not enriched.get('album_name') or not enriched.get('release_type'):
        # `youtube_music_track_index_for_match` already resolved (and
        # cached) the album's browseId while computing the track index
        # above — reuse it to backfill the album title and release
        # type too, since the search-derived `match` sometimes lacks
        # `album.name` even when the video is genuinely part of a
        # catalogued release.
        browse_id = _album_browse_id(match, enriched)
        if browse_id:
            if not enriched.get('album_name'):
                album_title = _cached_album_title(browse_id)
                if album_title:
                    enriched['album_name'] = album_title
            if not enriched.get('release_type'):
                release_type = _cached_album_release_type(browse_id)
                if release_type:
                    enriched['release_type'] = release_type
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


def _artists_overlap(
    target_artists: Optional[list[str]], result: dict[str, Any]
) -> bool:
    """True when the candidate shares at least one artist with the target.

    Vacuously true when the target's artist list is unknown, so callers
    without artist context (e.g. an album-tracklist scan) aren't
    unfairly blocked. Otherwise a hard requirement: a song that merely
    shares its exact title with the target (title collisions across
    unrelated artists are common for short/generic names — "Broken
    Arrows" turns up from at least three different acts) must never be
    picked just for being the "least wrong" duration match.
    """

    target_set = {(a or '').lower() for a in (target_artists or []) if a}
    if not target_set:
        return True
    candidate_set = {
        (a.get('name') or '').lower()
        for a in (result.get('artists') or [])
        if isinstance(a, dict)
    }
    return bool(target_set & candidate_set)


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
    target_album: str = '',
) -> Optional[dict[str, Any]]:
    target_title_l = (target_title or '').lower()
    target_album_norm = _norm_compact_title(target_album)

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

        # Hard requirement: the title must actually resemble the source
        # title. Duration/artist/album scoring alone can otherwise pick a
        # completely unrelated song (e.g. a "- Remastered 2023" suffix
        # throws off the search and every hit is a different track by the
        # same artist) — better to reject the track than embed the wrong
        # audio under the right metadata.
        if target_title and not _titles_match(
            target_title, result.get('title')
        ):
            continue

        # Hard requirement: at least one artist must overlap. See
        # `_artists_overlap`'s docstring — a title collision with an
        # unrelated artist must never win on duration alone.
        if not _artists_overlap(target_artists, result):
            continue

        candidate_duration = result.get('duration_seconds') or _parse_duration(
            result.get('duration')
        )
        if target_duration and candidate_duration:
            score = abs(candidate_duration - target_duration)
        else:
            score = 5

        # Album is the decisive signal when the source album is known: it
        # separates the studio version from live / compilation / re-recorded
        # takes of the same song that share title, artist and near-identical
        # length (durations differ by a second or two, so duration alone is
        # not enough). Only applied when the candidate carries album info so
        # album-less `videos` results are not unfairly penalised.
        if target_album_norm:
            candidate_album = ''
            alb = result.get('album')
            if isinstance(alb, dict):
                candidate_album = alb.get('name') or ''
            if candidate_album:
                if _albums_match(target_album, candidate_album):
                    score -= 25
                else:
                    score += 15

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


def _song_from_video_details(video_id: str) -> dict[str, Any]:
    """Basic song info from ``get_song``'s raw video-player payload.

    This is the only reliable, always-available source for an arbitrary
    videoId (title, uploader/author, duration, thumbnail) — but it is
    raw player data with no catalog metadata (album, track number).
    """

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


def song_from_video_id(video_id: str) -> dict[str, Any]:
    """Look up song info for a YouTube videoId, including album/track
    metadata when the video is part of an official YouTube Music album.

    ``get_song`` (raw player data) never carries catalog metadata, and
    ``get_watch_playlist`` was found — empirically, against the live
    API — not to reliably include it either. Catalog metadata (album,
    track number) is only reliably available through search, so once
    the basic title/artist/duration are known, the resolved title is
    run through the same matching pipeline used for Spotify-sourced
    downloads (:func:`find_match`) to look up a catalog hit, and
    :func:`enrich_from_match` fills in album/track metadata from it
    when found — never overriding the video actually requested.
    """

    song = _song_from_video_details(video_id)
    if not song.get('name'):
        return song

    try:
        _, match = find_match(song)
    except Exception:
        logger.opt(exception=True).debug(
            'song_from_video_id: catalog lookup failed for {}', video_id
        )
        match = None
    if not match:
        return song

    enriched = enrich_from_match(song, match)
    # enrich_from_match never touches these, but pin them explicitly so
    # the returned song always describes the video the caller asked
    # for, never whichever video the catalog lookup happened to match.
    enriched['song_id'] = video_id
    enriched['url'] = f'https://music.youtube.com/watch?v={video_id}'
    enriched['source'] = 'youtube'
    return enriched
