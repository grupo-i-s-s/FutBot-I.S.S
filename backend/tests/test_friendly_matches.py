from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_club
from app.errors import AppError
from app.main import app
from app.controller import match_stream_controller
from app.repository import matches_repository
from app.services import matches_service
from app.services.match_stream_services import StreamAccess


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


def test_create_persists_authenticated_club_id():
    db = Mock()
    db.refresh.side_effect = lambda match: setattr(match, "match_id", 42)
    data = SimpleNamespace(start_datetime=datetime.now(timezone.utc) + timedelta(hours=1))

    result = matches_service.create_friendly_match(db, 7, data)

    match = db.add.call_args.args[0]
    assert match.creator_id == 7
    assert result["match_id"] == 42
    db.commit.assert_called_once()


def test_create_rejects_past_date_without_writing():
    db = Mock()
    data = SimpleNamespace(start_datetime=datetime.now(timezone.utc) - timedelta(hours=1))

    with pytest.raises(AppError) as error:
        matches_service.create_friendly_match(db, 7, data)

    assert error.value.code == "MATCH_INVALID_DATE"
    db.add.assert_not_called()


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


@pytest.mark.parametrize("match, code", [
    (None, "MATCH_NOT_FOUND"),
    (SimpleNamespace(match_id=3, creator_id=7, visitor_id=None,
                     init_date=datetime.now(timezone.utc) + timedelta(hours=1)), "MATCH_SELF_JOIN"),
    (SimpleNamespace(match_id=3, creator_id=1, visitor_id=2,
                     init_date=datetime.now(timezone.utc) + timedelta(hours=1)), "MATCH_FULL"),
    (SimpleNamespace(match_id=3, creator_id=1, visitor_id=None,
                     init_date=datetime.now(timezone.utc) - timedelta(hours=1)), "MATCH_STARTED"),
])
def test_join_rejects_invalid_matches(monkeypatch, match, code):
    db = Mock()
    monkeypatch.setattr(matches_repository, "get_by_id_for_update", lambda *_: match)

    with pytest.raises(AppError) as error:
        matches_service.join_match(db, 3, 7)

    assert error.value.code == code
    db.commit.assert_not_called()


def test_join_sets_visitor_once(monkeypatch):
    db = Mock()
    match = SimpleNamespace(
        match_id=3, creator_id=1, visitor_id=None,
        init_date=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    monkeypatch.setattr(matches_repository, "get_by_id_for_update", lambda *_: match)

    result = matches_service.join_match(db, 3, 7)

    assert match.visitor_id == 7
    assert result["match_id"] == 3
    db.commit.assert_called_once()


def test_stream_stays_open_until_client_sends_data(monkeypatch):
    monkeypatch.setattr(
        match_stream_controller, "authorize_with_db", lambda *_: StreamAccess("session")
    )

    with TestClient(app) as client:
        with client.websocket_connect(
            "/matches/3/stream",
            headers={"Origin": next(iter(settings.allowed_origins))},
        ) as socket:
            socket.send_text("unexpected input")
            with pytest.raises(WebSocketDisconnect) as error:
                socket.receive_text()

    assert error.value.code == 1008
