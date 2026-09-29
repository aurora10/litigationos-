-- document_text lives here (needed for GET /documents/{id}/text; filled by D05 OCR)
CREATE TABLE IF NOT EXISTS document_text (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INT NOT NULL,
    text_content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_document_text_doc ON document_text(document_id);
CREATE INDEX IF NOT EXISTS idx_document_text_fts ON document_text USING GIN (to_tsvector('simple', text_content));
