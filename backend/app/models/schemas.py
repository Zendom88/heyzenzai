from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


# ──────────────────────────────────────────────
# Intent
# ──────────────────────────────────────────────

class IntentType(str, Enum):
    BOOKING = "BOOKING"
    MODIFY = "MODIFY"
    FAQ = "FAQ"
    ESCALATE = "ESCALATE"
    UNKNOWN = "UNKNOWN"


class IntentResult(BaseModel):
    primary_intent: IntentType
    secondary_intent: Optional[IntentType] = None
    confidence: float  # 0.0 – 1.0
    raw_message: str


# ──────────────────────────────────────────────
# Booking Session State Machine
# ──────────────────────────────────────────────

class BookingState(str, Enum):
    IDLE = "IDLE"
    COLLECT_SERVICE = "COLLECT_SERVICE"
    COLLECT_DATE = "COLLECT_DATE"
    COLLECT_TIME = "COLLECT_TIME"
    COLLECT_NAME = "COLLECT_NAME"
    CONFIRM = "CONFIRM"
    BOOKED = "BOOKED"
    MODIFY = "MODIFY"


class BookingEntities(BaseModel):
    service: Optional[str] = None
    date: Optional[str] = None       # ISO 8601: YYYY-MM-DD
    time: Optional[str] = None       # HH:MM (24h)
    duration_mins: Optional[int] = None
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    calendar_event_id: Optional[str] = None


class ConversationSession(BaseModel):
    session_id: str                  # WhatsApp sender phone (E.164)
    salon_id: str
    state: BookingState = BookingState.IDLE
    entities: BookingEntities = BookingEntities()
    message_history: list[dict] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ──────────────────────────────────────────────
# Salon Config
# ──────────────────────────────────────────────

class ServiceConfig(BaseModel):
    name: str
    duration_mins: int
    price_sgd: float
    description: Optional[str] = None


class BusinessHours(BaseModel):
    open: str   # "09:00"
    close: str  # "20:00"


class SalonConfig(BaseModel):
    salon_id: str
    business_name: str
    whatsapp_number: str       # E.164, e.g. +6591234567 (the WABA number)
    owner_phone: str           # Personal number for escalations
    calendar_id: str           # Google Calendar ID
    google_refresh_token: Optional[str] = None
    services: list[ServiceConfig] = []
    hours: dict[str, BusinessHours] = {}   # {"monday": {...}, ...}
    location: str = ""
    policies: str = ""
    is_active: bool = True


# ──────────────────────────────────────────────
# WhatsApp Webhook Payload (Meta Cloud API)
# ──────────────────────────────────────────────

class WhatsAppTextMessage(BaseModel):
    body: str


class WhatsAppInteractiveReply(BaseModel):
    type: str  # "button_reply" | "list_reply"
    id: str
    title: str


class WhatsAppMessage(BaseModel):
    id: str
    from_: str  # sender phone
    timestamp: str
    type: str   # "text" | "interactive" | "button"
    text: Optional[WhatsAppTextMessage] = None
    interactive: Optional[dict] = None


class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: list[dict]


# ──────────────────────────────────────────────
# Calendar
# ──────────────────────────────────────────────

class TimeSlot(BaseModel):
    date: str        # YYYY-MM-DD
    start: str       # HH:MM
    end: str         # HH:MM
    label: str       # Human readable: "Thursday 3 Apr, 3:00 PM"


class AppointmentCreate(BaseModel):
    salon_id: str
    client_name: str
    client_phone: str
    service: str
    slot: TimeSlot
    source: str = "heyzenzai"
