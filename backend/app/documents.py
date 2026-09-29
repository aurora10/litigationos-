"""Document upload & access (D04, D05-T03 sets states; D09 fills text search)."""
import os
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile

from app.audit import audit
from app.deps import current_user_id
from app import storage

router = APIRouter(tags=["documents"])


def _db() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, autocommit=True)


def _row(r):
    return {
        "id": str(r[0]), "case_id": str(r[1]), "filename": r[2], "mime_type": r[3],
        "object_key": r[4], "file_hash": r[5], "upload_date": r[6].isoformat(),
        "processing_status": r[7],
    }


@router.post("/cases/{case_id}/documents", status_code=201)
async def upload_document(case_id: UUID, file: UploadFile, user_id: str = Depends(current_user_id)):
    data = await file.read()
    mime = file.content_type or "application/octet-stream"
    storage.ensure_bucket()
    key, sha = storage.put_original(data, file.filename or "upload.bin", mime)
    with _db() as conn:
        if not conn.execute("SELECT 1 FROM cases WHERE id=%s", (str(case_id),)).fetchone():
            raise HTTPException(404, "Case not found")
        doc = conn.execute(
            "INSERT INTO documents (case_id,filename,mime_type,object_key,file_hash)"
            " VALUES (%s,%s,%s,%s,%s)"
            " RETURNING id,case_id,filename,mime_type,object_key,file_hash,upload_date,processing_status",
            (str(case_id), file.filename, mime, key, sha),
        ).fetchone()
        conn.execute(
            "INSERT INTO document_versions (document_id,version_number,version_type,object_key) VALUES (%s,1,'ORIGINAL',%s)",
            (str(doc[0]), key),
        )
    # notify the OCR pipeline (D05 consumes this queue; duplicates are harmless)
    try:
        import redis as _redis
        _redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0")).lpush(
            "ingestion", f"documents:uploaded:{doc[0]}"
        )
    except Exception:
        pass  # queue not critical to upload correctness
    out = _row(doc)
    audit("USER", user_id, "UPLOAD", "document", out["id"], new={"case_id": str(case_id), "filename": file.filename, "file_hash": sha})
    return out


@router.get("/cases/{case_id}/documents")
def list_documents(case_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        rows = conn.execute(
            "SELECT id,case_id,filename,mime_type,object_key,file_hash,upload_date,processing_status"
            " FROM documents WHERE case_id=%s ORDER BY upload_date DESC", (str(case_id),)
        ).fetchall()
    return [_row(r) for r in rows]


@router.get("/documents/{doc_id}")
def get_document(doc_id: UUID, user_id: str = Depends(current_user_id)):
    with _db() as conn:
        r = conn.execute(
            "SELECT id,case_id,filename,mime_type,object_key,file_hash,upload_date,processing_status"
            " FROM documents WHERE id=%s", (str(doc_id),)
        ).fetchone()
    if not r:
        raise HTTPException(404, "Document not found")
    doc = _row(r)
    doc["download_url"] = storage.presigned_url(doc["object_key"])
    return doc


@router.get("/documents/{doc_id}/text")
def get_document_text(doc_id: UUID, page: int | None = Query(None), user_id: str = Depends(current_user_id)):
    with _db() as conn:
        q = "SELECT page_number,text_content FROM document_text WHERE document_id=%s"
        params: list = [str(doc_id)]
        if page is not None:
            q += " AND page_number=%s"
            params.append(page)
        q += " ORDER BY page_number"
        rows = conn.execute(q, params).fetchall()
    return {"document_id": str(doc_id), "pages": [{"page": r[0], "text": r[1]} for r in rows]}
