"""
Supabase database client.
Handles session state, salon config, and conversation logs.
"""
import logging
from datetime import datetime
from typing import Optional, List
from zoneinfo import ZoneInfo

from supabase import create_client, Client

from app.config import settings
from app.models.schemas import BookingState, ConversationSession, BookingEntities, SalonConfig

logger = logging.getLogger(__name__)
SGT = ZoneInfo("Asia/Singapore")

_supabase: Optional[Client] = None


def get_client() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(settings.supabase_url, settings.supabase_service_key)
    return _supabase


# ──────────────────────────────────────────────
# Sessions
# ──────────────────────────────────────────────

async def get_session(session_id: str, salon_id: str) -> ConversationSession:
    """Load an existing session or create a new one."""
    db = get_client()
    result = db.table("sessions").select("*").eq("session_id", session_id).maybe_single().execute()

    if result.data:
        row = result.data
        return ConversationSession(
            session_id=row["session_id"],
            salon_id=row["salon_id"],
            state=BookingState(row["state"]),
            entities=BookingEntities(**row["entities"]),
            message_history=row.get("message_history", []),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    # New session
    return ConversationSession(
        session_id=session_id,
        salon_id=salon_id,
        state=BookingState.IDLE,
        entities=BookingEntities(),
        message_history=[],
    )


async def save_session(session: ConversationSession) -> None:
    """Upsert session state to Supabase."""
    db = get_client()
    db.table("sessions").upsert({
        "session_id": session.session_id,
        "salon_id": session.salon_id,
        "state": session.state.value,
        "entities": session.entities.model_dump(),
        "message_history": session.message_history[-20:],  # keep last 20 msgs
        "updated_at": datetime.now(SGT).isoformat(),
    }).execute()


# ──────────────────────────────────────────────
# Salon Config
# ──────────────────────────────────────────────

async def get_salon_by_whatsapp_number(whatsapp_number: str) -> Optional[SalonConfig]:
    """Look up a salon by the inbound WhatsApp number."""
    db = get_client()
    result = (
        db.table("salons")
        .select("*")
        .eq("whatsapp_number", whatsapp_number)
        .eq("is_active", True)
        .maybe_single()
        .execute()
    )
    if not result.data:
        return None
    return _row_to_salon(result.data)


async def get_all_salons() -> list[SalonConfig]:
    """Fetch all active salons. Used by retention engine cron jobs."""
    db = get_client()
    result = db.table("salons").select("*").eq("is_active", True).execute()
    return [_row_to_salon(row) for row in result.data]


async def save_salon_oauth_token(salon_id: str, refresh_token: str) -> None:
    """Store the Google OAuth refresh token after salon onboarding."""
    db = get_client()
    db.table("salons").update({"google_refresh_token": refresh_token}).eq("salon_id", salon_id).execute()


# ──────────────────────────────────────────────
# Conversation Logging
# ──────────────────────────────────────────────

async def log_conversation(
    session_id: str,
    salon_id: str,
    direction: str,  # "inbound" | "outbound"
    message: str,
    intent: Optional[str] = None,
) -> None:
    """Write a conversation log entry for analytics."""
    db = get_client()
    db.table("conversation_logs").insert({
        "session_id": session_id,
        "salon_id": salon_id,
        "direction": direction,
        "message": message,
        "intent": intent,
        "created_at": datetime.now(SGT).isoformat(),
    }).execute()


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _row_to_salon(row: dict) -> SalonConfig:
    from app.models.schemas import ServiceConfig, BusinessHours
    services = [ServiceConfig(**s) for s in (row.get("services_json") or [])]
    hours_raw = row.get("hours_json") or {}
    hours = {day: BusinessHours(**h) for day, h in hours_raw.items()}
    return SalonConfig(
        salon_id=row["id"],
        business_name=row["business_name"],
        whatsapp_number=row["whatsapp_number"],
        owner_phone=row.get("owner_phone", ""),
        calendar_id=row.get("calendar_id", ""),
        google_refresh_token=row.get("google_refresh_token"),
        services=services,
        hours=hours,
        location=row.get("location", ""),
        policies=row.get("policies", ""),
        is_active=row.get("is_active", True),
    )
