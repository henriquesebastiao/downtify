"""Backup and restore (downtify/backup.py, downtify/backup_routes.py)."""

from __future__ import annotations

import asyncio
import gzip
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from downtify import api, backup, backup_routes
from downtify.monitor import KIND_ARTIST, PlaylistMonitorDB
from downtify.track_index import TrackIndex

T0 = datetime(2026, 11, 1, 3, 0, 0, tzinfo=timezone.utc)
SONG = {
    'file': 'Band/Album/Song.mp3',
    'title': 'Song',
    'artist': 'Band',
    'artists': ['Band'],
    'album': 'Album',
    'year': '2020',
    'duration': 201.4,
    'isrc': 'USAAA2000001',
    'codec': 'mp3',
}


def _data(songs=(SONG,), watches=()):
    return backup.build(
        settings={'max_parallel_downloads': 2},
        watches=list(watches),
        songs=[backup.song_record(s) for s in songs],
        now=T0,
    )


# ── Two copies ──────────────────────────────────────────────────────


def test_a_backup_is_written_and_reads_back(tmp_path):
    info = backup.write_backup(tmp_path, _data(), now=T0)

    assert info.name == 'downtify-backup-20261101-030000.json.gz'
    assert (info.settings, info.watches, info.songs) == (True, 0, 1)
    assert backup.read(tmp_path / info.name) == _data()


def test_the_newest_bumps_the_oldest_out_keeping_two(tmp_path):
    for hours in range(3):
        backup.write_backup(tmp_path, _data(), now=T0 + timedelta(hours=hours))

    assert backup.backup_names(tmp_path) == [
        'downtify-backup-20261101-050000.json.gz',
        'downtify-backup-20261101-040000.json.gz',
    ]


def test_a_failed_backup_deletes_nothing(tmp_path, monkeypatch):
    for hours in range(2):
        backup.write_backup(tmp_path, _data(), now=T0 + timedelta(hours=hours))
    before = backup.backup_names(tmp_path)

    def broken(path):
        raise backup.BackupError('check failed')

    monkeypatch.setattr(backup, 'read', broken)
    with pytest.raises(backup.BackupError):
        backup.write_backup(tmp_path, _data(), now=T0 + timedelta(hours=5))

    assert backup.backup_names(tmp_path) == before
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(before)


def test_two_backups_in_one_second_both_keep_their_file(tmp_path):
    first = backup.write_backup(tmp_path, _data(), now=T0)
    second = backup.write_backup(tmp_path, _data(), now=T0)

    assert first.name != second.name
    assert len(backup.backup_names(tmp_path)) == 2


def test_leftovers_of_an_interrupted_backup_are_cleared(tmp_path):
    (tmp_path / 'downtify-backup-20261101-010000.json.gz.partial').write_text(
        'half'
    )
    backup.write_backup(tmp_path, _data(), now=T0)

    assert [p.name for p in tmp_path.iterdir()] == [
        'downtify-backup-20261101-030000.json.gz'
    ]


# ── Reading ─────────────────────────────────────────────────────────


def test_plain_json_is_read_too():
    raw = json.dumps(_data()).encode()

    assert backup.parse(raw) == _data()
    assert backup.parse(gzip.compress(raw)) == _data()


@pytest.mark.parametrize(
    'raw',
    [
        b'not json',
        b'{"format": "other"}',
        json.dumps({**_data(), 'version': backup.VERSION + 1}).encode(),
        json.dumps({**_data(), 'songs': None}).encode(),
    ],
)
def test_what_is_not_a_backup_is_refused(raw):
    with pytest.raises(backup.BackupError):
        backup.parse(raw)


def test_only_backup_names_are_served(tmp_path):
    backup.write_backup(tmp_path, _data(), now=T0)
    (tmp_path / 'settings.json').write_text('{}')

    assert backup.path_of(tmp_path, '../settings.json') is None
    assert backup.path_of(tmp_path, 'settings.json') is None
    assert backup.path_of(tmp_path, 'downtify-backup-20261101-030000.json.gz')


# ── Schedule ────────────────────────────────────────────────────────


def test_schedule():
    assert not backup.due(None, 0)
    assert backup.due(None, 24)
    last = T0.isoformat()
    assert not backup.due(last, 24, T0 + timedelta(hours=23))
    assert backup.due(last, 24, T0 + timedelta(hours=24))
    assert backup.clamp_interval('168') == 168
    assert backup.clamp_interval(5) == 0


# ── Restoring songs ─────────────────────────────────────────────────


def test_songs_whose_file_is_gone_are_downloaded_again():
    kept = {**SONG, 'file': 'kept.mp3', 'title': 'Kept'}
    lost = backup.song_record(SONG, spotify_id='4uLU6hMCjMI75M1A2tKUQC')

    songs = backup.missing_songs(
        [backup.song_record(kept), lost], lambda f: f == 'kept.mp3'
    )

    assert songs == [
        {
            'name': 'Song',
            'artists': ['Band'],
            'artist': 'Band',
            'album_name': 'Album',
            'year': '2020',
            'release_date': '',
            'duration': 201,
            'isrc': 'USAAA2000001',
            'song_id': '4uLU6hMCjMI75M1A2tKUQC',
            'url': 'https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC',
        }
    ]


