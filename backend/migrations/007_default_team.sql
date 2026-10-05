BEGIN;

CREATE TABLE default_teams (
    club_id INTEGER PRIMARY KEY
        REFERENCES clubs(id) ON DELETE CASCADE,
    line_up JSON NOT NULL
);

COMMIT;