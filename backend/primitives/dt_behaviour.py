from dataclasses import dataclass, field
from enum import StrEnum
from primitives.behaviours import BehaviourMode


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
    substitutes_id: list[int] = field(default_factory=list)
    can_substitute: bool = False
    pause_index: int | None = None


@dataclass(frozen=True)
class DtAction:
    tactical_changes: list[dict] = field(default_factory=list)
    substitutions: list[dict] = field(default_factory=list)


def sampaoli(observation: DtObservation) -> DtAction:
    return DtAction()


def _set_team_mode(observation: DtObservation, mode: BehaviourMode) -> DtAction:
    substitutions = []
    if observation.can_substitute and observation.pause_index == 2:
        substitutions.append({
            "outgoing_player_id": observation.players_id[-1],
            "incoming_player_id": observation.substitutes_id[0],
        })
    return DtAction(
        tactical_changes=[{"player_id": player_id, "mode": mode} for player_id in observation.players_id],
        substitutions=substitutions,
    )


def cholo_simeone(observation: DtObservation) -> DtAction:
    if observation.my_goals > observation.rival_goals:
        return _set_team_mode(observation, BehaviourMode.DEFENSIVE)
    return DtAction()


def pep_guardiola(observation: DtObservation) -> DtAction:
    return _set_team_mode(observation, BehaviourMode.BALANCED)


def come_back(observation: DtObservation) -> DtAction:
    return _set_team_mode(observation, BehaviourMode.OFFENSIVE)


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

LEGACY_DT_CODES = {
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


def _team_mode_code(mode: BehaviourMode, *, protect_lead: bool = False) -> str:
    lead_guard = "    if obs.my_goals <= obs.rival_goals:\n        return DtAction()\n" if protect_lead else ""
    return (
        "from primitives.dt_behaviour import DtAction\n"
        "from primitives.behaviours import BehaviourMode\n\n"
        "def decide(obs):\n"
        f"{lead_guard}"
        "    substitutions = []\n"
        "    if obs.can_substitute and obs.pause_index == 2:\n"
        "        substitutions = [sustituir(obs.players_id[-1], obs.substitutes_id[0])]\n"
        "    return DtAction(\n"
        f"        tactical_changes=[cambiar_comportamiento(jugador, BehaviourMode.{mode}) for jugador in obs.players_id],\n"
        "        substitutions=substitutions,\n"
        "    )"
    )


DEFAULT_DT_CODES = {
    "No hacer nada": "from primitives.dt_behaviour import DtAction\n\ndef decide(obs):\n    return DtAction()",
    "Cuidar resultado": _team_mode_code(BehaviourMode.DEFENSIVE, protect_lead=True),
    "Manejar la pelota": _team_mode_code(BehaviourMode.BALANCED),
    "Remontada": _team_mode_code(BehaviourMode.OFFENSIVE),
}


def resolve_dt_behaviour(code: str, name: str) -> DtBehaviourMode:
    """Resuelve el código del DT mapeándolo a los modos predeterminados."""
    if not isinstance(code, str):
        raise ValueError("El comportamiento necesita código Python.")
    source = code.strip()

    for default_name, default_code in DEFAULT_DT_CODES.items():
        if source in (default_code, LEGACY_DT_CODES[default_name].strip()):
            return DEFAULT_DT_MODES[default_name]

    raise ValueError(
        f"El comportamiento de DT {name!r} no tiene un programa compatible."
    )


def dt_decide(mode: DtBehaviourMode, observation: DtObservation) -> DtAction:
    return DT_PROGRAMS[mode](observation)
