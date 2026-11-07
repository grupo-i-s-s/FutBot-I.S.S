BEGIN;

ALTER TABLE league_registrations
    ADD COLUMN lineup_version INTEGER NOT NULL DEFAULT 0,
    ADD CONSTRAINT ck_league_registrations_lineup_version
        CHECK (lineup_version >= 0);

ALTER TABLE matches
    ADD COLUMN league_id INTEGER
        REFERENCES leagues(id) ON DELETE RESTRICT,
    ADD COLUMN lineup_snapshot JSONB;

CREATE INDEX ix_matches_league_id ON matches(league_id);

COMMIT;