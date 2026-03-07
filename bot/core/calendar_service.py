"""
BEIET - Google Calendar Service.
Handles checking professor availability and scheduling meetings using a Service Account.
"""

import datetime
import logging
import os
from dateutil import tz
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from bot.config import config

logger = logging.getLogger("beiet.calendar")

SCOPES = ['https://www.googleapis.com/auth/calendar']

class CalendarService:
    def __init__(self):
        self.service = None
        self.creds = None
        self.timezone = tz.gettz('America/Santiago') # Default timezone for Chile
        self._initialize_service()

    def _initialize_service(self):
        """Initializes the Google Calendar API service."""
        creds_path = config.google_calendar_credentials
        
        if not creds_path or not os.path.exists(creds_path):
            logger.warning(f"⚠️ Google Calendar credentials not found at '{creds_path}'. Calendar features will run in mock mode.")
            return

        try:
            self.creds = service_account.Credentials.from_service_account_file(
                creds_path, scopes=SCOPES
            )
            # Optionally delegate domain authority if configured
            # self.creds = self.creds.with_subject('admin@yourdomain.com')
            
            self.service = build('calendar', 'v3', credentials=self.creds)
            logger.info("✅ Google Calendar API service initialized successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Calendar API: {e}")

    def get_availability(self, days: int = 7) -> str:
        """
        Fetches the upcoming free/busy information for the professor's calendar.
        Returns a formatted markdown string of available slots.
        """
        if not self.service or not config.professor_calendar_id:
            return "⚠️ El servicio de calendario no está configurado (Mock Mode: El profesor tiene disponibilidad simulada el Viernes a las 15:00)."

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        time_min = now.isoformat()
        time_max = (now + datetime.timedelta(days=days)).isoformat()

        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "timeZone": "UTC",
            "items": [{"id": config.professor_calendar_id}]
        }

        try:
            events_result = self.service.freebusy().query(body=body).execute()
            busy_slots = events_result['calendars'][config.professor_calendar_id].get('busy', [])
            
            # Simple logic: If there are busy slots, we list them. 
            # In a real scheduling app, you'd calculate the INVERSE of busy slots 
            # inside standard working hours (e.g., 9-18).
            
            if not busy_slots:
                return f"El calendario del profesor está libre en los próximos {days} días. Puedes proponer cualquier horario hábil."
            
            # Just showing raw busy gaps for the LLM to interpret
            slots_str = "El profesor tiene los siguientes bloques OCUPADOS (no agendar aquí):\n"
            for slot in busy_slots:
                start = datetime.datetime.fromisoformat(slot['start'].replace('Z', '+00:00')).astimezone(self.timezone)
                end = datetime.datetime.fromisoformat(slot['end'].replace('Z', '+00:00')).astimezone(self.timezone)
                slots_str += f"- {start.strftime('%Y-%m-%d %H:%M')} a {end.strftime('%H:%M')} \n"
                
            slots_str += "\nEl LLM debe analizar esto y proponer 2 bloques libres en horario hábil."
            return slots_str

        except HttpError as error:
            logger.error(f"An error occurred fetching free/busy: {error}")
            return "❌ Hubo un error al consultar la disponibilidad del profesor."

    def create_meeting(self, student_name: str, topic: str, start_time: datetime.datetime, duration_minutes: int = 30) -> str:
        """
        Creates a calendar event with a Google Meet link.
        """
        if not self.service or not config.professor_calendar_id:
            return "⚠️ (Mock Mode) Cita agendada exitosamente en el simulador. [Enlace de Meet Simulado]"

        end_time = start_time + datetime.timedelta(minutes=duration_minutes)

        event = {
            'summary': f'Tutoría BEIET: {student_name} - {topic}',
            'description': f'Tutoría solicitada a través de BEIET Discord Bot.\nTema: {topic}\nEstudiante: {student_name}',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Santiago',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Santiago',
            },
            # Create a Google Meet link
            'conferenceData': {
                'createRequest': {
                    'requestId': f"beiet_meet_{datetime.datetime.now().timestamp()}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        }

        try:
            event_result = self.service.events().insert(
                calendarId=config.professor_calendar_id, 
                body=event,
                conferenceDataVersion=1 # Required for Google Meet creation
            ).execute()
            
            meet_link = event_result.get('hangoutLink', 'No se pudo generar enlace de Meet')
            return meet_link
        except HttpError as error:
            logger.error(f"An error occurred creating the meeting: {error}")
            return None

calendar_service = CalendarService()
