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


@dataclass(frozen=True)
class Action:
    move_target: tuple[float, float]
    kick_target: tuple[float, float] | None = None


def balanced(observation: Observation) -> Action:
    if observation.is_closest_teammate:
        target = observation.ball_position
    else:
        target = (
            (observation.home_position[0] + observation.ball_position[0]) / 2,
            observation.home_position[1],
        )
    return Action(target, observation.opponent_goal if observation.can_kick else None)


def offensive(observation: Observation) -> Action:
    return Action(
        observation.ball_position,
        observation.opponent_goal if observation.can_kick else None,
    )


def defensive(observation: Observation) -> Action:
    chase = observation.ball_in_own_half and observation.is_closest_teammate
    return Action(
        observation.ball_position if chase else observation.home_position,
        observation.opponent_goal if observation.can_kick else None,
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
