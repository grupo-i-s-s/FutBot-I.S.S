BEGIN;
WITH clubs_without_dt AS (
    SELECT clubs.id, clubs.user_id
    FROM clubs
    WHERE NOT EXISTS (SELECT 1 FROM dt WHERE dt.club_id = clubs.id)
),
presets (name, code) AS (
    VALUES
        ('No hacer nada', $strategy$from primitives.dt_behaviour import DtAction

def decide(obs):
    return DtAction()$strategy$),
        ('Cuidar resultado', $strategy$from primitives.dt_behaviour import DtAction
from primitives.behaviours import BehaviourMode

def decide(obs):
    if obs.my_goals <= obs.rival_goals:
        return DtAction()
    substitutions = []
    if obs.can_substitute and obs.pause_index == 2:
        substitutions = [sustituir(obs.players_id[-1], obs.substitutes_id[0])]
    return DtAction(
        tactical_changes=[cambiar_comportamiento(jugador, BehaviourMode.DEFENSIVE) for jugador in obs.players_id],
        substitutions=substitutions,
    )$strategy$),
        ('Manejar la pelota', $strategy$from primitives.dt_behaviour import DtAction
from primitives.behaviours import BehaviourMode

def decide(obs):
    substitutions = []
    if obs.can_substitute and obs.pause_index == 2:
        substitutions = [sustituir(obs.players_id[-1], obs.substitutes_id[0])]
    return DtAction(
        tactical_changes=[cambiar_comportamiento(jugador, BehaviourMode.BALANCED) for jugador in obs.players_id],
        substitutions=substitutions,
    )$strategy$),
        ('Remontada', $strategy$from primitives.dt_behaviour import DtAction
from primitives.behaviours import BehaviourMode

def decide(obs):
    substitutions = []
    if obs.can_substitute and obs.pause_index == 2:
        substitutions = [sustituir(obs.players_id[-1], obs.substitutes_id[0])]
    return DtAction(
        tactical_changes=[cambiar_comportamiento(jugador, BehaviourMode.OFFENSIVE) for jugador in obs.players_id],
        substitutions=substitutions,
    )$strategy$)
),
created AS (
    INSERT INTO dt_behaviours (user_id, name, code)
    SELECT club.user_id, preset.name, preset.code
    FROM clubs_without_dt AS club CROSS JOIN presets AS preset
    RETURNING id, user_id, name
)
INSERT INTO dt (club_id, is_active, behaviour_id)
SELECT club.id, false, created.id
FROM clubs_without_dt AS club
JOIN created ON created.user_id = club.user_id AND created.name = 'No hacer nada';

COMMIT;
