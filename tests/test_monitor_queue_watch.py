"""The queue says which watch is downloading each song."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from downtify import monitor
from downtify.monitor import MonitoredPlaylist, queue_watch, with_watch


def _watch(kind=monitor.KIND_PLAYLIST, name='2010s Mix'):
    return MonitoredPlaylist(
        id=7,
        spotify_id='abc',
        name=name,
        url='https://open.spotify.com/playlist/abc',
        interval_minutes=60,
        enabled=True,
        last_checked=None,
        last_track_count=0,
        created_at='2026-11-19T00:00:00',
        kind=kind,
    )


def _downloader(tmp_path, *, organize=False):
    return SimpleNamespace(
        download_dir=str(tmp_path),
        organize_by_artist=organize,
        organize_by_album=False,
    )


def test_song_events_name_the_watch_other_events_untouched(tmp_path):
    sent = []

    async def broadcast(message):
        sent.append(message)

    info = queue_watch(_watch(), _downloader(tmp_path))
    send = with_watch(broadcast, info)

    async def run():
        await send({'song': {'song_id': 's'}, 'progress': 10})
        await send({'type': 'monitor_status'})

    asyncio.run(run())

    assert sent[0]['watch'] == info
    assert info['id'] == 7
    assert info['kind'] == 'playlist'
    assert info['source'] == 'spotify'
    assert 'watch' not in sent[1]


def test_cover_file_is_where_the_playlist_cover_is_saved(tmp_path):
    flat = queue_watch(_watch(), _downloader(tmp_path))
    organized = queue_watch(_watch(), _downloader(tmp_path, organize=True))
    artist = queue_watch(
        _watch(monitor.KIND_ARTIST, 'Drake'), _downloader(tmp_path)
    )

    assert flat['cover_file'].endswith('2010s Mix.jpg')
    assert '/' in flat['cover_file']  # inside the playlist's own folder
    assert organized['cover_file'].endswith('2010s Mix.jpg')
    assert not artist['cover_file']
