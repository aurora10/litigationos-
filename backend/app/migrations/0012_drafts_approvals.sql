-- D14: drafts + approvals
CREATE TABLE IF NOT EXISTS drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    kind TEXT NOT NULL CHECK (kind IN ('EMAIL','LETTER','BRIEFING','HEARING_PREP')),
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','REVIEW','APPROVED','REJECTED','EXECUTED')),
    created_by TEXT NOT NULL DEFAULT 'agent',  -- agent|user
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_drafts_case ON drafts(case_id);

CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_type TEXT NOT NULL CHECK (approval_type IN ('SEND_EMAIL','FILE_DOCUMENT','VERIFY_FACT','SUBMIT_DRAFT')),
    status TEXT NOT NULL DEFAULT 'REVIEW' CHECK (status IN ('DRAFT','REVIEW','APPROVED','REJECTED','EXECUTED')),
    payload JSONB NOT NULL,          -- e.g. {draft_id, to, subject} or {citation_id}
    created_by TEXT NOT NULL DEFAULT 'agent',
    decided_by TEXT,
    decided_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);
