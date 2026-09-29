-- D04-T01: documents + document_versions (originals immutable)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    filename TEXT NOT NULL,
    mime_type TEXT,
    object_key TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    upload_date TIMESTAMP NOT NULL DEFAULT now(),
    processing_status TEXT NOT NULL DEFAULT 'UPLOADED' CHECK (processing_status IN ('UPLOADED','PROCESSING','READY','FAILED'))
);
CREATE INDEX IF NOT EXISTS idx_documents_case ON documents(case_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_object_key ON documents(object_key);

CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    version_number INT NOT NULL,
    version_type TEXT NOT NULL CHECK (version_type IN ('ORIGINAL','OCR','TRANSCRIPT','SUMMARY')),
    object_key TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE(document_id, version_type, version_number)
);
