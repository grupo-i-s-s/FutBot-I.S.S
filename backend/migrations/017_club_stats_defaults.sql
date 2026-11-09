BEGIN;

INSERT INTO "Club_Stats" (club_id)
SELECT id FROM clubs WHERE id <> 999
ON CONFLICT (club_id) DO NOTHING;

COMMIT;
