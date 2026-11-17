"""Scale rehearsal for the SQLite-to-PostgreSQL migration.

Builds a synthetic install (every store, as the parity test does), fills it
with ``--tracks`` library rows and the rows that go with them (playlists,
likes, owners, download log, caches, activity, history) using raw SQL, then
runs ``migrate`` into a fresh PostgreSQL schema and prints per-table counts,
timings and peak memory. Afterwards a few store lookups on the migrated
database are compared with the same lookups on the SQLite originals.

Everything lives under a temporary directory and the PostgreSQL schema is
dropped at the end, even on failure. Synthetic data only.

    uv run --frozen python benchmarks/migrate_scale.py --tracks 100000 \\
        --database-url postgresql://postgres@localhost:55432/downtify_test
"""

from __future__ import annotations

import argparse
import functools
import json
import resource
import shutil
import string
import sys
import tempfile
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from downtify.activity import ActivityLog  # noqa: E402
from downtify.auth import AuthStore  # noqa: E402
from downtify.compilation import CompilationMarks  # noqa: E402
from downtify.db.core import Database  # noqa: E402
from downtify.db.migrate_sqlite import (  # noqa: E402
    Report,
    format_report,
    migrate,
)
from downtify.deemix_upgrade_store import AudioReplacementStore  # noqa: E402
from downtify.discover import DiscoverStore  # noqa: E402
from downtify.doctor_audio import AudioHashCache  # noqa: E402
from downtify.download_log import DownloadLog  # noqa: E402
from downtify.download_queue import PendingDownloads  # noqa: E402
from downtify.duplicate_merge import KeptApart  # noqa: E402
from downtify.external_playlists import ExternalPlaylistImports  # noqa: E402
from downtify.file_providers import FileProviders  # noqa: E402
from downtify.library_listing_store import LibraryListingStore  # noqa: E402
from downtify.library_metadata_cache import (  # noqa: E402
    LibraryMetadataCache,
)
from downtify.library_sync import LibrarySync  # noqa: E402
from downtify.library_trash import LibraryTrash, TrashRoot  # noqa: E402
from downtify.library_upgrade_db import LibraryUpgradeDB  # noqa: E402
from downtify.library_usage import UsageSnapshots  # noqa: E402
from downtify.library_visibility import LibraryVisibility  # noqa: E402
from downtify.likes import LikedTracks  # noqa: E402
from downtify.loudness import LoudnessAnalyzer  # noqa: E402
from downtify.lyrics_cache import LyricsLookupCache  # noqa: E402
from downtify.monitor import PlaylistMonitorDB  # noqa: E402
from downtify.navidrome_index import NavidromeIndex  # noqa: E402
from downtify.playlist_batches import PlaylistBatchStore  # noqa: E402
from downtify.playlist_catalog import (  # noqa: E402
    ManualPlaylistOwners,
    PlaylistCatalog,
)
from downtify.playlist_hidden import PlaylistHiddenSongs  # noqa: E402
from downtify.playlist_shares import PlaylistShares  # noqa: E402
from downtify.playlist_spotify_cache import (  # noqa: E402
    PlaylistSpotifyCache,
)
from downtify.podcasts import PodcastStore  # noqa: E402
from downtify.track_index import TrackIndex  # noqa: E402
from downtify.track_owners import TrackOwners  # noqa: E402
from downtify.traffic import TrafficCounters  # noqa: E402

LIBRARY_FILE = 'downtify_library.db'
ACTIVITY_FILE = 'downtify_activity.db'
MONITOR_FILE = 'downtify_monitor.db'

PLAYLISTS = 200
LIKE_EVERY = 10
OWNERS = 3
SMALL_ROWS = 5000
DISCOVER_ROWS = 3000
ID_ALPHABET = string.digits + string.ascii_letters
ID_LENGTH = 22
PLAYLIST_ID_BASE = 1 << 60
BASE_TIME = datetime(2024, 1, 1, tzinfo=timezone.utc)
BYTES_PER_MB = 1024 * 1024
MAX_SHOWN = 90

