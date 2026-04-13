heyzenzai-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              ← FastAPI entrypoint
│   ├── config.py            ← Settings from .env
│   ├── webhook.py           ← Meta webhook handler (GET + POST /webhook)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── router.py        ← Intent Router (BOOKING/MODIFY/FAQ/ESCALATE)
│   │   ├── booking.py       ← Booking Engine (state machine + calendar)
│   │   ├── faq.py           ← FAQ Engine (knowledge base)
│   │   └── retention.py     ← Reminder + rebooking cron jobs
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── whatsapp.py      ← Meta Cloud API client
│   │   ├── calendar.py      ← Google Calendar API client
│   │   └── db.py            ← Supabase client (sessions, salons, logs)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       ← All Pydantic models
│   └── routes/
│       ├── __init__.py
│       ├── oauth.py         ← Google OAuth flow for salon onboarding
│       └── health.py        ← Health check endpoint
├── tests/
│   ├── __init__.py
│   └── test_conversation.py ← Local test harness (no WhatsApp needed)
├── .env.example             ← Copy to .env and fill in credentials
├── Dockerfile               ← For Fly.io / Railway deployment
├── fly.toml                 ← Fly.io config (Singapore region)
├── requirements.txt         ← Python dependencies
└── supabase_schema.sql      ← Run in Supabase SQL editor to set up DB
