"""
Retention & Recovery Engine (Phase 3+)

Handles:
- 24h pre-appointment reminder messages
- 4-week re-booking nudges based on service lifecycle
- No-show follow-up

This module is designed to be called from a scheduled cron job.
"""
import logging
from datetime import date, timedelta

from app.config import settings
from app.integrations.calendar import CalendarClient
from app.integrations.whatsapp import send_whatsapp_message
from app.integrations.db import get_all_salons

logger = logging.getLogger(__name__)

REMINDER_TEMPLATE = (
    "Hi {name}! 😊 Just a reminder of your *{service}* appointment at *{salon}* "
    "tomorrow ({time}). Reply *YES* to confirm or *RESCHEDULE* to pick a new time."
)

REBOOKING_NUDGE_TEMPLATE = (
    "Hi {name}! 👋 It's been {weeks} weeks since your last *{service}* with us. "
    "Would you like to book your next session? Reply *BOOK* and I'll find you a great slot! 😊"
)


async def send_daily_reminders():
    """
    Cron job: runs daily at 9 AM SGT.
    Fetches all appointments for tomorrow and sends WhatsApp utility reminders.
    """
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    salons = await get_all_salons()

    for salon in salons:
        if not salon.is_active:
            continue
        try:
            calendar = CalendarClient(salon)
            appointments = await calendar.get_appointments_for_date(tomorrow)
            for appt in appointments:
                client_phone = appt.get("client_phone")
                client_name = appt.get("client_name", "there")
                service = appt.get("service", "appointment")
                time_label = appt.get("time_label", "")

                if not client_phone:
                    continue

                msg = REMINDER_TEMPLATE.format(
                    name=client_name,
                    service=service,
                    salon=salon.business_name,
                    time=time_label,
                )
                await send_whatsapp_message(
                    to=client_phone,
                    message=msg,
                    phone_number_id=salon.whatsapp_number,
                )
                logger.info(f"Reminder sent to {client_phone} for {salon.business_name}")
        except Exception as e:
            logger.error(f"Reminder job failed for salon {salon.salon_id}: {e}")


async def send_rebooking_nudges():
    """
    Cron job: runs weekly.
    Identifies clients whose service lifecycle suggests they're due for a return visit.

    Service rebooking intervals (configurable per service type):
    - Hair colour / highlights: 6 weeks
    - Brow threading: 4 weeks
    - Facial treatments: 4–6 weeks
    - Waxing: 4 weeks
    - Laser treatments: 4–6 weeks
    """
    DEFAULT_REBOOKING_WEEKS = 4
    salons = await get_all_salons()

    for salon in salons:
        if not salon.is_active:
            continue
        try:
            calendar = CalendarClient(salon)
            past_appointments = await calendar.get_appointments_older_than_days(
                days=DEFAULT_REBOOKING_WEEKS * 7 - 2  # 2-day grace window
            )
            for appt in past_appointments:
                if appt.get("nudge_sent"):
                    continue
                client_phone = appt.get("client_phone")
                client_name = appt.get("client_name", "there")
                service = appt.get("service", "your last service")
                if not client_phone:
                    continue

                msg = REBOOKING_NUDGE_TEMPLATE.format(
                    name=client_name,
                    weeks=DEFAULT_REBOOKING_WEEKS,
                    service=service,
                )
                await send_whatsapp_message(
                    to=client_phone,
                    message=msg,
                    phone_number_id=salon.whatsapp_number,
                )
                logger.info(f"Rebooking nudge sent to {client_phone}")
        except Exception as e:
            logger.error(f"Rebooking nudge job failed for salon {salon.salon_id}: {e}")
