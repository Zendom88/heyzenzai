import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from app.config import settings
from app.models.schemas import (
    BookingEntities,
    BookingState,
    ConversationSession,
    SalonConfig,
    TimeSlot,
)
from app.integrations.calendar import CalendarClient
from app.integrations.db import get_session, save_session

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# System Prompt
# ──────────────────────────────────────────────

BOOKING_SYSTEM_PROMPT = """You are a warm, professional booking assistant for a Singapore beauty and wellness salon.
You communicate via WhatsApp. Keep messages SHORT (under 2 sentences ideally). Use friendly, polite English.
You may understand Singlish but always reply in clean English.

Your job is to guide the customer through booking an appointment step by step.

CURRENT SALON CONTEXT:
{salon_context}

CURRENT BOOKING STATE: {state}
ENTITIES COLLECTED SO FAR: {entities}

Based on the conversation history and the customer's latest message, do ONE of:
1. Extract any new booking entities from the message and advance the state
2. Ask the next required question (one question at a time, never two)
3. Present available time slots if date/service is known
4. Confirm the booking details before finalising

ENTITY EXTRACTION RULES:
- date: Convert relative dates to YYYY-MM-DD. "tomorrow" = {tomorrow}, "next Thursday" = calculate correctly.
- time: Convert to HH:MM 24h format. "3pm" = "15:00", "morning" = ask for specific time.
- service: Match against the salon's service list. If ambiguous, ask to clarify.
- Never invent or guess service names or prices. Only use what is in SALON CONTEXT.

RESPOND WITH JSON ONLY:
{{
  "reply": "<the WhatsApp message to send to the customer>",
  "new_state": "IDLE|COLLECT_SERVICE|COLLECT_DATE|COLLECT_TIME|COLLECT_NAME|CONFIRM|BOOKED",
  "updated_entities": {{
    "service": "string or null",
    "date": "YYYY-MM-DD or null",
    "time": "HH:MM or null",
    "client_name": "string or null",
    "client_phone": "string or null"
  }},
  "request_slots": true/false
}}

Set "request_slots": true ONLY when you have both a service and a date and need to show real availability."""


CONFIRM_TEMPLATE = """✅ *Booking Confirmed!*

📅 {date_label}
🕐 {time}
💆 {service}
📍 {location}

We'll send you a reminder the day before. See you soon! 😊

_(Reply CHANGE to reschedule or CANCEL to cancel)_"""


async def handle_booking(
    session: ConversationSession,
    salon: SalonConfig,
    message: str,
    calendar: CalendarClient,
) -> tuple[str, ConversationSession]:
    """
    Main booking agent handler.
    Returns (reply_text, updated_session).
    """
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    salon_context = _build_salon_context(salon)

    system = BOOKING_SYSTEM_PROMPT.format(
        salon_context=salon_context,
        state=session.state.value,
        entities=session.entities.model_dump_json(),
        tomorrow=tomorrow,
    )

    # Build message history for context
    history_msgs = session.message_history[-10:]  # last 10 messages only
    user_prompt = f"Customer: {message}"

    try:
        raw = await _call_llm(system=system, history=history_msgs, user=user_prompt)
        data = json.loads(raw)
    except Exception as e:
        logger.error(f"Booking LLM call failed: {e}")
        return "Sorry, I'm having a bit of trouble right now. Please try again in a moment! 🙏", session

    reply: str = data.get("reply", "")
    new_state = BookingState(data.get("new_state", session.state.value))
    updated_entities_raw: dict = data.get("updated_entities", {})
    request_slots: bool = data.get("request_slots", False)

    # Merge updated entities
    current = session.entities.model_dump()
    for k, v in updated_entities_raw.items():
        if v is not None:
            current[k] = v
    session.entities = BookingEntities(**current)
    session.state = new_state

    # If LLM requests slot availability, fetch and append to reply
    if request_slots and session.entities.service and session.entities.date:
        service_cfg = next(
            (s for s in salon.services if s.name.lower() == (session.entities.service or "").lower()),
            None,
        )
        duration = service_cfg.duration_mins if service_cfg else 60
        slots = await calendar.get_available_slots(
            salon_id=salon.salon_id,
            date_str=session.entities.date,
            duration_mins=duration,
            business_hours=salon.hours,
        )
        if slots:
            session.entities.duration_mins = duration
            slot_text = _format_slots(slots)
            reply = f"I found these available slots for {session.entities.service}:\n\n{slot_text}\n\nWhich works best for you? 😊"
        else:
            reply = f"Sorry, no slots are available on that day for {session.entities.service}. Would you like to try another date?"
            session.state = BookingState.COLLECT_DATE
            session.entities.date = None

    # Handle confirmed booking — write to calendar
    if new_state == BookingState.BOOKED and _all_entities_complete(session.entities):
        try:
            event_id = await calendar.create_appointment(
                salon_id=salon.salon_id,
                entities=session.entities,
                service_label=session.entities.service or "",
                location=salon.location,
            )
            session.entities.calendar_event_id = event_id
            date_label = _format_date_label(session.entities.date or "")
            reply = CONFIRM_TEMPLATE.format(
                date_label=date_label,
                time=_format_time_12h(session.entities.time or ""),
                service=session.entities.service,
                location=salon.location,
            )
        except Exception as e:
            logger.error(f"Calendar write failed: {e}")
            reply = "I've noted your booking but had trouble saving it. Our team will confirm with you shortly! 🙏"
            session.state = BookingState.IDLE

    # Update conversation history
    session.message_history.append({"role": "user", "content": message})
    session.message_history.append({"role": "assistant", "content": reply})

    # Persist session
    await save_session(session)

    return reply, session


def _build_salon_context(salon: SalonConfig) -> str:
    services_list = "\n".join(
        f"- {s.name}: SGD {s.price_sgd:.0f}, {s.duration_mins} mins"
        for s in salon.services
    )
    hours_list = "\n".join(
        f"- {day.capitalize()}: {h.open} – {h.close}"
        for day, h in salon.hours.items()
    )
    return f"""Business: {salon.business_name}
Location: {salon.location}
Services:\n{services_list}
Hours:\n{hours_list}
Policies: {salon.policies}"""


def _format_slots(slots: list[TimeSlot]) -> str:
    return "\n".join(f"{i+1}. {s.label}" for i, s in enumerate(slots[:5]))


def _all_entities_complete(e: BookingEntities) -> bool:
    return all([e.service, e.date, e.time, e.client_name])


def _format_date_label(date_str: str) -> str:
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%A, %-d %B %Y")
    except Exception:
        return date_str


def _format_time_12h(time_str: str) -> str:
    try:
        t = datetime.strptime(time_str, "%H:%M")
        return t.strftime("%-I:%M %p")
    except Exception:
        return time_str


async def _call_llm(system: str, history: list[dict], user: str) -> str:
    if settings.ai_provider == "gemini":
        return await _call_gemini(system, history, user)
    return await _call_openai(system, history, user)


async def _call_gemini(system: str, history: list[dict], user: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system,
        generation_config={"response_mime_type": "application/json"},
    )
    # Build chat history
    chat_history = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        chat_history.append({"role": role, "parts": [msg["content"]]})
    chat = model.start_chat(history=chat_history)
    response = chat.send_message(user)
    return response.text


async def _call_openai(system: str, history: list[dict], user: str) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    messages = [{"role": "system", "content": system}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user})
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=messages,
    )
    return response.choices[0].message.content
