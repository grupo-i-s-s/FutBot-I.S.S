from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.errors import AppError
from app.services import club_services


@pytest.fixture
def repos(monkeypatch):
    clubs = Mock()
    players = Mock()

    monkeypatch.setattr(club_services, "club_repository", clubs)
    monkeypatch.setattr(club_services, "player_repository", players)

    return clubs, players


def test_returns_rival_profile_with_only_public_fields(db, repos):
    clubs, players = repos

    clubs.get_club_profile_data.return_value = {
        "id": 2,
        "name": "Club rival",
        "avatar": "avatar-01.png",
        "played": 3,
        "wins": 1,
        "draws": 1,
        "losses": 1,
        "position": 1,
        "points": 3,
        # Campos adicionales que no deben aparecer en la respuesta.
        "user_id": 20,
        "email": "privado@example.com",
    }

    players.get_players_by_club.return_value = [
        SimpleNamespace(
            id=21,
            name="Jugador rival",
            behavior_id=99,
            code="codigo_privado",
        ),
    ]

    result = club_services.get_club_profile(db, 2)
    body = result.model_dump(by_alias=True)

    assert body == {
        "id": 2,
        "name": "Club rival",
        "avatar": "avatar-01.png",
        "stats": {
            "played": 3,
            "wins": 1,
            "draws": 1,
            "losses": 1,
        },
        "ranking": {
            "position": 1,
            "points": 3,
            "source": "PUBLIC_LEAGUES",
        },
        "players": [
            {"id": 21, "name": "Jugador rival"},
        ],
    }

    clubs.get_club_profile_data.assert_called_once_with(db, 2)
    players.get_players_by_club.assert_called_once_with(db, 2)
    db.commit.assert_not_called()


def test_club_without_results_returns_zeros(db, repos):
    clubs, players = repos

    clubs.get_club_profile_data.return_value = {
        "id": 3,
        "name": "Club nuevo",
        "avatar": "avatar-01.png",
        "played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "position": 3,
        "points": 0,
    }
    players.get_players_by_club.return_value = []

    result = club_services.get_club_profile(db, 3)

    assert result.stats.model_dump() == {
        "played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
    }
    assert result.ranking.points == 0
    assert result.players == []


def test_missing_club_raises_functional_error(db, repos):
    clubs, players = repos
    clubs.get_club_profile_data.return_value = None

    with pytest.raises(AppError) as error:
        club_services.get_club_profile(db, 9999)

    assert error.value.code == "CLUB_NOT_FOUND"
    players.get_players_by_club.assert_not_called()