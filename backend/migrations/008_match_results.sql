BEGIN;

ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'WAITING',
    ADD COLUMN IF NOT EXISTS duration_ms INTEGER NOT NULL DEFAULT 300000,
    ADD COLUMN IF NOT EXISTS clock_ms INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS local_score INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS visitor_score INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS sequence INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS snapshot JSONB,
    ADD COLUMN IF NOT EXISTS runtime_state JSONB;

-- Conserva las restricciones existentes, incluida la ampliación de estados de 009.
DO $migration$
DECLARE
    constraint_name TEXT;
    constraint_definition TEXT;
BEGIN
    FOR constraint_name, constraint_definition IN
        SELECT *
        FROM (
            VALUES
                (
                    'ck_matches_status',
                    $$CHECK (status IN ('WAITING', 'RUNNING', 'FINISHED'))$$
                ),
                (
                    'ck_matches_clock',
                    'CHECK (duration_ms > 0 AND clock_ms >= 0 AND clock_ms <= duration_ms)'
                ),
                (
                    'ck_matches_result',
                    'CHECK (local_score >= 0 AND visitor_score >= 0 AND sequence >= 0)'
                ),
                (
                    'ck_matches_finished',
                    $$CHECK (
                        status != 'FINISHED'
                        OR (
                            finished_at IS NOT NULL
                            AND clock_ms = duration_ms
                            AND snapshot IS NOT NULL
                        )
                    )$$
                )
        ) AS definitions(name, definition)
    LOOP
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conrelid = 'matches'::regclass
              AND conname = constraint_name
        ) THEN
            EXECUTE format(
                'ALTER TABLE matches ADD CONSTRAINT %I %s',
                constraint_name,
                constraint_definition
            );
        END IF;
    END LOOP;
END;
$migration$;

COMMIT;
