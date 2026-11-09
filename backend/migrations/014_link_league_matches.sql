BEGIN;

UPDATE matches AS match
SET league_id = round.league_id
FROM league_rounds AS round
WHERE match.league_round_id = round.id
  AND match.league_id IS NULL;

COMMIT;