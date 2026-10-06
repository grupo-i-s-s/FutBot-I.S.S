"""Reglas propias de cancha y goles, con el motor físico simulado."""
import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from primitives import physics


@pytest.mark.parametrize("width, height, goal", [
    (0, 60, 15), (-1, 60, 15), (100, 0, 15), (100, -1, 15),
    (100, 60, 0), (100, 60, -1), (100, 60, 60), (100, 60, 61),
])
def test_invalid_field_is_rejected_before_creating_physics_engine(monkeypatch, width, height, goal):
    engine = Mock(side_effect=AssertionError("must not build engine"))
    monkeypatch.setattr(physics.pymunk, "Space", engine)
    with pytest.raises(ValueError, match="cancha"):
        physics.create_world(physics.Field(width, height, goal), [], (50, 30))
    engine.assert_not_called()


def world(ball_position):
    return SimpleNamespace(field=physics.Field(100, 60, 20),
                           space=Mock(), ball=SimpleNamespace(position=ball_position),
                           players=[SimpleNamespace(velocity=(3, 4))])


@pytest.mark.parametrize("position, scorer", [
    ((100, 20), "LEFT"), ((100, 40), "LEFT"), ((0, 30), "RIGHT"),
    ((100, 19.99), None), ((0, 40.01), None), ((50, 30), None),
])
def test_scoring_uses_goal_opening_and_correct_attacking_side(position, scorer):
    state = world(position)
    assert physics.step(state, 0.1) == scorer
    assert state.space.step.call_count == (1 if scorer else 4)
    assert all(call.args == (0.025,) for call in state.space.step.call_args_list)
    assert state.players[0].velocity == (0, 0)


@pytest.mark.parametrize("dt", [0, -0.1])
def test_invalid_step_does_not_advance_world(dt):
    state = world((50, 30))
    with pytest.raises(ValueError, match="dt"):
        physics.step(state, dt)
    state.space.step.assert_not_called()
    assert state.players[0].velocity == (3, 4)
