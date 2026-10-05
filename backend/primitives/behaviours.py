"""Contrato y programas Python predeterminados del motor de partidos."""

from dataclasses import dataclass
from enum import StrEnum


class BehaviourMode(StrEnum):
    BALANCED = "BALANCED"
    OFFENSIVE = "OFFENSIVE"
    DEFENSIVE = "DEFENSIVE"


@dataclass(frozen=True)
class Observation:
    player_position: tuple[float, float]
    ball_position: tuple[float, float]
    home_position: tuple[float, float]
    opponent_goal: tuple[float, float]
    is_closest_teammate: bool
    ball_in_own_half: bool
    can_kick: bool
    field_size: tuple[float, float] = (100, 60)
    goal_width: float = 15


@dataclass(frozen=True)
class Action:
    move_target: tuple[float, float]
    kick_target: tuple[float, float] | None = None


def _attack_direction(observation: Observation) -> int:
    return 1 if observation.opponent_goal[0] > observation.home_position[0] else -1


def _approach_ball(observation: Observation) -> tuple[float, float]:
    # Llegar por detrás permite patear hacia adelante, sin amontonarse sobre la pelota.
    direction = _attack_direction(observation)
    field_width, field_height = observation.field_size
    return (
        max(1.5, min(field_width - 1.5, observation.ball_position[0] - direction * 2)),
        max(1.5, min(field_height - 1.5, observation.ball_position[1])),
    )


def _shot_target(observation: Observation) -> tuple[float, float] | None:
    if not observation.can_kick:
        return None
    x, center_y = observation.opponent_goal
    # Elegir un lateral del arco evita que todos los remates recorran el eje central.
    lane = -1 if observation.home_position[1] < center_y else 1
    if observation.home_position[1] == center_y:
        lane = -_attack_direction(observation)
    return x, center_y + lane * observation.goal_width * 4 / 15


def balanced(observation: Observation) -> Action:
    if observation.is_closest_teammate:
        target = _approach_ball(observation)
    else:
        target = (
            (observation.home_position[0] + observation.ball_position[0]) / 2,
            observation.home_position[1],
        )
    return Action(target, _shot_target(observation))


def offensive(observation: Observation) -> Action:
    if observation.is_closest_teammate:
        target = _approach_ball(observation)
    else:
        direction = _attack_direction(observation)
        # Los acompañantes se desmarcan por su carril delante de la pelota.
        target = (
            max(5, min(observation.field_size[0] - 5, observation.ball_position[0] + direction * 12)),
            observation.home_position[1],
        )
    return Action(target, _shot_target(observation))


def defensive(observation: Observation) -> Action:
    chase = observation.ball_in_own_half and observation.is_closest_teammate
    return Action(
        _approach_ball(observation) if chase else observation.home_position,
        _shot_target(observation),
    )


PROGRAMS = {
    BehaviourMode.BALANCED: balanced,
    BehaviourMode.OFFENSIVE: offensive,
    BehaviourMode.DEFENSIVE: defensive,
}
DEFAULT_MODES = {
    "Equilibrado": BehaviourMode.BALANCED,
    "Ofensivo": BehaviourMode.OFFENSIVE,
    "Defensivo": BehaviourMode.DEFENSIVE,
}
DEFAULT_CODES = {
    "Equilibrado": "from primitives.behaviours import balanced\n\ndef decide(observation):\n    return balanced(observation)",
    "Ofensivo": "from primitives.behaviours import offensive\n\ndef decide(observation):\n    return offensive(observation)",
    "Defensivo": "from primitives.behaviours import defensive\n\ndef decide(observation):\n    return defensive(observation)",
}
LEGACY_CODE = 'print("hola futbot!")'


def resolve_behaviour(code: str, name: str) -> BehaviourMode:
    """Resuelve el código registrado; mantiene compatibles los defaults anteriores."""
    if not isinstance(code, str):
        raise ValueError("El comportamiento necesita código Python.")
    source = code.strip()
    for default_name, default_code in DEFAULT_CODES.items():
        if source == default_code:
            return DEFAULT_MODES[default_name]
    if source == LEGACY_CODE and name in DEFAULT_MODES:
        return DEFAULT_MODES[name]
    raise ValueError(f"El comportamiento {name!r} no tiene un programa compatible.")


def decide(mode: BehaviourMode, observation: Observation) -> Action:
    return PROGRAMS[mode](observation)
