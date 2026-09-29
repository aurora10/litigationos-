-- D06-T01: inbox + proposals
CREATE TABLE IF NOT EXISTS inbox_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_channel TEXT NOT NULL DEFAULT 'UPLOAD',
    original_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    classification JSONB,
    match_status TEXT NOT NULL DEFAULT 'CASE_MATCH_NEEDED' CHECK (match_status IN ('MATCHED','CASE_MATCH_NEEDED')),
    matched_case_id UUID REFERENCES cases(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED' CHECK (status IN ('NEW','PROCESSING','REVIEW_REQUIRED','APPROVED','REJECTED','DUPLICATE')),
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    reviewed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_inbox_status ON inbox_items(status);
CREATE INDEX IF NOT EXISTS idx_inbox_case ON inbox_items(matched_case_id);

CREATE TABLE IF NOT EXISTS inbox_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inbox_item_id UUID NOT NULL REFERENCES inbox_items(id) ON DELETE CASCADE,
    proposal_type TEXT NOT NULL CHECK (proposal_type IN ('TIMELINE_EVENT','DEADLINE','EVIDENCE','ISSUE')),
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'PROPOSED' CHECK (status IN ('PROPOSED','ACCEPTED','MODIFIED','REJECTED')),
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_proposals_item ON inbox_proposals(inbox_item_id);

-- timeline + evidence targets for proposals (lightweight v1 of D07/D08 domains)
CREATE TABLE IF NOT EXISTS timeline_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    event_date TIMESTAMP NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    verification_status TEXT NOT NULL DEFAULT 'PROPOSED' CHECK (verification_status IN ('PROPOSED','APPROVED','REJECTED')),
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    due_date DATE NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'PROPOSED' CHECK (status IN ('PROPOSED','APPROVED','COMPLETED','MISSED'))
);
CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    description TEXT,
    evidence_type TEXT NOT NULL CHECK (evidence_type IN ('DOCUMENT','EMAIL','PHOTO','VIDEO','AUDIO','LETTER','NOTE')),
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
    source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL
);
