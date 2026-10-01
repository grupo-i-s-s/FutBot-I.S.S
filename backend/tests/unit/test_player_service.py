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


def test_assign_behaviour_updates_player_in_own_club(monkeypatch):
    db = MagicMock()
    player = MagicMock(id=11, club_id=3)
    behaviour = MagicMock(id=7, club_id=3)
    get_player = MagicMock(return_value=player)
    get_behaviour = MagicMock(return_value=behaviour)
    set_behaviour = MagicMock()
    monkeypatch.setattr(player_service.player_repository, "get_player_by_id", get_player)
    monkeypatch.setattr(player_service.behaviour_repository, "get_behaviour_by_id", get_behaviour)
    monkeypatch.setattr(player_service.player_repository, "set_player_behaviour", set_behaviour)

    result = player_service.assign_behaviour(db, club_id=3, player_id=11, behaviour_id=7)

    assert result is player
    get_player.assert_called_once_with(db, 3, 11)
    get_behaviour.assert_called_once_with(db, 3, 7)
    set_behaviour.assert_called_once_with(db, player, 7)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(player)


@pytest.mark.parametrize(
    ("missing", "code"),
    [("player", "PLAYER_NOT_FOUND"), ("behaviour", "BEHAVIOUR_NOT_FOUND")],
)
def test_assign_behaviour_rejects_missing_or_foreign_entities(monkeypatch, missing, code):
    db = MagicMock()
    monkeypatch.setattr(
        player_service.player_repository,
        "get_player_by_id",
        MagicMock(return_value=None if missing == "player" else MagicMock(id=11)),
    )
    monkeypatch.setattr(
        player_service.behaviour_repository,
        "get_behaviour_by_id",
        MagicMock(return_value=None if missing == "behaviour" else MagicMock(id=7)),
    )
    set_behaviour = MagicMock()
    monkeypatch.setattr(player_service.player_repository, "set_player_behaviour", set_behaviour)

    with pytest.raises(AppError) as exc_info:
        player_service.assign_behaviour(db, club_id=3, player_id=11, behaviour_id=7)

    assert exc_info.value.code == code
    set_behaviour.assert_not_called()
    db.commit.assert_not_called()


def test_assign_behaviour_rolls_back_failed_write(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(
        player_service.player_repository, "get_player_by_id", MagicMock(return_value=MagicMock(id=11))
    )
    monkeypatch.setattr(
        player_service.behaviour_repository, "get_behaviour_by_id", MagicMock(return_value=MagicMock(id=7))
    )
    monkeypatch.setattr(
        player_service.player_repository,
        "set_player_behaviour",
        MagicMock(side_effect=RuntimeError("database error")),
    )

    with pytest.raises(RuntimeError):
        player_service.assign_behaviour(db, club_id=3, player_id=11, behaviour_id=7)

    db.rollback.assert_called_once()
    db.commit.assert_not_called()
