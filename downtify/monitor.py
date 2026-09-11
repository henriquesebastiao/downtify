"""Periodic playlist monitoring and automatic downloading."""

from __future__ import annotations

import asyncio
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger

from . import m3u, providers, spotify
from .downloader import Downloader

MONITOR_LOOP_INTERVAL = 60  # seconds between loop sweeps
MINUTES_PER_DAY = 1440

SYNC_TIME_ENV_VAR = 'DOWNTIFY_MONITOR_SYNC_TIME'


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sync_anchor_time() -> Optional[time]:
    """Parse ``DOWNTIFY_MONITOR_SYNC_TIME`` (``HH:MM``, 24h, local time).

    Returns ``None`` when unset or malformed, in which case scheduling
    falls back to the plain ``last_checked + interval`` behavior. Only
    read from the environment at call time (not cached) so it can be
    changed without a restart of the whole process in tests, and so a
    typo doesn't get baked in for the process lifetime.
    """
    raw = os.getenv(SYNC_TIME_ENV_VAR, '').strip()
    if not raw:
        return None
    hour_str, _, minute_str = raw.partition(':')
    try:
        hour = int(hour_str)
        minute = int(minute_str) if minute_str else 0
        return time(hour, minute)
    except ValueError:
        logger.warning(
            '{}={!r} is not a valid HH:MM time; ignoring it.',
            SYNC_TIME_ENV_VAR,
            raw,
        )
        return None


def _next_due_at(last: datetime, interval_minutes: int) -> datetime:
    """Compute when *last*'s next check is due.

    For sub-day intervals this is simply ``last + interval``. For
    intervals that are a whole number of days (daily, weekly, every 2
    weeks, monthly), the result is additionally snapped to the
    :data:`SYNC_TIME_ENV_VAR` time-of-day when it's set, so all
    day-or-longer playlists sync at the same configured hour (e.g.
    ``03:00``) instead of at whatever time the playlist happened to be
    added or last checked. The date component always advances by at
    least one full interval, so the snap never moves the due time
    earlier than an unsnapped ``last + interval`` would allow.
    """
    due = last + timedelta(minutes=interval_minutes)
    if interval_minutes % MINUTES_PER_DAY != 0:
        return due
    anchor = _sync_anchor_time()
    if anchor is None:
        return due
    local_due = due.astimezone()
    anchored_local = local_due.replace(
        hour=anchor.hour, minute=anchor.minute, second=0, microsecond=0
    )
    return anchored_local.astimezone(timezone.utc)


def _is_due(last_checked: Optional[str], interval_minutes: int) -> bool:
    if last_checked is None:
        return True
    try:
        last = datetime.fromisoformat(last_checked)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= _next_due_at(
            last, interval_minutes
        )
    except ValueError:
        return True


KIND_PLAYLIST = 'playlist'
KIND_ARTIST = 'artist'

SOURCE_SPOTIFY = 'spotify'
SOURCE_YOUTUBE_MUSIC = 'youtube_music'


def watch_source(url: str) -> str:
    """The service a watch was added from, read off the URL it was added with.

    Anything that isn't a YouTube URL is Spotify, which is what every
    watch was before YouTube Music ones existed, so older rows need no
    migration.
    """
    if providers.parse_youtube_url(url or '') is not None:
        return SOURCE_YOUTUBE_MUSIC
    return SOURCE_SPOTIFY


def parse_playlist_url(url: str) -> Optional[tuple[str, str]]:
    """``(source, playlist_id)`` for a Spotify or YouTube Music playlist URL."""
    parsed = spotify.parse_spotify_url(url or '')
    if parsed is not None and parsed[0] == 'playlist':
        return SOURCE_SPOTIFY, parsed[1]
    youtube_parsed = providers.parse_youtube_url(url or '')
    if youtube_parsed is not None and youtube_parsed[0] == 'playlist':
        return SOURCE_YOUTUBE_MUSIC, youtube_parsed[1]
    return None


