BEGIN;

ALTER TABLE leagues
ADD COLUMN access_code VARCHAR(50);

ALTER TABLE league_registrations
ADD COLUMN line_up JSON NOT NULL;

COMMIT;