# Stores whose constructor takes only the library database path. Same list
# as tests/db/test_schema_parity.py, so every table the server creates is
# present in the source files.
_LIBRARY_STORES: tuple[Callable[[Path], Any], ...] = (
    TrackIndex,
    NavidromeIndex,
    LibraryMetadataCache,
    LibraryListingStore,
    PlaylistCatalog,
    ManualPlaylistOwners,
    PlaylistShares,
    PlaylistHiddenSongs,
    FileProviders,
    DownloadLog,
    UsageSnapshots,
    ExternalPlaylistImports,
    PlaylistBatchStore,
    PendingDownloads,
    PlaylistSpotifyCache,
    LyricsLookupCache,
    LikedTracks,
    TrackOwners,
    LibraryVisibility,
    CompilationMarks,
    PodcastStore,
    LibrarySync,
    DiscoverStore,
    LibraryUpgradeDB,
    AudioReplacementStore,
)


def _build_sqlite(root: Path) -> dict[str, Path]:
    """Open every store the server builds, on files named as in production.

    Returns the six SQLite files keyed by their path relative to the data
    directory. The data directory is ``root / 'data'``.
    """

    data = root / 'data'
    doctor = data / 'doctor'
    downloads = root / 'downloads'
    doctor.mkdir(parents=True)
    downloads.mkdir()
    library = data / LIBRARY_FILE
    monitor = data / MONITOR_FILE
    auth = data / 'downtify_auth.db'
    activity = data / ACTIVITY_FILE
    audio = doctor / 'audio_hashes.db'
    kept = doctor / 'duplicates.db'

    for store in _LIBRARY_STORES:
        store(library)
    LoudnessAnalyzer(library, lambda: None)
    TrafficCounters(library)
    LibraryTrash(library, {'downloads': TrashRoot(downloads)})
    PlaylistMonitorDB(monitor)
    AuthStore(auth, data / '.auth_secret')
    ActivityLog(activity)
    AudioHashCache(audio)
    KeptApart(kept)

    return {
        LIBRARY_FILE: library,
        MONITOR_FILE: monitor,
        'downtify_auth.db': auth,
        ACTIVITY_FILE: activity,
        'doctor/audio_hashes.db': audio,
        'doctor/duplicates.db': kept,
    }


def _track_id(index: int) -> str:
    """A stable, Spotify-shaped (22 base62 characters) id for *index*."""

    chars = []
    value = index
    for _ in range(ID_LENGTH):
        value, digit = divmod(value, len(ID_ALPHABET))
        chars.append(ID_ALPHABET[digit])
    return ''.join(reversed(chars))


def _path(index: int) -> str:
    return (
        f'Artist {index % 4000:04d}/Album {index // 12:06d}/'
        f'{index % 12 + 1:02d} - Track {index:07d}.mp3'
    )


def _ck(index: int) -> str:
    return f'ck{index:010d}'


def _ts(index: int) -> str:
    return (BASE_TIME + timedelta(seconds=index)).isoformat()


def _playlist_name(index: int) -> str:
    return f'Playlist {index:03d}'


def _playlist_sid(index: int) -> str:
    return _track_id(PLAYLIST_ID_BASE + index)


def _artists_json(index: int) -> str:
    """Three artist objects, about 500 bytes, as the library cache stores."""

    artists = []
    for k in range(3):
        artist_id = _track_id(index + k)
        artists.append({
            'id': artist_id,
            'name': f'Artist {(index + k) % 4000:04d}',
            'external_urls': {
                'spotify': f'https://open.spotify.com/artist/{artist_id}'
            },
        })
    return json.dumps(artists)


def _row_json(index: int) -> str:
    return json.dumps({
        'file': _path(index),
        'title': f'Title {index}',
        'artist': f'Artist {index % 4000:04d}',
        'album': f'Album {index // 12:06d}',
        'album_artist': f'Artist {index % 4000:04d}',
        'track_number': index % 12 + 1,
        'duration': 180.0 + index % 120,
        'year': '2019',
        'explicit': False,
    })


