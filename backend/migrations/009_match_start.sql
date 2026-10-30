BEGIN;

ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS cancellation_reason VARCHAR(64);

ALTER TABLE matches
    DROP CONSTRAINT IF EXISTS ck_matches_status,
    DROP CONSTRAINT IF EXISTS ck_matches_cancellation_reason;

ALTER TABLE matches
    ADD CONSTRAINT ck_matches_status CHECK (
        status IN (
                   'WAITING',
                   'WAITING_OPPONENT',
                   'SCHEDULED',
                   'RUNNING',
                   'FINISHED',
                   'CANCELLED'
            )
        ),
    ADD CONSTRAINT ck_matches_cancellation_reason CHECK (
        status != 'CANCELLED'
        OR cancellation_reason IS NOT NULL
    );

COMMIT;
