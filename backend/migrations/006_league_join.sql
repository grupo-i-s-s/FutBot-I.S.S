BEGIN;

ALTER TABLE leagues
    ADD COLUMN IF NOT EXISTS access_code VARCHAR(50);

ALTER TABLE league_registrations
    ADD COLUMN IF NOT EXISTS line_up JSON NOT NULL DEFAULT '[]'::json;

COMMIT;
