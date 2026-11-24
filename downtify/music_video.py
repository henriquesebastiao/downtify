"""Music videos: each song's official video, saved next to it (#680).

With **Download music videos** on (``download_music_videos``), every
song Downtify finishes downloading gets its music video looked up on
YouTube Music and saved in the same folder, named after the song's file
by a template (``music_video_name``, default ``{filename}-video`` - the
name Plex links to the track as its music video). The web player then
shows it in Now playing while the song plays.

The lookup only takes a video that is clearly the song's: its title and
artist must match, and live takes, lyric videos, covers, remixes and
"official audio" uploads are left out unless the song itself is one.
Official music videos come first, then the one whose length is closest
to the song's.

Videos are downloaded one at a time on their own thread, after the song
is done, so they never hold up the download queue; a failure is only
logged. :class:`MusicVideos` remembers which video belongs to which
song (by library path), so the player can find it and deleting the song
removes its video too.
"""

from __future__ import annotations

import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import yt_dlp
from loguru import logger

from . import providers
from .db.config import Dialect
from .db.core import Database, as_database

#: Default name: the song's file name plus Plex's ``-video`` suffix.
DEFAULT_NAME = '{filename}-video'
#: What a name template may use.
NAME_VARIABLES = ('filename', 'title', 'artist', 'album', 'track_number')
#: Containers a video is saved in.
FORMATS = ('mp4', 'mkv')
DEFAULT_FORMAT = 'mp4'
#: Extensions a saved video can have, most wanted first.
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.webm')
#: Tallest video downloaded (px).
MAX_HEIGHT = 1080
#: YouTube Music's type for an artist's official music video.
OFFICIAL_TYPE = 'MUSIC_VIDEO_TYPE_OMV'

#: Words that make a video something other than the song's own video -
#: unless the song's title says it too.
_OTHER_VERSION_RE = re.compile(
    r'\b(live|lyrics?|letra|cover|karaoke|reaction|remix|instrumental|'
    r'slowed|sped[ -]?up|nightcore|8d|audio|visuali[sz]er|tutorial|'
    r'teaser|trailer|shorts?|acoustic|performance|session)\b',
    re.IGNORECASE,
)
#: Bracketed decorations of a video title: "(Official Music Video)",
#: "[4K Remaster]", "(Clip officiel)".
_DECORATION_RE = re.compile(
    r'\s*[\(\[][^\)\]]*\b(official|oficial|officiel|video|vídeo|clip|mv|'
    r'hd|4k|hq|remaster(?:ed)?)\b[^\)\]]*[\)\]]',
    re.IGNORECASE,
)
#: Characters a file name can't hold on common filesystems.
_UNSAFE_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_VARIABLE_RE = re.compile(r'\{([a-z_]+)\}')
#: Tolerated length difference (s) before a video counts as another cut.
_LENGTH_SLACK = 45


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Settings ────────────────────────────────────────────────────────────


def clean_template(value: Any) -> str:
    """*value* as a name template: known ``{variables}`` only, no folder
    separators, :data:`DEFAULT_NAME` when it is empty or names nothing."""

    text = str(value or '').strip()
    if not text:
        return DEFAULT_NAME
    for name in _VARIABLE_RE.findall(text):
        if name not in NAME_VARIABLES:
            text = text.replace('{' + name + '}', '')
    text = text.replace('/', '').replace('\\', '').strip()
    if not _VARIABLE_RE.search(text):
        return DEFAULT_NAME
    return text[:200]


def clean_format(value: Any) -> str:
    text = str(value or '').strip().lower().lstrip('.')
    return text if text in FORMATS else DEFAULT_FORMAT


def _artist_of(song: dict[str, Any]) -> str:
    artists = song.get('artists')
    if isinstance(artists, list) and artists:
        return str(artists[0] or '')
    return str(song.get('artist') or '')


