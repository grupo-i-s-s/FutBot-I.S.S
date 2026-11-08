BEGIN;

CREATE TABLE IF NOT EXISTS pending_email_verifications (
    email VARCHAR(254) PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    club_name VARCHAR(50) NOT NULL,
    code_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    last_sent_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    resend_window_started_at TIMESTAMPTZ NOT NULL,
    resend_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_pending_email_verifications_expires_at
    ON pending_email_verifications (expires_at);

COMMIT;