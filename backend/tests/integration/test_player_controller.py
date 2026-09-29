
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.dependencies import get_current_user_and_club
from app.main import app
from app.models.auth_model import Club, User
from app.models.player import Player
from app.services import player_service


def mock_get_current_user_and_club():
    dummy_user = User(
        id=1,
        name="Test User",
        email="test@example.com",
        username="testuser",
        password_hash="dummy",
    )

    dummy_club = Club(
        id=1,
        user_id=1,
        name="Club Test",
        avatar="avatar.png",
    )

    return dummy_user, dummy_club


def test_create_player_endpoint_success(monkeypatch):
    created_player = Player(
        id=1,
        club_id=1,
        name="Dibu Martinez",
        power=60,
        agility=60,
        control=60,
        speed=60,
        strength=60,
    )

    def mock_create_player(db, club_id, data):
        return created_player

    monkeypatch.setattr(
        player_service,
        "create_player",
        mock_create_player,
    )

    app.dependency_overrides[get_current_user_and_club] = (
        mock_get_current_user_and_club
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/players",
                json={
                    "name": "Dibu Martinez",
                    "power": 60,
                    "agility": 60,
                    "control": 60,
                    "speed": 60,
                    "strength": 60,
                },
            )

        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Dibu Martinez"
        assert data["clubId"] == 1
        assert data["power"] == 60
        assert data["agility"] == 60
        assert data["control"] == 60
        assert data["speed"] == 60
        assert data["strength"] == 60
        assert data["id"] == 1

    finally:
        app.dependency_overrides.clear()


def test_create_player_rejects_out_of_range_pacss():
    app.dependency_overrides[get_current_user_and_club] = (
        mock_get_current_user_and_club
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/players",
                json={
                    "name": "Invalido",
                    "power": 10,
                    "agility": 75,
                    "control": 75,
                    "speed": 70,
                    "strength": 70,
                },
            )

        assert response.status_code in (400, 422)

    finally:
        app.dependency_overrides.clear()


def test_create_player_rejects_sum_different_from_300():
    app.dependency_overrides[get_current_user_and_club] = (
        mock_get_current_user_and_club
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/players",
                json={
                    "name": "Invalido",
                    "power": 60,
                    "agility": 60,
                    "control": 60,
                    "speed": 60,
                    "strength": 50,
                },
            )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_create_player_rejects_boolean_or_float():
    app.dependency_overrides[get_current_user_and_club] = (
        mock_get_current_user_and_club
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/players",
                json={
                    "name": "Invalido",
                    "power": True,
                    "agility": 60.5,
                    "control": 60,
                    "speed": 60,
                    "strength": 60,
                },
            )

        assert response.status_code in (400, 422)

    finally:
        app.dependency_overrides.clear()
