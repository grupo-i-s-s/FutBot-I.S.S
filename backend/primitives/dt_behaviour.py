from dataclasses import dataclass
from enum import StrEnum
from primitives.behaviours import BehaviourMode


# 1. Los modos que el DT puede tener
class DtBehaviourMode(StrEnum):
    SAMPAOLI = "SAMPAOLI"
    CHOLO_SIMEONE = "CHOLO_SIMEONE"
    GUARDIOLA = "GUARDIOLA"
    COME_BACK = "COME_BACK"


@dataclass(frozen=True)
class DtObservation:
    time_played: int
    my_goals: int
    rival_goals: int
    players_id: list[int]


@dataclass(frozen=True)
class DtAction:
    tactical_changes: list[dict]


def sampaoli(observation: DtObservation) -> DtAction:

    return DtAction(tactical_changes=[])  # Sampaoli no hace nada xd


def cholo_simeone(
    observation: DtObservation,
) -> DtAction:  # Simeone defiende el resultado desde el 1/0 y pone todo en defensivo

    cambios = [
        {"player_id": p_id, "mode": BehaviourMode.DEFENSIVE}
        for p_id in observation.players_id
    ]
    return DtAction(tactical_changes=cambios)


def pep_guardiola(
    observation: DtObservation,
) -> DtAction:  # Guardiola pone todo en balanced
    cambios = [
        {"player_id": p_id, "mode": BehaviourMode.BALANCED}
        for p_id in observation.players_id
    ]
    return DtAction(tactical_changes=cambios)


def come_back(
    observation: DtObservation,
) -> DtAction:  # Come_back pone todo el offensivo
    cambios = [
        {"player_id": p_id, "mode": BehaviourMode.OFFENSIVE}
        for p_id in observation.players_id
    ]
    return DtAction(tactical_changes=cambios)


DT_PROGRAMS = {
    DtBehaviourMode.SAMPAOLI: sampaoli,
    DtBehaviourMode.CHOLO_SIMEONE: cholo_simeone,
    DtBehaviourMode.GUARDIOLA: pep_guardiola,
    DtBehaviourMode.COME_BACK: come_back,
}

DEFAULT_DT_MODES = {
    "No hacer nada": DtBehaviourMode.SAMPAOLI,
    "Cuidar resultado": DtBehaviourMode.CHOLO_SIMEONE,
    "Manejar la pelota": DtBehaviourMode.GUARDIOLA,
    "Remontada": DtBehaviourMode.COME_BACK,
}

DEFAULT_DT_CODES = {
    "No hacer nada": (
        "from dt_behaviour import DtAction\n\n"
        "def decide(obs):\n"
        "    return DtAction(tactical_changes = cambios)"
    ),
    "Cuidar resultado": (
        "from dt_behaviour import DtAction\n\n"
        "from primitives.behaviours import BehaviourMode\n\n"
        "def decide(obs):\n"
        "    if obs.my_goals > obs.rival_goals:\n"
        "        cambios = [{'player_id': pid, 'mode':BehaviourMode.DEFENSIVE} for pid in obs.players_id]\n"
        "        return DtAction(tactical_changes=cambios)\n"
    ),
    "Manejar la pelota": (
        "from dt_behaviour import DtAction\n\n"
        ""
        "from primitives.behaviours import BehaviourMode\n\n"
        "def decide(obs):\n "
        "   cambios = [{'player_id': p_id, 'mode': BehaviourMode.BALANCED} for p_id in obs.players_id]\n"
        "   return DtAction(tactical_changes = cambios) \n"
    ),
    "Remontada": (
        "from dt_behaviour import DtAction\n\n"
        ""
        "from primitives.behaviours import BehaviourMode\n\n"
        "def decide(obs):\n "
        "   cambios = [{'player_id': p_id, 'mode': BehaviourMode.OFFENSIVE} for p_id in obs.players_id]\n"
        "   return DtAction(tactical_changes = cambios) \n"
    ),
}


def resolve_dt_behaviour(code: str, name: str) -> DtBehaviourMode:
    """Resuelve el código del DT mapeándolo a los modos predeterminados."""
    if not isinstance(code, str):
        raise ValueError("El comportamiento necesita código Python.")
    source = code.strip()

    for default_name, default_code in DEFAULT_DT_CODES.items():
        if source == default_code:
            return DEFAULT_DT_MODES[default_name]

    raise ValueError(
        f"El comportamiento de DT {name!r} no tiene un programa compatible."
    )


def dt_decide(mode: DtBehaviourMode, observation: DtObservation) -> DtAction:
    return DT_PROGRAMS[mode](observation)
