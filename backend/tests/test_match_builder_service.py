from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.errors import AppError
from app.repository import matches_repository
from app.services.match_builder_service import build_match


def roster(club_id: int, count: int = 3) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            id=club_id * 10 + index,
            club_id=club_id,
            name=f"Jugador {club_id}-{index}",
            speed=50 + index,
            power=60 + index,
        )
        for index in range(count)
    ]


def test_builder_uses_clubs_from_match_and_maps_real_player_ids(monkeypatch):
    match = SimpleNamespace(creator_id=7, visitor_id=9)
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

    assert queried_clubs == [7, 9]
    assert [player.id for player in partido.player_profiles] == [70, 71, 72, 90, 91, 92]
    assert [player.club_id for player in partido.player_profiles] == [7, 7, 7, 9, 9, 9]
    assert partido.player_bodies[70] is partido.world.players[0]
    assert partido.player_bodies[92] is partido.world.players[5]
    assert [player["teamId"] for player in partido.get_players_state()] == [7, 7, 7, 9, 9, 9]


def test_builder_rejects_incomplete_lineup(monkeypatch):
    monkeypatch.setattr(
        matches_repository,
        "get_by_id",
        lambda db, match_id: SimpleNamespace(creator_id=7, visitor_id=9),
    )
    monkeypatch.setattr(
        matches_repository,
        "get_starting_players",
        lambda db, club_id: roster(club_id, 2 if club_id == 9 else 3),
    )

    with pytest.raises(AppError) as error:
        build_match(Mock(), 42)

    assert error.value.code == "MATCH_INVALID_LINEUP"
