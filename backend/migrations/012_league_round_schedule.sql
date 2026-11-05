BEGIN;

ALTER TABLE league_rounds
    ADD COLUMN schedule_confirmed BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE league_rounds SET schedule_confirmed = TRUE WHERE number = 1;

COMMIT;
