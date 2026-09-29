-- D08-T01: issues, arguments, claims, claim_sources (evidence from 0006)
CREATE TABLE IF NOT EXISTS issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    question TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','RESOLVED','WITHDRAWN')),
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_issues_case ON issues(case_id);

CREATE TABLE IF NOT EXISTS arguments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    argument_type TEXT NOT NULL CHECK (argument_type IN ('SUPPORTING','OPPOSING','COUNTERARGUMENT')),
    statement TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_arguments_issue ON arguments(issue_id);

CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    issue_id UUID REFERENCES issues(id) ON DELETE SET NULL,
    statement TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED' CHECK (verification_status IN ('UNVERIFIED','VERIFIED','CONTESTED')),
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_claims_case ON claims(case_id);

CREATE TABLE IF NOT EXISTS claim_sources (
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    provenance_id UUID NOT NULL REFERENCES provenance(id) ON DELETE CASCADE,
    PRIMARY KEY (claim_id, provenance_id)
);
