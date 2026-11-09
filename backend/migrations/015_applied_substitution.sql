BEGIN;

CREATE UNIQUE INDEX uq_applied_substitution
    ON planned_substitutions(match_id, club_id, pause_index)
    WHERE status = 'APPLIED';

COMMIT;
