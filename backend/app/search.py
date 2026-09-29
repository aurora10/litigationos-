"""Hybrid search (D09): full-text (pg_trgm/to_tsvector) + semantic (pgvector),
always returning a provenance pointer (document + page)."""
import os
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query

from app.deps import current_user_id

router = APIRouter(tags=["search"])

# dimension-normalising hashing embedder — deterministic, no external dep (v1).
# Replaced by a real provider embedder at D11 (same call signature).
DIMS = 3072


def _embed(text: str) -> list[float]:
    import hashlib
    vec = [0.0] * DIMS
    for token in text.lower().split():
        h = hashlib.sha256(token.encode()).digest()
        idx = int.from_bytes(h[:2], "big") % DIMS
        vec[idx] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


def _db():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, autocommit=True)


@router.get("/search")
def search(q: str = Query(...), case_id: UUID | None = None, semantic: bool = Query(False),
           limit: int = Query(10, le=50), user_id: str = Depends(current_user_id)):
    with _db() as conn:
        if semantic:
            emb = _embed(q)
            vec_sql = "[" + ",".join(f"{v:.6f}" for v in emb) + "]"
            rows = conn.execute(
                "SELECT d.id, d.filename, de.page_number, left(de.chunk_text,300) AS excerpt,"
                "       de.embedding <=> %s::vector AS score"
                " FROM document_embeddings de JOIN documents d ON d.id=de.document_id"
                " WHERE (%s IS NULL OR d.case_id=%s)"
                " ORDER BY de.embedding <=> %s::vector LIMIT %s",
                (vec_sql, str(case_id) if case_id else None, str(case_id) if case_id else None,
                 vec_sql, limit),
            ).fetchall()
            kind = "semantic"
        else:
            rows = conn.execute(
                "SELECT d.id, d.filename, t.page_number, left(t.text_content,300) AS excerpt,"
                "       ts_rank(to_tsvector('simple', t.text_content), plainto_tsquery('simple', %s)) AS score"
                " FROM document_text t JOIN documents d ON d.id=t.document_id"
                " WHERE to_tsvector('simple', t.text_content) @@ plainto_tsquery('simple', %s)"
                "   AND (%s IS NULL OR d.case_id=%s)"
                " ORDER BY score DESC LIMIT %s",
                (q, q, str(case_id) if case_id else None, str(case_id) if case_id else None, limit),
            ).fetchall()
            kind = "fulltext"
    return {
        "query": q, "kind": kind,
        "results": [
            {"document_id": str(r[0]), "filename": r[1], "page": r[2],
             "excerpt": r[3], "score": float(r[4]),
             "provenance": {"document_id": str(r[0]), "page": r[2]}}
            for r in rows
        ],
    }


@router.post("/cases/{case_id}/documents/{doc_id}/embed", status_code=202)
def embed_document(case_id: UUID, doc_id: UUID, user_id: str = Depends(current_user_id)):
    """Chunk a document's OCR'd text and store embeddings (called after OCR in v1)."""
    with _db() as conn:
        pages = conn.execute(
            "SELECT page_number, text_content FROM document_text WHERE document_id=%s ORDER BY page_number",
            (str(doc_id),),
        ).fetchall()
        if not pages:
            return {"embedded_chunks": 0}
        conn.execute("DELETE FROM document_embeddings WHERE document_id=%s", (str(doc_id),))
        n = 0
        for page, text in pages:
            for chunk in _chunks(text, 800):
                emb = _embed(chunk)
                conn.execute(
                    "INSERT INTO document_embeddings (document_id,page_number,chunk_text,embedding)"
                    " VALUES (%s,%s,%s,%s::vector)",
                    (str(doc_id), page, chunk, "[" + ",".join(f"{v:.6f}" for v in emb) + "]"),
                )
                n += 1
    return {"document_id": str(doc_id), "embedded_chunks": n}


def _chunks(text: str, size: int):
    words = text.split()
    buf: list[str] = []
    count = 0
    for w in words:
        buf.append(w); count += len(w) + 1
        if count >= size:
            yield " ".join(buf); buf = []; count = 0
    if buf:
        yield " ".join(buf)
