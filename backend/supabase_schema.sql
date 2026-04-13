-- HeyZenzai Supabase Schema
-- Run this in your Supabase SQL editor

-- ──────────────────────────────────────────────
-- Salons
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS salons (
    id                  TEXT PRIMARY KEY,           -- e.g. "salon_tanjongpagar_zen"
    business_name       TEXT NOT NULL,
    whatsapp_number     TEXT UNIQUE NOT NULL,        -- E.164: +6591234567
    owner_phone         TEXT NOT NULL,               -- For escalation alerts
    calendar_id         TEXT NOT NULL,               -- Google Calendar ID
    google_refresh_token TEXT,                       -- Stored after OAuth
    services_json       JSONB DEFAULT '[]'::jsonb,
    hours_json          JSONB DEFAULT '{}'::jsonb,
    location            TEXT DEFAULT '',
    policies            TEXT DEFAULT '',
    is_active           BOOLEAN DEFAULT true,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ──────────────────────────────────────────────
-- Conversation Sessions (Booking State Machine)
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    session_id          TEXT PRIMARY KEY,           -- WhatsApp sender phone (E.164)
    salon_id            TEXT REFERENCES salons(id) ON DELETE CASCADE,
    state               TEXT NOT NULL DEFAULT 'IDLE',
    entities            JSONB DEFAULT '{}'::jsonb,
    message_history     JSONB DEFAULT '[]'::jsonb,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_salon ON sessions(salon_id);

-- ──────────────────────────────────────────────
-- Conversation Logs (Analytics)
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversation_logs (
    id          BIGSERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL,
    salon_id    TEXT REFERENCES salons(id) ON DELETE SET NULL,
    direction   TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    message     TEXT NOT NULL,
    intent      TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_salon_created ON conversation_logs(salon_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_session ON conversation_logs(session_id);

-- ──────────────────────────────────────────────
-- Sample Salon Insert (for local testing)
-- Replace values with your actual test salon
-- ──────────────────────────────────────────────
/*
INSERT INTO salons (
    id, business_name, whatsapp_number, owner_phone, calendar_id,
    services_json, hours_json, location, policies
) VALUES (
    'salon_test_001',
    'Zen Aesthetics (Test)',
    '+6591234567',
    '+6591234567',
    'primary',
    '[
        {"name": "Classic Facial", "duration_mins": 60, "price_sgd": 120, "description": "Deep cleansing with extraction."},
        {"name": "Brow Threading", "duration_mins": 20, "price_sgd": 25, "description": null},
        {"name": "Hydrafacial", "duration_mins": 75, "price_sgd": 280, "description": "Premium hydrating treatment."}
    ]'::jsonb,
    '{
        "monday": {"open": "10:00", "close": "20:00"},
        "tuesday": {"open": "10:00", "close": "20:00"},
        "wednesday": {"open": "10:00", "close": "20:00"},
        "thursday": {"open": "10:00", "close": "20:00"},
        "friday": {"open": "10:00", "close": "21:00"},
        "saturday": {"open": "10:00", "close": "21:00"},
        "sunday": {"open": "12:00", "close": "18:00"}
    }'::jsonb,
    '18 Tanjong Pagar Road, #02-01, Singapore 088443',
    'No-show fee: SGD 30. Cancellations within 24h may incur a fee.'
);
*/
