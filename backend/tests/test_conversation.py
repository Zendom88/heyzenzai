"""
Local test harness — run the full agent pipeline without WhatsApp.
Usage: python tests/test_conversation.py

Simulates a real booking conversation and checks calendar + DB writes.
Requires .env to be configured with at least:
  - GEMINI_API_KEY or OPENAI_API_KEY
  - SUPABASE_URL + SUPABASE_SERVICE_KEY
  - GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET + a test salon's google_refresh_token
"""
import asyncio
import sys
import os

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.agents.router import classify_intent
from app.agents.booking import handle_booking
from app.agents.faq import handle_faq
from app.models.schemas import (
    ConversationSession, BookingState, BookingEntities,
    SalonConfig, ServiceConfig, BusinessHours,
)
from app.integrations.calendar import CalendarClient


# ──────────────────────────────────────────────
# Mock salon — replace with your real test data
# ──────────────────────────────────────────────

MOCK_SALON = SalonConfig(
    salon_id="test_salon_001",
    business_name="Zen Aesthetics (Test)",
    whatsapp_number="+6591234567",
    owner_phone="+6591234567",
    calendar_id="primary",  # Uses your own Google Calendar for testing
    google_refresh_token=os.getenv("TEST_GOOGLE_REFRESH_TOKEN", ""),
    location="18 Tanjong Pagar Road, #02-01, Singapore 088443",
    policies="No-show fee: SGD 30. Cancellations within 24h may incur a fee.",
    services=[
        ServiceConfig(name="Classic Facial", duration_mins=60, price_sgd=120,
                      description="Deep cleansing with extraction and mask."),
        ServiceConfig(name="Brow Threading", duration_mins=20, price_sgd=25),
        ServiceConfig(name="Full Body Wax", duration_mins=90, price_sgd=180),
        ServiceConfig(name="Laser Hair Removal", duration_mins=45, price_sgd=250,
                      description="Single session, small area."),
        ServiceConfig(name="Hydrafacial", duration_mins=75, price_sgd=280),
    ],
    hours={
        "monday": BusinessHours(open="10:00", close="20:00"),
        "tuesday": BusinessHours(open="10:00", close="20:00"),
        "wednesday": BusinessHours(open="10:00", close="20:00"),
        "thursday": BusinessHours(open="10:00", close="20:00"),
        "friday": BusinessHours(open="10:00", close="21:00"),
        "saturday": BusinessHours(open="10:00", close="21:00"),
        "sunday": BusinessHours(open="12:00", close="18:00"),
    },
)


# ──────────────────────────────────────────────
# Conversation simulator
# ──────────────────────────────────────────────

async def simulate_agent(message: str, session: ConversationSession) -> tuple[str, ConversationSession]:
    """Route a single message through the full agent pipeline."""
    print(f"\n👤 Client: {message}")

    intent_result = await classify_intent(message)
    print(f"   🧠 Intent: {intent_result.primary_intent.value} ({intent_result.confidence:.0%})")

    from app.models.schemas import IntentType
    if intent_result.primary_intent == IntentType.FAQ:
        reply = await handle_faq(salon=MOCK_SALON, message=message)
        print(f"   🤖 Bot: {reply}")
        return reply, session

    elif intent_result.primary_intent in (IntentType.BOOKING, IntentType.MODIFY):
        calendar = CalendarClient(MOCK_SALON)
        reply, session = await handle_booking(
            session=session,
            salon=MOCK_SALON,
            message=message,
            calendar=calendar,
        )
        print(f"   🤖 Bot: {reply}")
        print(f"   📋 State: {session.state.value} | Entities: {session.entities.model_dump(exclude_none=True)}")
        return reply, session

    elif intent_result.primary_intent == IntentType.ESCALATE:
        reply = "I'm flagging this for our team right away! 🙏 Someone will reach out shortly."
        print(f"   🚨 ESCALATED | Bot: {reply}")
        return reply, session

    else:
        reply = f"Hi there! I'm the booking assistant for {MOCK_SALON.business_name}. How can I help? 😊"
        print(f"   🤖 Bot: {reply}")
        return reply, session


async def run_booking_flow():
    """Full end-to-end booking conversation test."""
    print("\n" + "="*60)
    print("TEST: Full Booking Flow")
    print("="*60)

    session = ConversationSession(
        session_id="+6598765432",
        salon_id=MOCK_SALON.salon_id,
        state=BookingState.IDLE,
        entities=BookingEntities(),
    )

    test_messages = [
        "Hi, I'd like to book a facial",
        "Next Thursday works for me",
        "Afternoon, maybe 3pm?",
        "My name is Sarah Lim",
    ]

    for msg in test_messages:
        _, session = await simulate_agent(msg, session)
        await asyncio.sleep(0.5)  # Avoid rate limiting


async def run_faq_test():
    """Test FAQ responses."""
    print("\n" + "="*60)
    print("TEST: FAQ Queries")
    print("="*60)

    session = ConversationSession(
        session_id="+6591111111",
        salon_id=MOCK_SALON.salon_id,
        state=BookingState.IDLE,
        entities=BookingEntities(),
    )

    faq_messages = [
        "How much does a facial cost?",
        "Where are you located?",
        "Do you do nail extensions?",  # Not in the menu — should not hallucinate
        "Is laser hair removal painful?",
    ]

    for msg in faq_messages:
        await simulate_agent(msg, session)
        await asyncio.sleep(0.3)


async def run_intent_classification_test():
    """Test intent router with edge cases."""
    print("\n" + "="*60)
    print("TEST: Intent Classification")
    print("="*60)

    test_cases = [
        ("hi want to book facial tmr", "BOOKING"),
        ("can i reschedule my appt", "MODIFY"),
        ("how much is waxing", "FAQ"),
        ("i got reaction from your cream!! call me now", "ESCALATE"),
        ("I want to book a brow threading but also do you do lashes?", "BOOKING"),
        ("aasdfjklasdf", "UNKNOWN"),
        ("ok", "UNKNOWN"),
    ]

    for msg, expected in test_cases:
        result = await classify_intent(msg)
        status = "✅" if result.primary_intent.value == expected else "❌"
        print(f"  {status} [{result.primary_intent.value}] (expected {expected}) — \"{msg}\"")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", choices=["booking", "faq", "intent", "all"], default="all")
    args = parser.parse_args()

    async def main():
        if args.test in ("intent", "all"):
            await run_intent_classification_test()
        if args.test in ("faq", "all"):
            await run_faq_test()
        if args.test in ("booking", "all"):
            await run_booking_flow()

    asyncio.run(main())
