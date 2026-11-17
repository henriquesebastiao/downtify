"""migrate_sqlite: copy a populated SQLite install into PostgreSQL.

Runs only when ``TEST_DATABASE_URL`` points at a PostgreSQL server. Every
test gets a fresh schema, dropped afterwards.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg import sql

from downtify.activity import ActivityLog
from downtify.auth import AuthStore
from downtify.db.core import Database
from downtify.db.migrate_sqlite import (
    MARKER_NAME,
    MigrationError,
    format_report,
    migrate,
    verify,
)
from downtify.duplicate_merge import KeptApart
from downtify.library_sync import LibrarySync
from downtify.likes import LikedTracks
from downtify.lyrics_cache import LyricsLookupCache
from downtify.monitor import PlaylistMonitorDB
from downtify.playlist_catalog import PlaylistCatalog
from downtify.podcasts import EpisodeInfo, PodcastStore
from downtify.track_owners import TrackOwners
from downtify.traffic import DIRECTION_OUT, TrafficCounters
from downtify.users import ROLE_USER
from tests.db.helpers import execute, query
from tests.db.test_schema_parity import _build_sqlite

_URL_ENV = 'TEST_DATABASE_URL'
SID_A = '4uLU6hMCjMI75M1A2tKUQC'
SID_B = '2dLLR6qlu5UJ5gk0dKz83h'
ORPHAN_PARENT = 'Ghost Playlist'
SIX_FILES = (
    'downtify_library.db',
    'downtify_monitor.db',
    'downtify_auth.db',
    'downtify_activity.db',
    'doctor/audio_hashes.db',
    'doctor/duplicates.db',
)

pytestmark = pytest.mark.skipif(
    not os.environ.get(_URL_ENV),
    reason=f'{_URL_ENV} not set',
)


@dataclass
class _Install:
    data: Path
    files: dict[str, Path]
    uid: int = 0
    token: str = ''
    sync_cursor: int = 0
    expected: dict[str, Any] = field(default_factory=dict)


def _entry(path: str, title: str) -> dict[str, Any]:
    return {
        'file': path,
        'title': title,
        'artist': 'Ana',
        'album': 'Sun',
        'duration': 120.0,
        'size': 1000,
        'track_number': 1,
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sqlite_tables(path: Path) -> list[str]:
    with closing(sqlite3.connect(path)) as conn:
        return [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND substr(name, 1, 7) <> 'sqlite_'"
            )
        ]


def _sqlite_count(path: Path, table: str) -> int:
    with closing(sqlite3.connect(path)) as conn:
        return int(
            conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        )


def _seed_library(lib: Path, music: Path, uid: int) -> int:
    """Library rows through the real stores; returns the sync cursor."""

    catalog = PlaylistCatalog(lib)
    rows = [
        (
            {
                'id': SID_A,
                'song_id': SID_A,
                'name': 'One',
                'subtitle': 'Ana',
            },
            'a/one.flac',
            music / 'one.flac',
        ),
        (
            {
                'id': SID_B,
                'song_id': SID_B,
                'name': 'Two',
                'subtitle': 'Ana',
            },
            'a/two.flac',
            music / 'two.flac',
        ),
    ]
    catalog.replace_playlist_tracks('Road Trip', rows, user_id=uid)

    LikedTracks(lib).like(
        'a/one.flac',
        content_key='ck-one',
        title='One',
        artist='Ana',
        duration=120.0,
        user_id=uid,
    )
    LikedTracks(lib).like('a/two.flac', content_key='ck-two', user_id=uid)
    TrackOwners(lib).add('ck-one', uid, 'a/one.flac')

    sync = LibrarySync(lib)
    sync.refresh(
        [_entry('a/one.flac', 'One'), _entry('a/two.flac', 'Two')], now=NOW
    )
    assert sync.touch('a/one.flac') is True

    podcasts = PodcastStore(lib)
    show = podcasts.add_show(
        'https://feeds.example/show.xml', 'Show', user_id=uid
    )
    podcasts.upsert_episodes(
        int(show['id']),
        [
            EpisodeInfo(
                guid='g1',
                title='Episode 1',
                description='',
                published_at='2026-01-01T00:00:00+00:00',
                duration_seconds=600.0,
                season_number=None,
                episode_number=1,
                enclosure_url='https://feeds.example/e1.mp3',
                enclosure_type='audio/mpeg',
            )
        ],
    )

    counters = TrafficCounters(lib)
    counters.add(uid, DIRECTION_OUT, 4096)
    counters.flush()
    LyricsLookupCache(lib).record('one ana', 'lrclib', False)

    # SQLite never enforced this foreign key: a playlist_tracks row whose
    # playlist does not exist, written with raw SQL.
    with closing(sqlite3.connect(lib)) as conn:
        conn.execute(
            'INSERT INTO playlist_tracks (playlist_name, track_spotify_id, '
            'content_key, filename, track_order) VALUES (?, ?, ?, ?, ?)',
            (ORPHAN_PARENT, 'ORPHAN1', 'ck-ghost', 'g/ghost.flac', 0),
        )
        conn.commit()
    return sync.cursor()


def _seed_rest(files: dict[str, Path], music: Path, uid: int) -> None:
    """Monitor, activity and doctor rows."""

    monitor = PlaylistMonitorDB(files['downtify_monitor.db'])
    watch = monitor.add_playlist(
        '37i9dQZF1',
        'Mix',
        'https://open.spotify.com/playlist/37i9dQZF1',
        user_id=uid,
    )
    monitor.mark_track_downloaded(watch.id, SID_A, 'a/one.flac')

    ActivityLog(files['downtify_activity.db']).record(
        'login', user_id=uid, username='maria', summary='signed in'
    )

    # The audio digest needs real audio, so the cached row is written
    # directly, in the table AudioHashCache reads.
    st = (music / 'one.flac').stat()
    with closing(sqlite3.connect(files['doctor/audio_hashes.db'])) as conn:
        conn.execute(
            'INSERT INTO audio_hashes (path, size, mtime_ns, digest) '
            'VALUES (?, ?, ?, ?)',
            (str(music / 'one.flac'), st.st_size, st.st_mtime_ns, 'd41d8'),
        )
        conn.commit()
    KeptApart(files['doctor/duplicates.db']).keep([
        str(music / 'one.flac'),
        str(music / 'two.flac'),
    ])


def _populate(root: Path) -> _Install:
    """A populated install on SQLite, built with the real store methods.

    The SQLite-backed answers are recorded in ``expected`` before any
    hashing, since reads can write.
    """

    files = _build_sqlite(root)
    data = root / 'data'
    music = root / 'music'
    music.mkdir()
    for name in ('one.flac', 'two.flac'):
        (music / name).write_bytes(name.encode() * 4)
    lib = files['downtify_library.db']

    auth = AuthStore(files['downtify_auth.db'], data / '.auth_secret')
    uid = int(auth.users.create('maria', 'password123', role=ROLE_USER)['id'])
    token = auth.create_session(uid, '203.0.113.5', 'test-agent')

    install = _Install(data=data, files=files, uid=uid, token=token)
    install.sync_cursor = _seed_library(lib, music, uid)
    _seed_rest(files, music, uid)

    likes = LikedTracks(lib)
    catalog = PlaylistCatalog(lib)
    show_id = int(PodcastStore(lib).list_shows(uid)[0]['id'])
    install.expected = {
        'playlists': catalog.list_playlist_names(),
        'road_trip': sorted(
            str(r['track_spotify_id'])
            for r in catalog.list_tracks('Road Trip')
        ),
        'likes': sorted(
            (r['stored_path'], r['user_id']) for r in likes.rows(uid)
        ),
        'show_name': PodcastStore(lib).get_show(show_id)['name'],
        'kept': sorted(KeptApart(files['doctor/duplicates.db']).pairs()),
        'traffic': TrafficCounters(lib).totals()[uid][DIRECTION_OUT],
    }
    return install


NOW = datetime.fromisoformat('2026-01-01T00:00:00+00:00')


@pytest.fixture
def pg_schema() -> Iterator[tuple[str, str]]:
    url = os.environ[_URL_ENV]
    schema = f'sc_{uuid.uuid4().hex[:8]}'
    with closing(psycopg.connect(url, autocommit=True)) as admin:
        admin.execute(
            sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema))
        )
    try:
        yield url, schema
    finally:
        with closing(psycopg.connect(url, autocommit=True)) as admin:
            admin.execute(
                sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(
                    sql.Identifier(schema)
                )
            )


def _count(db: Database, table: str) -> int:
    return int(query(db, f'SELECT COUNT(*) FROM "{table}"')[0][0])


def test_migrate_copies_and_verifies(tmp_path: Path, pg_schema) -> None:
    url, schema = pg_schema
    install = _populate(tmp_path)
    sources = {
        table: _sqlite_count(path, table)
        for path in install.files.values()
        for table in _sqlite_tables(path)
    }
    sqlite_before = {name: _sha256(p) for name, p in install.files.items()}

    db = Database.postgres(url, search_path=schema, max_size=4)
    try:
        report = migrate(install.data, db)
        assert report.ok, format_report(report)
        assert report.problems == []
        assert sorted(report.files_found) == sorted(SIX_FILES)

        names = [t.name for t in report.tables]
        assert set(names) == set(sources)
        assert names.index('playlists') < names.index('playlist_tracks')
        assert names.index('podcast_shows') < names.index('podcast_episodes')

        by_name = {t.name: t for t in report.tables}
        for table, count in sources.items():
            skip = 1 if table == 'playlist_tracks' else 0
            row = by_name[table]
            assert row.source_rows == count
            assert row.skipped == skip
            assert row.copied == count - skip
            assert row.target_rows == count - skip
            assert row.checksum_ok is True
            assert _count(db, table) == count - skip
        assert by_name['traffic_counters'].source_file == (
            'downtify_library.db'
        )
        assert (
            query(
                db,
                'SELECT COUNT(*) FROM playlist_tracks WHERE playlist_name = ?',
                ORPHAN_PARENT,
            )[0][0]
            == 0
        )
        assert 'Result: OK' in format_report(report)

        # Identity sequences: a new row gets an id past every copied id.
        max_before = query(db, 'SELECT MAX(id) FROM liked_tracks')[0][0]
        assert LikedTracks(db).count(install.uid) == 2
        LikedTracks(db).like('new.flac', user_id=install.uid)
        new_id = query(
            db, "SELECT id FROM liked_tracks WHERE stored_path = 'new.flac'"
        )[0][0]
        assert new_id > max_before

        # library_sync: the sequence matches the copied cursor and goes on.
        assert LibrarySync(db).cursor() == install.sync_cursor
        seq = query(db, 'SELECT last_value, is_called FROM library_sync_seq')
        assert tuple(seq[0]) == (install.sync_cursor, True)
        assert LibrarySync(db).touch('a/one.flac') is True
        assert LibrarySync(db).cursor() == install.sync_cursor + 1

        _check_stores(db, install)

        marker = install.data / MARKER_NAME
        assert marker.exists()
        datetime.fromisoformat(marker.read_text(encoding='utf-8').strip())
    finally:
        db.close()

    assert {n: _sha256(p) for n, p in install.files.items()} == sqlite_before


def _check_stores(db: Database, install: _Install) -> None:
    """Sequences continue, and the PostgreSQL stores answer as SQLite did."""

    expected = install.expected
    assert PlaylistCatalog(db).list_playlist_names() == (expected['playlists'])
    assert (
        sorted(
            str(r['track_spotify_id'])
            for r in PlaylistCatalog(db).list_tracks('Road Trip')
        )
        == expected['road_trip']
    )
    assert (
        sorted(
            (r['stored_path'], r['user_id'])
            for r in LikedTracks(db).rows(install.uid)
            if r['stored_path'] != 'new.flac'
        )
        == expected['likes']
    )
    user = AuthStore(db, install.data / '.auth_secret').session_user(
        install.token
    )
    assert user is not None
    assert int(user['id']) == install.uid
    assert user['username'] == 'maria'
    assert (
        PodcastStore(db).list_shows(install.uid)[0]['name']
        == (expected['show_name'])
    )
    assert sorted(KeptApart(db).pairs()) == expected['kept']
    assert (
        TrafficCounters(db).totals()[install.uid][DIRECTION_OUT]
        == (expected['traffic'])
    )


def test_migrate_refuses_repeats_and_force_redoes(
    tmp_path: Path, pg_schema
) -> None:
    url, schema = pg_schema
    install = _populate(tmp_path)
    sqlite_before = {n: _sha256(p) for n, p in install.files.items()}
    library_rows = _sqlite_count(
        install.files['downtify_library.db'], 'liked_tracks'
    )

    db = Database.postgres(url, search_path=schema, max_size=4)
    try:
        assert migrate(install.data, db).ok

        # A second run is refused: the marker is there.
        with pytest.raises(MigrationError, match='already migrated'):
            migrate(install.data, db)

        # Without the marker, the populated target is refused.
        (install.data / MARKER_NAME).unlink()
        with pytest.raises(MigrationError, match='already has rows'):
            migrate(install.data, db)
        assert not (install.data / MARKER_NAME).exists()

        # force truncates and copies again, leaving no stray rows.
        LikedTracks(db).like('extra.flac', user_id=install.uid)
        forced = migrate(install.data, db, force=True)
        assert forced.ok, format_report(forced)
        assert _count(db, 'liked_tracks') == library_rows
        assert (
            query(
                db,
                'SELECT COUNT(*) FROM liked_tracks '
                "WHERE stored_path = 'extra.flac'",
            )[0][0]
            == 0
        )
        assert (install.data / MARKER_NAME).exists()
    finally:
        db.close()

    assert {n: _sha256(p) for n, p in install.files.items()} == sqlite_before


def test_verify_passes_on_an_untouched_migration(
    tmp_path: Path, pg_schema
) -> None:
    url, schema = pg_schema
    install = _populate(tmp_path)

    db = Database.postgres(url, search_path=schema, max_size=4)
    try:
        assert migrate(install.data, db).ok
        report = verify(install.data, db)
        assert report.ok, format_report(report)
        assert report.problems == []
        assert all(t.checksum_ok for t in report.tables)
    finally:
        db.close()


def test_verify_names_a_corrupted_non_key_column(
    tmp_path: Path, pg_schema
) -> None:
    url, schema = pg_schema
    install = _populate(tmp_path)

    db = Database.postgres(url, search_path=schema, max_size=4)
    try:
        assert migrate(install.data, db).ok
        changed = execute(
            db,
            'UPDATE playlist_tracks SET filename = ? '
            'WHERE track_spotify_id = ?',
            'a/CORRUPT.flac',
            SID_A,
        )
        assert changed == 1

        report = verify(install.data, db)
        assert report.ok is False
        bad = [t.name for t in report.tables if not t.checksum_ok]
        assert bad == ['playlist_tracks']
        assert any(
            p.startswith('playlist_tracks: checksum mismatch')
            and 'filename' in p
            for p in report.problems
        ), report.problems
        # Row counts still match: only the content differs.
        by_name = {t.name: t for t in report.tables}
        row = by_name['playlist_tracks']
        assert row.target_rows == row.copied
    finally:
        db.close()


def test_verify_catches_a_deleted_row(tmp_path: Path, pg_schema) -> None:
    url, schema = pg_schema
    install = _populate(tmp_path)

    db = Database.postgres(url, search_path=schema, max_size=4)
    try:
        assert migrate(install.data, db).ok
        deleted = execute(
            db,
            'DELETE FROM playlist_tracks WHERE track_spotify_id = ?',
            SID_B,
        )
        assert deleted == 1

        report = verify(install.data, db)
        assert report.ok is False
        problems = '\n'.join(report.problems)
        assert 'playlist_tracks' in problems
        by_name = {t.name: t for t in report.tables}
        assert by_name['playlist_tracks'].target_rows == (
            by_name['playlist_tracks'].copied - 1
        )
        assert by_name['playlist_tracks'].checksum_ok is False
    finally:
        db.close()
