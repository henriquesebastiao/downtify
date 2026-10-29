"""Per-watch storage, activity and provenance (downtify/watch_stats.py)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from downtify.monitor import MonitoredPlaylist
from downtify.watch_stats import (
    activity_series,
    clamp_days,
    holders_by_file,
    provenance,
    trend,
    watch_stats,
)

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)


def _iso(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat()


def _watch(watch_id, key, name, created_days_ago=100, user_id=0):
    return MonitoredPlaylist(
        id=watch_id,
        spotify_id=key,
        name=name,
        url=f'https://open.spotify.com/playlist/{key}',
        interval_minutes=60,
        enabled=True,
        last_checked=_iso(0),
        last_track_count=0,
        created_at=_iso(created_days_ago),
        user_id=user_id,
    )


def _event(watch, track, outcome, days_ago, filename=None, **extra):
    return {
        'playlist_id': watch.id,
        'watch_key': extra.pop('key', watch.spotify_id),
        'watch_name': watch.name,
        'user_id': watch.user_id,
        'track_id': track,
        'outcome': outcome,
        'filename': filename or f'{track}.mp3',
        'provider': extra.pop('provider', ''),
        'initial': int(extra.pop('initial', False)),
        'happened_at': _iso(days_ago),
    }


def _row(watch, track, filename=None, days_ago=1.0):
    return {
        'playlist_id': watch.id,
        'track_spotify_id': track,
        'filename': filename or f'{track}.mp3',
        'downloaded_at': _iso(days_ago),
    }


def test_trend_directions():
    assert trend([]) == {'direction': 'new', 'slope': 0.0}
    assert trend([3, 4])['direction'] == 'new'
    assert trend([0, 0, 0, 0]) == {'direction': 'idle', 'slope': 0.0}
    assert trend([15, 15, 15, 15]) == {'direction': 'steady', 'slope': 0.0}
    assert trend([5, 10, 15, 20]) == {'direction': 'up', 'slope': 5.0}
    assert trend([20, 15, 10, 5])['direction'] == 'down'
    # Noise of a song or so either way is no trend.
    assert trend([1, 0, 1, 0])['direction'] == 'steady'


def test_clamp_days():
    assert clamp_days('7') == 7
    assert clamp_days(0) == 1
    assert clamp_days(9999) == 365
    assert clamp_days('soon') == 30


def test_activity_series_buckets_whole_days_or_weeks():
    times = [NOW - timedelta(hours=1), NOW - timedelta(days=2, hours=1)]
    # Seven days: one bucket per day, oldest first.
    assert activity_series(times, NOW, NOW - timedelta(days=99), 7) == [
        0,
        0,
        0,
        0,
        1,
        0,
        1,
    ]
    # Thirty days: whole weeks only.
    assert activity_series(times, NOW, NOW - timedelta(days=99), 30) == [
        0,
        0,
        0,
        2,
    ]
    # A watch three days old has three buckets, not seven.
    assert activity_series(times, NOW, NOW - timedelta(days=3), 7) == [
        1,
        0,
        1,
    ]


def test_holders_by_file_can_keep_files_on_disk_only():
    a, b = _watch(1, 'a', 'A'), _watch(2, 'b', 'B')
    rows = [_row(a, 't1', 'x.mp3'), _row(b, 't1', 'x.mp3'), _row(b, 't2')]
    assert holders_by_file(rows) == {'x.mp3': {1, 2}, 't2.mp3': {2}}
    assert holders_by_file(rows, {'x.mp3': 5}) == {'x.mp3': {1, 2}}


def test_a_shared_file_is_one_file():
    a, b = _watch(1, 'a', 'Mix'), _watch(2, 'b', 'Static')
    rows = [
        _row(a, 'shared', 'shared.mp3'),
        _row(b, 'shared', 'shared.mp3'),
        _row(a, 'only-a'),
        _row(b, 'only-b'),
        _row(b, 'gone'),
    ]
    sizes = {'shared.mp3': 100, 'only-a.mp3': 30, 'only-b.mp3': 50}

    stats = watch_stats([a, b], rows, [], sizes, now=NOW)
    by_id = {row['id']: row for row in stats['watches']}

    assert by_id[1]['storage'] == {
        'files': 2,
        'missing': 0,
        'unique_files': 1,
        'shared_files': 1,
        'bytes': 130,
        'unique_bytes': 30,
        'shared_bytes': 100,
        'share_bytes': 80,
    }
    assert by_id[2]['storage']['missing'] == 1
    assert by_id[2]['storage']['unique_bytes'] == 50
    assert stats['totals'] == {
        'watches': 2,
        'files': 3,
        'bytes': 180,
        'shared_files': 1,
    }


def test_shared_counts_watches_outside_the_scope():
    mine, theirs = _watch(1, 'a', 'Mine'), _watch(2, 'b', 'Theirs')
    rows = [_row(mine, 't', 'x.mp3'), _row(theirs, 't', 'x.mp3')]

    stats = watch_stats([mine], rows, [], {'x.mp3': 10}, now=NOW)

    [row] = stats['watches']
    assert row['storage']['shared_files'] == 1
    assert row['storage']['share_bytes'] == 5
    assert stats['totals']['watches'] == 1


def test_activity_leaves_out_linked_tracks_and_the_backfill():
    watch = _watch(1, 'mix', 'Weekly Mix', created_days_ago=60)
    events = [
        _event(watch, 'b1', 'downloaded', 59, initial=True),
        _event(watch, 'b2', 'linked', 59, initial=True),
        _event(watch, 'n1', 'downloaded', 20),
        _event(watch, 'n2', 'downloaded', 10),
        _event(watch, 'n3', 'downloaded', 2, provider='slskd'),
        _event(watch, 'l1', 'linked', 3),
        _event(watch, 'old', 'unknown', 25),
        # Its old target before a retarget: someone else's history.
        _event(watch, 'x1', 'downloaded', 5, key='previous'),
    ]
    rows = [_row(watch, e['track_id']) for e in events[:7]]
    sizes = {f'{e["track_id"]}.mp3': 10 for e in events}

    stats = watch_stats(
        [watch],
        rows,
        events,
        sizes,
        now=NOW,
        days=30,
        providers={'n1.mp3': 'youtube-music'},
        failures={1: 4},
    )
    [row] = stats['watches']

    assert row['period'] == {
        'added': 4,
        'downloaded': 3,
        'linked': 1,
        'unknown': 1,
        'initial': 0,
        'bytes': 40,
    }
    assert row['rate']['per_day'] == round(4 / 30, 3)
    assert row['rate']['per_week'] == round(4 / 30 * 7, 2)
    assert row['status'] == {
        'downloaded': 4,
        'linked': 2,
        'unknown': 1,
        'failing': 4,
    }
    assert row['providers'] == {
        'unknown': 5,
        'youtube-music': 1,
        'slskd': 1,
    }
    # Four whole weeks: the unknown one counts as added too.
    assert row['series'] == [1, 1, 1, 1]
    assert row['trend']['direction'] == 'steady'
    assert row['last_added_at'] == _iso(2)
    assert stats['bucket_days'] == 7


def test_a_young_watch_rates_over_its_own_age():
    watch = _watch(1, 'mix', 'New Mix', created_days_ago=2)
    events = [
        _event(watch, 'b', 'downloaded', 2, initial=True),
        _event(watch, 'n', 'downloaded', 1),
    ]

    [row] = watch_stats([watch], [], events, {}, now=NOW, days=30)['watches']

    assert row['period']['initial'] == 1
    assert row['rate']['per_day'] == 0.5
    assert row['trend']['direction'] == 'new'


def test_provenance_names_the_first_watch_that_downloaded_it():
    first, second = _watch(1, 'a', 'Discover'), _watch(2, 'b', 'Daily')
    events = [
        _event(second, 't', 'linked', 1, 'x.mp3'),
        _event(first, 't', 'downloaded', 5, 'x.mp3', provider='slskd'),
    ]
    events.sort(key=lambda e: e['happened_at'])
    rows = [
        _row(first, 't', 'x.mp3', 5),
        _row(second, 't', 'x.mp3', 1),
    ]

    found = provenance(rows, events, {1: first, 2: second})

    origin = found['origin']
    assert origin['watch'] is first
    assert (origin['name'], origin['provider'], origin['estimated']) == (
        'Discover',
        'slskd',
        False,
    )
    assert [(h['watch'].id, h['outcome']) for h in found['holders']] == [
        (1, 'downloaded'),
        (2, 'linked'),
    ]


def test_provenance_of_a_deleted_or_retargeted_watch_keeps_its_name():
    gone = _watch(9, 'a', 'Old Mix', user_id=4)
    events = [_event(gone, 't', 'downloaded', 5, 'x.mp3')]

    origin = provenance([], events, {})['origin']
    assert origin['watch'] is None
    assert (origin['watch_id'], origin['name'], origin['user_id']) == (
        9,
        'Old Mix',
        4,
    )

    retargeted = _watch(9, 'b', 'Something Else')
    origin = provenance([], events, {9: retargeted})['origin']
    assert origin['watch'] is None


def test_provenance_from_before_outcomes_is_an_estimate():
    watch = _watch(1, 'a', 'Mix')
    events = [_event(watch, 't', 'unknown', 5, 'x.mp3')]

    found = provenance([_row(watch, 't', 'x.mp3')], events, {1: watch})

    assert found['origin']['estimated'] is True
    assert found['holders'][0]['outcome'] == 'unknown'
    assert provenance([], [], {})['origin'] is None


def test_a_linked_file_takes_the_provider_its_download_recorded():
    first, second = _watch(1, 'a', 'Discover'), _watch(2, 'b', 'Daily')
    events = [
        _event(first, 't', 'downloaded', 5, 'x.mp3', provider='slskd'),
        _event(second, 't', 'linked', 1, 'x.mp3'),
    ]
    rows = [_row(first, 't', 'x.mp3'), _row(second, 't', 'x.mp3')]

    stats = watch_stats([second], rows, events, {'x.mp3': 1}, now=NOW)
    assert stats['watches'][0]['providers'] == {'slskd': 1}

    # What the library recorded for the file wins.
    stats = watch_stats(
        [second],
        rows,
        events,
        {'x.mp3': 1},
        now=NOW,
        providers={'x.mp3': 'deemix'},
    )
    assert stats['watches'][0]['providers'] == {'deemix': 1}