def render_name(template: str, track: Path, song: dict[str, Any]) -> str:
    """The video's file name (no extension) for the song at *track*."""

    number = song.get('track_number')
    values = {
        'filename': track.stem,
        'title': str(song.get('name') or song.get('title') or ''),
        'artist': _artist_of(song),
        'album': str(song.get('album_name') or song.get('album') or ''),
        'track_number': f'{int(number):02d}'
        if str(number or '').isdigit()
        else '',
    }
    name = _VARIABLE_RE.sub(
        lambda m: values.get(m.group(1), ''), clean_template(template)
    )
    name = _UNSAFE_RE.sub('_', name).strip(' .')
    if not name or name == track.stem:
        name = f'{track.stem}-video'
    return name


# ── Picking the video ───────────────────────────────────────────────────


def clean_video_title(title: Any) -> str:
    """A video's title without "(Official Video)"-style decorations."""

    return _DECORATION_RE.sub('', str(title or '')).strip()


def _seconds(row: dict[str, Any]) -> Optional[float]:
    value = row.get('duration_seconds')
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    text = str(row.get('duration') or '')
    if not text:
        return None
    try:
        parts = [int(p) for p in text.split(':')]
    except ValueError:
        return None
    total = 0
    for part in parts:
        total = total * 60 + part
    return float(total) or None


def _other_version(video_title: str, song_title: str) -> bool:
    wanted = {w.lower() for w in _OTHER_VERSION_RE.findall(song_title)}
    found = {w.lower() for w in _OTHER_VERSION_RE.findall(video_title)}
    return bool(found - wanted)


def pick_video(
    rows: list[dict[str, Any]],
    *,
    title: str,
    artists: list[str],
    duration: Optional[float],
    titles_match: Callable[[Any, Any], bool],
    artists_overlap: Callable[[list[str], dict[str, Any]], bool],
) -> Optional[dict[str, Any]]:
    """The search row that is the song's music video, or ``None``.

    *titles_match* / *artists_overlap* are the same comparisons the audio
    match uses (:mod:`downtify.providers`), passed in to keep this pure.
    """

    best: Optional[tuple[tuple[int, float], dict[str, Any]]] = None
    for row in rows:
        if not isinstance(row, dict) or not row.get('videoId'):
            continue
        raw_title = str(row.get('title') or '')
        if _other_version(raw_title, title):
            continue
        if not titles_match(title, clean_video_title(raw_title)):
            continue
        if not artists_overlap(artists, row):
            continue
        length = _seconds(row)
        gap = abs(length - duration) if length and duration else 0.0
        if duration and length and length < duration - _LENGTH_SLACK:
            continue
        if duration and length and length > duration * 2 + _LENGTH_SLACK:
            continue
        official = row.get('videoType') == OFFICIAL_TYPE or bool(
            re.search(r'official|oficial|officiel', raw_title, re.I)
        )
        rank = (0 if official else 1, gap)
        if best is None or rank < best[0]:
            best = (rank, row)
    return best[1] if best else None


def search_query(song: dict[str, Any]) -> str:
    title = str(song.get('name') or song.get('title') or '').strip()
    artist = _artist_of(song).strip()
    return f'{artist} {title} official music video'.strip()


