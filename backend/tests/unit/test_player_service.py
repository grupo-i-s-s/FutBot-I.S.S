from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.schemas.player import PlayerCreate
from app.services import player_service


def test_create_player_rejects_sum_different_from_300(monkeypatch):
    db = MagicMock()

    payload = PlayerCreate(
        name="Messi",
        power=60,
        agility=60,
        control=60,
        speed=60,
        strength=50,
    )

    with pytest.raises(HTTPException) as exc_info:
        player_service.create_player(
            db=db,
            club_id=1,
            data=payload,
        )

    assert exc_info.value.status_code == 400
    assert "300" in exc_info.value.detail


def test_create_player_success(monkeypatch):
    db = MagicMock()

    payload = PlayerCreate(
        name="Messi",
        power=60,
        agility=60,
        control=60,
        speed=60,
        strength=60,
    )

    created_player = MagicMock()
    created_player.id = 1
    created_player.club_id = 1
    created_player.name = "Messi"

    repository_create = MagicMock(return_value=created_player)
    monkeypatch.setattr(
        player_service.player_repository,
        "create",
        repository_create,
    )

    result = player_service.create_player(
        db=db,
        club_id=1,
        data=payload,
    )

    assert result.club_id == 1
    assert result.name == "Messi"
    repository_create.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(created_player)
