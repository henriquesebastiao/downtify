"""``downtify/library_usage.py``: the library's size, growth, duplicates,
working copies and download totals for ``GET /api/library/usage`` -
pure functions over listing rows, plus the daily snapshot store."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from downtify.download_log import (
    OUTCOME_COMPLETED,
    OUTCOME_FAILED,
    OUTCOME_SKIPPED,
)
from downtify.library_usage import (
    UsageSnapshots,
    added_times,
    download_totals,
    duplicates,
    forecast_days,
    growth,
    library_snapshot,
    library_totals,
    location_of,
    period_added,
    snapshot_of,
    split_working_copies,
    usage_report,
)

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
MB = 1024 * 1024


def _row(file, size=MB, *, days_ago=None, **extra):
    row = {'file': file, 'size': size, 'title': '', 'artist': '', **extra}
    if days_ago is not None:
        row['added'] = (NOW - timedelta(days=days_ago)).timestamp()
    return row


def test_a_file_lives_in_downloads_slskd_or_an_extra_folder():
    assert location_of('Artist - Song.mp3') == 'downloads'
    assert location_of('slskd/user/Song.flac') == 'slskd'
    assert location_of('ext/abc123/Album/Song.mp3') == 'folders'


# ── working copies ──────────────────────────────────────────────────────────


def test_a_recorded_transfer_is_a_working_copy_not_library_content():
    rows = [_row('Song.flac', 30 * MB), _row('slskd/u/Song.flac', 29 * MB)]

    library, working = split_working_copies(
        rows,
        sources={'slskd/u/Song.flac': 29 * MB},
        slskd_in_place=True,
        referenced=set(),
    )

    assert [r['file'] for r in library] == ['Song.flac']
    assert working == {'slskd/u/Song.flac': 29 * MB}


def test_a_transfer_outside_the_library_folders_still_counts():
    library, working = split_working_copies(
        [_row('Song.flac')],
        sources={'../slskd/u/Song.flac': 5},
        slskd_in_place=False,
        referenced=set(),
    )

    assert len(library) == 1
    assert working == {'../slskd/u/Song.flac': 5}


def test_unreferenced_slskd_files_are_working_copies_when_not_kept_there():
    rows = [
        _row('slskd/u/Kept.flac', 10),
        _row('slskd/u/Leftover.flac', 20),
        _row('Song.mp3', 30),
    ]

    library, working = split_working_copies(
        rows,
        sources={},
        slskd_in_place=False,
        referenced={'slskd/u/Kept.flac'},
    )

    assert sorted(r['file'] for r in library) == [
        'Song.mp3',
        'slskd/u/Kept.flac',
    ]
    assert working == {'slskd/u/Leftover.flac': 20}


def test_slskd_files_are_the_library_while_they_are_left_in_place():
    library, working = split_working_copies(
        [_row('slskd/u/Song.flac')],
        sources={},
        slskd_in_place=True,
        referenced=set(),
    )

    assert len(library) == 1
    assert working == {}


# ── totals and the period ───────────────────────────────────────────────────


def test_totals_break_down_by_provider_location_and_format():
    rows = [
        _row('A.mp3', 10 * MB),
        _row('B.mp3', 5 * MB),
        _row('slskd/u/C.flac', 40 * MB),
        _row('ext/f1/D.mp3', 1 * MB),
    ]

    totals = library_totals(rows, {'A.mp3': 'youtube-music'})

    assert totals['files'] == 4
    assert totals['bytes'] == 56 * MB
    assert totals['by_provider'] == [
        {'id': 'slskd', 'files': 1, 'bytes': 40 * MB},
        {'id': 'youtube-music', 'files': 1, 'bytes': 10 * MB},
        {'id': 'unknown', 'files': 1, 'bytes': 5 * MB},
        {'id': 'folder', 'files': 1, 'bytes': 1 * MB},
    ]
    assert [b['id'] for b in totals['by_location']] == [
        'slskd',
        'downloads',
        'folders',
    ]
    assert totals['by_format'][0] == {
        'id': 'flac',
        'files': 1,
        'bytes': 40 * MB,
    }


def test_a_recorded_download_time_wins_over_the_file_date():
    rows = [_row('A.mp3', days_ago=100), _row('B.mp3', days_ago=3)]

    times = added_times(rows, {'A.mp3': (NOW - timedelta(days=1)).isoformat()})

    assert times['A.mp3'] == NOW - timedelta(days=1)
    assert times['B.mp3'] == NOW - timedelta(days=3)


def test_the_period_counts_what_came_in_by_provider_and_bucket():
    rows = [
        _row('Old.mp3', 7, days_ago=40),
        _row('A.mp3', 10, days_ago=1),
        _row('B.mp3', 20, days_ago=2),
        _row('slskd/u/C.flac', 100, days_ago=6),
    ]
    times = added_times(rows, {})

    period = period_added(rows, times, {'A.mp3': 'youtube'}, now=NOW, days=7)

    assert period['files'] == 3
    assert period['bytes'] == 130
    assert period['bucket_days'] == 1
    assert len(period['series']) == 7
    assert period['series'][-2] == {'files': 1, 'bytes': 10}
    assert period['series'][-3] == {'files': 1, 'bytes': 20}
    assert {p['id']: p['files'] for p in period['by_provider']} == {
        'slskd': 1,
        'youtube': 1,
        'unknown': 1,
    }


def test_a_long_period_is_bucketed_by_week():
    period = period_added([], {}, {}, now=NOW, days=90)

    assert period['bucket_days'] == 7
    assert len(period['series']) == 13


# ── growth ──────────────────────────────────────────────────────────────────


def test_growth_is_estimated_from_file_dates_before_the_first_snapshot():
    rows = [_row('A.mp3', 10, days_ago=5), _row('B.mp3', 20, days_ago=2)]
    times = added_times(rows, {})

    grown = growth(
        [], rows, times, now=NOW, days=7, current={'files': 2, 'bytes': 30}
    )

    points = grown['points']
    assert len(points) == 8
    assert points[0] == {
        'day': '2026-10-20',
        'files': 0,
        'bytes': 0,
        'estimated': True,
    }
    assert points[3]['bytes'] == 10
    assert points[-2]['bytes'] == 30
    assert points[-1] == {
        'day': '2026-10-27',
        'files': 2,
        'bytes': 30,
        'estimated': False,
    }
    assert grown['change'] == {'files': 2, 'bytes': 30}
    assert grown['since'] is None


def test_growth_takes_the_latest_snapshot_up_to_each_day():
    snapshots = [
        {'day': '2026-10-10', 'files': 1, 'bytes': 100},
        {'day': '2026-10-23', 'files': 3, 'bytes': 300},
        {'day': '2026-10-25', 'files': 2, 'bytes': 250},
    ]

    grown = growth(
        snapshots,
        [],
        {},
        now=NOW,
        days=7,
        current={'files': 4, 'bytes': 400},
    )

    by_day = {p['day']: p for p in grown['points']}
    assert by_day['2026-10-20']['bytes'] == 100
    assert by_day['2026-10-22']['bytes'] == 100
    assert by_day['2026-10-23']['bytes'] == 300
    assert by_day['2026-10-24']['bytes'] == 300
    assert by_day['2026-10-26']['bytes'] == 250
    assert not any(p['estimated'] for p in grown['points'])
    assert grown['change'] == {'files': 3, 'bytes': 300}
    assert grown['per_day_bytes'] == round(300 / 7)
    assert grown['since'] == '2026-10-10'


def test_a_year_of_growth_has_a_point_a_week():
    grown = growth(
        [], [], {}, now=NOW, days=365, current={'files': 0, 'bytes': 0}
    )

    assert grown['step_days'] == 7
    assert len(grown['points']) == 53
    assert grown['points'][-1]['day'] == '2026-10-27'


def test_the_disk_fills_at_the_rate_the_library_grows():
    assert forecast_days({'free': 1000}, 10) == 100
    assert forecast_days({'free': 1000}, 0) is None
    assert forecast_days({'free': 1000}, -5) is None
    assert forecast_days(None, 10) is None


# ── duplicates ──────────────────────────────────────────────────────────────


def test_the_same_file_in_two_folders_is_an_exact_duplicate():
    rows = [
        _row('Mix A/Artist - Song.mp3', 8 * MB, artist='Artist', title='Song'),
        _row('Mix B/Artist - Song.mp3', 8 * MB, artist='Artist', title='Song'),
        _row('Other.mp3', 3 * MB, artist='Else', title='Other'),
    ]

    found = duplicates(rows, {})

    assert found['groups'] == 1
    assert found['files'] == 1
    assert found['bytes'] == 8 * MB
    assert found['exact'] == {'groups': 1, 'files': 1, 'bytes': 8 * MB}
    assert found['likely']['groups'] == 0
    group = found['examples'][0]
    assert group['kind'] == 'exact'
    assert [f['file'] for f in group['files']] == [
        'Mix A/Artist - Song.mp3',
        'Mix B/Artist - Song.mp3',
    ]


def test_one_song_from_two_providers_is_a_likely_duplicate():
    rows = [
        _row(
            'Artist - Song.mp3',
            8 * MB,
            artist='Artist',
            title='Song',
            duration=200.0,
        ),
        _row(
            'slskd/u/01 Song.flac',
            30 * MB,
            artist='Artist; Guest',
            title='Song (feat. Guest)',
            duration=201.5,
        ),
    ]

    found = duplicates(rows, {'Artist - Song.mp3': 'youtube-music'})

    assert found['likely'] == {'groups': 1, 'files': 1, 'bytes': 8 * MB}
    group = found['examples'][0]
    assert group['kind'] == 'likely'
    # Keeping the biggest copy frees the rest.
    assert [(f['file'], f['provider']) for f in group['files']] == [
        ('slskd/u/01 Song.flac', 'slskd'),
        ('Artist - Song.mp3', 'youtube-music'),
    ]


@pytest.mark.parametrize(
    ('first', 'second'),
    [
        (200.0, 230.0),  # an extended version
        (0.0, 200.0),  # a length nobody knows can't tell
    ],
)
def test_songs_of_different_lengths_are_not_duplicates(first, second):
    rows = [
        _row('A.mp3', 1, artist='Artist', title='Song', duration=first),
        _row('B.mp3', 2, artist='Artist', title='Song', duration=second),
    ]

    assert duplicates(rows, {})['groups'] == 0


# ── downloads ───────────────────────────────────────────────────────────────


def test_download_totals_count_each_outcome_and_completed_bytes():
    def at(days):
        return (NOW - timedelta(days=days)).isoformat()

    rows = [
        {'at': at(40), 'outcome': OUTCOME_FAILED, 'provider': '', 'bytes': 0},
        {
            'at': at(1),
            'outcome': OUTCOME_COMPLETED,
            'provider': 'slskd',
            'bytes': 30,
        },
        {
            'at': at(2),
            'outcome': OUTCOME_COMPLETED,
            'provider': 'youtube-music',
            'bytes': 5,
        },
        {'at': at(2), 'outcome': OUTCOME_SKIPPED, 'provider': '', 'bytes': 0},
        {'at': at(3), 'outcome': OUTCOME_FAILED, 'provider': '', 'bytes': 0},
    ]

    totals = download_totals(rows, now=NOW, days=7, first_at=at(40))

    assert totals[OUTCOME_COMPLETED] == 2
    assert totals[OUTCOME_SKIPPED] == 1
    assert totals[OUTCOME_FAILED] == 1
    assert totals['bytes'] == 35
    assert totals['by_provider'][0] == {'id': 'slskd', 'files': 1, 'bytes': 30}
    assert totals['series'][-2][OUTCOME_COMPLETED] == 1
    assert totals['series'][-3] == {
        OUTCOME_COMPLETED: 1,
        OUTCOME_SKIPPED: 1,
        OUTCOME_FAILED: 0,
    }
    assert totals['since'] == at(40)


# ── the whole report and its snapshot ───────────────────────────────────────


def test_the_report_keeps_working_copies_out_of_the_library():
    rows = [
        _row('Song.flac', 30, days_ago=1, artist='A', title='Song'),
        _row('slskd/u/Song.flac', 29, days_ago=1, artist='A', title='Song'),
    ]

    report = usage_report(
        rows,
        providers={'Song.flac': 'slskd'},
        recorded={},
        sources={'slskd/u/Song.flac': 29},
        slskd_in_place=False,
        referenced={'Song.flac'},
        snapshots=[],
        downloads=[],
        downloads_since=None,
        disk={'total': 1000, 'used': 900, 'free': 100},
        now=NOW,
        days=30,
    )

    assert report['library']['files'] == 1
    assert report['library']['bytes'] == 30
    assert report['working']['files'] == 1
    assert report['working']['bytes'] == 29
    assert report['working']['examples'] == [
        {'file': 'slskd/u/Song.flac', 'bytes': 29}
    ]
    # The source copy is no duplicate of the song it was copied into.
    assert report['duplicates']['groups'] == 0
    assert report['period']['files'] == 1
    assert report['disk']['free'] == 100
    assert (
        report['disk']['days_left'] == 100 // report['growth']['per_day_bytes']
    )
    assert snapshot_of(report) == {
        'files': 1,
        'bytes': 30,
        'working_files': 1,
        'working_bytes': 29,
        'by_provider': report['library']['by_provider'],
        'by_location': report['library']['by_location'],
    }
    assert library_snapshot(
        rows,
        providers={'Song.flac': 'slskd'},
        sources={'slskd/u/Song.flac': 29},
        slskd_in_place=False,
        referenced={'Song.flac'},
    ) == snapshot_of(report)


def test_snapshots_keep_one_reading_a_day(tmp_path):
    store = UsageSnapshots(tmp_path / 'library.db')
    store.record({'files': 1, 'bytes': 10}, NOW - timedelta(days=9))
    store.record({'files': 2, 'bytes': 20}, NOW - timedelta(days=2))
    store.record({'files': 3, 'bytes': 30}, NOW - timedelta(hours=1))
    store.record({'files': 4, 'bytes': 40, 'working_files': 1}, NOW)

    rows = store.since('2026-10-24')

    # The reading before the period still stands for its first days.
    assert [(r['day'], r['bytes']) for r in rows] == [
        ('2026-10-18', 10),
        ('2026-10-25', 20),
        ('2026-10-27', 40),
    ]
    assert rows[-1]['working_files'] == 1