def find_video(song: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Look *song*'s music video up on YouTube Music (network)."""

    title = str(song.get('name') or song.get('title') or '').strip()
    if not title:
        return None
    artists = [str(a) for a in song.get('artists') or [] if a] or (
        [_artist_of(song)] if _artist_of(song) else []
    )
    try:
        duration = float(song.get('duration') or 0) or None
    except (TypeError, ValueError):
        duration = None
    rows = providers.search_music_videos(search_query(song))
    return pick_video(
        rows,
        title=title,
        artists=artists,
        duration=duration,
        titles_match=providers.titles_match,
        artists_overlap=providers.artists_overlap,
    )


# ── Downloading ─────────────────────────────────────────────────────────


def ydl_video_options(base: dict[str, Any], container: str) -> dict[str, Any]:
    """*base* (the audio download's yt-dlp options: cookies, clients,
    retries) set up for a video of at most :data:`MAX_HEIGHT` px, H.264
    and AAC first so browsers and media servers play it."""

    opts = dict(base)
    height = f'[height<={MAX_HEIGHT}]'
    opts['format'] = (
        f'bv*{height}[vcodec^=avc1]+ba[ext=m4a]/'
        f'b{height}[ext=mp4]/bv*{height}+ba/b{height}/b'
    )
    opts['merge_output_format'] = container
    opts.pop('postprocessors', None)
    return opts


def saved_video(folder: Path, name: str) -> Optional[Path]:
    """The video saved as *name* in *folder*, whatever its extension."""

    for ext in VIDEO_EXTENSIONS:
        candidate = folder / f'{name}{ext}'
        if candidate.is_file():
            return candidate
    return None


class MusicVideos:
    """``music_videos`` rows: which video belongs to which song."""

    def __init__(self, path_or_db: str | Path | Database) -> None:
        self.db = as_database(path_or_db, 'library')
        self._lock = threading.Lock()
        if self.db.dialect is Dialect.SQLITE:
            with self.db.connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS music_videos (
                        file TEXT PRIMARY KEY,
                        video TEXT NOT NULL,
                        video_id TEXT NOT NULL DEFAULT '',
                        added_at TEXT NOT NULL
                    )
                """)

    @staticmethod
    def _key(file: Any) -> str:
        return str(file or '').strip().replace('\\', '/')

    def get(self, file: str) -> Optional[str]:
        """The library path of *file*'s video, if one was saved."""

        with self.db.connect() as conn:
            row = conn.execute(
                'SELECT video FROM music_videos WHERE file = ?',
                (self._key(file),),
            ).fetchone()
        return str(row['video']) if row else None

    def set(self, file: str, video: str, video_id: str = '') -> None:
        with self._lock, self.db.connect() as conn:
            conn.execute(
                """INSERT INTO music_videos (file, video, video_id, added_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(file) DO UPDATE SET video = excluded.video,
                   video_id = excluded.video_id,
                   added_at = excluded.added_at""",
                (self._key(file), self._key(video), video_id, _now()),
            )

    def forget(self, file: str) -> Optional[str]:
        """Drop *file*'s row; the video's path it named, if any."""

        video = self.get(file)
        if video is not None:
            with self._lock, self.db.connect() as conn:
                conn.execute(
                    'DELETE FROM music_videos WHERE file = ?',
                    (self._key(file),),
                )
        return video

    def count(self) -> int:
        with self.db.connect() as conn:
            row = conn.execute(
                'SELECT COUNT(*) AS n FROM music_videos'
            ).fetchone()
        return int(row['n'])


#: One video download at a time, apart from the song queue.
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='music-video')


def executor() -> ThreadPoolExecutor:
    return _EXECUTOR


def fetch_for_track(
    *,
    song: dict[str, Any],
    stored: str,
    full: Path,
    downloader: Any,
    store: MusicVideos,
    settings: dict[str, Any],
    stored_of: Callable[[Path], str],
) -> Optional[str]:
    """Save the music video of the song at *full* (library path
    *stored*) next to it; the video's library path, or ``None`` when
    there is none to be had. Blocking: run it on :func:`executor`."""

    if store.get(stored):
        return None
    name = render_name(settings.get('music_video_name') or '', full, song)
    container = clean_format(settings.get('music_video_format'))
    already = saved_video(full.parent, name)
    if already is not None:
        store.set(stored, stored_of(already))
        return stored_of(already)
    row = find_video(song)
    if row is None:
        logger.info('No music video found for {}', stored)
        return None
    video_id = str(row['videoId'])
    base, _cookies = downloader._ydl_options(
        str(full.parent / f'{name}.%(ext)s'), lambda _status: None
    )
    opts = ydl_video_options(base, container)
    with (
        downloader._private_cookiefile(opts),
        yt_dlp.YoutubeDL(opts) as ydl,
    ):
        ydl.download([f'https://www.youtube.com/watch?v={video_id}'])
    saved = saved_video(full.parent, name)
    if saved is None:
        logger.warning('Music video {} left no file for {}', video_id, stored)
        return None
    video = stored_of(saved)
    store.set(stored, video, video_id)
    logger.info('Music video saved: {} ({})', video, video_id)
    return video