def fetch_playlist(
    source: str, playlist_id: str
) -> tuple[str, list[dict[str, Any]]]:
    """``(name, tracks)`` of a playlist on either service (blocking)."""
    if source == SOURCE_YOUTUBE_MUSIC:
        return providers.playlist_info_and_tracks_from_id(playlist_id)
    return spotify.playlist_info_and_tracks(playlist_id)


@dataclass
class MonitoredPlaylist:
    id: int
    spotify_id: str
    name: str
    url: str
    interval_minutes: int
    enabled: bool
    last_checked: Optional[str]
    last_track_count: int
    created_at: str
    # 'playlist' watches a playlist's tracks; 'artist' watches a YouTube
    # Music artist's discography for new releases. ``spotify_id`` is just
    # the unique key a watch is addressed by: the Spotify or YouTube Music
    # playlist id, or for an artist the YouTube Music channel id.
    kind: str = KIND_PLAYLIST

    @property
    def source(self) -> str:
        return watch_source(self.url)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), 'source': self.source}


class PlaylistMonitorDB:
    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._lock = asyncio.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS monitored_playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spotify_id TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    interval_minutes INTEGER NOT NULL DEFAULT 60,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    last_checked TEXT,
                    last_track_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS downloaded_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER NOT NULL,
                    track_spotify_id TEXT NOT NULL,
                    downloaded_at TEXT NOT NULL,
                    FOREIGN KEY (playlist_id) REFERENCES monitored_playlists(id)
                        ON DELETE CASCADE,
                    UNIQUE(playlist_id, track_spotify_id)
                );
                CREATE TABLE IF NOT EXISTS seen_albums (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER NOT NULL,
                    album_id TEXT NOT NULL,
                    name TEXT,
                    seen_at TEXT NOT NULL,
                    FOREIGN KEY (playlist_id) REFERENCES monitored_playlists(id)
                        ON DELETE CASCADE,
                    UNIQUE(playlist_id, album_id)
                );
            """)
            # Migration: add filename column if it doesn't exist yet
            try:
                conn.execute(
                    'ALTER TABLE downloaded_tracks ADD COLUMN filename TEXT'
                )
            except Exception:
                pass
            # Migration: watches used to be playlists only.
            try:
                conn.execute(
                    'ALTER TABLE monitored_playlists ADD COLUMN kind TEXT '
                    f"NOT NULL DEFAULT '{KIND_PLAYLIST}'"
                )
            except Exception:
                pass

    def add_playlist(
        self,
        spotify_id: str,
        name: str,
        url: str,
        interval_minutes: int = 60,
        kind: str = KIND_PLAYLIST,
    ) -> MonitoredPlaylist:
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO monitored_playlists
                   (spotify_id, name, url, interval_minutes, enabled,
                    created_at, kind)
                   VALUES (?, ?, ?, ?, 1, ?, ?)""",
                (spotify_id, name, url, interval_minutes, _now_iso(), kind),
            )
            row = conn.execute(
                'SELECT * FROM monitored_playlists WHERE id = ?',
                (cur.lastrowid,),
            ).fetchone()
            return _row_to_playlist(row)

    def list_playlists(self) -> list[MonitoredPlaylist]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT * FROM monitored_playlists ORDER BY created_at DESC'
            ).fetchall()
            return [_row_to_playlist(r) for r in rows]

    def get_playlist(self, playlist_id: int) -> Optional[MonitoredPlaylist]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM monitored_playlists WHERE id = ?',
                (playlist_id,),
            ).fetchone()
            return _row_to_playlist(row) if row else None

    def get_by_spotify_id(
        self, spotify_id: str
    ) -> Optional[MonitoredPlaylist]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM monitored_playlists WHERE spotify_id = ?',
                (spotify_id,),
            ).fetchone()
            return _row_to_playlist(row) if row else None

    def delete_playlist(self, playlist_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                'DELETE FROM monitored_playlists WHERE id = ?',
                (playlist_id,),
            )
            return cur.rowcount > 0

    def update_playlist(
        self, playlist_id: int, **kwargs: Any
    ) -> Optional[MonitoredPlaylist]:
        allowed = {
            'interval_minutes',
            'enabled',
            'last_checked',
            'last_track_count',
            'name',
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return self.get_playlist(playlist_id)
        set_clause = ', '.join(f'{k} = ?' for k in updates)
        values = list(updates.values()) + [playlist_id]
        with self._connect() as conn:
            conn.execute(
                f'UPDATE monitored_playlists SET {set_clause} WHERE id = ?',
                values,
            )
            row = conn.execute(
                'SELECT * FROM monitored_playlists WHERE id = ?',
                (playlist_id,),
            ).fetchone()
            return _row_to_playlist(row) if row else None

    def get_track_filenames(
        self, playlist_id: int
    ) -> dict[str, Optional[str]]:
        """Return ``{track_spotify_id: filename}`` for all known tracks."""
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT track_spotify_id, filename FROM downloaded_tracks WHERE playlist_id = ?',
                (playlist_id,),
            ).fetchall()
            return {r['track_spotify_id']: r['filename'] for r in rows}

    def get_seen_album_ids(self, playlist_id: int) -> set[str]:
        """Return the album ids already processed for an artist watch."""
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT album_id FROM seen_albums WHERE playlist_id = ?',
                (playlist_id,),
            ).fetchall()
            return {r['album_id'] for r in rows}

    def mark_album_seen(
        self,
        playlist_id: int,
        album_id: str,
        name: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO seen_albums
                   (playlist_id, album_id, name, seen_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(playlist_id, album_id) DO UPDATE SET
                   name=excluded.name""",
                (playlist_id, album_id, name, _now_iso()),
            )

    def mark_track_downloaded(
        self,
        playlist_id: int,
        track_spotify_id: str,
        filename: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO downloaded_tracks
                   (playlist_id, track_spotify_id, downloaded_at, filename)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(playlist_id, track_spotify_id) DO UPDATE SET
                   downloaded_at=excluded.downloaded_at,
                   filename=excluded.filename""",
                (playlist_id, track_spotify_id, _now_iso(), filename),
            )


def _row_to_playlist(row: sqlite3.Row) -> MonitoredPlaylist:
    keys = row.keys()
    return MonitoredPlaylist(
        id=row['id'],
        spotify_id=row['spotify_id'],
        name=row['name'],
        url=row['url'],
        interval_minutes=row['interval_minutes'],
        enabled=bool(row['enabled']),
        last_checked=row['last_checked'],
        last_track_count=row['last_track_count'],
        created_at=row['created_at'],
        # Rows written before the kind migration have no column at all
        # when reading from a stale connection/schema cache.
        kind=(row['kind'] if 'kind' in keys else KIND_PLAYLIST)
        or KIND_PLAYLIST,
    )


async def _fill_from_spotify_track(song: dict[str, Any]) -> None:
    """Top up a Spotify playlist row from the track's own embed.

    Playlist embed entries are missing release year and use the playlist
    cover instead of the album cover; the per-track embed has both. The
    playlist values stay as a fallback if the per-track fetch fails.
    """
    try:
        full = await asyncio.to_thread(spotify.track_from_id, song['song_id'])
    except Exception:
        logger.opt(exception=True).warning(
            'Per-track Spotify fetch failed for {}; '
            'falling back to playlist data',
            song['song_id'],
        )
        return
    for key in ('cover_url', 'year', 'release_date', 'album_name', 'artists'):
        value = full.get(key)
        if value:
            song[key] = value


async def check_playlist(
    playlist: MonitoredPlaylist,
    db: PlaylistMonitorDB,
    downloader: Downloader,
    broadcast: Callable[[dict[str, Any]], Any],
    loop: asyncio.AbstractEventLoop,
    settings: Optional[dict[str, Any]] = None,
) -> int:
    """Fetch playlist, detect new tracks, download them. Returns count downloaded."""
    logger.info(
        'Checking monitored playlist "{}" ({})',
        playlist.name,
        playlist.spotify_id,
    )

    from_spotify = playlist.source == SOURCE_SPOTIFY
    fetch_tracks = (
        spotify.playlist_tracks_from_id
        if from_spotify
        else providers.playlist_tracks_from_id
    )
    try:
        tracks = await asyncio.to_thread(fetch_tracks, playlist.spotify_id)
    except Exception:
        logger.exception('Failed to fetch playlist {}', playlist.spotify_id)
        await asyncio.to_thread(
            db.update_playlist, playlist.id, last_checked=_now_iso()
        )
        return 0

    known_tracks = await asyncio.to_thread(db.get_track_filenames, playlist.id)

    pl_subdir = m3u.sanitize_playlist_name(playlist.name)

    # Filenames already on disk from earlier sweeps, keyed by track id,
    # topped up as each new track lands. Lets the M3U be rewritten after
    # every single download without re-resolving the whole playlist
    # against the filesystem each time (which is O(tracks) globs per
    # write, and quadratic over a large sweep).
    resolved: dict[str, str] = {}

    new_tracks = []
    for t in tracks:
        if not t.get('song_id'):
            continue
        tid = t['song_id']
        if tid not in known_tracks:
            new_tracks.append(t)
        else:
            stored = known_tracks[tid]
            if stored is None:
                continue
            if not (downloader.download_dir / stored).exists():
                # File was deleted — re-download
                new_tracks.append(t)
            else:
                resolved[tid] = stored

    if new_tracks:
        logger.info(
            'Found {} track(s) to download in playlist "{}"',
            len(new_tracks),
            playlist.name,
        )

    delay_seconds = (settings or {}).get('download_delay_seconds', 0) or 0

    downloaded = 0
    for index, song in enumerate(new_tracks):
        track_id = song['song_id']
        pl_name = playlist.name

        # YouTube Music rows already carry their own video's metadata.
        if from_spotify:
            await _fill_from_spotify_track(song)

        def _make_cb(s: dict, name: str) -> Callable[[float, str], None]:
            def _cb(pct: float, message: str) -> None:
                asyncio.run_coroutine_threadsafe(
                    broadcast({
                        'song': s,
                        'progress': pct,
                        'message': message,
                        'playlist_name': name,
                    }),
                    loop,
                )

            return _cb

        try:
            filename = await loop.run_in_executor(
                None,
                lambda s=song: downloader.download(
                    s, _make_cb(s, pl_name), subdir=pl_subdir
                ),
            )
            await asyncio.to_thread(
                db.mark_track_downloaded, playlist.id, track_id, filename
            )
            downloaded += 1
            if filename:
                resolved[track_id] = filename
            if settings is None or settings.get('generate_m3u', True):
                # Rewrite the M3U after every track rather than once the
                # whole sweep finishes, so the playlist grows as it
                # downloads and a slow/hung track further down the list
                # never holds up what's already on disk.
                await asyncio.to_thread(
                    _regenerate_m3u, playlist, tracks, downloader, resolved
                )
            if delay_seconds > 0 and index != len(new_tracks) - 1:
                await asyncio.sleep(delay_seconds)
        except Exception:
            logger.exception('Failed to auto-download track {}', track_id)

    await asyncio.to_thread(
        db.update_playlist,
        playlist.id,
        last_checked=_now_iso(),
        last_track_count=len(tracks),
    )

    if downloaded > 0 and (
        settings is None or settings.get('generate_m3u', True)
    ):
        await asyncio.to_thread(_regenerate_m3u, playlist, tracks, downloader)
    return downloaded


def _progress_cb(
    song: dict[str, Any],
    label: str,
    broadcast: Callable[[dict[str, Any]], Any],
    loop: asyncio.AbstractEventLoop,
) -> Callable[[float, str], None]:
    """Build a downloader progress callback that broadcasts over the WS."""

    def _cb(pct: float, message: str) -> None:
        asyncio.run_coroutine_threadsafe(
            broadcast({
                'song': song,
                'progress': pct,
                'message': message,
                'playlist_name': label,
            }),
            loop,
        )

    return _cb


async def check_artist(
    playlist: MonitoredPlaylist,
    db: PlaylistMonitorDB,
    downloader: Downloader,
    broadcast: Callable[[dict[str, Any]], Any],
    loop: asyncio.AbstractEventLoop,
    settings: Optional[dict[str, Any]] = None,
) -> int:
    """Download every release of a watched artist that isn't known yet.

    ``playlist.spotify_id`` is the artist's YouTube Music channel id. The
    discography is listed in one call per sweep; only releases missing
    from ``seen_albums`` have their tracklists fetched, so a steady-state
    sweep costs a single request. Returns the number of tracks
    downloaded.
    """
    logger.info(
        'Checking monitored artist "{}" ({})',
        playlist.name,
        playlist.spotify_id,
    )

    try:
        albums = await asyncio.to_thread(
            providers.artist_albums_from_channel_id, playlist.spotify_id
        )
    except Exception:
        logger.exception(
            'Failed to fetch discography for artist {}', playlist.spotify_id
        )
        await asyncio.to_thread(
            db.update_playlist, playlist.id, last_checked=_now_iso()
        )
        return 0

    seen = await asyncio.to_thread(db.get_seen_album_ids, playlist.id)
    new_albums = [
        a for a in albums if a.get('album_id') and a['album_id'] not in seen
    ]
    if new_albums:
        logger.info(
            'Found {} new release(s) for artist "{}"',
            len(new_albums),
            playlist.name,
        )

    delay_seconds = (settings or {}).get('download_delay_seconds', 0) or 0
    known_tracks = await asyncio.to_thread(db.get_track_filenames, playlist.id)

    downloaded = 0
    for album in new_albums:
        album_id = album['album_id']
        try:
            tracks = await asyncio.to_thread(
                providers.album_tracks_from_browse_id, album_id
            )
        except Exception:
            logger.exception(
                'Failed to fetch tracks for release {} ({})',
                album.get('name'),
                album_id,
            )
            continue

        complete = True
        for song in tracks:
            track_id = song.get('song_id')
            if not track_id:
                complete = False
                continue
            if track_id in known_tracks:
                continue
            try:
                filename = await loop.run_in_executor(
                    None,
                    lambda s=song: downloader.download(
                        s, _progress_cb(s, playlist.name, broadcast, loop)
                    ),
                )
                await asyncio.to_thread(
                    db.mark_track_downloaded, playlist.id, track_id, filename
                )
                known_tracks[track_id] = filename
                downloaded += 1
                if delay_seconds > 0:
                    await asyncio.sleep(delay_seconds)
            except Exception:
                complete = False
                logger.exception(
                    'Failed to auto-download track {} of release {}',
                    track_id,
                    album.get('name'),
                )

        # Only remember the release once every track is accounted for, so
        # a transient failure is retried on the next sweep instead of
        # being silently skipped forever. Tracks that already succeeded
        # are cheap to skip via `known_tracks`.
        if complete:
            await asyncio.to_thread(
                db.mark_album_seen, playlist.id, album_id, album.get('name')
            )

    await asyncio.to_thread(
        db.update_playlist,
        playlist.id,
        last_checked=_now_iso(),
        last_track_count=len(albums),
    )
    return downloaded


def _regenerate_m3u(
    playlist: MonitoredPlaylist,
    tracks: list[dict[str, Any]],
    downloader: Downloader,
    resolved: Optional[dict[str, str]] = None,
) -> None:
    """Rewrite the playlist's M3U, in playlist order.

    Walks the full ordered track list (not just the freshly downloaded
    ones) and hands the entries to :func:`m3u.write_m3u`. Tracks with no
    file are dropped, so a partially-downloaded playlist still yields a
    valid, correctly-ordered M3U.

    With *resolved* (``{track_id: filename}``) filenames are taken from
    that map alone — the cheap path used for the rewrite after each
    individual download. Without it every track is resolved against the
    filesystem instead, which is the authoritative view used for the
    final rewrite at the end of a sweep.
    """

    pl_subdir = m3u.sanitize_playlist_name(playlist.name)
    entries: list[dict[str, Any]] = []
    for song in tracks:
        if resolved is None:
            filename = downloader.existing_filename_for(song, subdir=pl_subdir)
        else:
            filename = resolved.get(song.get('song_id') or '')
        if not filename:
            continue
        entries.append({
            'filename': filename,
            'title': song.get('name', ''),
            'artist': ', '.join(song.get('artists') or []),
            'duration': song.get('duration', 0),
        })
    if not entries:
        logger.warning(
            'M3U skip for monitored playlist "{}": no tracks on disk',
            playlist.name,
        )
        return
    # When organize-by-artist/album is on the tracks live in those folders
    # rather than the per-playlist subfolder, so the M3U goes to the legacy
    # Playlists/ directory where its relative paths still resolve.
    organize = downloader.organize_by_artist or downloader.organize_by_album
    m3u.write_m3u(
        downloader.download_dir,
        playlist.name,
        entries,
        playlist_subdir=None if organize else pl_subdir,
    )


# Ids of watches with a check running right now. Adding a watch starts its
# first check immediately, and the background sweep would otherwise start
# a second one for the same never-checked watch while the first is still
# downloading — both then fetch the same tracks into the same files.
_checks_running: set[int] = set()


async def check_watch(
    playlist: MonitoredPlaylist,
    db: PlaylistMonitorDB,
    downloader: Downloader,
    broadcast: Callable[[dict[str, Any]], Any],
    loop: asyncio.AbstractEventLoop,
    settings: Optional[dict[str, Any]] = None,
) -> int:
    """Run the right check for a watch by kind, unless one is already running."""
    if playlist.id in _checks_running:
        logger.info('Watch "{}" is already being checked', playlist.name)
        return 0
    _checks_running.add(playlist.id)
    try:
        check = (
            check_artist if playlist.kind == KIND_ARTIST else check_playlist
        )
        return await check(playlist, db, downloader, broadcast, loop, settings)
    finally:
        _checks_running.discard(playlist.id)


async def monitor_loop(
    db: PlaylistMonitorDB,
    get_downloader: Callable[[], Optional[Downloader]],
    broadcast: Callable[[dict[str, Any]], Any],
    loop: asyncio.AbstractEventLoop,
    settings: Optional[dict[str, Any]] = None,
) -> None:
    """Background task: sweep all enabled playlists that are due for checking."""
    while True:
        try:
            playlists = await asyncio.to_thread(db.list_playlists)
            for pl in playlists:
                if not pl.enabled:
                    continue
                if not _is_due(pl.last_checked, pl.interval_minutes):
                    continue
                downloader = get_downloader()
                if downloader is None:
                    continue
                try:
                    count = await check_watch(
                        pl, db, downloader, broadcast, loop, settings
                    )
                    if count > 0:
                        logger.info(
                            'Auto-downloaded {} new track(s) from "{}"',
                            count,
                            pl.name,
                        )
                except Exception:
                    logger.exception(
                        'Error while checking watch "{}"', pl.name
                    )
        except Exception:
            logger.exception('Unexpected error in monitor loop')
        await asyncio.sleep(MONITOR_LOOP_INTERVAL)
