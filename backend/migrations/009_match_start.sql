BEGIN;

ALTER TABLE matches
    ADD COLUMN cancellation_reason VARCHAR(64);

ALTER TABLE matches
    DROP CONSTRAINT ck_matches_status;

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