"""Tests for CalendarService.compute_free_slots() — pure logic, no API calls."""

import datetime
from unittest.mock import patch

import pytest
from dateutil import tz

from bot.core.calendar_service import (
    CalendarService,
    TimeSlot,
    BUSINESS_HOUR_START,
    BUSINESS_HOUR_END,
    SLOT_DURATION_MINUTES,
)

SANTIAGO = tz.gettz("America/Santiago")

# Total 30-min slots per business day: (18-9)*2 = 18
SLOTS_PER_DAY = (BUSINESS_HOUR_END - BUSINESS_HOUR_START) * 60 // SLOT_DURATION_MINUTES


def _make_service() -> CalendarService:
    """Create a CalendarService without initializing Google API."""
    with patch.object(CalendarService, "_initialize_service"):
        svc = CalendarService()
        svc.timezone = SANTIAGO
    return svc


def _dt(year, month, day, hour=0, minute=0) -> datetime.datetime:
    """Helper to create tz-aware datetimes in Santiago."""
    return datetime.datetime(year, month, day, hour, minute, tzinfo=SANTIAGO)


class TestComputeFreeSlotsNoBusy:
    """When there are no busy slots, all business-hour blocks should be free."""

    def test_full_weekday_returns_18_slots(self):
        svc = _make_service()
        # Mock 'now' to Monday 2026-03-09 at 00:00 (start of day, all slots are future)
        mock_now = _dt(2026, 3, 9, 0, 0)
        with patch("bot.core.calendar_service.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.timedelta = datetime.timedelta
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            free = svc.compute_free_slots([], days=1)

        assert len(free) == SLOTS_PER_DAY
        assert free[0].start.hour == BUSINESS_HOUR_START
        assert free[-1].end.hour == BUSINESS_HOUR_END

    def test_weekend_days_skipped(self):
        svc = _make_service()
        # Saturday 2026-03-14
        mock_now = _dt(2026, 3, 14, 0, 0)
        with patch("bot.core.calendar_service.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.timedelta = datetime.timedelta
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            # days=2 covers Saturday + Sunday only
            free = svc.compute_free_slots([], days=2)

        assert len(free) == 0

    def test_week_has_five_working_days(self):
        svc = _make_service()
        # Monday 2026-03-09 at midnight
        mock_now = _dt(2026, 3, 9, 0, 0)
        with patch("bot.core.calendar_service.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.timedelta = datetime.timedelta
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            free = svc.compute_free_slots([], days=7)

        assert len(free) == SLOTS_PER_DAY * 5


class TestComputeFreeSlotsWithBusy:
    """Busy blocks should exclude overlapping candidates."""

    def test_single_busy_block_excludes_one_slot(self):
        svc = _make_service()
        # Monday 2026-03-09, busy from 10:00-10:30
        mock_now = _dt(2026, 3, 9, 0, 0)
        busy = [TimeSlot(start=_dt(2026, 3, 9, 10, 0), end=_dt(2026, 3, 9, 10, 30))]

        with patch("bot.core.calendar_service.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.timedelta = datetime.timedelta
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            free = svc.compute_free_slots(busy, days=1)

        assert len(free) == SLOTS_PER_DAY - 1
        # The 10:00-10:30 slot should not be in the result
        starts = {s.start.hour * 60 + s.start.minute for s in free}
        assert 10 * 60 not in starts

    def test_partial_overlap_excludes_both_adjacent_slots(self):
        svc = _make_service()
        # Busy 10:15-10:45 overlaps both 10:00-10:30 and 10:30-11:00
        mock_now = _dt(2026, 3, 9, 0, 0)
        busy = [TimeSlot(start=_dt(2026, 3, 9, 10, 15), end=_dt(2026, 3, 9, 10, 45))]

        with patch("bot.core.calendar_service.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.timedelta = datetime.timedelta
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            free = svc.compute_free_slots(busy, days=1)

        assert len(free) == SLOTS_PER_DAY - 2

    def test_full_day_busy_returns_zero_slots(self):
        svc = _make_service()
        mock_now = _dt(2026, 3, 9, 0, 0)
        # Busy the entire business day
        busy = [TimeSlot(start=_dt(2026, 3, 9, 9, 0), end=_dt(2026, 3, 9, 18, 0))]

        with patch("bot.core.calendar_service.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.timedelta = datetime.timedelta
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            free = svc.compute_free_slots(busy, days=1)

        assert len(free) == 0


class TestPastSlotSkipping:
    """Slots that have already passed today should be excluded."""

    def test_past_morning_slots_skipped(self):
        svc = _make_service()
        # Monday 2026-03-09 at 12:00 — morning slots (09:00-12:00) should be skipped
        mock_now = _dt(2026, 3, 9, 12, 0)

        with patch("bot.core.calendar_service.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.timedelta = datetime.timedelta
            mock_dt.datetime.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
            free = svc.compute_free_slots([], days=1)

        # 12:00-18:00 = 6 hours = 12 slots
        assert len(free) == 12
        assert free[0].start.hour == 12
        assert free[0].start.minute == 0
