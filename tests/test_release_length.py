"""An artist watch keeps a song whose length differs a little from the
catalogue's, as the download itself did.

The downloader (slskd, YouTube) accepts audio within its duration
tolerance (10 s / 15 % by default). The release check after it used to
demand 3 s, so a mixtape track listed 8 s shorter on MusicBrainz was
downloaded, rejected ("Downloaded file does not validate against the
requested release"), left on disk, and on every later try reported as
"A different recording occupies the requested release path".
"""

from __future__ import annotations

import asyncio

from downtify import monitor
from downtify.downloader import Downloader
from downtify.release_files import matches_release
from tests.test_artist_watch_duplicates import (
    CHANNEL_ID,
    _album,
    _patch,
    _track,
    _write_track,
)


def _song(duration=240, **extra):
    return {
        **_track('a', 'Brand New', 'Heartbreak Drake', 4, duration=duration),
        **extra,
    }


def test_a_few_seconds_off_still_matches_the_release(tmp_path):
    path = tmp_path / 'one.mp3'
    _write_track(path, _song(duration=248))

    assert matches_release(path, _song(duration=240))


def test_far_off_lengths_and_other_tags_still_do_not_match(tmp_path):
    path = tmp_path / 'one.mp3'
    _write_track(path, _song(duration=240))

    # A 30-second preview, or a file three times as long.
    assert not matches_release(path, _song(duration=600))
    short = tmp_path / 'short.mp3'
    _write_track(short, _song(duration=30))
    assert not matches_release(short, _song(duration=240))
    # Length is not identity: the album and track tags still have to agree.
    assert not matches_release(path, {**_song(), 'album_name': 'So Far Gone'})
    assert not matches_release(path, {**_song(), 'track_number': 5})


def test_the_users_slskd_tolerance_is_used(tmp_path):
    path = tmp_path / 'one.mp3'
    _write_track(path, _song(duration=300))
    song = _song(duration=240)

    # 60 s off: past the default allowance, inside a 30 % one.
    assert not matches_release(path, song)
    assert matches_release(
        path,
        song,
        {'duration_tolerance_seconds': 10, 'duration_tolerance_percent': 30},
    )


class _LongerDownloader:
    """Downloads every song 8 s longer than the catalogue lists it."""

    organize_by_artist = True
    organize_by_album = False

    def __init__(self, root):
        self.download_dir = root
        self.calls: list[str] = []

    @staticmethod
    def existing_filename_for(song, subdir=None):
        return None

    def download(self, song, progress_cb=None, subdir=None):
        self.calls.append(song['song_id'])
        filename = f'Drake/{song["song_id"]}.mp3'
        _write_track(
            self.download_dir / filename,
            {**song, 'duration': song['duration'] + 8},
        )
        return filename


def _check(tmp_path, downloader):
    db = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist(
        CHANNEL_ID, 'Drake', 'url', 60, monitor.KIND_ARTIST
    )
    events: list[dict] = []

    async def broadcast(message):
        events.append(message)

    async def scenario():
        return await monitor.check_artist(
            watch,
            db,
            downloader,
            broadcast,
            asyncio.get_running_loop(),
            settings={},
        )

    return asyncio.run(scenario()), db, watch, events


def test_the_watch_keeps_a_song_a_few_seconds_longer(monkeypatch, tmp_path):
    _patch(
        monkeypatch,
        [_album('HD', 'Heartbreak Drake')],
        {'HD': [_song(duration=240)]},
    )
    dl = _LongerDownloader(tmp_path)

    downloaded, db, watch, events = _check(tmp_path, dl)

    assert downloaded == 1
    assert db.get_track_filenames(watch.id)['a'] == 'Drake/a.mp3'
    assert db.get_seen_album_ids(watch.id) == {'HD'}
    assert [e['status'] for e in events if 'status' in e] == ['done']


def test_an_earlier_rejected_download_is_taken_up_not_reported(tmp_path):
    """The file an earlier sweep downloaded and then refused sits at the
    song's own name; the next sweep finds it instead of failing with "A
    different recording occupies the requested release path"."""

    dl = Downloader(
        download_dir=tmp_path,
        output_template='{artists} - {title}.{output-ext}',
        organize_by_artist=True,
        organize_by_album=False,
    )
    song = {**_song(duration=240), '_monitor_release': 'HD'}
    _write_track(
        tmp_path / 'Drake/Drake - Brand New.mp3', {**song, 'duration': 248}
    )

    assert dl.find_existing_download(song) == 'Drake/Drake - Brand New.mp3'
