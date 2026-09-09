"""Tests for the Playlist Monitor scheduling helpers in downtify/monitor.py."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

from downtify.monitor import (
    SYNC_TIME_ENV_VAR,
    _is_due,
    _next_due_at,
    _sync_anchor_time,
)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ── _sync_anchor_time ────────────────────────────────────────────────────────


def test_sync_anchor_time_returns_none_when_unset(monkeypatch):
    monkeypatch.delenv(SYNC_TIME_ENV_VAR, raising=False)
    assert _sync_anchor_time() is None


def test_sync_anchor_time_returns_none_when_blank(monkeypatch):
    monkeypatch.setenv(SYNC_TIME_ENV_VAR, '   ')
    assert _sync_anchor_time() is None


def test_sync_anchor_time_parses_hh_mm(monkeypatch):
    monkeypatch.setenv(SYNC_TIME_ENV_VAR, '03:30')
    assert _sync_anchor_time() == time(3, 30)


def test_sync_anchor_time_parses_hour_only(monkeypatch):
    monkeypatch.setenv(SYNC_TIME_ENV_VAR, '7')
    assert _sync_anchor_time() == time(7, 0)


def test_sync_anchor_time_returns_none_for_garbage(monkeypatch):
    monkeypatch.setenv(SYNC_TIME_ENV_VAR, 'not-a-time')
    assert _sync_anchor_time() is None


def test_sync_anchor_time_returns_none_for_out_of_range_hour(monkeypatch):
    monkeypatch.setenv(SYNC_TIME_ENV_VAR, '25:00')
    assert _sync_anchor_time() is None


# ── _next_due_at ─────────────────────────────────────────────────────────────


def test_next_due_at_sub_day_interval_ignores_anchor(monkeypatch):
    monkeypatch.setenv(SYNC_TIME_ENV_VAR, '03:00')
    last = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    assert _next_due_at(last, 60) == last + timedelta(minutes=60)


def test_next_due_at_daily_without_anchor_is_unchanged(monkeypatch):
    monkeypatch.delenv(SYNC_TIME_ENV_VAR, raising=False)
    last = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    assert _next_due_at(last, 1440) == last + timedelta(days=1)


def test_next_due_at_daily_snaps_to_anchor_utc(monkeypatch):
    # Local time == UTC unless the test environment sets TZ, which
    # local-CI/dev boxes running this suite don't; treat local as UTC.
    monkeypatch.setenv(SYNC_TIME_ENV_VAR, '03:00')
    last = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    due = _next_due_at(last, 1440)
    local_due = due.astimezone()
    assert (local_due.hour, local_due.minute) == (3, 0)
    # The snapped date must not move earlier than an unsnapped due time.
    assert due.date() == (last + timedelta(days=1)).astimezone().date()


def test_next_due_at_weekly_snaps_to_anchor(monkeypatch):
    monkeypatch.setenv(SYNC_TIME_ENV_VAR, '03:00')
    last = datetime(2026, 1, 1, 22, 0, tzinfo=timezone.utc)
    due = _next_due_at(last, 10080)  # 7 days
    local_due = due.astimezone()
    assert (local_due.hour, local_due.minute) == (3, 0)
    assert local_due.date() == (last + timedelta(days=7)).astimezone().date()


def test_next_due_at_daily_snap_never_precedes_unsnapped_due(monkeypatch):
    monkeypatch.setenv(SYNC_TIME_ENV_VAR, '00:01')
    last = datetime(2026, 1, 1, 23, 59, tzinfo=timezone.utc)
    due = _next_due_at(last, 1440)
    assert due >= last + timedelta(minutes=1)


# ── _is_due ──────────────────────────────────────────────────────────────────


def test_is_due_true_when_never_checked():
    assert _is_due(None, 1440) is True


def test_is_due_false_before_interval_elapses(monkeypatch):
    monkeypatch.delenv(SYNC_TIME_ENV_VAR, raising=False)
    last = datetime.now(timezone.utc) - timedelta(minutes=30)
    assert _is_due(_iso(last), 60) is False


def test_is_due_true_after_interval_elapses(monkeypatch):
    monkeypatch.delenv(SYNC_TIME_ENV_VAR, raising=False)
    last = datetime.now(timezone.utc) - timedelta(minutes=90)
    assert _is_due(_iso(last), 60) is True


def test_is_due_handles_naive_iso_as_utc(monkeypatch):
    monkeypatch.delenv(SYNC_TIME_ENV_VAR, raising=False)
    last = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=90
    )
    assert _is_due(last.isoformat(), 60) is True


def test_is_due_returns_true_for_invalid_timestamp():
    assert _is_due('not-a-date', 60) is True


def test_is_due_respects_anchor_for_daily_interval(monkeypatch):
    # last_checked was 25h ago (past the 24h interval), but the anchor
    # time hasn't arrived yet today relative to "now" in the test's
    # local clock is inherently flaky to assert exactly, so instead we
    # check the underlying decision matches _next_due_at directly.
    monkeypatch.setenv(SYNC_TIME_ENV_VAR, '03:00')
    last = datetime.now(timezone.utc) - timedelta(hours=25)
    expected = datetime.now(timezone.utc) >= _next_due_at(last, 1440)
    assert _is_due(_iso(last), 1440) == expected
