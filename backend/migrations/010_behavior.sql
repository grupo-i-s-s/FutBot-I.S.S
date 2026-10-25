BEGIN;

ALTER TABLE behaviors
    ADD COLUMN kind VARCHAR(20) NOT NULL DEFAULT 'PLAYER',
    ADD COLUMN version INT NOT NULL DEFAULT 1,
    ADD COLUMN validation_status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
; 
ALTER TABLE behaviors
    ADD CONSTRAINT ck_behaviors_version CHECK (version >= 1);

UPDATE behaviors
SET validation_status = 'VALID'
WHERE kind = 'PLAYER'
    AND validation_status = 'PENDING'
    AND btrim(code) IN (
        $balanced$from primitives.behaviours import balanced

def decide(observation):
    return balanced(observation)$balanced$,

        $offensive$from primitives.behaviours import offensive

def decide(observation):
    return offensive(observation)$offensive$,

        $defensive$from primitives.behaviours import defensive

def decide(observation):
    return defensive(observation)$defensive$
    );
COMMIT;