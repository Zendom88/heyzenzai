"""
WhatsApp Webhook handler.
Receives incoming messages from Meta Cloud API and dispatches to agents.
"""
import logging
from fastapi import APIRouter, Request, Response, HTTPException, Query

from app.config import settings
from app.agents.router import classify_intent
from app.agents.booking import handle_booking
from app.agents.faq import handle_faq
from app.integrations.whatsapp import parse_incoming_message, send_whatsapp_message
from app.integrations.db import (
    get_session, get_salon_by_whatsapp_number, log_conversation
)
from app.integrations.calendar import CalendarClient
from app.models.schemas import BookingState, IntentType

logger = logging.getLogger(__name__)
router = APIRouter()

ESCALATION_REPLY = (
    "I'm flagging this for our team right away! 🙏 "
    "Someone will reach out to you shortly. Thank you for your patience."
)
UNKNOWN_REPLY = (
    "Hi there! 👋 I'm the booking assistant for {salon}. "
    "I can help you book, reschedule, or answer questions about our services. "
    "Just let me know what you need! 😊"
)


# ──────────────────────────────────────────────
# Webhook Verification (GET)
# ──────────────────────────────────────────────

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
):
    """Meta webhook verification handshake."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_webhook_verify_token:
        logger.info("Webhook verified successfully.")
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Webhook verification failed")


# ──────────────────────────────────────────────
# Incoming Messages (POST)
# ──────────────────────────────────────────────

@router.post("/webhook")
async def receive_webhook(request: Request):
    """
    Process incoming WhatsApp messages.
    Must respond with 200 within 20 seconds (Meta requirement).
    """
    payload = await request.json()

    # Ignore status updates (delivery receipts etc.)
    if _is_status_update(payload):
        return {"status": "ok"}

    msg = parse_incoming_message(payload)
    if not msg:
        return {"status": "ok"}

    sender = msg["sender"]
    text = msg["text"]

    # Determine which salon this WhatsApp number belongs to
    # Note: In production, the WABA number is in the payload metadata.
    # For MVP, we look up by the receiving phone number ID from Meta payload.
    waba_number = _extract_waba_number(payload)
    salon = await get_salon_by_whatsapp_number(waba_number)

    if not salon:
        logger.warning(f"No salon found for WABA number: {waba_number}")
        return {"status": "ok"}

    # Log inbound
    await log_conversation(
        session_id=sender,
        salon_id=salon.salon_id,
        direction="inbound",
        message=text,
    )

    # Load session state
    session = await get_session(session_id=sender, salon_id=salon.salon_id)

    # Classify intent
    intent_result = await classify_intent(text)
    primary_intent = intent_result.primary_intent

    await log_conversation(
        session_id=sender,
        salon_id=salon.salon_id,
        direction="inbound",
        message=text,
        intent=primary_intent.value,
    )

    # Dispatch to agent
    reply = ""

    if primary_intent == IntentType.ESCALATE:
        reply = ESCALATION_REPLY
        # Alert the salon owner
        await send_whatsapp_message(
            to=salon.owner_phone,
            message=f"⚠️ ESCALATION: Client {sender} needs human help.\nMessage: \"{text}\"",
        )
        # Reset session so next message starts fresh
        session.state = BookingState.IDLE

    elif primary_intent == IntentType.FAQ:
        # Check if mid-booking and this is a tangential question
        if session.state not in (BookingState.IDLE, BookingState.BOOKED):
            # Answer the FAQ, then nudge back to booking
            faq_answer = await handle_faq(salon=salon, message=text)
            reply = f"{faq_answer}\n\nWould you like to continue with your booking? 😊"
        else:
            reply = await handle_faq(salon=salon, message=text)

    elif primary_intent in (IntentType.BOOKING, IntentType.MODIFY):
        calendar = CalendarClient(salon)
        reply, session = await handle_booking(
            session=session,
            salon=salon,
            message=text,
            calendar=calendar,
        )

    else:  # UNKNOWN
        reply = UNKNOWN_REPLY.format(salon=salon.business_name)

    # Send reply
    if reply:
        await send_whatsapp_message(to=sender, message=reply)
        await log_conversation(
            session_id=sender,
            salon_id=salon.salon_id,
            direction="outbound",
            message=reply,
        )

    return {"status": "ok"}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _is_status_update(payload: dict) -> bool:
    """Detect delivery/read receipts — ignore these."""
    try:
        value = payload["entry"][0]["changes"][0]["value"]
        return "statuses" in value and "messages" not in value
    except (KeyError, IndexError):
        return False


def _extract_waba_number(payload: dict) -> str:
    """Extract the receiving WABA phone number from the webhook payload metadata."""
    try:
        value = payload["entry"][0]["changes"][0]["value"]
        metadata = value.get("metadata", {})
        display_phone = metadata.get("display_phone_number", "")
        # Normalize to E.164
        number = display_phone.replace(" ", "").replace("-", "")
        if not number.startswith("+"):
            number = f"+{number}"
        return number
    except (KeyError, IndexError):
        return ""
