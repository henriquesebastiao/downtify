"""What each watch added, and how (``downtify/watch_history.py``): the
sweeps record outcomes, providers, backfills and failures."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from downtify import monitor
from downtify.monitor import LibraryStores, PlaylistMonitorDB
from downtify.track_index import TrackIndex
from downtify.watch_history import (
    OUTCOME_DOWNLOADED,
    OUTCOME_LINKED,
    OUTCOME_UNKNOWN,
)

TRACK_A = '4uLU6hMCjMI75M1A2tKUQC'
TRACK_B = '7ouMYWpwJ422jRcDASZB7P'
TRACK_C = '1301WleyT98MSxVHPZCA6M'
PLAYLIST_ID = '37i9dQZF1DXcBWIGoYBM5M'
OTHER_PLAYLIST_ID = '37i9dQZF1DX0XUsuxWHRQd'


class _Downloader:
    organize_by_artist = False
    organize_by_album = False
    slskd_settings: dict = {}

    def __init__(self, download_dir: Path, *, overwrite: bool = True):
        self.download_dir = download_dir
        self.overwrite_existing_files = overwrite
        self.failing: set[str] = set()

    def download(self, song, cb, subdir=None):
        if song['song_id'] in self.failing:
            raise RuntimeError('no match')
        name = f'{subdir}/{song["name"]}.mp3'
        path = self.download_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'audio')
        cb(100.0, 'Done', 'youtube-music')
        return name

    @staticmethod
    def existing_filename_for(song, subdir=None):
        return None


def _song(track_id, name):
    return {'song_id': track_id, 'name': name, 'artists': ['Artist']}


def _sweep(monkeypatch, db, downloader, tracks, library=None):
    """One check of the database's (only) watch, as it stands now."""

    [watch] = db.list_playlists()
    monkeypatch.setattr(
        monitor.spotify, 'playlist_tracks_from_id', lambda _id: tracks
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda _id: {})

    async def _broadcast(_msg):
        return None

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            monitor.check_playlist(
                watch,
                db,
                downloader,
                _broadcast,
                loop,
                {'generate_m3u': False},
                library,
            )
        )
    finally:
        loop.close()


def _watch(db, spotify_id=PLAYLIST_ID, name='Road Trip', user_id=0):
    return db.add_playlist(
        spotify_id,
        name,
        f'https://open.spotify.com/playlist/{spotify_id}',
        user_id=user_id,
    )


def _events(db, **kwargs):
    return [
        (e['track_id'], e['outcome'], bool(e['initial']))
        for e in db.history.events(**kwargs)
    ]


def test_first_check_is_marked_as_the_backfill(monkeypatch, tmp_path):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    _watch(db)
    downloader = _Downloader(tmp_path / 'downloads')

    _sweep(monkeypatch, db, downloader, [_song(TRACK_A, 'Alpha')])
    _sweep(
        monkeypatch,
        db,
        downloader,
        [_song(TRACK_A, 'Alpha'), _song(TRACK_B, 'Beta')],
    )

    assert _events(db) == [
        (TRACK_A, OUTCOME_DOWNLOADED, True),
        (TRACK_B, OUTCOME_DOWNLOADED, False),
    ]
    event = db.history.events()[1]
    assert event['provider'] == 'youtube-music'
    assert event['filename'] == 'Road Trip/Beta.mp3'
    assert event['watch_key'] == PLAYLIST_ID
    assert event['watch_name'] == 'Road Trip'


def test_a_song_already_in_the_library_is_linked_not_downloaded(
    monkeypatch, tmp_path
):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    _watch(db)
    downloads = tmp_path / 'downloads'
    (downloads / 'Elsewhere').mkdir(parents=True)
    (downloads / 'Elsewhere' / 'Alpha.mp3').write_bytes(b'audio')
    index = TrackIndex(tmp_path / 'library.db')
    index.register(TRACK_A, 'Elsewhere/Alpha.mp3')
    downloader = _Downloader(downloads, overwrite=False)

    _sweep(
        monkeypatch,
        db,
        downloader,
        [_song(TRACK_A, 'Alpha'), _song(TRACK_B, 'Beta')],
        LibraryStores(track_index=index),
    )

    assert sorted(_events(db)) == [
        (TRACK_A, OUTCOME_LINKED, True),
        (TRACK_B, OUTCOME_DOWNLOADED, True),
    ]


def test_a_reused_file_counts_as_linked(monkeypatch, tmp_path):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    _watch(db)
    downloader = _Downloader(tmp_path / 'downloads')

    def _already_there(song, cb, subdir=None):
        cb(100.0, 'Already downloaded')
        return f'{subdir}/{song["name"]}.mp3'

    downloader.download = _already_there
    _sweep(monkeypatch, db, downloader, [_song(TRACK_A, 'Alpha')])

    assert _events(db) == [(TRACK_A, OUTCOME_LINKED, True)]


