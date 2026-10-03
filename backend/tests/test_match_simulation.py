from types import SimpleNamespace

import pytest

from primitives import match_simulation


def team(name, count=3):
    return match_simulation.Team(
        name,
        [SimpleNamespace(id=index, speed=60, power=60) for index in range(count)],
    )


def test_match_requires_three_players_per_side():
    with pytest.raises(ValueError, match="tres jugadores"):
        match_simulation.Partido(team("local", 2), team("visitante"))


def test_goal_is_awarded_to_correct_side_and_resets_positions(monkeypatch):
    match = match_simulation.Partido(team("local"), team("visitante"))
    assert len(match.world.players) == 6
    assert len(match.player_profiles) == 6

    monkeypatch.setattr(match, "run_behaviour", lambda *_: None)
    monkeypatch.setattr(match_simulation, "step", lambda *_: "LEFT")
    match.world.players[0].position = (25, 25)

    match.run_match(1 / 30)

    assert match.scorer == {"LOCAL": 1, "VISITANTE": 0}
    assert tuple(match.world.players[0].position) == match.init_players_pos[0]
    assert tuple(match.world.ball.position) == match.init_ball_pos
