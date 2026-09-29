from unittest.mock import MagicMock

import pytest

from app.errors import AppError
from app.models.player_model import Player
from app.schemas.player import PlayerCreate
from app.services import player_service


def valid_payload() -> PlayerCreate:
    return PlayerCreate(
        name="Messi",
        power=60,
        agility=60,
        control=60,
        speed=60,
        strength=60,
    )


def test_create_player_success(monkeypatch):
    db = MagicMock()
    behaviour = MagicMock(id=7)

    monkeypatch.setattr(
        player_service.behaviour_repository,
        "get_default_behaviour",
        MagicMock(return_value=behaviour),
    )
    repository_create = MagicMock(side_effect=lambda db, player: player)
    monkeypatch.setattr(
        player_service.player_repository,
        "create_player",
        repository_create,
    )

    result = player_service.create_player(db=db, club_id=1, data=valid_payload())

    assert isinstance(result, Player)
    assert result.club_id == 1
    assert result.behavior_id == 7
    assert result.name == "Messi"
    repository_create.assert_called_once()
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_create_player_without_behaviour_fails(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(
        player_service.behaviour_repository,
        "get_default_behaviour",
        MagicMock(return_value=None),
    )

    with pytest.raises(AppError) as exc_info:
        player_service.create_player(db=db, club_id=1, data=valid_payload())

    assert exc_info.value.code == "ACCOUNT_INCOMPLETE"
    db.commit.assert_not_called()


def test_create_player_rolls_back_on_error(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(
        player_service.behaviour_repository,
        "get_default_behaviour",
        MagicMock(return_value=MagicMock(id=7)),
    )
    monkeypatch.setattr(
        player_service.player_repository,
        "create_player",
        MagicMock(side_effect=RuntimeError("db caida")),
    )

    with pytest.raises(RuntimeError):
        player_service.create_player(db=db, club_id=1, data=valid_payload())

    db.rollback.assert_called_once()
    db.commit.assert_not_called()