def test_failures_are_kept_until_the_track_succeeds_or_leaves(
    monkeypatch, tmp_path
):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = _watch(db)
    downloader = _Downloader(tmp_path / 'downloads')
    downloader.failing = {TRACK_A, TRACK_B}
    tracks = [_song(TRACK_A, 'Alpha'), _song(TRACK_B, 'Beta')]

    _sweep(monkeypatch, db, downloader, tracks)
    _sweep(monkeypatch, db, downloader, tracks)

    failures = {f['track_id']: f for f in db.history.failures(watch.id)}
    assert set(failures) == {TRACK_A, TRACK_B}
    assert failures[TRACK_A]['attempts'] == 2
    assert failures[TRACK_A]['name'] == 'Alpha'
    assert failures[TRACK_A]['artists'] == 'Artist'
    assert 'no match' in failures[TRACK_A]['error']
    assert db.history.failure_counts() == {watch.id: 2}

    # A works now; B left the playlist.
    downloader.failing = set()
    _sweep(
        monkeypatch,
        db,
        downloader,
        [_song(TRACK_A, 'Alpha')],
    )
    assert db.history.failures(watch.id) == []
    assert _events(db) == [(TRACK_A, OUTCOME_DOWNLOADED, False)]


def test_retargeting_keeps_the_history_but_drops_failures(tmp_path):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = _watch(db)
    db.mark_track_downloaded(
        watch.id, TRACK_A, 'Road Trip/Alpha.mp3', outcome=OUTCOME_DOWNLOADED
    )
    db.history.record_failure(watch.id, _song(TRACK_B, 'Beta'), 'boom')

    db.retarget_playlist(
        watch.id,
        OTHER_PLAYLIST_ID,
        'Rap Caviar',
        f'https://open.spotify.com/playlist/{OTHER_PLAYLIST_ID}',
    )

    [event] = db.history.events(playlist_id=watch.id)
    assert (event['watch_key'], event['watch_name']) == (
        PLAYLIST_ID,
        'Road Trip',
    )
    assert db.history.failures(watch.id) == []


def test_deleting_a_watch_keeps_who_downloaded_what(tmp_path):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = _watch(db, user_id=7)
    db.mark_track_downloaded(
        watch.id, TRACK_A, 'Road Trip/Alpha.mp3', outcome=OUTCOME_DOWNLOADED
    )
    db.delete_playlist(watch.id)

    assert db.history.holdings('Road Trip/Alpha.mp3') == []
    [event] = db.history.events(filename='Road Trip/Alpha.mp3')
    assert (event['watch_name'], event['user_id']) == ('Road Trip', 7)


def test_a_moved_song_takes_its_history_along(tmp_path):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = _watch(db)
    db.mark_track_downloaded(
        watch.id, TRACK_A, 'Road Trip/Alpha.mp3', outcome=OUTCOME_DOWNLOADED
    )

    db.update_filename_for_spotify(TRACK_A, 'Artist/Alpha.mp3')

    assert [e['filename'] for e in db.history.events()] == ['Artist/Alpha.mp3']
    [row] = db.history.holdings('Artist/Alpha.mp3')
    assert row['track_spotify_id'] == TRACK_A


def test_holdings_and_events_by_track_id(tmp_path):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = _watch(db)
    db.mark_track_downloaded(
        watch.id, TRACK_A, 'old/Alpha.mp3', outcome=OUTCOME_DOWNLOADED
    )

    assert db.history.holdings('new/Alpha.mp3') == []
    assert len(db.history.holdings('new/Alpha.mp3', {TRACK_A})) == 1
    assert len(db.history.events(filename='x', track_ids={TRACK_A})) == 1
    assert db.history.events(track_ids={TRACK_C}) == []


def test_rows_from_before_the_history_become_unknown_events(tmp_path):
    path = tmp_path / 'monitor.db'
    db = PlaylistMonitorDB(path)
    watch = _watch(db, user_id=3)
    db.mark_track_downloaded(watch.id, TRACK_A, 'Road Trip/Alpha.mp3')
    db.mark_track_downloaded(watch.id, TRACK_B, 'Road Trip/Beta.mp3')
    assert db.history.events() == []
    with sqlite3.connect(path) as conn:
        # A track from the watch's first day, and one from much later;
        # then back to a database from before the history existed.
        conn.execute(
            "UPDATE monitored_playlists SET created_at = '2026-01-01T00:00:00+00:00'"
        )
        conn.execute(
            'UPDATE downloaded_tracks SET downloaded_at = ? WHERE '
            'track_spotify_id = ?',
            ('2026-01-01T05:00:00.123456+00:00', TRACK_A),
        )
        conn.execute(
            'UPDATE downloaded_tracks SET downloaded_at = ? WHERE '
            'track_spotify_id = ?',
            ('2026-03-01T00:00:00+00:00', TRACK_B),
        )
        conn.execute('DROP TABLE watch_events')

    db = PlaylistMonitorDB(path)
    events = db.history.events()

    assert [
        (e['track_id'], e['outcome'], e['initial'], e['user_id'])
        for e in events
    ] == [
        (TRACK_A, OUTCOME_UNKNOWN, 1, 3),
        (TRACK_B, OUTCOME_UNKNOWN, 0, 3),
    ]
    # Only once: opening the database again adds nothing.
    assert len(PlaylistMonitorDB(path).history.events()) == 2
