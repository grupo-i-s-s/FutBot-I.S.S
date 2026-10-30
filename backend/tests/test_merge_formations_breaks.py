"""Regresiones del merge: checkpoints de ambas ramas y cambio de arco."""
import json

import pytest

from primitives import match_simulation, physics
from primitives.match_simulation import Match, PlayerProfile, Team


def make_match():
    teams = [
        Team(club_id, f"Club {club_id}", tuple(
            PlayerProfile(
                club_id * 10 + index, club_id, f"Jugador {index}",
                speed=60, power=60, agility=60, strength=60, control=60,
            )
            for index in range(3)
        ), formation_id=formation_id)
        for club_id, formation_id in ((1, 2), (2, 3))
    ]
    return Match(*teams, duration_ms=1000, hydration_break_ms=100, half_break_ms=200)


@pytest.fixture(autouse=True)
def isolate_physics(monkeypatch):
    monkeypatch.setattr(match_simulation, "step", lambda *_: None)
    monkeypatch.setattr(Match, "run_behaviour", lambda *_: None)


@pytest.mark.parametrize("elapsed", [0.2, 0.6, 0.7, 0.8, 0.9])
def test_merged_checkpoint_recovers_formations_breaks_and_sides(elapsed):
    simulation = make_match()
    simulation.run_match(elapsed)
    checkpoint = json.loads(json.dumps(simulation.checkpoint()))
    restored = Match.from_checkpoint(checkpoint)

    assert checkpoint["version"] == 3
    assert json.loads(json.dumps(restored.checkpoint())) == checkpoint
    assert restored.local_team.formation_id == 2
    assert restored.visitor_team.formation_id == 3
    assert restored.home_positions == simulation.home_positions
    assert restored.snapshot(8, "now") == simulation.snapshot(8, "now")
    restored.run_match(2)
    assert restored.finished and restored.sides_swapped
    assert restored.team_side(1) == "RIGHT"
    assert restored.team_side(2) == "LEFT"


@pytest.mark.parametrize("version", [1, 2])
def test_formation_branch_checkpoint_without_breaks_still_resumes(version):
    simulation = make_match()
    checkpoint = json.loads(json.dumps(simulation.checkpoint()))
    checkpoint["version"] = version
    for key in ("breaks", "sides_swapped", "kickoff_club_id"):
        checkpoint.pop(key)
    restored = Match.from_checkpoint(checkpoint)
    assert restored.local_team.formation_id == 2
    assert restored.init_players_pos == simulation.init_players_pos
    restored.run_match(1)
    assert restored.finished and not restored.sides_swapped


def test_develop_checkpoint_with_breaks_and_without_formations_still_resumes():
    simulation = make_match()
    simulation.run_match(0.6)
    checkpoint = json.loads(json.dumps(simulation.checkpoint()))
    checkpoint["version"] = 2
    for key in ("local_team", "visitor_team"):
        checkpoint[key].pop("formation_id")
        checkpoint[key].pop("formation_positions")
    for key in ("sides_swapped", "kickoff_club_id"):
        checkpoint.pop(key)

    restored = Match.from_checkpoint(checkpoint)
    assert restored.local_team.formation_id == restored.visitor_team.formation_id == 1
    assert restored.snapshot(1, "now")["state"]["phase"] == "HALF_BREAK"
    restored.run_match(0.2)
    assert restored.sides_swapped


def test_halftime_mirrors_formations_once_and_keeps_score_and_roster():
    simulation = make_match()
    positions = simulation.init_players_pos
    roster = simulation.player_profiles
    simulation.scorer.update(LOCAL=2, VISITANTE=1)
    simulation.run_match(0.6)
    assert not simulation.sides_swapped
    frozen = simulation.checkpoint()["bodies"]
    simulation.run_match(0.1)
    assert simulation.checkpoint()["bodies"] == frozen
    simulation.run_match(0.1)
    assert simulation.init_players_pos == tuple((100 - x, y) for x, y in positions)
    assert simulation.player_profiles == roster
    assert simulation.scorer == {"LOCAL": 2, "VISITANTE": 1}
    assert tuple(simulation.world.ball.position) == (50, 30)
    assert simulation.kickoff_club_id == 2
    for body, position in zip(simulation.world.players, simulation.kickoff_positions(), strict=True):
        assert tuple(body.position) == pytest.approx(position)
        assert tuple(body.velocity) == (0, 0)
    state = simulation.snapshot(1, "now")["state"]
    assert [team["side"] for team in state["teams"]] == ["RIGHT", "LEFT"]
    assert [team["score"] for team in state["teams"]] == [2, 1]
    mirrored = simulation.init_players_pos
    simulation.start_second_half()
    assert simulation.init_players_pos == mirrored


@pytest.mark.parametrize("position,velocity,expected", [
    ((99, 30), (100, 0), {"LOCAL": 0, "VISITANTE": 1}),
    ((1, 30), (-100, 0), {"LOCAL": 1, "VISITANTE": 0}),
])
def test_goal_is_awarded_to_the_correct_club_in_second_half(monkeypatch, position, velocity, expected):
    simulation = make_match()
    simulation.start_second_half()
    simulation.world.ball.position = position
    simulation.world.ball.velocity = velocity
    monkeypatch.setattr(match_simulation, "step", physics.step)
    simulation.run_match(1 / 30)
    assert simulation.scorer == expected
