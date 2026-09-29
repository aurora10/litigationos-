# DATABASE_SCHEMA.md — Database Schema Specification (Appendix A)

Version 1.0 · PostgreSQL 17+ · Extensions: `uuid-ossp`, `pgvector`, `pg_trgm`

## Design goals
1. Case-centric · 2. Immutable evidence · 3. Full audit trail · 4. AI-friendly retrieval · 5. Provenance for every fact · 6. Scales to millions of documents · 7. Multi-user capable later (v1 single-user).

## Core domains
Authentication · Cases · Documents · Evidence · Provenance · Claims · Timeline · Issues · Communications · Deadlines · Research · Agent · Approvals · Audit · Search · Inbox

### CASE DOMAIN
- **cases**: id UUID PK · title TEXT · description TEXT · jurisdiction TEXT · case_number TEXT · status TEXT (OPEN/ARCHIVED) · court TEXT · created_at TS · updated_at TS. Indexes: `idx_cases_status`, `idx_cases_case_number`.
- **parties**: id UUID · case_id FK · name TEXT · role TEXT (PLAINTIFF/DEFENDANT/LANDLORD/TENANT/LAWYER/COURT/WITNESS/OTHER) · email TEXT · phone TEXT.

### DOCUMENT DOMAIN
- **documents** (metadata only): id · case_id FK · filename · mime_type · object_key · file_hash TEXT (SHA-256) · upload_date · processing_status (UPLOADED/PROCESSING/READY/FAILED).
- **document_versions**: id · document_id FK · version_number INT · version_type (ORIGINAL/OCR/TRANSCRIPT/SUMMARY). The ORIGINAL row never changes.
- **document_text**: id · document_id FK · page_number INT · text_content TEXT. Index: GIN `to_tsvector` full text.
- **document_embeddings**: id · document_id FK · chunk_id UUID · embedding VECTOR(3072). Index: hnsw (or ivfflat at low scale).

### EVIDENCE DOMAIN
- **evidence**: id · case_id FK · title · description · evidence_type (DOCUMENT/EMAIL/PHOTO/VIDEO/AUDIO/LETTER/NOTE) · verification_status (UNVERIFIED/VERIFIED/CONTESTED).

### PROVENANCE DOMAIN (critical)
- **provenance**: id · source_document_id FK · page_number INT · paragraph_number INT · timestamp_start FLOAT · timestamp_end FLOAT · confidence FLOAT. Enables "every fact → exact source location".

### CLAIMS
- **claims**: id · case_id FK · statement TEXT · verification_status.
- **claim_sources**: claim_id FK · provenance_id FK (many-to-many).

### TIMELINE DOMAIN
- **timeline_events**: id · case_id FK · event_date TS · title · description · verification_status (PROPOSED/APPROVED/REJECTED).
- **timeline_sources**: event_id FK · provenance_id FK.

### ISSUES DOMAIN
- **issues**: id · case_id FK · title · question TEXT · status.
- **arguments**: id · issue_id FK · argument_type (SUPPORTING/OPPOSING/COUNTERARGUMENT) · statement TEXT.

### DEADLINES DOMAIN
- **deadlines**: id · case_id FK · due_date DATE · description · status (PROPOSED/APPROVED/COMPLETED/MISSED).

### COMMUNICATION DOMAIN
- **communications**: id · case_id FK · direction (IN/OUT) · channel (EMAIL/LETTER/PHONE/SMS/WHATSAPP/TELEGRAM).
- **emails**: communication_id FK · provider_message_id TEXT (dedupe) · thread_id TEXT · sender · recipients JSONB · subject.

### RESEARCH DOMAIN
- **legal_sources**: id · source_type (LEGISLATION/CASE_LAW/COMMENTARY/REGULATION) · jurisdiction · citation TEXT · title · url.
- **legal_citations**: id · case_id FK · legal_source_id FK · exact_passage TEXT · relevance TEXT · verification (VERIFIED/UNVERIFIABLE/MISMATCH).

### AGENT DOMAIN
- **agent_tasks**: id · case_id FK · task_type · status (QUEUED/RUNNING/WAITING_APPROVAL/COMPLETED/FAILED).
- **agent_actions**: id · task_id FK · tool_name · result JSONB · created_at.

### APPROVAL DOMAIN
- **approvals**: id · approval_type (SEND_EMAIL/FILE_DOCUMENT/VERIFY_FACT/…) · status (DRAFT/REVIEW/APPROVED/REJECTED/EXECUTED) · payload JSONB.
- **drafts**: id · case_id FK · kind (EMAIL/LETTER/BRIEFING/HEARING_PREP) · body TEXT · status.

### AUDIT DOMAIN
- **audit_logs**: id · actor_type (USER/AGENT/SYSTEM) · actor_id UUID · action TEXT · entity_type · entity_id · old_value JSONB · new_value JSONB · created_at. **Append-only: DB role has no UPDATE/DELETE.**

### INBOX DOMAIN
- **inbox_items**: id · source_channel · original_document_id FK NULL · classification JSONB (type/sender/date/entities) · match_status (MATCHED/CASE_MATCH_NEEDED) · matched_case_id FK NULL · status (NEW/PROCESSING/REVIEW_REQUIRED/APPROVED/REJECTED/DUPLICATE).
- **inbox_proposals**: id · inbox_item_id FK · proposal_type (TIMELINE_EVENT/DEADLINE/EVIDENCE/ISSUE) · payload JSONB · status (PROPOSED/ACCEPTED/MODIFIED/REJECTED).

## Notes
- All FKs `ON DELETE RESTRICT` for evidence/provenance/audit; soft archive for cases.
- Full schema DDL is generated at D03/D04 migrations; this appendix is the contract they implement.
