"""Podcast subscriptions: RSS feeds, episode downloads, and playback state.

Podcasts are not Spotify tracks routed through YouTube — every episode is
already a plain audio file sitting at an RSS ``<enclosure>`` URL, so the
whole yt-dlp/matching pipeline in :mod:`downtify.downloader` is beside
the point here. This module is the podcast equivalent of that file: it
turns a link into episodes, downloads and tags them, and keeps a show in
sync on a schedule.

Three ways in, one destination (an RSS feed URL):

* A direct RSS feed URL is fetched and parsed as-is.
* A Spotify ``show`` or ``episode`` link only ever gives a name (the
  embed page renders the show's latest episode; there is no "show"
  entity to scrape — see :func:`downtify.spotify.fetch_embed_entity`).
  That name is matched against the iTunes podcast directory
  (:mod:`downtify.itunes`) to find the feed. A Spotify-exclusive show
  has no public feed and is reported as such, not silently ignored.
* Free-text search also goes through the iTunes podcast directory.

Episodes are identified by RSS ``guid`` (falling back to the enclosure
URL for feeds sloppy enough to omit one), so re-fetching a feed never
loses track of what is already downloaded, and an episode the user
deleted on purpose (``dismissed``) is never re-downloaded — unlike one
a retention sweep pruned automatically, which is fair game again if the
show's retention setting is later raised. See ``episode_plan`` for the
exact retention rules.

Scheduling reuses :mod:`downtify.monitor`'s watch table (kind
``"podcast"``, keyed by feed URL) rather than a second background loop;
this module only supplies what a podcast watch does when it's checked
(:func:`sync_show`) and everything specific to podcasts (shows,
episodes, tags, playback position) that the generic watch row knows
nothing about.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Optional

import feedparser
import httpx
from loguru import logger
from mutagen.id3 import (
    APIC,
    COMM,
    ID3,
    TALB,
    TCON,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TPOS,
    TRCK,
)
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

from . import itunes
from .image_size import image_short_side
from .library_catalog import PODCASTS_DIRNAME
from .m3u import sanitize_playlist_name
from .spotify import fetch_embed_entity, parse_spotify_url
from .sqlite_utils import connect_sqlite

_FEED_TIMEOUT = 20
_DOWNLOAD_TIMEOUT = httpx.Timeout(15, read=120)
_CHUNK_SIZE = 1 << 16  # 64 KiB

#: Enclosure MIME type -> file extension. Only audio; a video enclosure
#: is dropped at parse time (video podcasts are a non-goal — see the
#: module docstring in the feature docs).
_AUDIO_EXT_BY_MIME = {
    'audio/mpeg': 'mp3',
    'audio/mp3': 'mp3',
    'audio/mp4': 'm4a',
    'audio/x-m4a': 'm4a',
    'audio/aac': 'aac',
    'audio/ogg': 'ogg',
    'audio/opus': 'opus',
    'audio/x-opus+ogg': 'opus',
}


class PodcastFeedNotFoundError(Exception):
    """Raised when a Spotify show/episode has no public RSS feed.

    Carries the show name Spotify gave us, so the caller can tell the
    user plainly what wasn't found rather than reporting a generic
    failure.
    """

    def __init__(self, show_name: str) -> None:
        self.show_name = show_name
        super().__init__(f'No public RSS feed found for {show_name!r}')


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── HTML show notes → plain text ───────────────────────────────────
class _TextExtractor(HTMLParser):
    """Strips tags from podcast descriptions, which are near-always HTML.

    Rendering that HTML would mean sanitizing it against XSS for no
    real benefit (show notes are a paragraph or two, not a document) —
    plain text is the deliberately simpler, safer choice. Block-level
    tags become line breaks so paragraphs stay readable.
    """

    _BLOCK_TAGS = frozenset({
        'p',
        'br',
        'div',
        'li',
        'ul',
        'ol',
        'h1',
        'h2',
        'h3',
        'h4',
    })

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in self._BLOCK_TAGS:
            self._parts.append('\n')

    def handle_endtag(self, tag: str) -> None:
        if tag in self._BLOCK_TAGS:
            self._parts.append('\n')

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def text(self) -> str:
        joined = html.unescape(''.join(self._parts))
        # Collapse the blank-line runs the tag-per-line pass above
        # tends to produce, and trim trailing spaces on each line.
        lines = [ln.strip() for ln in joined.splitlines()]
        out: list[str] = []
        for ln in lines:
            if ln or (out and out[-1]):
                out.append(ln)
        return '\n'.join(out).strip()


def strip_html(text: str) -> str:
    """Plain-text rendering of a (possibly-HTML) show/episode description."""

    if not text:
        return ''
    if '<' not in text:
        return html.unescape(text).strip()
    parser = _TextExtractor()
    try:
        parser.feed(text)
    except Exception:
        # Malformed markup: better a few stray tags than no description.
        return re.sub(r'<[^>]+>', ' ', text).strip()
    return parser.text()


def _parse_itunes_duration(raw: Any) -> float:
    """``itunes:duration`` as seconds: ``"1:02:03"``, ``"12:34"`` or ``"754"``."""

    text = str(raw or '').strip()
    if not text:
        return 0.0
    if ':' not in text:
        try:
            return float(text)
        except ValueError:
            return 0.0
    parts = text.split(':')
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return 0.0
    seconds = 0.0
    for n in nums:
        seconds = seconds * 60 + n
    return seconds


def _safe_int(raw: Any) -> Optional[int]:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


# ── Parsed feed shape ───────────────────────────────────────────────
@dataclass
class EpisodeInfo:
    guid: str
    title: str
    description: str
    published_at: str  # ISO 8601 UTC, or '' when unparseable
    duration_seconds: float
    season_number: Optional[int]
    episode_number: Optional[int]
    enclosure_url: str
    enclosure_type: str


@dataclass
class ParsedFeed:
    name: str
    author: str
    description: str
    artwork_url: str
    feed_url: str
    episodes: list[EpisodeInfo] = field(default_factory=list)


def _entry_enclosure(entry: Any) -> Optional[tuple[str, str]]:
    for enc in entry.get('enclosures') or []:
        url = str(enc.get('href') or '').strip()
        mime = str(enc.get('type') or '').strip().lower()
        if not url:
            continue
        if mime.startswith('video/'):
            continue
        return url, mime
    return None


def parse_feed_bytes(content: bytes, feed_url: str) -> ParsedFeed:
    """Parse RSS/Atom bytes into a :class:`ParsedFeed`.

    ``feedparser`` is deliberately used instead of a hand-rolled
    ``xml.etree`` reader: real podcast feeds are routinely malformed
    (unescaped ``&``, mismatched encodings, non-standard date formats),
    and surviving that is feedparser's entire job — it sets a ``bozo``
    flag rather than raising, and still returns whatever it could
    recover. Episodes with no usable audio enclosure (missing, or video)
    are dropped rather than listed as unplayable.
    """

    parsed = feedparser.parse(content)
    if parsed.bozo:
        logger.info(
            'Podcast feed {} parsed with warnings: {}',
            feed_url,
            parsed.get('bozo_exception'),
        )
    feed = parsed.feed
    name = str(feed.get('title') or '').strip()
    author = str(feed.get('author') or feed.get('itunes_author') or '').strip()
    description = strip_html(
        str(feed.get('subtitle') or feed.get('summary') or '')
    )
    image = feed.get('image') or {}
    artwork_url = str(
        (image.get('href') if isinstance(image, dict) else '') or ''
    ).strip()

    episodes: list[EpisodeInfo] = []
    for entry in parsed.entries:
        enclosure = _entry_enclosure(entry)
        if enclosure is None:
            continue
        url, mime = enclosure
        guid = str(entry.get('id') or entry.get('guid') or url).strip()
        if not guid:
            continue
        published_at = ''
        if entry.get('published_parsed'):
            try:
                published_at = datetime(
                    *entry.published_parsed[:6], tzinfo=timezone.utc
                ).isoformat()
            except (TypeError, ValueError):
                published_at = ''
        episodes.append(
            EpisodeInfo(
                guid=guid,
                title=str(entry.get('title') or 'Untitled episode').strip(),
                description=strip_html(str(entry.get('summary') or '')),
                published_at=published_at,
                duration_seconds=_parse_itunes_duration(
                    entry.get('itunes_duration')
                ),
                season_number=_safe_int(entry.get('itunes_season')),
                episode_number=_safe_int(entry.get('itunes_episode')),
                enclosure_url=url,
                enclosure_type=mime,
            )
        )
    return ParsedFeed(
        name=name or feed_url,
        author=author,
        description=description,
        artwork_url=artwork_url,
        feed_url=feed_url,
        episodes=episodes,
    )


def fetch_feed(feed_url: str) -> ParsedFeed:
    """Fetch and parse a podcast RSS feed (blocking)."""

    resp = httpx.get(
        feed_url,
        timeout=_FEED_TIMEOUT,
        follow_redirects=True,
        headers={
            'User-Agent': 'Downtify/podcasts (+https://github.com/henriquesebastiao/downtify)'
        },
    )
    resp.raise_for_status()
    return parse_feed_bytes(resp.content, feed_url)


# ── Resolving what the user pasted/typed ───────────────────────────
def _normalize_for_match(text: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', text.casefold())).strip()


def match_episode(
    episodes: list[EpisodeInfo], title: str
) -> Optional[EpisodeInfo]:
    """Best-effort match of a Spotify episode title into a feed's episodes.

    Titles rarely match byte-for-byte (Spotify sometimes drops a
    numbering prefix a feed keeps, or vice versa), so this is a
    normalized-substring match, the same tolerance
    :mod:`downtify.itunes` uses for songs.
    """

    target = _normalize_for_match(title)
    if not target:
        return None
    for ep in episodes:
        candidate = _normalize_for_match(ep.title)
        if candidate == target or target in candidate or candidate in target:
            return ep
    return None


def resolve_spotify_podcast(url: str) -> tuple[ParsedFeed, Optional[str]]:
    """Resolve a Spotify show/episode URL to its feed.

    Returns ``(feed, matched_episode_guid)`` — the guid is set only for
    an episode link whose title could be matched into the feed.
    Raises :class:`PodcastFeedNotFoundError` when Spotify resolves a
    name but iTunes has no public feed for it (the expected outcome for
    a Spotify-exclusive show), and ``ValueError`` for anything else
    that goes wrong reading the Spotify side.
    """

    parsed = parse_spotify_url(url)
    if parsed is None or parsed[0] not in {'show', 'episode'}:
        raise ValueError('Not a Spotify show or episode link')
    kind, spotify_id = parsed
    entity = fetch_embed_entity(kind, spotify_id)
    show_name = str(entity.get('subtitle') or '').strip()
    if not show_name:
        raise ValueError('Could not read the show name from Spotify')
    match = itunes.resolve_podcast_feed(show_name)
    if match is None or not match.get('feed_url'):
        raise PodcastFeedNotFoundError(show_name)
    feed = fetch_feed(match['feed_url'])
    if not feed.artwork_url and match.get('artwork_url'):
        feed.artwork_url = itunes.artwork_url_at(match['artwork_url'], 1200)
    matched_guid = None
    if kind == 'episode':
        episode_title = str(entity.get('name') or '').strip()
        found = (
            match_episode(feed.episodes, episode_title)
            if episode_title
            else None
        )
        matched_guid = found.guid if found else None
    return feed, matched_guid


def search_shows(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """iTunes podcast directory search, for the free-text search box."""

    return [
        {
            'name': r.get('collectionName', ''),
            'author': r.get('artistName', ''),
            'feed_url': r.get('feedUrl', ''),
            'artwork_url': r.get('artworkUrl600', ''),
        }
        for r in itunes.search_podcasts(query, limit=limit)
    ]


# ── Cover art: the largest of the feed's own image and iTunes' ─────
def _fetch_image_bytes(url: str) -> Optional[bytes]:
    if not url:
        return None
    try:
        resp = httpx.get(url, timeout=_FEED_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        return resp.content
    except Exception:
        logger.opt(exception=True).debug(
            'Podcast artwork fetch failed: {}', url
        )
        return None


def best_cover_bytes(
    feed_artwork_url: str, itunes_artwork_url: str = ''
) -> Optional[bytes]:
    """The larger of the feed's own artwork and iTunes', by pixel size.

    Same "largest available" idea as ``cover_sources.py`` uses for
    music, just with two candidates instead of four — podcasts have no
    Spotify or YouTube Music artwork to compare against.
    """

    candidates = []
    for url in (
        feed_artwork_url,
        itunes.artwork_url_at(itunes_artwork_url, 1200)
        if itunes_artwork_url
        else '',
    ):
        if not url:
            continue
        data = _fetch_image_bytes(url)
        if data:
            candidates.append((image_short_side(data), data))
    if not candidates:
        return None
    return max(candidates, key=lambda c: c[0])[1]


# ── Tagging ──────────────────────────────────────────────────────────
def embed_podcast_tags(
    path: Path,
    *,
    title: str,
    show_name: str,
    author: str,
    published_at: str,
    description: str,
    episode_number: Optional[int],
    season_number: Optional[int],
    cover_bytes: Optional[bytes],
) -> None:
    """Tag a downloaded episode: title, show as album, author as artist.

    Episode/season map onto track/disc number — the same fields most
    podcast apps and media servers already read for that purpose.
    ``description`` goes in a comment field rather than a dedicated
    podcast-only frame, so it round-trips through ordinary players too.
    A container this doesn't recognize is left untagged (still a
    perfectly playable file) rather than failing the download.
    """

    year = published_at[:4] if published_at[:4].isdigit() else ''
    comment = description[:2000]
    suffix = path.suffix.lower().lstrip('.')
    try:
        if suffix == 'mp3':
            _tag_mp3_episode(
                path,
                title,
                show_name,
                author,
                year,
                comment,
                episode_number,
                season_number,
                cover_bytes,
            )
        elif suffix in {'m4a', 'mp4', 'aac'}:
            _tag_mp4_episode(
                path,
                title,
                show_name,
                author,
                year,
                comment,
                episode_number,
                season_number,
                cover_bytes,
            )
        elif suffix == 'ogg':
            _tag_vorbis_episode(
                OggVorbis(str(path)),
                title,
                show_name,
                author,
                year,
                comment,
                episode_number,
                season_number,
            )
        elif suffix == 'opus':
            _tag_vorbis_episode(
                OggOpus(str(path)),
                title,
                show_name,
                author,
                year,
                comment,
                episode_number,
                season_number,
            )
        else:
            logger.info('Podcast tagging: unsupported container {}', path.name)
    except Exception:
        logger.opt(exception=True).warning(
            'Podcast tagging failed for {}', path
        )


def _tag_mp3_episode(
    path: Path,
    title: str,
    album: str,
    artist: str,
    year: str,
    comment: str,
    episode: Optional[int],
    season: Optional[int],
    cover_bytes: Optional[bytes],
) -> None:
    audio = MP3(str(path), ID3=ID3)
    if audio.tags is None:
        audio.add_tags()
    audio.tags.delall('APIC')
    audio.tags.add(TIT2(encoding=3, text=title))
    if artist:
        audio.tags.add(TPE1(encoding=3, text=artist))
        audio.tags.add(TPE2(encoding=3, text=artist))
    if album:
        audio.tags.add(TALB(encoding=3, text=album))
    if year:
        audio.tags.add(TDRC(encoding=3, text=year))
    if episode is not None:
        audio.tags.add(TRCK(encoding=3, text=str(episode)))
    if season is not None:
        audio.tags.add(TPOS(encoding=3, text=str(season)))
    audio.tags.add(TCON(encoding=3, text='Podcast'))
    if comment:
        audio.tags.delall('COMM')
        audio.tags.add(COMM(encoding=3, lang='eng', desc='', text=comment))
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
    audio.save(v2_version=4)


def _tag_mp4_episode(
    path: Path,
    title: str,
    album: str,
    artist: str,
    year: str,
    comment: str,
    episode: Optional[int],
    season: Optional[int],
    cover_bytes: Optional[bytes],
) -> None:
    audio = MP4(str(path))
    audio['\xa9nam'] = [title]
    if artist:
        audio['\xa9ART'] = [artist]
        audio['aART'] = [artist]
    if album:
        audio['\xa9alb'] = [album]
    if year:
        audio['\xa9day'] = [year]
    if episode is not None:
        audio['\xa9ep'] = [str(episode)]
        audio['trkn'] = [(episode, 0)]
    if season is not None:
        audio['disk'] = [(season, 0)]
    audio['\xa9gen'] = ['Podcast']
    audio['pcst'] = [True]
    if comment:
        audio['\xa9cmt'] = [comment]
    if cover_bytes:
        audio['covr'] = [
            MP4Cover(cover_bytes, imageformat=MP4Cover.FORMAT_JPEG)
        ]
    audio.save()


def _tag_vorbis_episode(
    audio: Any,
    title: str,
    album: str,
    artist: str,
    year: str,
    comment: str,
    episode: Optional[int],
    season: Optional[int],
) -> None:
    # No cover here: OggVorbis/OggOpus picture blocks need base64 METADATA_BLOCK_PICTURE
    # handling music downloads don't need either (they already ship separate helpers
    # in downloader.py); episodes still get every text tag, just not embedded art.
    audio['title'] = [title]
    if artist:
        audio['artist'] = [artist]
    if album:
        audio['album'] = [album]
    if year:
        audio['date'] = [year]
    if episode is not None:
        audio['tracknumber'] = [str(episode)]
    if season is not None:
        audio['discnumber'] = [str(season)]
    audio['genre'] = ['Podcast']
    if comment:
        audio['description'] = [comment]
    audio.save()


# ── Downloading an episode ──────────────────────────────────────────
ProgressCallback = Callable[[float], None]


def _extension_for(enclosure_type: str, enclosure_url: str) -> str:
    ext = _AUDIO_EXT_BY_MIME.get(enclosure_type)
    if ext:
        return ext
    suffix = (
        Path(enclosure_url.split('?', maxsplit=1)[0])
        .suffix.lower()
        .lstrip('.')
    )
    return suffix if suffix and len(suffix) <= 4 else 'mp3'


def episode_filename(episode: EpisodeInfo) -> str:
    date_prefix = episode.published_at[:10] if episode.published_at else ''
    ext = _extension_for(episode.enclosure_type, episode.enclosure_url)
    base = sanitize_playlist_name(episode.title)
    name = f'{date_prefix} - {base}' if date_prefix else base
    return f'{name}.{ext}'


def download_episode(
    episode: EpisodeInfo,
    *,
    show_name: str,
    author: str,
    folder_name: str,
    download_dir: Path,
    cover_bytes: Optional[bytes],
    progress: Optional[ProgressCallback] = None,
) -> str:
    """Download one episode's enclosure, tag it, return its library path.

    Streamed straight to disk — episodes are already-compressed audio,
    so unlike music there is no transcode step. Raises on a network or
    filesystem failure; callers decide whether that fails just this
    episode or the whole sync sweep.
    """

    show_dir = download_dir / PODCASTS_DIRNAME / folder_name
    show_dir.mkdir(parents=True, exist_ok=True)
    target = show_dir / episode_filename(episode)

    total = 0
    written = 0
    with httpx.stream(
        'GET',
        episode.enclosure_url,
        timeout=_DOWNLOAD_TIMEOUT,
        follow_redirects=True,
    ) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get('content-length') or 0)
        tmp = target.with_suffix(target.suffix + '.part')
        with open(tmp, 'wb') as fh:
            for chunk in resp.iter_bytes(_CHUNK_SIZE):
                fh.write(chunk)
                written += len(chunk)
                if progress and total:
                    progress(min(99.0, written / total * 100))
        tmp.replace(target)

    embed_podcast_tags(
        target,
        title=episode.title,
        show_name=show_name,
        author=author,
        published_at=episode.published_at,
        description=episode.description,
        episode_number=episode.episode_number,
        season_number=episode.season_number,
        cover_bytes=cover_bytes,
    )
    if progress:
        progress(100.0)
    return f'{PODCASTS_DIRNAME}/{folder_name}/{target.name}'


# ── Storage ──────────────────────────────────────────────────────────
def _show_dict(row: Any) -> dict[str, Any]:
    return {
        'id': row['id'],
        'feed_url': row['feed_url'],
        'name': row['name'],
        'author': row['author'],
        'description': row['description'],
        'artwork_url': row['artwork_url'],
        'source_url': row['source_url'],
        'folder_name': row['folder_name'],
        'retention': row['retention'],
        'created_at': row['created_at'],
    }


def _episode_dict(row: Any) -> dict[str, Any]:
    return {
        'id': row['id'],
        'show_id': row['show_id'],
        'guid': row['guid'],
        'title': row['title'],
        'description': row['description'],
        'published_at': row['published_at'],
        'duration_seconds': row['duration_seconds'],
        'season_number': row['season_number'],
        'episode_number': row['episode_number'],
        'enclosure_url': row['enclosure_url'],
        'enclosure_type': row['enclosure_type'],
        'filename': row['filename'],
        'downloaded_at': row['downloaded_at'],
        'dismissed': bool(row['dismissed']),
        'position_seconds': row['position_seconds'] or 0,
        'played': bool(row['played'] or 0),
    }


class PodcastStore:
    """Shows, episodes and per-episode playback position.

    Lives in the same ``downtify_library.db`` as the other library
    stores (``likes.py``, ``track_index.py``, ...). Scheduling — the
    interval, enabled flag and last-checked time — is *not* kept here;
    it lives in :class:`downtify.monitor.PlaylistMonitorDB`'s watch
    table (kind ``"podcast"``, keyed by ``feed_url``), which already
    does exactly that job for playlists and artists.
    """

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self):
        conn = connect_sqlite(self._path, row_factory=True)
        # Needed per-connection (SQLite doesn't persist it in the file);
        # without it, deleting a show would silently orphan its episode
        # and playback rows instead of cascading to them.
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS podcast_shows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feed_url TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    author TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    artwork_url TEXT NOT NULL DEFAULT '',
                    source_url TEXT NOT NULL DEFAULT '',
                    folder_name TEXT NOT NULL,
                    retention INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS podcast_episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    show_id INTEGER NOT NULL,
                    guid TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    published_at TEXT NOT NULL DEFAULT '',
                    duration_seconds REAL NOT NULL DEFAULT 0,
                    season_number INTEGER,
                    episode_number INTEGER,
                    enclosure_url TEXT NOT NULL DEFAULT '',
                    enclosure_type TEXT NOT NULL DEFAULT '',
                    filename TEXT,
                    downloaded_at TEXT,
                    dismissed INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (show_id) REFERENCES podcast_shows(id)
                        ON DELETE CASCADE,
                    UNIQUE(show_id, guid)
                );
                CREATE TABLE IF NOT EXISTS podcast_playback (
                    episode_id INTEGER PRIMARY KEY,
                    position_seconds REAL NOT NULL DEFAULT 0,
                    played INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (episode_id) REFERENCES podcast_episodes(id)
                        ON DELETE CASCADE
                );
            """)

    # ── shows ────────────────────────────────────────────────────
    def add_show(
        self,
        feed_url: str,
        name: str,
        *,
        author: str = '',
        description: str = '',
        artwork_url: str = '',
        source_url: str = '',
        retention: int = 0,
    ) -> dict[str, Any]:
        folder_name = sanitize_playlist_name(name)
        with self._connect() as conn:
            existing = {
                r['folder_name']
                for r in conn.execute(
                    'SELECT folder_name FROM podcast_shows'
                ).fetchall()
            }
            if folder_name in existing:
                # Two shows can share a sanitized name ("Radiolab" vs a
                # differently-cased duplicate feed); keep folders unique
                # rather than silently interleaving their episodes.
                suffix = 2
                while f'{folder_name} ({suffix})' in existing:
                    suffix += 1
                folder_name = f'{folder_name} ({suffix})'
            cur = conn.execute(
                """INSERT INTO podcast_shows
                   (feed_url, name, author, description, artwork_url,
                    source_url, folder_name, retention, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    feed_url,
                    name,
                    author,
                    description,
                    artwork_url,
                    source_url,
                    folder_name,
                    retention,
                    _now_iso(),
                ),
            )
            row = conn.execute(
                'SELECT * FROM podcast_shows WHERE id = ?', (cur.lastrowid,)
            ).fetchone()
            return _show_dict(row)

    def get_show(self, show_id: int) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM podcast_shows WHERE id = ?', (show_id,)
            ).fetchone()
            return _show_dict(row) if row else None

    def get_show_by_feed_url(self, feed_url: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM podcast_shows WHERE feed_url = ?', (feed_url,)
            ).fetchone()
            return _show_dict(row) if row else None

    def list_shows(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT * FROM podcast_shows ORDER BY name COLLATE NOCASE'
            ).fetchall()
            return [_show_dict(r) for r in rows]

    def update_show(
        self, show_id: int, **fields: Any
    ) -> Optional[dict[str, Any]]:
        allowed = {
            'name',
            'author',
            'description',
            'artwork_url',
            'retention',
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_show(show_id)
        with self._connect() as conn:
            set_clause = ', '.join(f'{k} = ?' for k in updates)
            conn.execute(
                f'UPDATE podcast_shows SET {set_clause} WHERE id = ?',
                [*updates.values(), show_id],
            )
        return self.get_show(show_id)

    def delete_show(self, show_id: int) -> Optional[dict[str, Any]]:
        show = self.get_show(show_id)
        if show is None:
            return None
        with self._connect() as conn:
            conn.execute('DELETE FROM podcast_shows WHERE id = ?', (show_id,))
        return show

    # ── episodes ─────────────────────────────────────────────────
    def upsert_episodes(
        self, show_id: int, episodes: list[EpisodeInfo]
    ) -> list[dict[str, Any]]:
        """Insert episodes new to this show; leave existing rows untouched.

        Returns the newly-inserted rows. A guid already on file is
        never updated from the feed — otherwise a show correcting a
        typo in an old episode's title would look, from here, exactly
        like nothing happened, which is fine; but it also means a
        ``dismissed`` or already-downloaded row can never be silently
        resurrected by a later fetch.
        """

        inserted: list[dict[str, Any]] = []
        with self._connect() as conn:
            known = {
                r['guid']
                for r in conn.execute(
                    'SELECT guid FROM podcast_episodes WHERE show_id = ?',
                    (show_id,),
                ).fetchall()
            }
            for ep in episodes:
                if ep.guid in known:
                    continue
                cur = conn.execute(
                    """INSERT INTO podcast_episodes
                       (show_id, guid, title, description, published_at,
                        duration_seconds, season_number, episode_number,
                        enclosure_url, enclosure_type)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        show_id,
                        ep.guid,
                        ep.title,
                        ep.description,
                        ep.published_at,
                        ep.duration_seconds,
                        ep.season_number,
                        ep.episode_number,
                        ep.enclosure_url,
                        ep.enclosure_type,
                    ),
                )
                row = conn.execute(
                    """SELECT e.*, p.position_seconds, p.played
                       FROM podcast_episodes e
                       LEFT JOIN podcast_playback p ON p.episode_id = e.id
                       WHERE e.id = ?""",
                    (cur.lastrowid,),
                ).fetchone()
                inserted.append(_episode_dict(row))
                known.add(ep.guid)
        return inserted

    def list_episodes(
        self, show_id: int, *, include_dismissed: bool = True
    ) -> list[dict[str, Any]]:
        query = """
            SELECT e.*, p.position_seconds, p.played
            FROM podcast_episodes e
            LEFT JOIN podcast_playback p ON p.episode_id = e.id
            WHERE e.show_id = ?
        """
        if not include_dismissed:
            query += ' AND e.dismissed = 0'
        query += ' ORDER BY e.published_at DESC, e.id DESC'
        with self._connect() as conn:
            rows = conn.execute(query, (show_id,)).fetchall()
            return [_episode_dict(r) for r in rows]

    def get_episode(self, episode_id: int) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT e.*, p.position_seconds, p.played
                   FROM podcast_episodes e
                   LEFT JOIN podcast_playback p ON p.episode_id = e.id
                   WHERE e.id = ?""",
                (episode_id,),
            ).fetchone()
            return _episode_dict(row) if row else None

    def mark_downloaded(self, episode_id: int, filename: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """UPDATE podcast_episodes
                   SET filename = ?, downloaded_at = ?, dismissed = 0
                   WHERE id = ?""",
                (filename, _now_iso(), episode_id),
            )

    def prune_download(self, episode_id: int, *, dismissed: bool) -> None:
        """Forget an episode's downloaded file.

        ``dismissed=True`` is a deliberate user delete: never
        auto-download it again. ``dismissed=False`` is an automatic
        retention prune: eligible to come back if retention is raised.
        """

        with self._connect() as conn:
            conn.execute(
                """UPDATE podcast_episodes
                   SET filename = NULL, downloaded_at = NULL, dismissed = ?
                   WHERE id = ?""",
                (1 if dismissed else 0, episode_id),
            )

    def set_playback(
        self,
        episode_id: int,
        *,
        position_seconds: Optional[float] = None,
        played: Optional[bool] = None,
    ) -> None:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM podcast_playback WHERE episode_id = ?',
                (episode_id,),
            ).fetchone()
            pos = row['position_seconds'] if row else 0.0
            was_played = bool(row['played']) if row else False
            if position_seconds is not None:
                pos = max(0.0, position_seconds)
            if played is not None:
                was_played = played
            conn.execute(
                """INSERT INTO podcast_playback
                       (episode_id, position_seconds, played, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(episode_id) DO UPDATE SET
                       position_seconds = excluded.position_seconds,
                       played = excluded.played,
                       updated_at = excluded.updated_at""",
                (episode_id, pos, int(was_played), _now_iso()),
            )

    def downloaded_episodes(self, show_id: int) -> list[dict[str, Any]]:
        """Downloaded, non-dismissed episodes, newest first."""

        return [
            e
            for e in self.list_episodes(show_id)
            if e['filename'] and not e['dismissed']
        ]


# ── Sync: fetch a feed, download what the retention policy wants ──
def episode_plan(
    store: PodcastStore,
    show: dict[str, Any],
    new_episodes: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """``(to_download, to_prune)`` for a show, given its retention setting.

    Two distinct policies, matching how people actually describe this:

    * ``retention == 0`` — "download everything new": every episode
      the feed has ever published is fair game once seen, but the very
      first sync only grabs the single most recent one (a fresh
      subscribe isn't an invitation to pull a show's entire back
      catalog). Nothing is ever pruned.
    * ``retention == N`` — "keep the latest N": after this sync, the N
      most recently published episodes are downloaded and anything
      older that was downloaded is pruned — a rolling window, checked
      on every sync including the first.
    """

    retention = int(show['retention'] or 0)
    downloaded = store.downloaded_episodes(show['id'])
    if retention == 0:
        if downloaded or not new_episodes:
            # Steady state: whatever showed up since the last check.
            return new_episodes, []
        # First sync ever: just the newest episode.
        newest = max(new_episodes, key=lambda e: e['published_at'] or '')
        return [newest], []

    all_known = store.list_episodes(show['id'], include_dismissed=False)
    by_recency = sorted(
        all_known, key=lambda e: e['published_at'] or '', reverse=True
    )
    keep = by_recency[:retention]
    keep_ids = {e['id'] for e in keep}
    to_download = [e for e in keep if not e['filename']]
    to_prune = [e for e in downloaded if e['id'] not in keep_ids]
    return to_download, to_prune


def sync_show(
    store: PodcastStore,
    show: dict[str, Any],
    download_dir: Path,
    *,
    progress: Optional[Callable[[dict[str, Any]], None]] = None,
) -> int:
    """Fetch a show's feed and bring its downloads in line with retention.

    Returns the number of episodes downloaded. Safe to call for the
    first-ever sync (right after subscribing) and every scheduled one
    after — the only difference is what :func:`episode_plan` decides to
    do, not this function's own logic.
    """

    feed = fetch_feed(show['feed_url'])
    inserted = store.upsert_episodes(show['id'], feed.episodes)
    metadata_updates = {}
    if feed.description and feed.description != show['description']:
        metadata_updates['description'] = feed.description
    if feed.author and feed.author != show['author']:
        metadata_updates['author'] = feed.author
    if feed.artwork_url and feed.artwork_url != show['artwork_url']:
        metadata_updates['artwork_url'] = feed.artwork_url
    if metadata_updates:
        show = store.update_show(show['id'], **metadata_updates) or show

    to_download, to_prune = episode_plan(store, show, inserted)
    for ep in to_prune:
        full = download_dir / ep['filename']
        try:
            full.unlink(missing_ok=True)
        except OSError:
            logger.opt(exception=True).warning(
                'Could not remove pruned episode {}', full
            )
        store.prune_download(ep['id'], dismissed=False)

    if not to_download:
        return 0

    cover_bytes = best_cover_bytes(show['artwork_url'])
    downloaded = 0
    for ep_row in to_download:
        info = EpisodeInfo(
            guid=ep_row['guid'],
            title=ep_row['title'],
            description=ep_row['description'],
            published_at=ep_row['published_at'],
            duration_seconds=ep_row['duration_seconds'],
            season_number=ep_row['season_number'],
            episode_number=ep_row['episode_number'],
            enclosure_url=ep_row['enclosure_url'],
            enclosure_type=ep_row['enclosure_type'],
        )

        def _report(pct: float, _ep=ep_row) -> None:
            if progress:
                progress({
                    'show': show['name'],
                    'episode': _ep['title'],
                    'progress': pct,
                })

        try:
            filename = download_episode(
                info,
                show_name=show['name'],
                author=show['author'],
                folder_name=show['folder_name'],
                download_dir=download_dir,
                cover_bytes=cover_bytes,
                progress=_report,
            )
            store.mark_downloaded(ep_row['id'], filename)
            downloaded += 1
        except Exception:
            logger.exception(
                'Podcast episode download failed: "{}" ({})',
                ep_row['title'],
                show['name'],
            )
    return downloaded
