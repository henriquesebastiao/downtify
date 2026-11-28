"""``downtify/storage_forecast.py``: how long until the disk is full, at
the library's usual pace, with new watches' first downloads and one busy
week left out of that pace."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from downtify.library_usage import usage_report
from downtify.storage_forecast import (
    STATUS_BACKLOG_TOO_BIG,
    STATUS_NO_DISK,
    STATUS_NOT_GROWING,
    STATUS_OK,
    WINDOW_DAYS,
    backlog,
    daily_growth,
    held_counts,
    storage_forecast,
    watch_additions,
)

NOW = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc)
GB = 1024**3
MB = 1024**2
NOTHING_TO_COME = {'bytes': 0, 'songs': 0}


def _points(per_day, *, start_bytes=100 * GB, days=WINDOW_DAYS):
    """Daily end sizes, oldest first, ending today; *per_day* is a number
    or a list of daily changes (oldest first)."""

    changes = per_day if isinstance(per_day, list) else [per_day] * days
    size = start_bytes
    today = NOW.date()
    points = [
        {
            'day': (today - timedelta(days=len(changes))).isoformat(),
            'bytes': size,
            'estimated': False,
        }
    ]
    for index, change in enumerate(changes):
        size += change
        day = today - timedelta(days=len(changes) - 1 - index)
        points.append({
            'day': day.isoformat(),
            'bytes': size,
            'estimated': False,
        })
    return points


def _day(days_ago):
    return (NOW.date() - timedelta(days=days_ago)).isoformat()


def test_a_steady_library_fills_the_disk_at_its_pace():
    forecast = storage_forecast(
        points=_points(GB),
        additions=[],
        disk={'total': 500 * GB, 'used': 400 * GB, 'free': 100 * GB},
        still_to_come=NOTHING_TO_COME,
        now=NOW,
    )

    assert forecast['status'] == STATUS_OK
    assert forecast['usual_per_day_bytes'] == GB
    assert forecast['full']['days'] == 100
    assert (
        forecast['full']['date']
        == (date(2026, 11, 28) + timedelta(days=100)).isoformat()
    )
    assert forecast['soonest']['days'] == forecast['latest']['days'] == 100
    assert forecast['spikes'] == []
    assert not forecast['rough']


def test_a_new_watchs_first_download_is_not_the_usual_pace():
    changes = [GB // 10] * WINDOW_DAYS
    # Three days ago a new artist watch pulled in 40 GB on its first check.
    changes[-3] += 40 * GB
    additions = [
        {
            'watch': 7,
            'name': 'Drake',
            'day': _day(2),
            'bytes': 40 * GB,
            'initial': True,
        },
    ]

    forecast = storage_forecast(
        points=_points(changes),
        additions=additions,
        disk={'free': 100 * GB},
        still_to_come=NOTHING_TO_COME,
        now=NOW,
    )

    assert forecast['usual_per_day_bytes'] == GB // 10
    assert forecast['recent_per_day_bytes'] == GB // 10
    assert forecast['full']['days'] == 1000
    assert forecast['one_off']['bytes'] == 40 * GB
    assert forecast['one_off']['watches'][0]['name'] == 'Drake'
    assert forecast['spikes'] == []


def test_one_busy_week_is_a_spike_and_moves_only_the_soonest_date():
    changes = [GB // 10] * WINDOW_DAYS
    # A batch queued by hand, last week: not a watch's first check.
    for index in range(-7, 0):
        changes[index] = 3 * GB

    forecast = storage_forecast(
        points=_points(changes),
        additions=[],
        disk={'free': 100 * GB},
        still_to_come=NOTHING_TO_COME,
        now=NOW,
    )

    assert forecast['usual_per_day_bytes'] == GB // 10
    assert forecast['full']['days'] == 1000
    assert forecast['soonest']['days'] < 100
    assert forecast['latest']['days'] == 1000
    assert len(forecast['spikes']) == 1
    assert forecast['spikes'][0]['to'] == _day(0)
    assert forecast['spikes'][0]['bytes'] == 21 * GB


def test_what_is_still_to_come_is_taken_off_the_free_space_first():
    still = backlog(
        queued=100,
        watches=[
            {
                'id': 1,
                'name': 'Big',
                'expected': 500,
                'held': 300,
                'failing': 50,
            },
            {
                'id': 2,
                'name': 'Done',
                'expected': 10,
                'held': 10,
                'failing': 0,
            },
        ],
        average_bytes=10 * MB,
    )

    assert still['queued'] == 100
    assert still['watch_songs'] == 150
    assert still['songs'] == 250
    assert still['bytes'] == 250 * 10 * MB
    assert [w['name'] for w in still['watches']] == ['Big']

    forecast = storage_forecast(
        points=_points(GB),
        additions=[],
        disk={'free': 10 * GB},
        still_to_come={'bytes': 4 * GB, 'songs': 1},
        now=NOW,
    )
    assert forecast['room_bytes'] == 6 * GB
    assert forecast['full']['days'] == 6


def test_a_backlog_bigger_than_the_free_space_says_so():
    forecast = storage_forecast(
        points=_points(GB),
        additions=[],
        disk={'free': GB},
        still_to_come={'bytes': 2 * GB, 'songs': 200},
        now=NOW,
    )

    assert forecast['status'] == STATUS_BACKLOG_TOO_BIG
    assert forecast['full'] is None


def test_a_library_that_is_not_growing_has_no_date():
    forecast = storage_forecast(
        points=_points(-GB // 100),
        additions=[],
        disk={'free': GB},
        still_to_come=NOTHING_TO_COME,
        now=NOW,
    )

    assert forecast['status'] == STATUS_NOT_GROWING
    assert forecast['full'] is None


def test_no_disk_reading_still_reports_the_pace():
    forecast = storage_forecast(
        points=_points(GB),
        additions=[],
        disk=None,
        still_to_come=NOTHING_TO_COME,
        now=NOW,
    )

    assert forecast['status'] == STATUS_NO_DISK
    assert forecast['usual_per_day_bytes'] == GB


def test_decades_away_is_beyond():
    forecast = storage_forecast(
        points=_points(MB),
        additions=[],
        disk={'free': 100 * GB},
        still_to_come=NOTHING_TO_COME,
        now=NOW,
    )

    assert forecast['full']['beyond'] is True
    assert forecast['full']['date'] is None


def test_a_young_library_skips_the_empty_days_and_is_rough():
    changes = [0] * (WINDOW_DAYS - 5) + [GB] * 5
    forecast = storage_forecast(
        points=_points(changes, start_bytes=0),
        additions=[],
        disk={'free': 10 * GB},
        still_to_come=NOTHING_TO_COME,
        now=NOW,
    )

    assert forecast['history_days'] == 5
    assert forecast['rough'] is True
    assert forecast['usual_per_day_bytes'] == GB
    assert forecast['full']['days'] == 10


def test_daily_growth_marks_estimated_days():
    points = [
        {'day': '2026-11-01', 'bytes': 10, 'estimated': True},
        {'day': '2026-11-02', 'bytes': 15, 'estimated': False},
        {'day': '2026-11-03', 'bytes': 12, 'estimated': False},
    ]

    assert daily_growth(points) == [
        {'day': '2026-11-02', 'bytes': 5, 'estimated': True},
        {'day': '2026-11-03', 'bytes': -3, 'estimated': False},
    ]


def test_watch_downloads_after_the_first_check_drive_the_growth():
    changes = [GB] * WINDOW_DAYS
    additions = [
        {
            'watch': 1,
            'name': 'Daily Mix',
            'day': _day(i),
            'bytes': GB // 2,
            'initial': False,
        }
        for i in range(WINDOW_DAYS)
    ]

    forecast = storage_forecast(
        points=_points(changes),
        additions=additions,
        disk={'free': 100 * GB},
        still_to_come=NOTHING_TO_COME,
        now=NOW,
    )

    drivers = forecast['drivers']
    assert drivers['watches'][0]['name'] == 'Daily Mix'
    assert drivers['watches'][0]['per_week_bytes'] == 7 * GB // 2
    assert drivers['other_per_week_bytes'] == 7 * GB // 2


def test_watch_additions_count_each_present_file_once():
    events = [
        {
            'playlist_id': 1,
            'watch_name': 'A',
            'outcome': 'downloaded',
            'filename': 'x.mp3',
            'initial': 1,
            'happened_at': (NOW - timedelta(days=1)).isoformat(),
        },
        {
            'playlist_id': 2,
            'watch_name': 'B',
            'outcome': 'downloaded',
            'filename': 'x.mp3',
            'initial': 0,
            'happened_at': NOW.isoformat(),
        },
        {
            'playlist_id': 2,
            'watch_name': 'B',
            'outcome': 'linked',
            'filename': 'y.mp3',
            'initial': 0,
            'happened_at': NOW.isoformat(),
        },
        {
            'playlist_id': 2,
            'watch_name': 'B',
            'outcome': 'downloaded',
            'filename': 'gone.mp3',
            'initial': 0,
            'happened_at': NOW.isoformat(),
        },
        {
            'playlist_id': 3,
            'watch_name': 'C',
            'outcome': 'unknown',
            'filename': 'old.mp3',
            'initial': 0,
            'happened_at': (NOW - timedelta(days=400)).isoformat(),
        },
    ]

    found = watch_additions(
        events,
        {'x.mp3': 5, 'y.mp3': 6, 'old.mp3': 7},
        since=NOW - timedelta(days=WINDOW_DAYS),
    )

    assert found == [
        {'watch': 1, 'name': 'A', 'day': _day(1), 'bytes': 5, 'initial': True},
    ]


def test_held_counts_skip_rows_without_a_file():
    assert held_counts([
        {'playlist_id': 1, 'filename': 'a.mp3'},
        {'playlist_id': 1, 'filename': ''},
        {'playlist_id': 2, 'filename': 'b.mp3'},
    ]) == {1: 1, 2: 1}


def test_the_usage_report_carries_the_forecast_and_the_tile_days():
    entries = [
        {
            'file': f'song{i}.mp3',
            'size': GB,
            'title': '',
            'artist': '',
            'added': (NOW - timedelta(days=i)).timestamp(),
        }
        for i in range(60)
    ]

    report = usage_report(
        entries,
        providers={},
        recorded={},
        sources={},
        slskd_in_place=False,
        referenced=set(),
        snapshots=[],
        downloads=[],
        downloads_since=None,
        disk={'total': 200 * GB, 'used': 100 * GB, 'free': 30 * GB},
        now=NOW,
        days=7,
        watched_playlists=[
            {'id': 1, 'name': 'P', 'expected': 15, 'held': 5, 'failing': 0},
        ],
        queued=0,
    )

    forecast = report['forecast']
    assert forecast['usual_per_day_bytes'] == GB
    assert forecast['still_to_come']['songs'] == 10
    assert forecast['room_bytes'] == 20 * GB
    assert forecast['full']['days'] == 20
    assert report['disk']['days_left'] == 20