# ── The routes ──────────────────────────────────────────────────────


@pytest.fixture
def install(tmp_path, monkeypatch):
    """A Downtify with one watch, one indexed song and its settings."""

    settings_path = tmp_path / 'data' / 'settings.json'
    settings_path.parent.mkdir()
    db = PlaylistMonitorDB(tmp_path / 'data' / 'monitor.db')
    watch = db.add_playlist(
        'UCabc',
        'Band',
        'https://music.youtube.com/channel/UCabc',
        kind=KIND_ARTIST,
        release_types='album',
        new_only=True,
    )
    db.update_playlist(watch.id, deezer_id='123', enabled=False)
    index = TrackIndex(tmp_path / 'data' / 'library.db')
    index.register('4uLU6hMCjMI75M1A2tKUQC', SONG['file'])
    monkeypatch.setattr(api.state, 'settings_path', settings_path)
    monkeypatch.setattr(api.state, 'monitor_db', db)
    monkeypatch.setattr(api.state, 'track_index', index)
    monkeypatch.setattr(api.state, 'file_providers', None)
    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(
        api.state,
        'settings',
        {**api.DEFAULT_SETTINGS, 'backup_interval_hours': 24},
    )
    monkeypatch.setattr(api, 'listing_for_request', lambda ctx: [SONG])
    monkeypatch.setattr(api, 'library_context', lambda: None)
    return db


class _Request:
    def __init__(self, **query):
        self.query_params = {k: str(v) for k, v in query.items()}
        self.scope = {}


def test_a_backup_holds_settings_watches_and_songs(install):
    info = asyncio.run(backup_routes.back_up('manual'))
    data = backup.read(backup_routes.folder() / info.name)

    assert data['settings']['backup_interval_hours'] == 24
    [watch] = data['watches']
    assert (watch['spotify_id'], watch['kind'], watch['new_only']) == (
        'UCabc',
        KIND_ARTIST,
        True,
    )
    assert (watch['deezer_id'], watch['enabled']) == ('123', False)
    [song] = data['songs']
    assert song['spotify_id'] == '4uLU6hMCjMI75M1A2tKUQC'
    assert song['title'] == 'Song'
    assert 'codec' not in song


def test_a_fresh_install_gets_the_watches_back(install, tmp_path):
    asyncio.run(backup_routes.back_up('manual'))
    data = backup.read(
        backup_routes.folder() / backup.backup_names(backup_routes.folder())[0]
    )
    fresh = PlaylistMonitorDB(tmp_path / 'fresh.db')
    api.state.monitor_db = fresh

    assert backup_routes._restore_watches(data['watches']) == (1, 0)
    assert backup_routes._restore_watches(data['watches']) == (0, 1)
    [watch] = fresh.list_playlists()
    assert (watch.kind, watch.release_types, watch.new_only) == (
        KIND_ARTIST,
        'album',
        True,
    )
    assert (watch.deezer_id, watch.enabled) == ('123', False)


def test_restore_queues_only_the_missing_songs(install, monkeypatch):
    sent = {}

    async def submit(songs, url, **kwargs):
        sent['songs'] = songs
        return {'job_ids': [s['song_id'] for s in songs]}

    async def log(*args, **kwargs):
        pass

    monkeypatch.setattr(api, '_submit_playlist_batch', submit)
    monkeypatch.setattr(api, 'log_activity', log)
    monkeypatch.setattr(api, 'resolve_library_file', lambda f, ctx: None)
    data = _data(songs=[SONG, {**SONG, 'file': 'b.mp3', 'title': 'B'}])

    result = asyncio.run(
        backup_routes._restore(_Request(settings=0, watches=0), data)
    )

    assert (result['songs_missing'], result['songs_queued']) == (2, 2)
    assert [s['name'] for s in sent['songs']] == ['Song', 'B']
    assert all(s['song_id'].startswith('backup:') for s in sent['songs'])
    assert result['settings'] == []
    assert result['watches_added'] == 0


def test_the_schedule_makes_a_backup_when_due(install):
    assert asyncio.run(backup_routes.maybe_back_up()) is True
    assert asyncio.run(backup_routes.maybe_back_up()) is False
    api.state.settings['backup_interval_hours'] = 0
    assert asyncio.run(backup_routes.maybe_back_up()) is False


def test_an_unknown_interval_is_refused(install):
    with pytest.raises(HTTPException):
        asyncio.run(
            backup_routes.backups_schedule(
                backup_routes.ScheduleRequest(interval_hours=5)
            )
        )
    status = asyncio.run(
        backup_routes.backups_schedule(
            backup_routes.ScheduleRequest(interval_hours=168)
        )
    )
    assert status['interval_hours'] == 168
