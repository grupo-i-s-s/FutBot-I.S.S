import json

import pytest

from primitives import match_simulation
from primitives.behaviours import Action, BehaviourMode


def team(club_id, count=3, modes=None):
    return match_simulation.Team(
        club_id=club_id,
        name=f"Club {club_id}",
        players=tuple(
            match_simulation.PlayerProfile(
                id=club_id * 10 + index,
                club_id=club_id,
                name=f"Jugador {index}",
                speed=60,
                power=60,
                behaviour_mode=modes[index] if modes else BehaviourMode.BALANCED,
            )
            for index in range(count)
        ),
    )


@pytest.mark.parametrize("count", [0, 2, 4])
def test_match_requires_three_players_per_side(count):
    with pytest.raises(ValueError, match="tres titulares"):
        match_simulation.Match(team(1, count), team(2))


def test_goal_is_awarded_to_correct_side_and_resets_positions(monkeypatch):
    match = match_simulation.Match(team(1), team(2))
    assert len(match.world.players) == 6
    assert len(match.player_profiles) == 6
    assert set(match.player_bodies) == {10, 11, 12, 20, 21, 22}
    assert [player["id"] for player in match.get_players_state()] == [10, 11, 12, 20, 21, 22]

    monkeypatch.setattr(match, "run_behaviour", lambda *_: None)
    monkeypatch.setattr(match_simulation, "step", lambda *_: "LEFT")
    match.world.players[0].position = (25, 25)

    match.run_match(1 / 30)

    assert match.scorer == {"LOCAL": 1, "VISITANTE": 0}
    assert tuple(match.world.players[0].position) == match.init_players_pos[0]
    assert tuple(match.world.ball.position) == match.init_ball_pos


def test_match_rejects_player_from_another_club():
    wrong_profile = match_simulation.PlayerProfile(
        id=99, club_id=2, name="Ajeno", speed=60, power=60
    )
    local = team(1)
    local = match_simulation.Team(1, local.name, (wrong_profile, *local.players[1:]))

    with pytest.raises(ValueError, match="ajeno"):
        match_simulation.Match(local, team(2))


@pytest.mark.parametrize(
    "position, velocity, expected_score",
    [
        ((99, 30), (100, 0), {"LOCAL": 1, "VISITANTE": 0}),
        ((1, 30), (-100, 0), {"LOCAL": 0, "VISITANTE": 1}),
    ],
    ids=["arco-derecho-gol-local", "arco-izquierdo-gol-visitante"],
)
def test_physical_goal_counts_once_for_attacking_team(
    monkeypatch, position, velocity, expected_score
):
    match = match_simulation.Match(team(1), team(2))
    # Un tiro controlado: conservamos la física real y evitamos nuevas patadas.
    monkeypatch.setattr(match, "run_behaviour", lambda *_: None)
    match.world.ball.position = position
    match.world.ball.velocity = velocity

    match.run_match(1 / 30)

    assert match.scorer == expected_score
    assert tuple(match.world.ball.position) == match.init_ball_pos
    assert tuple(match.world.ball.velocity) == (0, 0)

    match.run_match(1 / 30)

    assert match.scorer == expected_score


@pytest.mark.parametrize("position, velocity", [((99, 5), (100, 0)), ((1, 5), (-100, 0))])
def test_shot_outside_goal_does_not_change_score(monkeypatch, position, velocity):
    match = match_simulation.Match(team(1), team(2))
    monkeypatch.setattr(match, "run_behaviour", lambda *_: None)
    match.world.ball.position = position
    match.world.ball.velocity = velocity

    match.run_match(1 / 30)

    assert match.scorer == {"LOCAL": 0, "VISITANTE": 0}


def test_assigned_behaviours_apply_different_movements():
    modes = (BehaviourMode.BALANCED, BehaviourMode.OFFENSIVE, BehaviourMode.DEFENSIVE)
    match = match_simulation.Match(team(1, modes=modes), team(2))
    match.world.ball.position = (80, 30)

    actions = [
        match.run_behaviour(body, profile, (100, 30), 1 / 30)
        for body, profile in zip(match.world.players[:3], match.local_team.players, strict=True)
    ]

    assert [action.move_target for action in actions] == [(45, 20), (80, 30), (30, 30)]
    assert match.world.players[0].velocity.x > 0
    assert match.world.players[1].velocity.y < 0
    assert tuple(match.world.players[2].velocity) == (0, 0)


