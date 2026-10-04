BEGIN;

ALTER TABLE matches
    ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'WAITING',
    ADD COLUMN duration_ms INTEGER NOT NULL DEFAULT 300000,
    ADD COLUMN clock_ms INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN local_score INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN visitor_score INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN sequence INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN started_at TIMESTAMPTZ,
    ADD COLUMN finished_at TIMESTAMPTZ,
    ADD COLUMN snapshot JSONB,
    ADD COLUMN runtime_state JSONB,
    ADD CONSTRAINT ck_matches_status CHECK (status IN ('WAITING', 'RUNNING', 'FINISHED')),
    ADD CONSTRAINT ck_matches_clock CHECK (duration_ms > 0 AND clock_ms >= 0 AND clock_ms <= duration_ms),
    ADD CONSTRAINT ck_matches_result CHECK (local_score >= 0 AND visitor_score >= 0 AND sequence >= 0),
    ADD CONSTRAINT ck_matches_finished CHECK (
        status != 'FINISHED' OR (finished_at IS NOT NULL AND clock_ms = duration_ms AND snapshot IS NOT NULL)
    );

COMMIT;
