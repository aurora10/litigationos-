-- D07-T01: provenance + link tables (timeline_events/evidence created in 0006)
CREATE TABLE IF NOT EXISTS provenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    page_number INT,
    paragraph_number INT,
    timestamp_start FLOAT,
    timestamp_end FLOAT,
    confidence FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_provenance_doc ON provenance(source_document_id);

CREATE TABLE IF NOT EXISTS timeline_sources (
    event_id UUID NOT NULL REFERENCES timeline_events(id) ON DELETE CASCADE,
    provenance_id UUID NOT NULL REFERENCES provenance(id) ON DELETE CASCADE,
    PRIMARY KEY (event_id, provenance_id)
);

CREATE TABLE IF NOT EXISTS evidence_sources (
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    provenance_id UUID NOT NULL REFERENCES provenance(id) ON DELETE CASCADE,
    PRIMARY KEY (evidence_id, provenance_id)
);
