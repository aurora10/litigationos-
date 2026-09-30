-- D13: communications + emails (already partially exists in 0006; make formal)
CREATE TABLE IF NOT EXISTS communications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    direction TEXT NOT NULL CHECK (direction IN ('IN','OUT')),
    channel TEXT NOT NULL CHECK (channel IN ('EMAIL','LETTER','PHONE','SMS','WHATSAPP','TELEGRAM')),
    subject TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_comms_case ON communications(case_id);

CREATE TABLE IF NOT EXISTS emails (
    communication_id UUID PRIMARY KEY REFERENCES communications(id) ON DELETE CASCADE,
    provider_message_id TEXT NOT NULL,
    thread_id TEXT,
    sender TEXT,
    recipients JSONB,
    subject TEXT,
    received_at TIMESTAMP,
    raw_body TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE(provider_message_id)
);