@pytest.mark.parametrize("player_index, position, direction", [(0, (48, 30), 1), (3, (52, 30), -1)])
def test_each_team_kicks_toward_opponent_goal(monkeypatch, player_index, position, direction):
    match = match_simulation.Match(team(1), team(2))
    match.world.players[player_index].position = position
    monkeypatch.setattr(match_simulation, "step", lambda *_: None)

    match.run_match(1 / 30)

    assert match.world.ball.velocity.x * direction > 0


def test_closest_player_wins_simultaneous_shots_not_last_player_in_loop(monkeypatch):
    match = match_simulation.Match(team(1), team(2))
    match.world.players[0].position = (49, 30)
    match.world.players[3].position = (52, 30)
    monkeypatch.setattr(match_simulation, "step", lambda *_: None)
    real_kick = match_simulation.kick
    shots = []

    def record_kick(*args):
        shots.append(args[0])
        return real_kick(*args)

    monkeypatch.setattr(match_simulation, "kick", record_kick)

    match.run_match(1 / 30)

    assert shots == [match.world.players[0]]
    assert match.world.ball.velocity.x > 0


def test_player_cannot_kick_from_fifteen_units_or_repeat_every_tick(monkeypatch):
    match = match_simulation.Match(team(1), team(2))
    monkeypatch.setattr(match_simulation, "step", lambda *_: None)
    real_kick = match_simulation.kick
    shots = []

    def record_kick(*args):
        shots.append(args[0])
        return real_kick(*args)

    monkeypatch.setattr(match_simulation, "kick", record_kick)
    match.world.players[0].position = (40, 30)
    match.run_match(1 / 30)
    assert shots == []

    match.world.players[0].position = (48, 30)
    match.run_match(1 / 30)
    match.run_match(1 / 30)
    assert shots == [match.world.players[0]]


def test_invalid_behaviour_action_leaves_player_idle_and_match_continues(monkeypatch):
    match = match_simulation.Match(team(1), team(2))
    monkeypatch.setattr(match_simulation, "decide", lambda *_: Action((200, 30)))

    match.run_match(1 / 30)

    assert match.time == pytest.approx(1 / 30)
    assert all(tuple(player.velocity) == (0, 0) for player in match.world.players)
    assert match.scorer == {"LOCAL": 0, "VISITANTE": 0}


def test_match_finishes_exactly_at_duration_and_freezes_result(monkeypatch):
    match = match_simulation.Match(team(1), team(2), match_id=42, duration_ms=50)
    steps = []
    monkeypatch.setattr(match_simulation, "step", lambda world, dt: steps.append(dt) or "LEFT")

    match.run_match(1 / 30)
    match.run_match(1 / 30)
    final = match.snapshot(3, "now")
    match.run_match(10)

    assert steps == pytest.approx([1 / 30, 0.05 - 1 / 30])
    assert match.time == 0.05
    assert match.finished and match.status == "FINISHED"
    assert final["matchId"] == 42
    assert final["state"]["clockMs"] == 50
    assert final["state"]["teams"][0]["score"] == 2
    assert match.snapshot(3, "now") == final
    assert json.loads(json.dumps(final)) == final


@pytest.mark.parametrize("duration", [0, -1, True, 1.5])
def test_invalid_duration_is_rejected(duration):
    with pytest.raises(ValueError, match="duración"):
        match_simulation.Match(team(1), team(2), duration_ms=duration)


def test_checkpoint_restores_roster_physics_clock_score_and_cooldown():
    match = match_simulation.Match(team(1), team(2), match_id=42, duration_ms=1000)
    match.run_match(1 / 30)
    match.scorer["VISITANTE"] = 2
    match.next_kick_at[10] = 0.5
    match.world.ball.position = (60, 40)
    match.world.ball.velocity = (10, -2)
    match.world.ball.angle = 0.3
    match.world.ball.angular_velocity = 0.2

    restored = match_simulation.Match.from_checkpoint(json.loads(json.dumps(match.checkpoint())))

    assert restored.snapshot(4, "now") == match.snapshot(4, "now")
    assert restored.checkpoint() == match.checkpoint()
    restored.run_match(1 / 30)
    assert restored.time == pytest.approx(2 / 30)