def _track_json(index: int) -> str:
    """About 2 KB of Spotify-like track JSON."""

    return json.dumps({
        'id': _track_id(index),
        'name': f'Title {index}',
        'artists': json.loads(_artists_json(index)),
        'album': {'name': f'Album {index // 12:06d}'},
        'duration_ms': 180000 + index % 120000,
        'explicit': False,
        'popularity': index % 100,
        'padding': f'{index:08d}' * 240,
    })


def _library_tracks(n: int) -> Iterator[tuple[Any, ...]]:
    for i in range(n):
        yield (_track_id(i), _path(i), _ck(i), _ts(i))


def _library_metadata(n: int) -> Iterator[tuple[Any, ...]]:
    for i in range(n):
        yield (
            _ck(i),
            _path(i),
            f'Title {i}',
            f'Artist {i % 4000:04d}',
            f'Album {i // 12:06d}',
            1,
            1400,
            f'Artist {i % 4000:04d}',
            i % 12 + 1,
            '2019',
            '2019-05-01',
            180.0 + i % 120,
            1,
            'mp3',
            320000,
            44100,
            2,
            'Pop',
            int(i % 7 == 0),
            _artists_json(i),
            0,
            1_700_000_000_000_000_000 + i,
            5_000_000 + i % 1000,
            _ts(i),
        )


def _sync_tracks(n: int) -> Iterator[tuple[Any, ...]]:
    for i in range(n):
        yield (
            _track_id(i),
            _path(i),
            _ck(i),
            '',
            _row_json(i),
            f'{i:040x}',
            i + 1,
            None,
        )


def _sync_meta(n: int) -> Iterator[tuple[Any, ...]]:
    yield ('seq', n)


def _playlists(_n: int) -> Iterator[tuple[Any, ...]]:
    for p in range(PLAYLISTS):
        yield (_playlist_name(p), _playlist_sid(p), _ts(p), 0)


def _playlist_tracks(n: int) -> Iterator[tuple[Any, ...]]:
    for i in range(n):
        yield (
            _playlist_name(i % PLAYLISTS),
            _track_id(i),
            _ck(i),
            _path(i),
            i // PLAYLISTS,
        )


def _liked_tracks(n: int) -> Iterator[tuple[Any, ...]]:
    for i in range(0, n, LIKE_EVERY):
        yield (
            _path(i),
            0,
            _ck(i),
            f'Title {i}',
            f'Artist {i % 4000:04d}',
            180.0 + i % 120,
            _ts(i),
        )


def _track_owners(n: int) -> Iterator[tuple[Any, ...]]:
    for i in range(n):
        yield (_ck(i), i % OWNERS, _ts(i), _path(i))


def _download_log(n: int) -> Iterator[tuple[Any, ...]]:
    for i in range(n):
        yield (
            _ts(i),
            'ok' if i % 9 else 'failed',
            'youtube',
            4_000_000 + i,
            _path(i),
        )


def _spotify_track_cache(n: int) -> Iterator[tuple[Any, ...]]:
    for i in range(n):
        yield (_track_id(i), _track_json(i), _ts(i))


def _discover_search(n: int) -> Iterator[tuple[Any, ...]]:
    for i in range(n):
        yield (f'artist-{i}', json.dumps({'items': []}), _ts(i))


def _discover_related(n: int) -> Iterator[tuple[Any, ...]]:
    for i in range(n):
        yield (f'artist-{i}', str(i), '[]', _ts(i))


def _discover_listens(n: int) -> Iterator[tuple[Any, ...]]:
    for i in range(n):
        yield (f'artist-{i}', 0, f'Artist {i}', i % 50, _ts(i))


def _activity(n: int) -> Iterator[tuple[Any, ...]]:
    for i in range(n):
        yield (
            _ts(i),
            i % OWNERS,
            f'user{i % OWNERS}',
            'download',
            f'Downloaded track {i}',
            json.dumps({'track': _track_id(i)}),
            'web',
            '192.0.2.10',
        )


