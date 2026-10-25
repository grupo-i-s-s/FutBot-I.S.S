import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from app.errors import AppError
from app.services import match_builder_service as service
from primitives.behaviours import BehaviourMode, DEFAULT_CODES, LEGACY_CODE


@pytest.fixture
def teams(monkeypatch):
    players = {}
    behaviours = {}
    lineups = {}
    for club_id in (7, 9):
        players[club_id] = [
            SimpleNamespace(
                id=club_id * 10 + index, club_id=club_id,
                name=f"Jugador {club_id}-{index}", speed=60, power=60,
                behavior_id=club_id * 100,
            )
            for index in range(6)
        ]
        behaviours[club_id] = [
            SimpleNamespace(
                id=club_id * 100 + index,
                name=name, code=DEFAULT_CODES[name],
            )
            for index, name in enumerate(("Equilibrado", "Ofensivo", "Defensivo"))
        ]
        lineups[club_id] = {
            "formationId": 2 if club_id == 7 else 3,
            "starters": [
                {"playerId": club_id * 10 + index, "behaviourId": club_id * 100 + mode}
                for index, mode in ((4, 2), (0, 0), (2, 1))
            ],
            "substitutes": [
                {"playerId": club_id * 10 + index, "behaviourId": club_id * 100}
                for index in (1, 3, 5)
            ],
        }

    matches = Mock()
    matches.get_by_id.return_value = SimpleNamespace(
        creator_id=7, visitor_id=9, duration_ms=300_000,
    )
    matches.get_club_names.return_value = {7: "Local", 9: "Visitante"}
    saved = Mock()
    saved.get_by_club.side_effect = lambda db, cid: SimpleNamespace(line_up=lineups[cid])
    player_repo = Mock()
    player_repo.get_players_by_club.side_effect = lambda db, cid: players[cid]
    behaviour_repo = Mock()
    behaviour_repo.get_all_behaviours.side_effect = lambda db, cid: behaviours[cid]
    monkeypatch.setattr(service, "matches_repository", matches)
    monkeypatch.setattr(service, "team_repository", saved)
    monkeypatch.setattr(service, "player_repository", player_repo)
    monkeypatch.setattr(service, "behaviour_repository", behaviour_repo)
    return SimpleNamespace(
        players=players, behaviours=behaviours, lineups=lineups,
        matches=matches, saved=saved,
    )


def test_builder_uses_saved_starter_order_formation_and_slot_behaviours(db, teams):
    match = service.build_match(db, 42)

    assert match.match_id == 42
    assert [player.id for player in match.player_profiles] == [74, 70, 72, 94, 90, 92]
    assert [player.club_id for player in match.player_profiles] == [7, 7, 7, 9, 9, 9]
    assert [player.behaviour_id for player in match.local_team.players] == [702, 700, 701]
    assert [player.behaviour_mode for player in match.local_team.players] == [
        BehaviourMode.DEFENSIVE, BehaviourMode.BALANCED, BehaviourMode.OFFENSIVE,
    ]
    assert match.local_team.formation_id == 2
    assert match.visitor_team.formation_id == 3
    assert match.home_positions[74] == pytest.approx((18, 30))
    assert match.home_positions[94] == pytest.approx((86, 30))
    assert match.player_bodies[74] is match.world.players[0]
    assert match.player_bodies[92] is match.world.players[5]
    teams.matches.get_starting_players.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("invalid", ["missing", "malformed", "incomplete", "duplicate", "formation"])
def test_builder_rejects_invalid_saved_lineup(db, teams, invalid):
    if invalid == "missing":
        teams.saved.get_by_club.side_effect = lambda *_: None
    elif invalid == "malformed":
        teams.lineups[7] = []
    elif invalid == "incomplete":
        teams.lineups[7]["starters"].pop()
    elif invalid == "duplicate":
        teams.lineups[7]["starters"][0] = teams.lineups[7]["substitutes"][0]
    else:
        teams.lineups[7]["formationId"] = 999

    with pytest.raises(AppError) as error:
        service.build_match(db, 42)
    assert error.value.code == "MATCH_INVALID_LINEUP"
    db.commit.assert_not_called()


@pytest.mark.parametrize("unavailable", ["player", "behaviour"])
def test_builder_rejects_deleted_or_foreign_selections(db, teams, unavailable):
    field = "playerId" if unavailable == "player" else "behaviourId"
    # An otherwise existing ID belonging to the opponent must also be rejected.
    teams.lineups[7]["starters"][0][field] = 94 if unavailable == "player" else 902
    with pytest.raises(AppError) as error:
        service.build_match(db, 42)
    assert error.value.code == "MATCH_INVALID_LINEUP"


def test_builder_freezes_configuration_and_supports_legacy_behaviours(db, teams):
    teams.behaviours[7][2].code = LEGACY_CODE
    match = service.build_match(db, 42)
    teams.behaviours[7][2].code = DEFAULT_CODES["Ofensivo"]
    teams.lineups[7]["formationId"] = 1

    assert match.local_team.players[0].behaviour_mode == BehaviourMode.DEFENSIVE
    assert match.local_team.formation_id == 2
    assert service.build_match(db, 43).local_team.formation_id == 1


def test_builder_rejects_unsupported_behaviour_code(db, teams):
    teams.behaviours[7][2].code = "raise RuntimeError('no ejecutar')"
    with pytest.raises(AppError) as error:
        service.build_match(db, 42)
    assert error.value.code == "MATCH_INVALID_BEHAVIOUR"


@pytest.mark.parametrize("missing, code", [("match", "MATCH_NOT_FOUND"), ("visitor", "MATCH_NO_VISITOR")])
def test_missing_match_or_opponent_is_rejected_before_loading_teams(db, teams, missing, code):
    teams.matches.get_by_id.return_value = (
        None if missing == "match" else SimpleNamespace(visitor_id=None)
    )
    with pytest.raises(AppError) as error:
        service.build_match(db, 42)
    assert error.value.code == code
    teams.saved.get_by_club.assert_not_called()
