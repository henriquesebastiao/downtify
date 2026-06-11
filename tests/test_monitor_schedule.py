"""Playlist monitor schedule helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from downtify.monitor import (
    CALENDAR_INTERVAL_MINUTES,
    next_scheduled_run,
    parse_check_time_minutes,
    parse_check_timezone,
)


def test_parse_check_time_minutes() -> None:
    assert parse_check_time_minutes('03:30') == 210
    assert parse_check_time_minutes('3:30') == 210
    assert parse_check_time_minutes(90) == 90
    assert parse_check_time_minutes('') is None
    assert parse_check_time_minutes('25:00') is None


def test_parse_check_timezone() -> None:
    assert parse_check_timezone('Europe/London') == 'Europe/London'
    assert parse_check_timezone('') is None
    assert parse_check_timezone('Not/AZone') is None


def test_daily_schedule_waits_for_time_of_day() -> None:
    tz = ZoneInfo('UTC')
    enabled_at = datetime(2026, 6, 11, 9, 0, tzinfo=tz).isoformat()
    next_run = next_scheduled_run(enabled_at, 1440, 180, 'UTC')
    assert next_run == datetime(2026, 6, 12, 3, 0, tzinfo=tz)
    assert datetime(2026, 6, 11, 10, 0, tzinfo=tz) < next_run
    assert datetime(2026, 6, 12, 3, 5, tzinfo=tz) >= next_run


def test_daily_schedule_uses_stored_timezone_not_server(monkeypatch) -> None:
    monkeypatch.setattr(
        'downtify.monitor._local_now',
        lambda: datetime(2026, 6, 11, 12, 0, tzinfo=ZoneInfo('UTC')),
    )
    enabled_at = datetime(
        2026, 6, 11, 8, 0, tzinfo=ZoneInfo('America/New_York')
    ).isoformat()
    server_next = next_scheduled_run(enabled_at, 1440, 180, None)
    browser_next = next_scheduled_run(
        enabled_at, 1440, 180, 'America/New_York'
    )
    assert server_next == datetime(2026, 6, 12, 3, 0, tzinfo=ZoneInfo('UTC'))
    assert browser_next == datetime(
        2026, 6, 12, 3, 0, tzinfo=ZoneInfo('America/New_York')
    )
    assert server_next != browser_next


def test_interval_schedule_without_check_time() -> None:
    last = datetime(2026, 6, 11, 10, 0, tzinfo=timezone.utc).isoformat()
    nxt = next_scheduled_run(last, 60, None)
    assert nxt == datetime(2026, 6, 11, 11, 0, tzinfo=timezone.utc)


def test_calendar_interval_constant() -> None:
    assert CALENDAR_INTERVAL_MINUTES == 1440