def _monitored_playlists(_n: int) -> Iterator[tuple[Any, ...]]:
    for p in range(PLAYLISTS):
        sid = _playlist_sid(p)
        yield (
            sid,
            _playlist_name(p),
            f'https://open.spotify.com/playlist/{sid}',
            60,
            1,
            None,
            0,
            _ts(p),
            0,
        )


def _watch_events(n: int) -> Iterator[tuple[Any, ...]]:
    for i in range(n):
        p = i % PLAYLISTS
        yield (
            p + 1,
            f'watch-{p:03d}',
            _playlist_name(p),
            0,
            _track_id(i),
            'downloaded',
            _path(i),
            'youtube',
            0,
            _ts(i),
        )


@dataclass(frozen=True)
class _Feed:
    file: str
    table: str
    columns: tuple[str, ...]
    count: int
    rows: Callable[[], Iterator[tuple[Any, ...]]]


_LIB_COLUMNS = {
    'library_tracks': (
        'spotify_track_id',
        'filename',
        'content_key',
        'registered_at',
    ),
    'library_metadata': (
        'content_key',
        'filename',
        'title',
        'artist',
        'album',
        'has_cover',
        'cover_px',
        'album_artist',
        'track_number',
        'year',
        'release_date',
        'duration',
        'meta_version',
        'codec',
        'bitrate',
        'sample_rate',
        'channels',
        'genre',
        'explicit',
        'artists',
        'compilation',
        'file_mtime_ns',
        'file_size',
        'cached_at',
    ),
    'sync_tracks': (
        'track_id',
        'path',
        'content_key',
        'tag_key',
        'row_json',
        'row_hash',
        'seq',
        'deleted_at',
    ),
    'sync_meta': ('key', 'value'),
    'playlists': ('name', 'spotify_id', 'updated_at', 'user_id'),
    'playlist_tracks': (
        'playlist_name',
        'track_spotify_id',
        'content_key',
        'filename',
        'track_order',
    ),
    'liked_tracks': (
        'stored_path',
        'user_id',
        'content_key',
        'title',
        'artist',
        'duration',
        'liked_at',
    ),
    'track_owners': ('content_key', 'user_id', 'added_at', 'stored_path'),
    'download_log': ('at', 'outcome', 'provider', 'bytes', 'filename'),
    'spotify_track_cache': ('track_spotify_id', 'track_json', 'fetched_at'),
    'discover_search': ('artist_key', 'results_json', 'fetched_at'),
    'discover_related': (
        'artist_key',
        'deezer_id',
        'related_json',
        'fetched_at',
    ),
    'discover_listens': (
        'artist_key',
        'user_id',
        'name',
        'plays',
        'last_played',
    ),
    'activity': (
        'at',
        'user_id',
        'username',
        'kind',
        'summary',
        'detail_json',
        'client',
        'ip',
    ),
    'monitored_playlists': (
        'spotify_id',
        'name',
        'url',
        'interval_minutes',
        'enabled',
        'last_checked',
        'last_track_count',
        'created_at',
        'user_id',
    ),
    'watch_events': (
        'playlist_id',
        'watch_key',
        'watch_name',
        'user_id',
        'track_id',
        'outcome',
        'filename',
        'provider',
        'initial',
        'happened_at',
    ),
}


