"""Download a track from YouTube and tag it with the chosen metadata."""

from __future__ import annotations

import concurrent.futures
import os
import re
import re as _re
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

import requests
import yt_dlp
from loguru import logger
from mutagen.flac import FLAC, Picture
from mutagen.id3 import (
    APIC,
    ID3,
    TALB,
    TCON,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TRCK,
    USLT,
)
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis
from yt_dlp.utils import DownloadError

from . import lyrics as lyrics_mod
from . import spotify as spotify_mod
from .itunes import fetch_genre as _fetch_itunes_genre
from .library_paths import library_stored_path, slskd_dir_from_downloader
from .m3u import sanitize_playlist_name
from .providers import enrich_from_match, find_match, find_match_for_video
from .slskd_provider import download_from_slskd
from .track_tag_match import (
    candidate_adds_mix_variant,
    duration_matches_song,
    media_duration_matches_mix_variant,
    remote_title_unacceptable,
    snapshot_spotify_metadata,
    song_duration_seconds,
    spotify_file_tag_mismatch_label,
    strip_mix_suffix,
    verify_youtube_download_file,
    youtube_probe_title_matches,
)

_INVALID_FS_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

ProgressCallback = Callable[[float, str, Optional[str]], None]


def _youtube_download_timeout_seconds(settings: dict[str, Any]) -> int:
    try:
        value = int(settings.get('download_timeout_seconds') or 900)
    except (TypeError, ValueError):
        value = 900
    return min(3600, max(60, value))


class _ConvertHeartbeat:
    """Keep queue UI alive while ffmpeg post-processes after yt-dlp 'finished'."""

    def __init__(
        self,
        progress_cb: ProgressCallback,
        *,
        label: str,
        provider: Optional[str],
        interval_seconds: float = 20.0,
    ) -> None:
        self._progress_cb = progress_cb
        self._label = label
        self._provider = provider
        self._interval = interval_seconds
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name='downtify-convert-heartbeat',
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        started = time.monotonic()
        while not self._stop.wait(self._interval):
            elapsed = int(time.monotonic() - started)
            mins, secs = divmod(elapsed, 60)
            try:
                self._progress_cb(
                    96.0,
                    f'{self._label} · converting ({mins}m {secs:02d}s)…',
                    self._provider,
                )
            except Exception:
                logger.opt(exception=True).debug('convert heartbeat error')


def _provider_display_name(provider: Optional[str]) -> str:
    if provider == 'youtube-music':
        return 'YouTube Music'
    if provider == 'youtube':
        return 'YouTube'
    if provider == 'slskd':
        return 'slskd'
    return ''


class NoAudioMatchError(RuntimeError):
    """No configured provider could source audio for the requested track."""


def _sanitize(text: str) -> str:
    safe = _INVALID_FS_CHARS.sub('', text or '').strip().strip('.')
    return safe or 'unknown'


# Order matters — yt-dlp tries clients top-to-bottom and uses the first one
# that yields usable formats. `ios` and `android` lead because they still
# provide audio formats in containers without a JS runtime, even though
# YouTube now requires a GVS PO Token for their HTTPS/HLS formats (those
# are skipped with a warning, but lower-quality streams remain available).
# `web_embedded` and `web` need a JS runtime for signature/n-challenge
# solving; without one, they yield no audio at all — so they're kept as
# last-resort fallbacks only. `mweb` and `tv` are included as hail-mary
# clients: `mweb` needs a PO Token too, and `tv` is affected by a DRM
# experiment (yt-dlp #12563), but including them costs nothing.
_DEFAULT_YT_PLAYER_CLIENTS = (
    'ios',
    'android',
    'web_embedded',
    'mweb',
    'web',
    'tv',
)

# Warning substrings emitted by yt-dlp that are known-harmless: they mean
# some optional format sources are skipped, but other clients in the list
# still serve usable audio. Suppressed to keep logs readable.
_SUPPRESSED_YT_WARNING_FRAGMENTS = (
    'GVS PO Token which was not provided',
    'Some tv client https formats have been skipped as they are DRM',
    'Signature solving failed: Some formats may be missing',
    'n challenge solving failed: Some formats may be missing',
    'Skipping client "ios" since it does not support cookies',
    'Skipping client "android" since it does not support cookies',
    'Some web_creator client https formats have been skipped',
    'SABR-only streaming experiment',
)


class _YtdlpLogger:
    @staticmethod
    def debug(msg: str) -> None:
        pass

    @staticmethod
    def info(msg: str) -> None:
        pass

    @staticmethod
    def warning(msg: str) -> None:
        if not any(frag in msg for frag in _SUPPRESSED_YT_WARNING_FRAGMENTS):
            logger.warning('yt-dlp: {}', msg)

    @staticmethod
    def error(msg: str) -> None:
        logger.error('yt-dlp: {}', msg)


def _yt_player_clients() -> list[str]:
    raw = os.getenv('DOWNTIFY_YT_PLAYER_CLIENTS', '').strip()
    if not raw:
        return list(_DEFAULT_YT_PLAYER_CLIENTS)
    clients = [c.strip() for c in raw.split(',') if c.strip()]
    return clients or list(_DEFAULT_YT_PLAYER_CLIENTS)


def ytdlp_cookies_configured(
    youtube_settings: Optional[dict[str, Any]] = None,
) -> bool:
    probe: dict[str, Any] = {}
    apply_ytdlp_cookie_opts(probe, youtube_settings)
    return 'cookiefile' in probe or 'cookiesfrombrowser' in probe


def apply_ytdlp_cookie_opts(
    ydl_opts: dict[str, Any],
    youtube_settings: Optional[dict[str, Any]] = None,
) -> None:
    """Attach cookiefile / cookiesfrombrowser when configured (settings or env)."""
    cookies_file = ''
    if youtube_settings:
        cookies_file = str(youtube_settings.get('cookies_file') or '').strip()
    if not cookies_file:
        cookies_file = os.getenv('DOWNTIFY_COOKIES_FILE', '').strip()
    if cookies_file:
        path = Path(cookies_file)
        if path.is_file():
            ydl_opts['cookiefile'] = str(path)
        else:
            logger.warning('yt-dlp cookies file not found: {}', cookies_file)

    cookies_browser = ''
    if youtube_settings:
        cookies_browser = str(
            youtube_settings.get('cookies_from_browser') or ''
        ).strip()
    if not cookies_browser:
        cookies_browser = os.getenv(
            'DOWNTIFY_COOKIES_FROM_BROWSER', ''
        ).strip()
    if cookies_browser:
        parts = cookies_browser.split(':', 1)
        ydl_opts['cookiesfrombrowser'] = (
            (parts[0],) if len(parts) == 1 else (parts[0], parts[1])
        )


