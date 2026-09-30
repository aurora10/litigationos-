-- D12: citations + verification
CREATE TABLE IF NOT EXISTS legal_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT NOT NULL CHECK (source_type IN ('LEGISLATION','CASE_LAW','COMMENTARY','REGULATION')),
    jurisdiction TEXT NOT NULL DEFAULT 'BE',
    citation TEXT NOT NULL,
    title TEXT,
    url TEXT,
    content TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_legal_sources_citation ON legal_sources(citation);

CREATE TABLE IF NOT EXISTS legal_citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    task_id UUID REFERENCES agent_tasks(id) ON DELETE SET NULL,
    legal_source_id UUID NOT NULL REFERENCES legal_sources(id) ON DELETE CASCADE,
    exact_passage TEXT NOT NULL,
    relevance TEXT,
    verification TEXT NOT NULL DEFAULT 'UNVERIFIABLE' CHECK (verification IN ('VERIFIED','UNVERIFIABLE','MISMATCH')),
    verification_note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    verified_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_legal_citations_case ON legal_citations(case_id);