def _feeds(n: int) -> list[_Feed]:
    likes = len(range(0, n, LIKE_EVERY))
    lib = LIBRARY_FILE
    cols = _LIB_COLUMNS

    def feed(file: str, table: str, count: int, rows: Callable[..., Any]):
        return _Feed(file, table, cols[table], count, rows)

    return [
        feed(lib, 'library_tracks', n, functools.partial(_library_tracks, n)),
        feed(
            lib, 'library_metadata', n, functools.partial(_library_metadata, n)
        ),
        feed(lib, 'sync_tracks', n, functools.partial(_sync_tracks, n)),
        feed(lib, 'sync_meta', 1, functools.partial(_sync_meta, n)),
        feed(lib, 'playlists', PLAYLISTS, functools.partial(_playlists, n)),
        feed(
            lib, 'playlist_tracks', n, functools.partial(_playlist_tracks, n)
        ),
        feed(lib, 'liked_tracks', likes, functools.partial(_liked_tracks, n)),
        feed(lib, 'track_owners', n, functools.partial(_track_owners, n)),
        feed(lib, 'download_log', n, functools.partial(_download_log, n)),
        feed(
            lib,
            'spotify_track_cache',
            n,
            functools.partial(_spotify_track_cache, n),
        ),
        feed(
            lib,
            'discover_search',
            DISCOVER_ROWS,
            functools.partial(_discover_search, DISCOVER_ROWS),
        ),
        feed(
            lib,
            'discover_related',
            DISCOVER_ROWS,
            functools.partial(_discover_related, DISCOVER_ROWS),
        ),
        feed(
            lib,
            'discover_listens',
            DISCOVER_ROWS,
            functools.partial(_discover_listens, DISCOVER_ROWS),
        ),
        feed(
            ACTIVITY_FILE,
            'activity',
            SMALL_ROWS,
            functools.partial(_activity, SMALL_ROWS),
        ),
        feed(
            MONITOR_FILE,
            'monitored_playlists',
            PLAYLISTS,
            functools.partial(_monitored_playlists, n),
        ),
        feed(
            MONITOR_FILE,
            'watch_events',
            SMALL_ROWS,
            functools.partial(_watch_events, SMALL_ROWS),
        ),
    ]


def _insert_sql(feed: _Feed) -> str:
    names = ', '.join(feed.columns)
    marks = ', '.join('?' for _ in feed.columns)
    return f'INSERT INTO {feed.table} ({names}) VALUES ({marks})'


def _generate(files: dict[str, Path], n: int) -> dict[str, float]:
    """Insert the synthetic rows with raw SQL; returns seconds per table."""

    timings: dict[str, float] = {}
    for feed in _feeds(n):
        statement = _insert_sql(feed)
        db = Database.sqlite(files[feed.file])
        started = time.perf_counter()
        with db.transaction() as conn:
            conn.executemany(statement, feed.rows())
        timings[feed.table] = time.perf_counter() - started
        print(
            f'  {feed.table:<22} {feed.count:>9} rows '
            f'{timings[feed.table]:>7.2f}s'
        )
    return timings


def _peak_rss_mb() -> float:
    """Process peak RSS. ru_maxrss is bytes on macOS, kilobytes on Linux."""

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == 'darwin':
        return peak / BYTES_PER_MB
    return peak / 1024


def _create_schema(url: str, schema: str) -> None:
    with closing(psycopg.connect(url, autocommit=True)) as admin:
        admin.execute(
            sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema))
        )


def _drop_schema(url: str, schema: str) -> None:
    with closing(psycopg.connect(url, autocommit=True)) as admin:
        admin.execute(
            sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(
                sql.Identifier(schema)
            )
        )


def _print_report(report: Report, seconds: float) -> None:
    header = (
        f'{"table":<24}{"file":<26}{"source":>10}{"skipped":>9}'
        f'{"copied":>10}{"target":>10}  checksum'
    )
    print(header)
    total = 0
    for t in report.tables:
        total += t.copied
        check = 'ok' if t.checksum_ok else 'MISMATCH'
        print(
            f'{t.name:<24}{t.source_file:<26}{t.source_rows:>10}'
            f'{t.skipped:>9}{t.copied:>10}{t.target_rows:>10}  {check}'
        )
    print(f'Report ok: {report.ok}')
    for problem in report.problems:
        print(f'  - {problem}')
    rate = total / seconds if seconds else 0.0
    print(f'Copied {total} rows in {seconds:.2f}s: {rate:,.0f} rows/second')


def _check(name: str, pg_value: Any, sqlite_value: Any) -> bool:
    ok = pg_value == sqlite_value
    shown = repr(pg_value)
    if len(shown) > MAX_SHOWN:
        shown = shown[: MAX_SHOWN - 3] + '...'
    print(f'  {name:<40} {"match" if ok else "MISMATCH"}  {shown}')
    return ok