_COOKIE_YT_CLIENTS = (
    'web_safari',
    'web',
    'tv_embedded',
    'web_embedded',
    'tv',
)

_YOUTUBE_AUTH_COOKIE_NAMES = frozenset({
    'LOGIN_INFO',
    'SID',
    '__Secure-1PSID',
    '__Secure-3PSID',
    'SAPISID',
    '__Secure-1PAPISID',
    '__Secure-3PAPISID',
})


def inspect_youtube_cookies(path: Path | str) -> dict[str, Any]:
    """Best-effort Netscape cookie file health check for YouTube auth."""
    cookie_path = Path(path)
    out: dict[str, Any] = {
        'path': str(cookie_path),
        'exists': cookie_path.is_file(),
        'auth_cookies_found': [],
        'looks_authenticated': False,
        'has_youtube_domain': False,
        'warnings': [],
    }
    if not cookie_path.is_file():
        out['warnings'].append('cookies file not found')
        return out
    try:
        text = cookie_path.read_text(encoding='utf-8', errors='replace')
    except OSError as exc:
        out['warnings'].append(f'cannot read cookies file: {exc}')
        return out
    if 'youtube.com' not in text.casefold():
        out['warnings'].append('no youtube.com cookies in file')
        return out
    out['has_youtube_domain'] = True
    names: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) < 7:
            continue
        domain, name = parts[0], parts[5]
        if 'youtube' in domain.casefold():
            names.add(name)
    found = sorted(names & _YOUTUBE_AUTH_COOKIE_NAMES)
    out['auth_cookies_found'] = found
    out['looks_authenticated'] = bool(found) and (
        'LOGIN_INFO' in names or '__Secure-3PSID' in names or 'SID' in names
    )
    if not out['looks_authenticated']:
        out['warnings'].append(
            'missing login session cookies; export from youtube.com while '
            'signed in (private window, only tab: youtube.com/robots.txt)'
        )
    return out


def _log_youtube_cookie_health(
    youtube_settings: Optional[dict[str, Any]],
) -> None:
    path_str = str((youtube_settings or {}).get('cookies_file') or '').strip()
    if not path_str:
        return
    health = inspect_youtube_cookies(path_str)
    for warning in health.get('warnings') or []:
        logger.warning('YouTube cookies: {}', warning)
    if health.get('looks_authenticated'):
        logger.info(
            'YouTube cookies: login session present ({})',
            ', '.join(health.get('auth_cookies_found') or []),
        )


def _cookie_yt_player_clients() -> list[str]:
    clients: list[str] = []
    if _yt_po_tokens():
        clients.append('mweb')
    clients.extend(_COOKIE_YT_CLIENTS)
    return clients


def _youtube_player_clients_for_profile(
    youtube_settings: Optional[dict[str, Any]],
    *,
    use_cookies: bool,
) -> list[str]:
    if use_cookies:
        return _cookie_yt_player_clients()
    return list(_yt_player_clients())


