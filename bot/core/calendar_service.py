"""
BEIET - Google Calendar Service.
Handles checking professor availability and scheduling meetings using a Service Account.
"""

import asyncio
import datetime
import logging
import os
from dataclasses import dataclass
from dateutil import tz
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from bot.config import config

logger = logging.getLogger("beiet.calendar")

SCOPES = ['https://www.googleapis.com/auth/calendar']

BUSINESS_HOUR_START = 9   # 09:00
BUSINESS_HOUR_END = 18    # 18:00
SLOT_DURATION_MINUTES = 30


@dataclass
class TimeSlot:
    """A single time block with start and end."""
    start: datetime.datetime
    end: datetime.datetime


class CalendarService:
    def __init__(self):
        self.service = None
        self.creds = None
        self.timezone = tz.gettz('America/Santiago')
        self._initialize_service()

    def _initialize_service(self):
        """Initializes the Google Calendar API service."""
        creds_path = config.google_calendar_credentials

        if not creds_path or not os.path.exists(creds_path):
            logger.warning(f"Google Calendar credentials not found at '{creds_path}'. Calendar features will run in mock mode.")
            return

        try:
            self.creds = service_account.Credentials.from_service_account_file(
                creds_path, scopes=SCOPES
            )
            self.service = build('calendar', 'v3', credentials=self.creds)
            logger.info("Google Calendar API service initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar API: {e}")

    # ── Google API sync wrappers (run via asyncio.to_thread) ──

    def _get_busy_slots_sync(self, time_min_iso: str, time_max_iso: str) -> list[dict]:
        """Synchronous freebusy API call."""
        body = {
            "timeMin": time_min_iso,
            "timeMax": time_max_iso,
            "timeZone": "UTC",
            "items": [{"id": config.professor_calendar_id}]
        }
        events_result = self.service.freebusy().query(body=body).execute()
        return events_result['calendars'][config.professor_calendar_id].get('busy', [])

    def _create_meeting_sync(self, student_name: str, topic: str, start_time: datetime.datetime, duration_minutes: int) -> dict:
        """Synchronous event creation API call."""
        end_time = start_time + datetime.timedelta(minutes=duration_minutes)
        event = {
            'summary': f'Tutoría BEIET: {student_name} - {topic}',
            'description': f'Tutoría solicitada a través de BEIET Discord Bot.\nTema: {topic}\nEstudiante: {student_name}',
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'America/Santiago'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'America/Santiago'},
            'conferenceData': {
                'createRequest': {
                    'requestId': f"beiet_meet_{datetime.datetime.now().timestamp()}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        }
        return self.service.events().insert(
            calendarId=config.professor_calendar_id,
            body=event,
            conferenceDataVersion=1
        ).execute()

    # ── Async public API ──

    async def get_busy_slots(self, days: int = 7) -> list[TimeSlot]:
        """Fetch busy blocks from Google Calendar (non-blocking)."""
        if not self.service or not config.professor_calendar_id:
            return []

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        time_min = now.isoformat()
        time_max = (now + datetime.timedelta(days=days)).isoformat()

        try:
            raw_slots = await asyncio.to_thread(
                self._get_busy_slots_sync, time_min, time_max
            )
            result = []
            for slot in raw_slots:
                start = datetime.datetime.fromisoformat(
                    slot['start'].replace('Z', '+00:00')
                ).astimezone(self.timezone)
                end = datetime.datetime.fromisoformat(
                    slot['end'].replace('Z', '+00:00')
                ).astimezone(self.timezone)
                result.append(TimeSlot(start=start, end=end))
            return result
        except HttpError as error:
            logger.error(f"Error fetching free/busy: {error}")
            return []

    def compute_free_slots(self, busy_slots: list[TimeSlot], days: int = 7) -> list[TimeSlot]:
        """
        Compute available 30-min blocks within business hours (Mon-Fri 09:00-18:00)
        by inverting busy blocks.
        """
        now = datetime.datetime.now(tz=self.timezone)
        free: list[TimeSlot] = []

        for day_offset in range(days):
            day = now.date() + datetime.timedelta(days=day_offset)

            # Skip weekends
            if day.weekday() >= 5:
                continue

            biz_start = datetime.datetime(
                day.year, day.month, day.day,
                BUSINESS_HOUR_START, 0, tzinfo=self.timezone
            )
            biz_end = datetime.datetime(
                day.year, day.month, day.day,
                BUSINESS_HOUR_END, 0, tzinfo=self.timezone
            )

            # Busy slots overlapping this day's business window
            day_busy = sorted(
                [s for s in busy_slots if s.start < biz_end and s.end > biz_start],
                key=lambda s: s.start,
            )

            # Walk 30-min candidates
            cursor = biz_start
            slot_delta = datetime.timedelta(minutes=SLOT_DURATION_MINUTES)
            while cursor + slot_delta <= biz_end:
                candidate_end = cursor + slot_delta

                # Skip past slots
                if candidate_end <= now:
                    cursor = candidate_end
                    continue

                # Check overlap with any busy block
                overlaps = any(
                    busy.start < candidate_end and busy.end > cursor
                    for busy in day_busy
                )

                if not overlaps:
                    free.append(TimeSlot(start=cursor, end=candidate_end))

                cursor = candidate_end

        return free

    async def get_availability_slots(self, days: int = 7) -> list[TimeSlot] | None:
        """
        Returns free TimeSlots, or None if running in mock mode.
        """
        if not self.service or not config.professor_calendar_id:
            return None

        busy = await self.get_busy_slots(days=days)
        return self.compute_free_slots(busy, days=days)

    async def check_conflict(self, start_time: datetime.datetime, duration_minutes: int = 30) -> bool:
        """
        Returns True if the proposed slot conflicts (busy, weekend, or outside business hours).
        """
        local_start = start_time.astimezone(self.timezone)
        local_end = local_start + datetime.timedelta(minutes=duration_minutes)

        # Weekend check
        if local_start.weekday() >= 5:
            return True

        # Business hours check (use full datetime comparison, consistent with compute_free_slots)
        biz_start = local_start.replace(hour=BUSINESS_HOUR_START, minute=0, second=0, microsecond=0)
        biz_end = local_start.replace(hour=BUSINESS_HOUR_END, minute=0, second=0, microsecond=0)
        if local_start < biz_start or local_end > biz_end:
            return True

        # Check against Google Calendar
        if not self.service or not config.professor_calendar_id:
            return False  # Mock mode: always allow

        busy = await self.get_busy_slots(days=1)
        return any(
            slot.start < local_end and slot.end > local_start
            for slot in busy
        )

    async def create_meeting(
        self, student_name: str, topic: str,
        start_time: datetime.datetime, duration_minutes: int = 30
    ) -> dict | None:
        """
        Creates a calendar event. Returns dict with google_event_id, meet_link, mock flag.
        Returns None on failure.
        """
        if not self.service or not config.professor_calendar_id:
            return {"google_event_id": "mock_event_id", "meet_link": None, "mock": True}

        try:
            event_result = await asyncio.to_thread(
                self._create_meeting_sync, student_name, topic, start_time, duration_minutes
            )
            return {
                "google_event_id": event_result.get("id", ""),
                "meet_link": event_result.get("hangoutLink"),
                "mock": False,
            }
        except HttpError as error:
            logger.error(f"Error creating meeting: {error}")
            return None


calendar_service = CalendarService()
