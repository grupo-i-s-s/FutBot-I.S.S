from fastapi.testclient import TestClient

from app.config import settings
from app.dependencies import get_current_club
from app.main import app
from app.models.auth_model import Club
from app.models.player_model import Player
from app.services import player_service

BROWSER_HEADERS = {
    "Origin": next(iter(settings.allowed_origins)),
    "X-Futbot-Request": "1",
}


def mock_get_current_club() -> Club:
    return Club(id=1, user_id=1, name="Club Test", avatar="avatar.png")


def post_player(json: dict):
    app.dependency_overrides[get_current_club] = mock_get_current_club
    try:
        with TestClient(app) as client:
            return client.post("/players", json=json, headers=BROWSER_HEADERS)
    finally:
        app.dependency_overrides.clear()


def patch_player_behaviour(json: dict):
    app.dependency_overrides[get_current_club] = mock_get_current_club
    try:
        with TestClient(app) as client:
            return client.patch("/players/1/behaviour", json=json, headers=BROWSER_HEADERS)
    finally:
        app.dependency_overrides.clear()


def test_create_player_endpoint_success(monkeypatch):
    created_player = Player(
        id=1,
        club_id=1,
        behavior_id=1,
        name="Dibu Martinez",
        power=60,
        agility=60,
        control=60,
        speed=60,
        strength=60,
    )
    monkeypatch.setattr(
        player_service,
        "create_player",
        lambda db, club_id, data: created_player,
    )

    response = post_player({
        "name": "Dibu Martinez",
        "power": 60,
        "agility": 60,
        "control": 60,
        "speed": 60,
        "strength": 60,
    })

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["clubId"] == 1
    assert data["behaviorId"] == 1
    assert data["name"] == "Dibu Martinez"
    for attribute in ("power", "agility", "control", "speed", "strength"):
        assert data[attribute] == 60


def test_create_player_rejects_out_of_range_pacss():
    response = post_player({
        "name": "Invalido",
        "power": 10,
        "agility": 75,
        "control": 75,
        "speed": 70,
        "strength": 70,
    })

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_player_rejects_sum_different_from_300():
    response = post_player({
        "name": "Invalido",
        "power": 60,
        "agility": 60,
        "control": 60,
        "speed": 60,
        "strength": 50,
    })

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "300" in error["fields"]["form"]


def test_create_player_rejects_boolean_or_float():
    response = post_player({
        "name": "Invalido",
        "power": True,
        "agility": 60.5,
        "control": 60,
        "speed": 60,
        "strength": 60,
    })

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_player_requires_session():
    with TestClient(app) as client:
        response = client.post(
            "/players",
            json={
                "name": "Sin sesion",
                "power": 60,
                "agility": 60,
                "control": 60,
                "speed": 60,
                "strength": 60,
            },
            headers=BROWSER_HEADERS,
        )

    assert response.status_code == 401


def test_assign_behaviour_endpoint_returns_updated_player(monkeypatch):
    updated_player = Player(
        id=1, club_id=1, behavior_id=7, name="Dibu Martinez",
        power=60, agility=60, control=60, speed=60, strength=60,
    )
    calls = []

    def fake_assign(db, club_id, player_id, behaviour_id):
        calls.append((club_id, player_id, behaviour_id))
        return updated_player

    monkeypatch.setattr(player_service, "assign_behaviour", fake_assign)
    response = patch_player_behaviour({"behaviourId": 7})

    assert response.status_code == 200
    assert response.json()["behaviorId"] == 7
    assert calls == [(1, 1, 7)]


def test_assign_behaviour_rejects_invalid_input():
    response = patch_player_behaviour({"behaviourId": 0})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

def get_players():
    app.dependency_overrides[get_current_club] = mock_get_current_club
    try:
        with TestClient(app) as client:
            return client.get("/players", headers=BROWSER_HEADERS)
    finally:
        app.dependency_overrides.clear()


def test_get_players_returns_players_from_service(monkeypatch):
    players = [
        Player(
            id=1,
            club_id=1,
            behavior_id=1,
            name="Dibu Martinez",
            power=60,
            agility=60,
            control=60,
            speed=60,
            strength=60,
        )
    ]

    monkeypatch.setattr(
        player_service,
        "get_players",
        lambda db, club_id: players,
    )

    response = get_players()

    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == 1
    assert data["items"][0]["clubId"] == 1
    assert data["items"][0]["behaviorId"] == 1
    assert data["items"][0]["name"] == "Dibu Martinez"

    for attribute in ("power", "agility", "control", "speed", "strength"):
        assert data["items"][0][attribute] == 60


def test_get_players_returns_empty_list_when_club_has_no_players(monkeypatch):
    monkeypatch.setattr(
        player_service,
        "get_players",
        lambda db, club_id: [],
    )

    response = get_players()

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_get_players_requires_session():
    with TestClient(app) as client:
        response = client.get(
            "/players",
            headers=BROWSER_HEADERS,
        )

    assert response.status_code == 401

def test_get_players_only_returns_players_from_current_club(monkeypatch):
    club_players = [
        Player(
            id=1,
            club_id=1,
            behavior_id=1,
            name="Jugador Club 1",
            power=60,
            agility=60,
            control=60,
            speed=60,
            strength=60,
        )
    ]

    def fake_get_players(db, club_id):
        assert club_id == 1
        return club_players

    monkeypatch.setattr(player_service, "get_players", fake_get_players)

    response = get_players()

    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["clubId"] == 1

def test_get_players_includes_created_player(monkeypatch):
    created_player = Player(
        id=2,
        club_id=1,
        behavior_id=1,
        name="Jugador Nuevo",
        power=60,
        agility=60,
        control=60,
        speed=60,
        strength=60,
    )

    monkeypatch.setattr(
        player_service,
        "create_player",
        lambda db, club_id, data: created_player,
    )
    monkeypatch.setattr(
        player_service,
        "get_players",
        lambda db, club_id: [created_player],
    )

    create_response = post_player({
        "name": "Jugador Nuevo",
        "power": 60,
        "agility": 60,
        "control": 60,
        "speed": 60,
        "strength": 60,
    })

    assert create_response.status_code == 201

    list_response = get_players()

    assert list_response.status_code == 200

    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == 2
    assert items[0]["clubId"] == 1
    assert items[0]["name"] == "Jugador Nuevo"