def _youtube_download_profiles(
    video_id: str,
    youtube_settings: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Cookie web clients first (age-restricted), then ios/android without cookies."""
    vid = str(video_id or '').strip()
    if not vid:
        return []
    www = f'https://www.youtube.com/watch?v={vid}'
    music = f'https://music.youtube.com/watch?v={vid}'
    profiles: list[dict[str, Any]] = []
    if ytdlp_cookies_configured(youtube_settings):
        profiles.append({
            'label': 'cookies+web',
            'use_cookies': True,
            'urls': [www],
        })
    profiles.append({
        'label': 'no-cookies',
        'use_cookies': False,
        'urls': [music, www],
    })
    return profiles


def _ytdlp_age_restricted_retry(exc: BaseException) -> bool:
    msg = str(exc).casefold()
    return (
        'age-restricted' in msg
        or 'only available on youtube' in msg
        or 'sign in to confirm your age' in msg
    )


def _yt_po_tokens() -> list[str]:
    """Comma-separated PO Tokens, each in the form ``<client>.<context>+<token>``.

    Example: ``mweb.gvs+ABC123,web.gvs+XYZ987``
    """
    raw = os.getenv('DOWNTIFY_YT_PO_TOKEN', '').strip()
    if not raw:
        return []
    return [t.strip() for t in raw.split(',') if t.strip()]


_YTDLP_AUDIO_FORMATS = (
    'bestaudio/best',
    'bestaudio[ext=m4a]/bestaudio/best[acodec!=none]/best/b',
    'ba/b/bv*+ba/b',
    'worst[acodec!=none]/worst',
)


def _youtube_extractor_args(
    youtube_settings: Optional[dict[str, Any]] = None,
    *,
    use_cookies: bool = False,
    allow_missing_pot: bool = False,
) -> dict[str, Any]:
    args: dict[str, Any] = {
        'player_client': _youtube_player_clients_for_profile(
            youtube_settings,
            use_cookies=use_cookies,
        ),
    }
    po = _yt_po_tokens()
    if po:
        args['po_token'] = po
    if allow_missing_pot:
        args['formats'] = ['missing_pot']
    return args


def _ytdlp_should_retry_without_cookies(
    exc: BaseException, *, used_cookies: bool
) -> bool:
    if not used_cookies:
        return False
    if _ytdlp_age_restricted_retry(exc):
        return False
    msg = str(exc).casefold()
    return (
        _ytdlp_format_unavailable_retry(exc)
        or '403' in msg
        or 'forbidden' in msg
    )


def _ytdlp_format_unavailable_retry(exc: BaseException) -> bool:
    msg = str(exc).casefold()
    return (
        'requested format is not available' in msg
        or 'only images are available' in msg
    )


def _ytdlp_should_try_alternate_video(exc: BaseException) -> bool:
    msg = str(exc).casefold()
    return (
        _ytdlp_age_restricted_retry(exc)
        or _ytdlp_format_unavailable_retry(exc)
        or '403' in msg
        or 'forbidden' in msg
        or 'sign in to confirm' in msg
        or 'cookies are no longer valid' in msg
    )


def _ytdlp_fallback_search_queries(song: dict[str, Any]) -> list[str]:
    """Build yt-dlp search queries; include stripped mix/edit variants."""

    title = str(song.get('name') or '').strip()
    artists = [
        a for a in (song.get('artists') or []) if isinstance(a, str) and a
    ]
    album = str(song.get('album_name') or '').strip()
    queries: list[str] = []

    def _add(parts: list[str]) -> None:
        query = ' '.join(part for part in parts if part).strip()
        if query and query not in queries:
            queries.append(query)

    base_title = strip_mix_suffix(title) or title
    title_words = base_title.split()
    short_ambiguous = (
        album
        and len(title_words) == 1
        and len(title_words[0]) <= 5
    )
    if short_ambiguous:
        _add([*artists[:2], base_title, album])
    _add([*artists[:2], base_title])
    if album and not short_ambiguous:
        _add([*artists[:2], base_title, album])
    if title.casefold() != base_title.casefold():
        _add([*artists[:2], title])
        if short_ambiguous:
            _add([*artists[:2], title, album])
        elif album:
            _add([*artists[:2], title, album])
    return queries


def _ytdlp_fallback_search_query(song: dict[str, Any]) -> str:
    """Build a yt-dlp search query; disambiguate very short track titles."""

    queries = _ytdlp_fallback_search_queries(song)
    return queries[0] if queries else ''


def _youtube_candidate_near_acceptable(
    song: dict[str, Any],
    probe: dict[str, Any],
) -> bool:
    """Looser pre-download filter when strict duration match finds nothing."""

    title = str(probe.get('title') or '')
    if remote_title_unacceptable(song, title):
        return False
    length = int(probe.get('duration') or 0)
    target = song_duration_seconds(song)
    if length <= 0 or not target:
        return True
    spotify_title = str(song.get('name') or '')
    if candidate_adds_mix_variant(spotify_title, title):
        return media_duration_matches_mix_variant(song, length)
    if not youtube_probe_title_matches(song, title):
        return False
    if length > target + max(60, int(target * 0.35)):
        return False
    if length < max(30, int(target * 0.4)) and target >= 60:
        return False
    return abs(length - target) <= max(60, int(target * 0.25))


def _ytdlp_search_video_ids(
    query: str,
    *,
    count: int,
) -> list[str]:
    if not query:
        return []
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
        'skip_download': True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f'ytsearch{count}:{query}', download=False)
    except Exception:
        logger.opt(exception=True).debug(
            'yt-dlp fallback search failed for query={!r}', query
        )
        return []
    entries = info.get('entries') if isinstance(info, dict) else None
    if not isinstance(entries, list):
        return []
    ids: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        vid = entry.get('id')
        if isinstance(vid, str) and vid.strip():
            ids.append(vid.strip())
    return ids


def _fallback_video_ids_via_ytdlp(
    song: dict[str, Any],
    *,
    youtube_settings: Optional[dict[str, Any]] = None,
    exclude: Optional[frozenset[str]] = None,
    limit: int = 5,
) -> list[str]:
    """Ranked YouTube video ids from yt-dlp search (no cookies)."""
    queries = _ytdlp_fallback_search_queries(song)
    if not queries:
        return []
    count = min(max(limit * 2, limit, 1), 10)
    skip = exclude or frozenset()
    verified: list[str] = []
    near: list[str] = []
    unverified: list[str] = []
    seen: set[str] = set()

    for query in queries:
        for vid in _ytdlp_search_video_ids(query, count=count):
            if not vid or vid in skip or vid in seen:
                continue
            seen.add(vid)
            probe = _ytdlp_video_probe(vid, youtube_settings=youtube_settings)
            if probe is None:
                unverified.append(vid)
                continue
            if _youtube_candidate_acceptable(song, probe):
                verified.append(vid)
            elif _youtube_candidate_near_acceptable(song, probe):
                near.append(vid)
            if len(verified) >= limit:
                break
        if len(verified) >= limit:
            break

    if verified:
        return verified[:limit]
    if near:
        return near[:limit]
    if not song_duration_seconds(song):
        return unverified[:limit]
    return []


def _fallback_video_id_via_ytdlp(
    song: dict[str, Any],
    *,
    youtube_settings: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """Best-effort YouTube fallback when YT Music search yields no match."""
    ids = _fallback_video_ids_via_ytdlp(
        song,
        youtube_settings=youtube_settings,
        limit=1,
    )
    if not ids:
        return None
    vid = ids[0]
    logger.info(
        'yt-dlp fallback picked videoId={} for title={!r}',
        vid,
        str(song.get('name') or '').strip(),
    )
    return vid


def _ytdlp_download_video(
    video_id: str,
    *,
    ydl_opts: dict[str, Any],
    youtube_settings: Optional[dict[str, Any]] = None,
) -> None:
    """Run yt-dlp profile/format fallbacks for one video id. Raises on failure."""
    profiles = _youtube_download_profiles(video_id, youtube_settings)
    if not profiles:
        raise RuntimeError('missing YouTube video id')

    last_err: Optional[BaseException] = None
    success = False
    for profile_index, profile in enumerate(profiles):
        profile_opts = dict(ydl_opts)
        if profile['use_cookies']:
            apply_ytdlp_cookie_opts(profile_opts, youtube_settings)
            if profile_opts.get('cookiefile'):
                logger.info(
                    'yt-dlp: using cookies from {}',
                    profile_opts['cookiefile'],
                )
            elif profile_opts.get('cookiesfrombrowser'):
                logger.info('yt-dlp: using cookies from browser')
        elif profile_index > 0:
            logger.info(
                'yt-dlp: cookie/web profile failed for {}, '
                'retrying with ios/android clients (no cookies)',
                video_id,
            )

        for url in profile['urls']:
            for fmt_index, fmt in enumerate(_YTDLP_AUDIO_FORMATS):
                attempt_opts = dict(profile_opts)
                attempt_opts['format'] = fmt
                attempt_opts['extractor_args'] = {
                    'youtube': _youtube_extractor_args(
                        youtube_settings,
                        use_cookies=profile['use_cookies'],
                        allow_missing_pot=(
                            fmt_index == len(_YTDLP_AUDIO_FORMATS) - 1
                        ),
                    ),
                }
                try:
                    with yt_dlp.YoutubeDL(attempt_opts) as ydl:
                        ydl.download([url])
                    success = True
                    last_err = None
                    break
                except DownloadError as exc:
                    last_err = exc
                    msg = str(exc).casefold()
                    if 'cookies are no longer valid' in msg:
                        logger.error(
                            'yt-dlp: YouTube cookies expired or rotated; '
                            're-export from youtube.com (private window) '
                            'and upload again'
                        )
                    if fmt_index + 1 < len(
                        _YTDLP_AUDIO_FORMATS
                    ) and _ytdlp_format_unavailable_retry(exc):
                        logger.info(
                            'yt-dlp: format {!r} unavailable for {} '
                            '({}), trying fallback',
                            fmt,
                            video_id,
                            profile['label'],
                        )
                        continue
                    break
            if success:
                break
        if success:
            break
        if (
            profile_index + 1 < len(profiles)
            and last_err is not None
            and _ytdlp_should_retry_without_cookies(
                last_err, used_cookies=profile['use_cookies']
            )
        ):
            continue
        if last_err is not None:
            raise last_err
    if not success and last_err is not None:
        raise last_err


def _ytdlp_video_probe(
    video_id: str,
    *,
    youtube_settings: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    vid = str(video_id or '').strip()
    if not vid:
        return None
    opts: dict[str, Any] = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': True,
    }
    apply_ytdlp_cookie_opts(opts, youtube_settings)
    url = f'https://www.youtube.com/watch?v={vid}'
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        logger.opt(exception=True).debug(
            'yt-dlp video probe failed for {}', vid
        )
        return None
    if not isinstance(info, dict):
        return None
    try:
        length = int(info.get('duration') or 0)
    except (TypeError, ValueError):
        length = 0
    title = str(info.get('title') or '').strip()
    if length <= 0 and not title:
        return None
    return {'duration': length, 'title': title}


def _remove_partial_downloads(target_dir: Path, basename: str) -> None:
    for candidate in target_dir.glob(f'{basename}.*'):
        if candidate.is_file():
            try:
                candidate.unlink()
            except OSError:
                logger.opt(exception=True).warning(
                    'Failed to remove partial download {}', candidate
                )


def _youtube_candidate_acceptable(
    song: dict[str, Any],
    probe: dict[str, Any],
) -> bool:
    title = str(probe.get('title') or '')
    if remote_title_unacceptable(song, title):
        logger.info(
            'yt-dlp: skip video title={!r} (audiobook/podcast/long-form) '
            'for spotify={!r}',
            title[:120],
            song.get('name'),
        )
        return False
    length = int(probe.get('duration') or 0)
    if length > 0 and not duration_matches_song(song, length):
        logger.info(
            'yt-dlp: skip video duration={}s (expected ~{}s) title={!r}',
            length,
            song_duration_seconds(song),
            song.get('name'),
        )
        return False
    if not youtube_probe_title_matches(song, title):
        logger.info(
            'yt-dlp: skip video title={!r} (title mismatch) for spotify={!r}',
            title[:120],
            song.get('name'),
        )
        return False
    return True


def _run_callable_with_timeout(
    func: Callable[[], None],
    *,
    timeout_seconds: int,
    label: str,
) -> None:
    if timeout_seconds <= 0:
        func()
        return
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(func)
        try:
            future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError as exc:
            raise TimeoutError(
                f'{label} exceeded {timeout_seconds}s'
            ) from exc


class Downloader:
    """Wraps ``yt-dlp`` plus ``mutagen`` tagging."""

    def __init__(
        self,
        download_dir: Path | str,
        audio_format: str = 'mp3',
        audio_bitrate: str = '320',
        output_template: str = '{artists} - {title}',
        lyrics_providers: Optional[list[str]] = None,
        organize_by_artist: bool = False,
        audio_providers: Optional[list[str]] = None,
        slskd_settings: Optional[dict[str, Any]] = None,
        youtube_settings: Optional[dict[str, Any]] = None,
    ):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.audio_format = audio_format
        self.audio_bitrate = audio_bitrate
        self.output_template = output_template
        self.lyrics_providers = list(lyrics_providers or [])
        self.organize_by_artist = organize_by_artist
        self.audio_providers = self._normalize_audio_providers(audio_providers)
        self.slskd_settings = self._normalize_slskd_settings(slskd_settings)
        self.youtube_settings = dict(youtube_settings or {})
        # Final tagged files land in Downtify's download root.
        self.slskd_settings['output_dir'] = str(self.download_dir)

    @staticmethod
    def _normalize_audio_providers(
        providers: Optional[list[str]],
    ) -> list[str]:
        allowed = {'youtube-music', 'youtube', 'slskd'}
        if not providers:
            return ['youtube-music']
        out: list[str] = []
        seen: set[str] = set()
        for raw in providers:
            p = str(raw or '').strip()
            if p in allowed and p not in seen:
                seen.add(p)
                out.append(p)
        return out or ['youtube-music']

    @staticmethod
    def _normalize_slskd_settings(
        settings: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        raw = settings if isinstance(settings, dict) else {}

        def _int(raw_value: Any, default: int) -> int:
            try:
                return int(raw_value)
            except (TypeError, ValueError):
                return default

        download_dir = str(raw.get('download_dir') or '/downloads').strip()
        return {
            'enabled': bool(raw.get('enabled', False)),
            'base_url': str(raw.get('base_url') or '').strip().rstrip('/'),
            'api_key': str(raw.get('api_key') or '').strip(),
            'download_dir': download_dir,
            'source_dir': str(raw.get('source_dir') or download_dir).strip(),
            'timeout_seconds': _int(raw.get('timeout_seconds') or 20, 20),
            'search_retries': _int(raw.get('search_retries') or 5, 5),
            'search_poll_seconds': _int(
                raw.get('search_poll_seconds') or 15, 15
            ),
            'download_attempts': _int(raw.get('download_attempts') or 5, 5),
            'poll_interval_seconds': _int(
                raw.get('poll_interval_seconds') or 5, 5
            ),
            'poll_max_attempts': _int(raw.get('poll_max_attempts') or 60, 60),
            'download_timeout_seconds': min(
                3600,
                max(30, _int(raw.get('download_timeout_seconds') or 600, 600)),
            ),
            'queued_timeout_seconds': min(
                3600,
                max(15, _int(raw.get('queued_timeout_seconds') or 180, 180)),
            ),
            'extensions': raw.get('extensions') or ['mp3', 'flac'],
            'min_bitrate': _int(raw.get('min_bitrate') or 256, 256),
            'leave_in_place': bool(raw.get('leave_in_place', True)),
        }

    def _resolve_video_id(
        self,
        song: dict[str, Any],
        progress_cb: Optional[ProgressCallback] = None,
    ) -> tuple[
        Optional[str], Optional[dict[str, Any]], Optional[str], Optional[Path]
    ]:
        """Resolve source by provider order.

        Returns ``(video_id, ytm_match, provider_used, local_file_path)``.
        """

        if progress_cb is not None:
            try:
                progress_cb(0.0, 'Searching for audio…', None)
            except Exception:
                logger.opt(exception=True).debug(
                    'progress callback error at search start'
                )

        tried_ytdlp = False
        for provider in self.audio_providers:
            if provider == 'youtube-music':
                if progress_cb is not None:
                    try:
                        progress_cb(
                            1.0,
                            'Matching on YouTube Music…',
                            'youtube-music',
                        )
                    except Exception:
                        logger.opt(exception=True).debug(
                            'progress callback error for youtube-music'
                        )
                video_id, match = find_match(song)
                if video_id:
                    logger.info(
                        'Match resolver: provider={} succeeded title={!r} '
                        'video_id={}',
                        provider,
                        song.get('name'),
                        video_id,
                    )
                    return video_id, match, provider, None
                logger.info(
                    'Match resolver: provider={} no match title={!r}',
                    provider,
                    song.get('name'),
                )
            elif provider == 'youtube':
                tried_ytdlp = True
                if progress_cb is not None:
                    try:
                        progress_cb(2.0, 'Searching on YouTube…', 'youtube')
                    except Exception:
                        logger.opt(exception=True).debug(
                            'progress callback error for youtube'
                        )
                video_id = _fallback_video_id_via_ytdlp(
                    song, youtube_settings=self.youtube_settings
                )
                if video_id:
                    logger.info(
                        'Match resolver: provider={} succeeded title={!r} '
                        'video_id={}',
                        provider,
                        song.get('name'),
                        video_id,
                    )
                    return video_id, None, provider, None
                logger.info(
                    'Match resolver: provider={} no match title={!r}',
                    provider,
                    song.get('name'),
                )
            elif provider == 'slskd':
                if not bool(self.slskd_settings.get('enabled')):
                    logger.info(
                        'Match resolver: provider={} disabled title={!r}',
                        provider,
                        song.get('name'),
                    )
                    continue
                slskd_idx = self.audio_providers.index('slskd')
                has_fallback = any(
                    p in {'youtube-music', 'youtube'}
                    for p in self.audio_providers[slskd_idx + 1 :]
                )
                local = download_from_slskd(
                    song, self.slskd_settings, progress_cb=progress_cb
                )
                if local is not None:
                    logger.info(
                        'Match resolver: provider={} succeeded title={!r} path={}',
                        provider,
                        song.get('name'),
                        local,
                    )
                    return None, None, provider, local
                if has_fallback and progress_cb is not None:
                    try:
                        progress_cb(
                            0.0,
                            'No match on slskd, trying next source…',
                            'slskd',
                        )
                    except Exception:
                        logger.opt(exception=True).debug(
                            'progress callback error after slskd timeout'
                        )
                logger.info(
                    'Match resolver: provider={} no match title={!r}',
                    provider,
                    song.get('name'),
                )

        if not tried_ytdlp and 'youtube-music' in self.audio_providers:
            if progress_cb is not None:
                try:
                    progress_cb(
                        2.0,
                        'Searching on YouTube…',
                        'youtube',
                    )
                except Exception:
                    logger.opt(exception=True).debug(
                        'progress callback error for yt-dlp fallback'
                    )
            video_id = _fallback_video_id_via_ytdlp(
                song, youtube_settings=self.youtube_settings
            )
            if video_id:
                logger.info(
                    'Match resolver: yt-dlp search fallback after provider '
                    'miss title={!r} video_id={}',
                    song.get('name'),
                    video_id,
                )
                return video_id, None, 'youtube', None

        return None, None, None, None

    @staticmethod
    def _artist_subdir(song: dict[str, Any]) -> str:
        artists = song.get('artists') or []
        return _sanitize(artists[0] if artists else 'unknown')

    def _format_basename(self, song: dict[str, Any]) -> str:
        artists = ', '.join(song.get('artists') or []) or 'Unknown Artist'
        template = self.output_template.replace('.{output-ext}', '')
        try:
            rendered = template.format(
                title=song.get('name', 'Unknown'),
                artists=artists,
                artist=artists,
                album=song.get('album_name', ''),
            )
        except (KeyError, IndexError):
            rendered = f'{artists} - {song.get("name", "Unknown")}'
        return _sanitize(rendered)

    def existing_filename_for(
        self,
        song: dict[str, Any],
        subdir: Optional[str] = None,
    ) -> Optional[str]:
        """Return the on-disk filename for ``song`` if any matching file exists.

        Mirrors :meth:`download`'s post-conversion path resolution: prefers
        ``{basename}.{audio_format}`` and falls back to any
        ``{basename}.*`` since yt-dlp occasionally keeps the upstream
        extension (opus, m4a). Returns ``None`` when no file matches.

        When ``subdir`` is given the lookup is scoped to that
        sub-directory and the returned name is relative to
        ``download_dir`` (``<subdir>/<file>.<ext>``).
        """

        basename = self._format_basename(song)
        effective_subdir = (
            self._artist_subdir(song) if self.organize_by_artist else subdir
        )
        target_dir, prefix = self._resolve_target_dir(effective_subdir)
        primary = target_dir / f'{basename}.{self.audio_format}'
        if primary.exists():
            return f'{prefix}{primary.name}'
        for candidate in target_dir.glob(f'{basename}.*'):
            if candidate.is_file():
                return f'{prefix}{candidate.name}'
        return None

    def _resolve_target_dir(self, subdir: Optional[str]) -> tuple[Path, str]:
        """Return ``(target_dir, relative_prefix)`` for an optional subdir.

        ``relative_prefix`` is empty when ``subdir`` is not used and
        otherwise terminates with ``'/'`` so callers can build the
        download-dir-relative path with simple concatenation.
        """

        if not subdir:
            return self.download_dir, ''
        safe = sanitize_playlist_name(subdir)
        return self.download_dir / safe, f'{safe}/'

    def _copy_local_source_into_target(
        self,
        source_path: Path,
        target_dir: Path,
        basename: str,
    ) -> Path:
        if not source_path.exists() or not source_path.is_file():
            raise RuntimeError(f'source file not found: {source_path}')
        ext = source_path.suffix or f'.{self.audio_format}'
        final_path = target_dir / f'{basename}{ext}'
        if source_path.resolve() != final_path.resolve():
            shutil.copy2(source_path, final_path)
        return final_path

    def _finalize_downloaded_file(
        self,
        final_path: Path,
        song: dict[str, Any],
        progress_cb: Optional[ProgressCallback],
        provider: Optional[str] = None,
    ) -> None:
        if not song.get('genre'):
            try:
                genre = _fetch_itunes_genre(song)
                if genre:
                    song = {**song, 'genre': genre}
            except Exception:
                logger.opt(exception=True).debug(
                    'iTunes genre lookup failed for {}', final_path
                )

        try:
            embed_metadata(final_path, song)
        except Exception:
            logger.exception('Failed to embed metadata into {}', final_path)

        if self.lyrics_providers:
            try:
                fetched = lyrics_mod.fetch(song, self.lyrics_providers)
            except Exception:
                logger.exception('Lyrics fetch crashed for {}', final_path)
                fetched = None
            if fetched is not None:
                try:
                    embed_lyrics(final_path, fetched)
                except Exception:
                    logger.exception(
                        'Failed to embed lyrics into {}', final_path
                    )

        if progress_cb:
            label = _provider_display_name(provider)
            msg = f'{label} · tagging' if label else 'Tagging'
            progress_cb(98.0, msg, provider)

    def download(  # noqa: PLR0914  # yt-dlp + slskd + tagging pipeline
        self,
        song: dict[str, Any],
        progress_cb: Optional[ProgressCallback] = None,
        subdir: Optional[str] = None,
    ) -> str:
        """Download ``song`` and return the resulting file name.

        When ``subdir`` is provided the file is written under
        ``download_dir/<sanitized_subdir>/`` and the returned name is
        relative to ``download_dir`` (``<subdir>/<file>.<ext>``). This
        is how playlist downloads are grouped into per-playlist folders.
        """

        video_id = song.get('youtube_id')
        if not video_id and (song.get('source') == 'youtube'):
            video_id = song.get('song_id')

        match: Optional[dict[str, Any]] = None
        provider: Optional[str] = None
        local_source_path: Optional[Path] = None
        if not video_id:
            song = spotify_mod.enrich_track_from_spotify_if_sparse(song)
            video_id, match, provider, local_source_path = (
                self._resolve_video_id(song, progress_cb=progress_cb)
            )
        elif not song.get('album_name') or not song.get('cover_url'):
            # We already have a target video, but the metadata is incomplete.
            # Look up the YT Music entry for THIS specific videoId so we
            # don't risk switching to a karaoke / cover that happens to
            # rank higher.
            try:
                match = find_match_for_video(song, video_id)
            except Exception:
                logger.opt(exception=True).debug('enrichment match failed')
                match = None
            provider = provider or 'youtube-music'

        if not video_id and local_source_path is None:
            raise NoAudioMatchError(
                f'Could not find an audio match for {song.get("name")!r}'
            )

        song = enrich_from_match(song, match)
        song = spotify_mod.enrich_track_from_spotify_if_sparse(song)

        basename = self._format_basename(song)
        effective_subdir = (
            self._artist_subdir(song) if self.organize_by_artist else subdir
        )
        target_dir, rel_prefix = self._resolve_target_dir(effective_subdir)
        target_dir.mkdir(parents=True, exist_ok=True)
        out_template = str(target_dir / f'{basename}.%(ext)s')

        yt_provider = (
            provider if provider in {'youtube', 'youtube-music'} else 'youtube'
        )

        if local_source_path is not None:
            if provider == 'slskd' and bool(
                self.slskd_settings.get('leave_in_place', True)
            ):
                final_path = local_source_path
                stored_name = library_stored_path(
                    final_path,
                    self.download_dir,
                    slskd_dir_from_downloader(self),
                )
            else:
                final_path = self._copy_local_source_into_target(
                    local_source_path, target_dir, basename
                )
                stored_name = f'{rel_prefix}{final_path.name}'
            if progress_cb:
                label = _provider_display_name(provider) or 'slskd'
                progress_cb(95.0, f'Downloaded ({label})', provider)
            self._finalize_downloaded_file(
                final_path, song, progress_cb, provider
            )
            return stored_name

        if progress_cb:
            label = _provider_display_name(yt_provider) or 'YouTube'
            progress_cb(5.0, f'{label} · preparing download…', yt_provider)

        def hook(data: dict[str, Any]) -> None:
            if progress_cb is None:
                return
            try:
                status = data.get('status')
                label = _provider_display_name(yt_provider) or 'YouTube'
                if status == 'downloading':
                    total = (
                        data.get('total_bytes')
                        or data.get('total_bytes_estimate')
                        or 0
                    )
                    downloaded = data.get('downloaded_bytes') or 0
                    if total:
                        progress_cb(
                            min(95.0, downloaded / total * 95.0),
                            f'{label} · downloading',
                            yt_provider,
                        )
                elif status == 'finished':
                    progress_cb(96.0, f'{label} · converting', yt_provider)
            except Exception:
                logger.opt(exception=True).debug('progress hook error')

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'quiet': True,
            'noprogress': True,
            'logger': _YtdlpLogger(),
            'noplaylist': True,
            'nocheckcertificate': True,
            'overwrites': True,
            'progress_hooks': [hook],
            # Resilience against flaky DNS/network in containers.
            # googlevideo.com CDN hosts are short-lived shards and a single
            # transient EAI_AGAIN/timeout used to abort the whole download.
            'retries': 10,
            'fragment_retries': 10,
            'extractor_retries': 3,
            'socket_timeout': 30,
            'format_sort': ['proto:https', 'ext:m4a', 'acodec', 'abr'],
            # Light pacing so we don't trigger 429 rate limits when the
            # user fires off multiple downloads back-to-back.
            'sleep_interval_requests': 1,
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': self.audio_format,
                    'preferredquality': self.audio_bitrate,
                }
            ],
            'postprocessor_args': {
                'ffmpeg': ['-threads', '4'],
            },
        }
        # Many container setups have IPv6 advertised but unroutable for
        # googlevideo.com, which surfaces as EAI_AGAIN on the AAAA lookup.
        # Setting DOWNTIFY_FORCE_IPV4=1 binds yt-dlp to IPv4 only.
        if os.getenv('DOWNTIFY_FORCE_IPV4', '').strip() in {
            '1',
            'true',
            'yes',
        }:
            ydl_opts['source_address'] = '0.0.0.0'

        _log_youtube_cookie_health(self.youtube_settings)

        primary_id = str(video_id or '').strip()
        if not primary_id:
            raise RuntimeError('missing YouTube video id')

        alt_ids = _fallback_video_ids_via_ytdlp(
            song,
            youtube_settings=self.youtube_settings,
            exclude=frozenset({primary_id}),
            limit=5,
        )
        candidate_ids: list[str] = [primary_id]
        for alt in alt_ids:
            if alt not in candidate_ids:
                candidate_ids.append(alt)
        tried_ids = set(candidate_ids)

        yt_timeout = _youtube_download_timeout_seconds(self.youtube_settings)
        convert_label = _provider_display_name(yt_provider) or 'YouTube'
        spotify_row = snapshot_spotify_metadata(song)

        last_err: Optional[BaseException] = None
        idx = 0
        while idx < len(candidate_ids):
            cand_id = candidate_ids[idx]
            if idx > 0:
                logger.info(
                    'yt-dlp: trying alternate videoId={} for title={!r}',
                    cand_id,
                    song.get('name'),
                )
                if progress_cb:
                    progress_cb(
                        5.0,
                        f'{convert_label} · trying alternate match…',
                        yt_provider,
                    )
            probe = _ytdlp_video_probe(
                cand_id,
                youtube_settings=self.youtube_settings,
            )
            if probe is not None and not _youtube_candidate_acceptable(
                song, probe
            ) and not _youtube_candidate_near_acceptable(song, probe):
                last_err = DownloadError(
                    f'YouTube candidate rejected ({probe.get("title")!r})'
                )
                if idx + 1 < len(candidate_ids):
                    idx += 1
                    continue
                raise last_err

            heartbeat: Optional[_ConvertHeartbeat] = None
            if progress_cb is not None:
                heartbeat = _ConvertHeartbeat(
                    progress_cb,
                    label=convert_label,
                    provider=yt_provider,
                )
                heartbeat.start()

            def _do_download(vid: str = cand_id) -> None:
                _ytdlp_download_video(
                    vid,
                    ydl_opts=ydl_opts,
                    youtube_settings=self.youtube_settings,
                )

            try:
                _run_callable_with_timeout(
                    _do_download,
                    timeout_seconds=yt_timeout,
                    label=f'YouTube download for {song.get("name")!r}',
                )
            except DownloadError as exc:
                last_err = exc
                has_more = idx + 1 < len(candidate_ids)
                if has_more and _ytdlp_should_try_alternate_video(exc):
                    idx += 1
                    continue
                raise
            except TimeoutError as exc:
                last_err = exc
                logger.warning(
                    'yt-dlp: timed out after {}s videoId={} title={!r}',
                    yt_timeout,
                    cand_id,
                    song.get('name'),
                )
                if idx + 1 < len(candidate_ids):
                    idx += 1
                    continue
                raise
            finally:
                if heartbeat is not None:
                    heartbeat.stop()

            final_path = target_dir / f'{basename}.{self.audio_format}'
            if not final_path.exists():
                for candidate in target_dir.glob(f'{basename}.*'):
                    if candidate.is_file():
                        final_path = candidate
                        break

            if not final_path.exists():
                last_err = DownloadError('yt-dlp produced no output file')
                if idx + 1 < len(candidate_ids):
                    idx += 1
                    continue
                raise last_err

            if not verify_youtube_download_file(
                final_path, spotify_row, probe=probe
            ):
                logger.info(
                    'yt-dlp: post-download verify failed videoId={} {}; '
                    'trying next candidate ({}/{})',
                    cand_id,
                    spotify_file_tag_mismatch_label({
                        **spotify_row,
                        'library_from_tags': True,
                    }),
                    idx + 1,
                    len(candidate_ids),
                )
                _remove_partial_downloads(target_dir, basename)
                last_err = DownloadError('downloaded file did not match Spotify')
                extra = _fallback_video_ids_via_ytdlp(
                    song,
                    youtube_settings=self.youtube_settings,
                    exclude=frozenset(tried_ids),
                    limit=5,
                )
                for alt in extra:
                    if alt not in tried_ids:
                        candidate_ids.append(alt)
                        tried_ids.add(alt)
                if idx + 1 < len(candidate_ids):
                    idx += 1
                    continue
                raise NoAudioMatchError(
                    f'Could not find an audio match for {song.get("name")!r}'
                ) from last_err

            self._finalize_downloaded_file(
                final_path, song, progress_cb, yt_provider
            )
            return f'{rel_prefix}{final_path.name}'

        if last_err is not None:
            raise NoAudioMatchError(
                f'Could not find an audio match for {song.get("name")!r}'
            ) from last_err
        raise NoAudioMatchError(
            f'Could not find an audio match for {song.get("name")!r}'
        )


def _download_cover(url: str) -> Optional[bytes]:
    if not url:
        return None
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception:
        logger.opt(exception=True).warning('Failed to fetch cover art {}', url)
        return None
    return response.content


def _album_track_index_for_tags(
    song: dict[str, Any],
) -> tuple[Optional[int], Optional[int]]:
    """Normalize ``track_number`` / ``album_track_total`` for tagging frames."""
    raw_n = song.get('track_number')
    raw_tot = song.get('album_track_total')
    try:
        n = int(raw_n)
    except (TypeError, ValueError):
        return None, None
    if n <= 0:
        return None, None
    tot: Optional[int] = None
    if raw_tot is not None and raw_tot != '':
        try:
            t = int(raw_tot)
        except (TypeError, ValueError):
            pass
        else:
            if t > 0:
                tot = t
    return n, tot


def _recording_date_for_tags(song: dict[str, Any]) -> str:
    """Prefer full ``YYYY-MM-DD`` from Spotify; fall back to year-only."""

    rd = str(song.get('release_date') or '').strip()
    if rd:
        return rd
    return str(song.get('year') or '').strip()


def embed_metadata(path: Path, song: dict[str, Any]) -> None:
    if not path.exists():
        return

    title = song.get('name', '')
    artists = song.get('artists') or []
    album = song.get('album_name', '') or ''
    recording_date = _recording_date_for_tags(song)
    genre = (song.get('genre') or '').strip()
    cover_bytes = _download_cover(song.get('cover_url', ''))
    track_number, album_track_total = _album_track_index_for_tags(song)
    if track_number is None:
        logger.debug(
            'Tag embed: no track_number/disc position for file={} '
            'song_id={} title={!r} raw_track_number={!r} raw_total={!r}',
            path.name,
            song.get('song_id'),
            title,
            song.get('track_number'),
            song.get('album_track_total'),
        )
    if not recording_date:
        logger.debug(
            'Tag embed: no recording date (year/release_date) for file={} '
            'song_id={} title={!r} raw_year={!r} raw_release_date={!r}',
            path.name,
            song.get('song_id'),
            title,
            song.get('year'),
            song.get('release_date'),
        )
    logger.debug(
        'Tag embed summary: {} track={}/{} date={!r}',
        path.name,
        track_number,
        album_track_total,
        recording_date,
    )

    suffix = path.suffix.lower().lstrip('.')

    if suffix == 'mp3':
        _tag_mp3(
            path,
            title,
            artists,
            album,
            recording_date,
            genre,
            cover_bytes,
            track_number,
            album_track_total,
        )
    elif suffix in {'m4a', 'mp4', 'aac'}:
        _tag_mp4(
            path,
            title,
            artists,
            album,
            recording_date,
            genre,
            cover_bytes,
            track_number,
            album_track_total,
        )
    elif suffix == 'flac':
        _tag_flac(
            path,
            title,
            artists,
            album,
            recording_date,
            genre,
            cover_bytes,
            track_number,
            album_track_total,
        )
    elif suffix in {'ogg', 'oga'}:
        _tag_ogg_vorbis(
            path,
            title,
            artists,
            album,
            recording_date,
            genre,
            track_number,
            album_track_total,
        )
    elif suffix == 'opus':
        _tag_opus(
            path,
            title,
            artists,
            album,
            recording_date,
            genre,
            track_number,
            album_track_total,
        )


def _tag_mp3(
    path: Path,
    title: str,
    artists: list[str],
    album: str,
    year: str,
    genre: str,
    cover_bytes: Optional[bytes],
    track_number: Optional[int],
    album_track_total: Optional[int],
) -> None:
    audio = MP3(str(path), ID3=ID3)
    if audio.tags is None:
        audio.add_tags()
    audio.tags.delall('APIC')
    audio.tags.add(TIT2(encoding=3, text=title))
    if artists:
        audio.tags.add(TPE1(encoding=3, text='/'.join(artists)))
        audio.tags.add(TPE2(encoding=3, text=artists[0]))
    if album:
        audio.tags.add(TALB(encoding=3, text=album))
    if track_number is not None:
        trck = (
            f'{track_number}/{album_track_total}'
            if album_track_total is not None
            else str(track_number)
        )
        audio.tags.add(TRCK(encoding=3, text=trck))
    if year:
        audio.tags.add(TDRC(encoding=3, text=year))
    if genre:
        audio.tags.add(TCON(encoding=3, text=genre))
    if cover_bytes:
        audio.tags.add(
            APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=cover_bytes,
            )
        )
    audio.save(v2_version=3)


def _tag_mp4(
    path: Path,
    title: str,
    artists: list[str],
    album: str,
    year: str,
    genre: str,
    cover_bytes: Optional[bytes],
    track_number: Optional[int],
    album_track_total: Optional[int],
) -> None:
    audio = MP4(str(path))
    audio['\xa9nam'] = title
    if artists:
        audio['\xa9ART'] = artists
        audio['aART'] = [artists[0]]
    if album:
        audio['\xa9alb'] = album
    if track_number is not None:
        total = album_track_total if album_track_total is not None else 0
        audio['trkn'] = [(track_number, total)]
    if year:
        audio['\xa9day'] = year
    if genre:
        audio['\xa9gen'] = genre
    if cover_bytes:
        audio['covr'] = [
            MP4Cover(cover_bytes, imageformat=MP4Cover.FORMAT_JPEG)
        ]
    audio.save()


def _tag_flac(
    path: Path,
    title: str,
    artists: list[str],
    album: str,
    year: str,
    genre: str,
    cover_bytes: Optional[bytes],
    track_number: Optional[int],
    album_track_total: Optional[int],
) -> None:
    audio = FLAC(str(path))
    audio['title'] = title
    if artists:
        audio['artist'] = artists
        audio['albumartist'] = artists[0]
    if album:
        audio['album'] = album
    if track_number is not None:
        audio['tracknumber'] = str(track_number)
        if album_track_total is not None:
            audio['tracktotal'] = str(album_track_total)
    if year:
        audio['date'] = year
    if genre:
        audio['genre'] = genre
    if cover_bytes:
        picture = Picture()
        picture.data = cover_bytes
        picture.type = 3
        picture.mime = 'image/jpeg'
        audio.clear_pictures()
        audio.add_picture(picture)
    audio.save()


def _tag_ogg_vorbis(
    path: Path,
    title: str,
    artists: list[str],
    album: str,
    year: str,
    genre: str,
    track_number: Optional[int],
    album_track_total: Optional[int],
) -> None:
    audio = OggVorbis(str(path))
    _apply_vorbis_comments(
        audio,
        title,
        artists,
        album,
        year,
        genre,
        track_number,
        album_track_total,
    )
    audio.save()


def _tag_opus(
    path: Path,
    title: str,
    artists: list[str],
    album: str,
    year: str,
    genre: str,
    track_number: Optional[int],
    album_track_total: Optional[int],
) -> None:
    audio = OggOpus(str(path))
    _apply_vorbis_comments(
        audio,
        title,
        artists,
        album,
        year,
        genre,
        track_number,
        album_track_total,
    )
    audio.save()


def _apply_vorbis_comments(
    audio,
    title,
    artists,
    album,
    year,
    genre,
    track_number: Optional[int],
    album_track_total: Optional[int],
):
    audio['title'] = title
    if artists:
        audio['artist'] = artists
        audio['albumartist'] = artists[0]
    if album:
        audio['album'] = album
    if track_number is not None:
        audio['TRACKNUMBER'] = str(track_number)
        if album_track_total is not None:
            audio['TRACKTOTAL'] = str(album_track_total)
    if year:
        audio['date'] = year
    if genre:
        audio['genre'] = genre


def embed_lyrics(path: Path, lyrics: 'lyrics_mod.Lyrics') -> None:
    """Embed plain lyrics into the audio tag and write a .lrc sidecar
    next to it when synced lyrics are available."""

    if not path.exists() or not lyrics.has_any():
        return

    if lyrics.synced:
        sidecar = path.with_suffix('.lrc')
        try:
            sidecar.write_text(lyrics.synced, encoding='utf-8')
        except OSError:
            logger.opt(exception=True).warning(
                'Could not write LRC sidecar {}', sidecar
            )

    text = lyrics.plain or _strip_lrc_timestamps(lyrics.synced or '')
    if not text:
        return

    suffix = path.suffix.lower().lstrip('.')
    if suffix == 'mp3':
        audio = MP3(str(path), ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        audio.tags.delall('USLT')
        audio.tags.add(USLT(encoding=3, lang='eng', desc='', text=text))
        audio.save(v2_version=3)
    elif suffix in {'m4a', 'mp4', 'aac'}:
        audio = MP4(str(path))
        audio['\xa9lyr'] = text
        audio.save()
    elif suffix == 'flac':
        audio = FLAC(str(path))
        audio['lyrics'] = text
        audio.save()
    elif suffix in {'ogg', 'oga'}:
        audio = OggVorbis(str(path))
        audio['lyrics'] = text
        audio.save()
    elif suffix == 'opus':
        audio = OggOpus(str(path))
        audio['lyrics'] = text
        audio.save()


def _strip_lrc_timestamps(synced: str) -> str:
    cleaned = _re.sub(r'\[\d{1,2}:\d{2}(?:\.\d{1,3})?\]', '', synced)
    return '\n'.join(
        line.strip() for line in cleaned.splitlines() if line.strip()
    )
