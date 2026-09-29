-- D02-T01: users table (single-user v1; multi-user capable schema)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'OWNER',
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
