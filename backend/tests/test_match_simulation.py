import pytest

from primitives import match_simulation


def team(club_id, count=3):
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
