"""LitigationOS OCR worker (D05).

Consumes redis queue 'ingestion' (messages: "documents:uploaded:<doc_id>").
For each document: fetch original from S3 -> OCR per page -> write
document_text + document_versions(OCR) -> processing_status READY.

Idempotent: re-running on the same document replaces OCR output (original
never touched). Languages from OCR_LANGS env (default nld+fra+rus).
"""
import io
import os
import shlex
import subprocess
import tempfile

import boto3
import psycopg
import redis
from botocore.config import Config

QUEUE = "ingestion"
LANGS = os.environ.get("OCR_LANGS", "nld+fra+rus")


def s3():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT", "http://s3:8333"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "any"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "unused"),
        config=Config(signature_version="s3v4"),
    )


def db():
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, autocommit=True)


def ocr_pages(file_bytes: bytes, mime: str) -> list[str]:
    """Return per-page text."""
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "input")
        with open(src, "wb") as f:
            f.write(file_bytes)
        if mime == "application/pdf" or file_bytes[:4] == b"%PDF":
            # pdf -> ppm per page
            subprocess.run(
                ["pdftoppm", "-r", "300", "-gray", src, os.path.join(td, "page")],
                check=True, capture_output=True,
            )
            pages = sorted(p for p in os.listdir(td) if p.startswith("page"))
            return [pytesseract_image(os.path.join(td, p)) for p in pages]
        return [pytesseract_image(src)]


def pytesseract_image(path: str) -> str:
    import pytesseract
    return pytesseract.image_to_string(path, lang=LANGS)


def process_document(doc_id: str) -> None:
    with db() as conn:
        row = conn.execute(
            "SELECT object_key, file_hash, mime_type FROM documents WHERE id=%s", (doc_id,)
        ).fetchone()
        if not row:
            print(f"worker: doc {doc_id} not found", flush=True)
            return
        conn.execute("UPDATE documents SET processing_status='PROCESSING' WHERE id=%s", (doc_id,))
    object_key, _, mime = row
    try:
        data = s3().get_object(Bucket=os.environ.get("S3_BUCKET", "litigation-evidence"), Key=object_key)["Body"].read()
        pages = ocr_pages(data, mime)
        with db() as conn:
            for i, text in enumerate(pages, start=1):
                conn.execute(
                    "INSERT INTO document_text (document_id,page_number,text_content) VALUES (%s,%s,%s)",
                    (doc_id, i, text),
                )
            conn.execute(
                "INSERT INTO document_versions (document_id,version_number,version_type) VALUES (%s,%s,'OCR')",
                (doc_id, len(pages)),
            )
            conn.execute("UPDATE documents SET processing_status='READY' WHERE id=%s", (doc_id,))
        print(f"worker: OCR done doc={doc_id} pages={len(pages)}", flush=True)
    except Exception as e:  # noqa: BLE001
        with db() as conn:
            conn.execute("UPDATE documents SET processing_status='FAILED' WHERE id=%s", (doc_id,))
        print(f"worker: OCR FAILED doc={doc_id}: {e}", flush=True)


def main() -> None:
    client = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
    client.ping()
    print("worker: connected to redis, OCR langs:", LANGS, flush=True)
    while True:
        try:
            item = client.blpop(QUEUE, timeout=30)
        except redis.exceptions.TimeoutError:
            continue  # idle timeout is normal — keep waiting
        if not item:
            continue
        msg = item[1].decode()
        print("worker: job", msg, flush=True)
        if msg.startswith("documents:uploaded:"):
            process_document(msg.split(":", 2)[2])


if __name__ == "__main__":
    main()
