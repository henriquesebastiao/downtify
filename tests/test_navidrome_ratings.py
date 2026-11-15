"""Tests for downtify/navidrome_ratings.py: dztnr's star scale, the
options sanitiser and the repeat-schedule rule. All pure and offline.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from downtify import navidrome_ratings

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ('rank', 'stars'),
    [
        (0, 0),
        (9_999, 0),
        (10_000, 1),
        (99_999, 1),
        (100_000, 2),
        (299_999, 2),
        (300_000, 3),
        (599_999, 3),
        (600_000, 4),
        (849_999, 4),
        (850_000, 5),
        (1_000_000, 5),
    ],
)
def test_absolute_stars_match_dztnr(rank, stars):
    assert navidrome_ratings.stars_from_rank(rank) == stars


@pytest.mark.parametrize(
    ('rank', 'top', 'stars'),
    [
        (800, 1000, 5),
        (799, 1000, 4),
        (600, 1000, 4),
        (400, 1000, 3),
        (200, 1000, 2),
        (199, 1000, 1),
        (1, 1000, 1),
        (0, 1000, 0),
        (500, None, 0),
        (500, 0, 0),
    ],
)
def test_relative_stars_match_dztnr(rank, top, stars):
    assert navidrome_ratings.stars_from_relative_rank(rank, top) == stars


def test_effective_settings_defaults_and_bad_values():
    assert navidrome_ratings.effective_settings(None) == {
        'repeat': 'off',
        'skip_rated': True,
        'skip_starred': False,
        'grading': 'absolute',
    }
    assert navidrome_ratings.effective_settings({
        'repeat': 'hourly',
        'grading': 'x',
        'skip_rated': 0,
    }) == {
        'repeat': 'off',
        'skip_rated': False,
        'skip_starred': False,
        'grading': 'absolute',
    }


def test_effective_settings_keeps_valid_values_and_drops_unknown_keys():
    assert navidrome_ratings.effective_settings({
        'repeat': 'monthly',
        'grading': 'album',
        'skip_starred': 1,
        'other': 'x',
    }) == {
        'repeat': 'monthly',
        'skip_rated': True,
        'skip_starred': True,
        'grading': 'album',
    }
    assert navidrome_ratings.effective_settings('nope') == (
        navidrome_ratings.effective_settings(None)
    )


def test_effective_settings_returns_a_fresh_dict():
    first = navidrome_ratings.effective_settings(None)
    first['repeat'] = 'daily'
    assert navidrome_ratings.effective_settings(None)['repeat'] == 'off'
    assert navidrome_ratings.DEFAULTS['repeat'] == 'off'


def test_next_run_at():
    weekly = {'repeat': 'weekly'}
    done = {'started_at': '2026-11-01T04:00:00+00:00', 'state': 'done'}
    failed = {**done, 'state': 'failed'}
    assert navidrome_ratings.next_run_at({'repeat': 'off'}, done) is None
    assert navidrome_ratings.next_run_at(weekly, None) == EPOCH
    assert navidrome_ratings.next_run_at(weekly, done) == datetime(
        2026, 11, 8, 4, tzinfo=timezone.utc
    )
    assert navidrome_ratings.next_run_at(weekly, failed) == datetime(
        2026, 11, 1, 10, tzinfo=timezone.utc
    )


@pytest.mark.parametrize(
    'last', [{}, {'started_at': None}, {'started_at': 'not a date'}]
)
def test_next_run_at_without_a_usable_last_run_is_due_now(last):
    assert navidrome_ratings.next_run_at({'repeat': 'daily'}, last) == EPOCH


def test_next_run_at_treats_naive_timestamps_as_utc():
    last = {'started_at': '2026-11-01T04:00:00', 'state': 'done'}
    assert navidrome_ratings.next_run_at({'repeat': 'daily'}, last) == (
        datetime(2026, 11, 2, 4, tzinfo=timezone.utc)
    )


def test_next_run_at_converts_offsets_to_utc():
    last = {'started_at': '2026-11-01T06:00:00+02:00', 'state': 'done'}
    assert navidrome_ratings.next_run_at({'repeat': 'daily'}, last) == (
        datetime(2026, 11, 2, 4, tzinfo=timezone.utc)
    )
