# INGESTION_PIPELINE.md — Universal Case Inbox & Ingestion Pipeline

Version 1.0

## Purpose
Convert incoming information into structured case data. **All information enters through the Case Inbox.**

## Supported inputs
Documents · Emails · Letters (scans) · Photos · Screenshots · Audio · Video · Web pages · Manual notes.

## High-level pipeline
RECEIVED → STORE ORIGINAL → CLASSIFY → EXTRACT → MATCH CASE → CREATE PROPOSALS → REVIEW → INDEX

1. **Preserve original** — immutability: store original filename, SHA-256 hash, upload date, source (`/originals/...`).
2. **Classification** — document type (Court Letter / Lawyer Email / Invoice / Lease Agreement / Photo Evidence / Audio Recording…), sender, recipient, category.
3. **Extraction** — documents: OCR · emails: body+headers · audio: Whisper transcript · video: FFmpeg frames + transcript.
4. **Entity extraction** — people, companies, addresses, dates, case numbers, lawyers, courts.
5. **Timeline extraction** — e.g. email dated 12/02/2026 → event "Landlord confirmed inspection date".
6. **Deadline extraction** — "Response required within 30 days", "Hearing on 17 March", appeal deadlines. **All deadlines require review.**
7. **Case matching** — case number → participants → email thread → semantic similarity → user confirmation.
8. **Proposal generation** — New Timeline Event / Deadline / Evidence / Issue. **Nothing is committed automatically.**
9. **Human review** — Accept / Reject / Modify.
10. **Indexing** — text, embeddings (VECTOR 3072), metadata, relationships.

## Inbox statuses
NEW → PROCESSING → REVIEW_REQUIRED → APPROVED | REJECTED | DUPLICATE → INDEXED.

## Channel pipelines
- **Email:** Gmail/Outlook → n8n → webhook → FastAPI → Inbox → Review → Case.
- **Physical letter:** phone scan → OCR → classification → Inbox → Review → Case.
- **Audio:** upload → Whisper → transcript → extraction → Review → Case.
- **Video:** upload → FFmpeg → transcript + frame analysis → Review → Case.

## Provenance requirements
Every extracted fact stores: source · location (page / timestamp) · extractor · confidence · verification status. Example: `{source: video_003.mp4, timestamp: 00:04:31, fact: "property damage visible", status: UNVERIFIED}`.
