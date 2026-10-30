import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from types import SimpleNamespace
from unittest.mock import Mock

from app.config import settings
from app.controller import match_stream_controller
from app.database import get_db
from app.dependencies import get_current_club
from app.main import app
from app.services import matches_service
from app.services.match_stream_services import StreamAccess


@pytest.fixture(autouse=True)
def no_background_scheduler(monkeypatch):
    # Estos contratos HTTP usan repositorios simulados, sin ejecutar partidos reales.
    async def stopped_scheduler(stop_event):
        return

    monkeypatch.setattr("app.main.run_match_scheduler", stopped_scheduler)


@pytest.fixture
def match_client():
    db = Mock()
    club = SimpleNamespace(id=7)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_club] = lambda: club
    try:
        with TestClient(app) as client:
            client.headers.update({
                "Origin": next(iter(settings.allowed_origins)),
                "X-FutBot-Request": "1",
            })
            yield client, db, club
    finally:
        app.dependency_overrides.clear()


def test_create_uses_authenticated_club_and_returns_match_id(match_client, monkeypatch):
    client, db, club = match_client
    calls = []

    def create(db, club_id, data):
        calls.append((db, club_id, data))
        return {"message": "Creado", "match_id": 42}

    monkeypatch.setattr(matches_service, "create_friendly_match", create)
    start = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    response = client.post("/friendly-matches", json={"startDateTime": start})

    assert response.status_code == 201
    assert response.json() == {"message": "Creado", "matchId": 42}
    assert calls[0][0] is db
    assert calls[0][1] == club.id


def test_list_returns_available_matches(match_client, monkeypatch):
    client, db, club = match_client
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    calls = []

    def available(session, club_id):
        calls.append((session, club_id))
        return [{
            "match_id": 42,
            "creator_club_name": "Otro club",
            "start_datetime": start,
        }]

    monkeypatch.setattr(matches_service, "list_available", available)
    response = client.get("/friendly-matches")

    assert response.status_code == 200
    assert response.json() == [{
        "matchId": 42,
        "creatorClubName": "Otro club",
        "startDateTime": start.isoformat().replace("+00:00", "Z"),
    }]
    assert calls == [(db, club.id)]


def test_create_returns_readable_error_for_past_date(match_client):
    client, db, _ = match_client
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    response = client.post("/friendly-matches", json={"startDateTime": past})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MATCH_INVALID_DATE"
    db.add.assert_not_called()


def test_join_ignores_no_client_club_and_uses_authenticated_club(match_client, monkeypatch):
    client, db, club = match_client
    calls = []

    def join(session, match_id, club_id):
        calls.append((session, match_id, club_id))
        return {"message": "Unido", "match_id": match_id}

    monkeypatch.setattr(matches_service, "join_match", join)
    response = client.post("/friendly-matches/join", json={"idPartido": 42})
    spoofed = client.post(
        "/friendly-matches/join", json={"idPartido": 42, "idEquipo": 999}
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Unido", "matchId": 42}
    assert calls == [(db, 42, club.id)]
    assert spoofed.status_code == 400


def test_stream_stays_open_until_client_sends_data(monkeypatch):
    monkeypatch.setattr(
        match_stream_controller, "authorize_with_db", lambda *_: StreamAccess("session", 7)
    )
    monkeypatch.setattr(match_stream_controller, "snapshot_with_db", lambda *_: {
        "sequence": 0, "state": {"status": "WAITING"},
    })

    with TestClient(app) as client:
        with client.websocket_connect(
                "/matches/3/stream",
                headers={"Origin": next(iter(settings.allowed_origins))},
        ) as socket:
            assert socket.receive_json()["state"]["status"] == "WAITING"
            socket.send_text("unexpected input")
            with pytest.raises(WebSocketDisconnect) as error:
                socket.receive_text()

    assert error.value.code == 1008