def _spot_check(target: Database, library: Path, n: int) -> bool:
    """Compare a few lookups on the migrated store with SQLite's answers."""

    picks = sorted({0, n // 2, n - 1})
    track_ids = [_track_id(i) for i in picks]
    paths = [_path(i) for i in picks]
    pg_sync = LibrarySync(target)
    sq_sync = LibrarySync(library)
    pg_likes = LikedTracks(target)
    sq_likes = LikedTracks(library)
    pg_catalog = PlaylistCatalog(target)
    sq_catalog = PlaylistCatalog(library)
    first, last = _playlist_name(0), _playlist_name(PLAYLISTS - 1)

    results = [
        _check('LibrarySync.cursor', pg_sync.cursor(), sq_sync.cursor()),
        _check(
            'LibrarySync.row_for (3 ids)',
            [pg_sync.row_for(t) for t in track_ids],
            [sq_sync.row_for(t) for t in track_ids],
        ),
        _check(
            'LibrarySync.ids_for_paths (3 paths)',
            pg_sync.ids_for_paths(paths),
            sq_sync.ids_for_paths(paths),
        ),
        _check('LikedTracks.count', pg_likes.count(), sq_likes.count()),
        _check(
            'LikedTracks.rows (user 0)',
            pg_likes.rows(0),
            sq_likes.rows(0),
        ),
        _check(
            'PlaylistCatalog.list_playlist_names',
            pg_catalog.list_playlist_names(),
            sq_catalog.list_playlist_names(),
        ),
        _check(
            f'PlaylistCatalog.list_tracks ({first})',
            pg_catalog.list_tracks(first),
            sq_catalog.list_tracks(first),
        ),
        _check(
            f'PlaylistCatalog.list_tracks ({last})',
            pg_catalog.list_tracks(last),
            sq_catalog.list_tracks(last),
        ),
        _check(
            'PlaylistCatalog.playlists_for_track (3 ids)',
            [pg_catalog.playlists_for_track(t) for t in track_ids],
            [sq_catalog.playlists_for_track(t) for t in track_ids],
        ),
    ]
    return all(results)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument(
        '--tracks',
        type=int,
        default=100_000,
        help='library rows to generate (default: 100000)',
    )
    parser.add_argument(
        '--database-url',
        required=True,
        help='PostgreSQL URL; a fresh scale_<uuid8> schema is created in it',
    )
    args = parser.parse_args(argv)
    if args.tracks < 1:
        parser.error('--tracks must be at least 1')
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    url = args.database_url
    schema = f'scale_{uuid.uuid4().hex[:8]}'
    root = Path(tempfile.mkdtemp(prefix='downtify-migrate-scale-'))
    target: Database | None = None
    ok = False
    try:
        print(f'Temp dir: {root}')
        print(f'Schema:   {schema}')
        print(f'Tracks:   {args.tracks}')

        started = time.perf_counter()
        files = _build_sqlite(root)
        print(f'Stores built in {time.perf_counter() - started:.2f}s')

        print('Generating synthetic rows:')
        started = time.perf_counter()
        _generate(files, args.tracks)
        gen_seconds = time.perf_counter() - started
        print(
            f'Generation: {gen_seconds:.2f}s, peak RSS {_peak_rss_mb():.0f} MB'
        )

        _create_schema(url, schema)
        target = Database.postgres(url, search_path=schema, max_size=4)

        started = time.perf_counter()
        report = migrate(root / 'data', target)
        migrate_seconds = time.perf_counter() - started
        print(f'Migration peak RSS (process so far): {_peak_rss_mb():.0f} MB')
        _print_report(report, migrate_seconds)

        print('Spot checks (migrated PostgreSQL vs SQLite source):')
        spot_ok = _spot_check(target, files[LIBRARY_FILE], args.tracks)
        ok = report.ok and spot_ok
        print(f'Spot checks: {"all match" if spot_ok else "MISMATCH"}')
        print(f'Overall: {"OK" if ok else "FAILED"}')
        if not report.ok:
            print(format_report(report))
    finally:
        if target is not None:
            target.close()
        _drop_schema(url, schema)
        shutil.rmtree(root, ignore_errors=True)
        print(f'Dropped schema {schema}; removed {root}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
