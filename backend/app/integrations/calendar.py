"""
Google Calendar API integration.
Handles reading availability and writing appointment events.
"""
import logging
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.config import settings
from app.models.schemas import BookingEntities, BusinessHours, SalonConfig, TimeSlot

logger = logging.getLogger(__name__)

SGT = ZoneInfo("Asia/Singapore")
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarClient:
    def __init__(self, salon: SalonConfig):
        self.salon = salon
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service
        creds = Credentials(
            token=None,
            refresh_token=self.salon.google_refresh_token,
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=SCOPES,
        )
        creds.refresh(Request())
        self._service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        return self._service

    async def get_available_slots(
        self,
        salon_id: str,
        date_str: str,
        duration_mins: int,
        business_hours: dict[str, BusinessHours],
    ) -> list[TimeSlot]:
        """
        Return available time slots for a given date.
        Checks the salon's Google Calendar for existing events and returns gaps.
        """
        service = self._get_service()
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        day_name = target_date.strftime("%A").lower()

        hours = business_hours.get(day_name)
        if not hours:
            return []  # Closed on this day

        open_h, open_m = map(int, hours.open.split(":"))
        close_h, close_m = map(int, hours.close.split(":"))

        day_start = datetime(target_date.year, target_date.month, target_date.day,
                             open_h, open_m, tzinfo=SGT)
        day_end = datetime(target_date.year, target_date.month, target_date.day,
                           close_h, close_m, tzinfo=SGT)

        # Fetch busy periods from Google Calendar
        freebusy_body = {
            "timeMin": day_start.isoformat(),
            "timeMax": day_end.isoformat(),
            "items": [{"id": self.salon.calendar_id}],
        }
        result = service.freebusy().query(body=freebusy_body).execute()
        busy_periods = result["calendars"][self.salon.calendar_id]["busy"]

        # Convert busy periods to datetime ranges
        busy_ranges = [
            (
                datetime.fromisoformat(b["start"]).astimezone(SGT),
                datetime.fromisoformat(b["end"]).astimezone(SGT),
            )
            for b in busy_periods
        ]

        # Generate candidate slots every 30 minutes
        slots: list[TimeSlot] = []
        slot_duration = timedelta(minutes=duration_mins)
        cursor = day_start
        while cursor + slot_duration <= day_end:
            slot_end = cursor + slot_duration
            if not _overlaps_busy(cursor, slot_end, busy_ranges):
                slots.append(TimeSlot(
                    date=date_str,
                    start=cursor.strftime("%H:%M"),
                    end=slot_end.strftime("%H:%M"),
                    label=cursor.strftime("%-d %b (%A), %-I:%M %p"),
                ))
            cursor += timedelta(minutes=30)

        return slots[:8]  # Return max 8 slots

    async def create_appointment(
        self,
        salon_id: str,
        entities: BookingEntities,
        service_label: str,
        location: str,
    ) -> str:
        """
        Write an appointment to Google Calendar.
        Returns the created event ID.
        """
        service = self._get_service()
        date_str = entities.date or ""
        time_str = entities.time or "09:00"
        duration = entities.duration_mins or 60

        dt_str = f"{date_str}T{time_str}:00"
        start = datetime.fromisoformat(dt_str).replace(tzinfo=SGT)
        end = start + timedelta(minutes=duration)

        event = {
            "summary": f"{service_label} – {entities.client_name}",
            "location": location,
            "description": (
                f"Client: {entities.client_name}\n"
                f"Phone: {entities.client_phone}\n"
                f"Service: {service_label}\n"
                f"Source: HeyZenzai"
            ),
            "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Singapore"},
            "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Singapore"},
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 60}],
            },
        }

        created = service.events().insert(
            calendarId=self.salon.calendar_id, body=event
        ).execute()

        logger.info(f"Calendar event created: {created['id']} for {entities.client_name}")
        return created["id"]

    async def get_appointments_for_date(self, date_str: str) -> list[dict]:
        """
        Fetch all HeyZenzai-booked appointments for a given date.
        Used by the retention engine for reminder messages.
        """
        service = self._get_service()
        target = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=SGT)
        time_min = target.replace(hour=0, minute=0, second=0).isoformat()
        time_max = target.replace(hour=23, minute=59, second=59).isoformat()

        result = service.events().list(
            calendarId=self.salon.calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        appointments = []
        for event in result.get("items", []):
            description = event.get("description", "")
            if "Source: HeyZenzai" not in description:
                continue  # Skip non-HeyZenzai events

            phone = _extract_field(description, "Phone")
            name = _extract_field(description, "Client")
            svc = _extract_field(description, "Service")
            start_dt = event.get("start", {}).get("dateTime", "")
            time_label = ""
            if start_dt:
                time_label = datetime.fromisoformat(start_dt).astimezone(SGT).strftime("%-I:%M %p")

            appointments.append({
                "event_id": event["id"],
                "client_name": name,
                "client_phone": phone,
                "service": svc,
                "time_label": time_label,
            })
        return appointments

    async def get_appointments_older_than_days(self, days: int) -> list[dict]:
        """Fetch HeyZenzai appointments from 'days' ago (for rebooking nudges)."""
        service = self._get_service()
        cutoff = datetime.now(SGT) - timedelta(days=days)
        target_date = (cutoff - timedelta(days=2)).date()

        time_min = datetime(target_date.year, target_date.month, target_date.day,
                            tzinfo=SGT).isoformat()
        time_max = (datetime(target_date.year, target_date.month, target_date.day,
                             tzinfo=SGT) + timedelta(hours=24)).isoformat()

        result = service.events().list(
            calendarId=self.salon.calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
        ).execute()

        appointments = []
        for event in result.get("items", []):
            description = event.get("description", "")
            if "Source: HeyZenzai" not in description:
                continue
            phone = _extract_field(description, "Phone")
            name = _extract_field(description, "Client")
            svc = _extract_field(description, "Service")
            appointments.append({
                "event_id": event["id"],
                "client_name": name,
                "client_phone": phone,
                "service": svc,
                "nudge_sent": False,  # TODO: track in Supabase
            })
        return appointments


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _overlaps_busy(
    slot_start: datetime,
    slot_end: datetime,
    busy_ranges: list[tuple[datetime, datetime]],
) -> bool:
    for busy_start, busy_end in busy_ranges:
        if slot_start < busy_end and slot_end > busy_start:
            return True
    return False


def _extract_field(description: str, field: str) -> str:
    for line in description.splitlines():
        if line.startswith(f"{field}:"):
            return line.split(":", 1)[1].strip()
    return ""
