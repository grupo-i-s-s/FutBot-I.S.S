import pytest

from primitives.behaviours import (
    BehaviourMode,
    DEFAULT_CODES,
    LEGACY_CODE,
    Observation,
    decide,
    resolve_behaviour,
)


def test_default_programs_make_distinct_decisions_with_same_observation():
    observation = Observation(
        player_position=(10, 20), ball_position=(80, 30), home_position=(10, 20),
        opponent_goal=(100, 30), is_closest_teammate=False,
        ball_in_own_half=False, can_kick=False,
    )

    actions = [decide(mode, observation) for mode in BehaviourMode]

    assert [action.move_target for action in actions] == [(45, 20), (80, 30), (10, 20)]
    assert all(action.kick_target is None for action in actions)


def test_program_code_determines_behaviour_even_when_name_changes():
    assert resolve_behaviour(DEFAULT_CODES["Ofensivo"], "Otro nombre") == BehaviourMode.OFFENSIVE


@pytest.mark.parametrize("name, mode", [
    ("Equilibrado", BehaviourMode.BALANCED),
    ("Ofensivo", BehaviourMode.OFFENSIVE),
    ("Defensivo", BehaviourMode.DEFENSIVE),
])
def test_old_defaults_remain_compatible(name, mode):
    assert resolve_behaviour(LEGACY_CODE, name) == mode


def test_unknown_python_is_not_a_registered_program():
    with pytest.raises(ValueError, match="compatible"):
        resolve_behaviour("while True: pass", "Ofensivo")
