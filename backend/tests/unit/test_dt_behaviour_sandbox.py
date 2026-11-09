import pytest

from primitives.behaviour_api.runtime import BehaviourRuntime, BehaviourRuntimeError
from primitives.behaviour_api.validation import validate_program
from primitives.behaviours import BehaviourMode
from primitives.dt_behaviour import DEFAULT_DT_CODES, DtObservation


TACTIC = """from primitives.dt_behaviour import DtAction
from primitives.behaviours import BehaviourMode

def decide(observation):
    if vamos_ganando():
        return DtAction()
    cambios = [cambiar_comportamiento(jugador, BehaviourMode.OFFENSIVE) for jugador in observation.players_id]
    if observation.can_substitute and observation.pause_index == 2:
        return DtAction(cambios, [sustituir(observation.players_id[-1], observation.substitutes_id[0])])
    return DtAction(cambios)
"""


def test_dt_strategy_validates_and_uses_the_current_roster_in_the_real_worker():
    assert validate_program(TACTIC, kind="DT") == []
    observation = DtObservation(
        time_played=45, my_goals=0, rival_goals=1, players_id=[21, 22, 23],
        substitutes_id=[24, 25], can_substitute=True, pause_index=2,
    )

    with BehaviourRuntime(decision_timeout=0.5) as runtime:
        key = runtime.load(TACTIC, kind="DT")
        action = runtime.dt_decide(key, observation)

    assert [change["player_id"] for change in action.tactical_changes] == [21, 22, 23]
    assert all(change["mode"] is BehaviourMode.OFFENSIVE for change in action.tactical_changes)
    assert action.substitutions == [{"outgoing_player_id": 23, "incoming_player_id": 24}]


@pytest.mark.parametrize("name", DEFAULT_DT_CODES)
def test_builtin_dt_examples_are_valid_sandbox_programs(name):
    assert validate_program(DEFAULT_DT_CODES[name], kind="DT") == []


@pytest.mark.parametrize(("body", "diagnostic"), [
    ("return None", "INVALID_DT_ACTION"),
    (
        "return DtAction([cambiar_comportamiento(observation.players_id[0], 'CUSTOM')])",
        "INVALID_BEHAVIOUR_MODE",
    ),
    (
        "observation.players_id[0] = 999\n"
        "    return DtAction([cambiar_comportamiento(observation.players_id[0], BehaviourMode.BALANCED)])",
        "INVALID_TACTICAL_CHANGE",
    ),
    (
        "return DtAction(substitutions=[sustituir(observation.players_id[0], 999)])",
        "INVALID_DT_SUBSTITUTION",
    ),
    (
        "if observation.substitutes_id:\n"
        "        return DtAction(substitutions=[sustituir(observation.players_id[0], observation.substitutes_id[0])])\n"
        "    return DtAction()",
        "INVALID_DT_SUBSTITUTION",
    ),
    ("return observation.__class__", "FORBIDDEN_ACCESS"),
    ("import os\n    return DtAction()", "IMPORT_NOT_ALLOWED"),
])
def test_dt_validation_rejects_unauthorized_commands_and_access(body, diagnostic):
    code = (
        "from primitives.dt_behaviour import DtAction\n"
        "from primitives.behaviours import BehaviourMode\n"
        f"def decide(observation):\n    {body}\n"
    )
    assert [error["code"] for error in validate_program(code, kind="DT")] == [diagnostic]


def test_dt_worker_rejects_a_player_program_and_keeps_its_own_program_available():
    observation = DtObservation(time_played=2, my_goals=0, rival_goals=0, players_id=[1, 2, 3])

    with BehaviourRuntime(decision_timeout=0.5) as runtime:
        player_key = runtime.load("def decide(observation):\n    return quedarse()")
        dt_key = runtime.load(TACTIC, kind="DT")

        with pytest.raises(BehaviourRuntimeError):
            runtime.dt_decide(player_key, observation)

        action = runtime.dt_decide(dt_key, observation)

    assert len(action.tactical_changes) == 3
    assert action.substitutions == []
