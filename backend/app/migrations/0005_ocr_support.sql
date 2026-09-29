-- D05 OCR output page rows already exist via document_text (migration 0004).
-- This migration adds the OCR side: status index for the worker + embeddings table used by D09.
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);

CREATE TABLE IF NOT EXISTS document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id UUID NOT NULL DEFAULT gen_random_uuid(),
    page_number INT,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(3072)
);
CREATE INDEX IF NOT EXISTS idx_embeddings_doc ON document_embeddings(document_id);
-- hnsw for vector search at our scale
CREATE INDEX IF NOT EXISTS idx_embeddings_vec ON document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
