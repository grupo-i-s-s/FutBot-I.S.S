import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from app.errors import AppError
from app.repository import matches_repository
from app.services import match_builder_service
from app.services.match_builder_service import build_match
from primitives.behaviours import BehaviourMode, DEFAULT_CODES, LEGACY_CODE


def roster(club_id: int, count: int = 3) -> list[tuple[SimpleNamespace, SimpleNamespace]]:
    names = ("Equilibrado", "Ofensivo", "Defensivo")
    return [
        (
            SimpleNamespace(
                id=club_id * 10 + index,
                club_id=club_id,
                name=f"Jugador {club_id}-{index}",
                speed=50 + index,
                power=60 + index,
            ),
            SimpleNamespace(
                id=club_id * 100 + index,
                name=names[index],
                code=DEFAULT_CODES[names[index]],
            ),
        )
        for index in range(count)
    ]


def test_builder_uses_clubs_from_match_and_maps_real_player_ids(monkeypatch):
    match = SimpleNamespace(creator_id=7, visitor_id=9, duration_ms=300_000)
    queried_clubs = []
    monkeypatch.setattr(matches_repository, "get_by_id", lambda db, match_id: match)

    def get_players(db, club_id):
        queried_clubs.append(club_id)
        return roster(club_id)

    monkeypatch.setattr(matches_repository, "get_starting_players", get_players)
    monkeypatch.setattr(
        matches_repository,
        "get_club_names",
        lambda db, club_ids: {7: "Local", 9: "Visitante"},
    )

    partido = build_match(Mock(), 42)

    assert partido.match_id == 42
    assert queried_clubs == [7, 9]
    assert [player.id for player in partido.player_profiles] == [70, 71, 72, 90, 91, 92]
    assert [player.club_id for player in partido.player_profiles] == [7, 7, 7, 9, 9, 9]
    assert partido.player_bodies[70] is partido.world.players[0]
    assert partido.player_bodies[92] is partido.world.players[5]
    assert [player["teamId"] for player in partido.get_players_state()] == [7, 7, 7, 9, 9, 9]
    assert [player.behaviour_mode for player in partido.local_team.players] == [
        BehaviourMode.BALANCED, BehaviourMode.OFFENSIVE, BehaviourMode.DEFENSIVE,
    ]
    assert [player.behaviour_id for player in partido.visitor_team.players] == [900, 901, 902]


def test_builder_rejects_incomplete_lineup(monkeypatch):
    monkeypatch.setattr(
        matches_repository,
        "get_by_id",
        lambda db, match_id: SimpleNamespace(creator_id=7, visitor_id=9, duration_ms=300_000),
    )
    monkeypatch.setattr(
        matches_repository,
        "get_starting_players",
        lambda db, club_id: roster(club_id, 2 if club_id == 9 else 3),
    )

    with pytest.raises(AppError) as error:
        build_match(Mock(), 42)

    assert error.value.code == "MATCH_INVALID_LINEUP"


def test_builder_freezes_assigned_behaviour_and_supports_old_defaults(monkeypatch):
    rows = {club_id: roster(club_id) for club_id in (7, 9)}
    rows[7][0][1].name = "Defensivo"
    rows[7][0][1].code = LEGACY_CODE
    monkeypatch.setattr(matches_repository, "get_by_id",
                        lambda *_: SimpleNamespace(creator_id=7, visitor_id=9, duration_ms=300_000))
    monkeypatch.setattr(matches_repository, "get_starting_players", lambda db, club_id: rows[club_id])
    monkeypatch.setattr(matches_repository, "get_club_names", lambda *_: {7: "Local", 9: "Visitante"})

    partido = build_match(Mock(), 42)
    rows[7][0][1].code = DEFAULT_CODES["Ofensivo"]

    assert partido.local_team.players[0].behaviour_mode == BehaviourMode.DEFENSIVE


def test_builder_rejects_unsupported_behaviour_code(monkeypatch):
    rows = roster(7)
    rows[0][1].code = "raise RuntimeError('no ejecutar')"
    monkeypatch.setattr(matches_repository, "get_by_id",
                        lambda *_: SimpleNamespace(creator_id=7, visitor_id=9, duration_ms=300_000))
    monkeypatch.setattr(matches_repository, "get_starting_players",
                        lambda db, club_id: rows if club_id == 7 else roster(9))
    monkeypatch.setattr(matches_repository, "get_club_names", lambda *_: {7: "Local", 9: "Visitante"})

    with pytest.raises(AppError) as error:
        build_match(Mock(), 42)

    assert error.value.code == "MATCH_INVALID_BEHAVIOUR"


@pytest.mark.parametrize("missing, code", [("match", "MATCH_NOT_FOUND"), ("visitor", "MATCH_NO_VISITOR")])
def test_builder_rejects_missing_match_or_opponent_before_loading_players(monkeypatch, missing, code):
    repository = Mock()
    repository.get_by_id.return_value = None if missing == "match" else SimpleNamespace(visitor_id=None)
    monkeypatch.setattr(match_builder_service, "matches_repository", repository)
    with pytest.raises(AppError) as error:
        match_builder_service.build_match(Mock(), 42)
    assert error.value.code == code
    repository.get_starting_players.assert_not_called()
