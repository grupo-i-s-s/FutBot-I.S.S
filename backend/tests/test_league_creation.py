from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_club
from app.main import app
from app.repository import league_repository
from app.security import verify_password


@pytest.fixture(autouse=True)
def no_background_scheduler(monkeypatch):
    # Estos contratos HTTP usan repositorios simulados, sin ejecutar partidos reales.
    async def stopped_scheduler(stop_event):
        return

    monkeypatch.setattr("app.main.run_match_scheduler", stopped_scheduler)


@pytest.fixture
def league_client():
    db = Mock()
    # La sesión simulada debe devolver los valores generados al hacer flush.
    def generated_values():
        league = db.add.call_args.args[0]
        league.id = 42
        league.status = "open"
        for index, registration in enumerate(league.registrations, start=1):
            registration.id = index
            registration.league_id = league.id
            registration.joined_at = datetime.now(timezone.utc)

    db.flush.side_effect = generated_values
    club = SimpleNamespace(id=7, name="Club creador")
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


def league_payload():
    return {
        "name": "  Liga de prueba  ",
        "min_teams": 3,
        "max_teams": 8,
        "start_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "round_interval": "DAILY",
    }


@pytest.mark.parametrize("is_private", [False, True])
def test_creation_registers_creator_and_returns_lobby(league_client, monkeypatch, is_private):
    client, db, club = league_client
    payload = league_payload()
    if is_private:
        payload["password"] = "clave-de-la-liga"

    response = client.post(f"/leagues/{'private' if is_private else 'public'}", json=payload)

    assert response.status_code == 201
    league = db.add.call_args.args[0]
    assert league.name == "Liga de prueba"
    assert league.is_private is is_private
    assert league.creator_club_id == club.id
    assert league.start_datetime.tzinfo is not None
    assert league.round_interval == "DAILY"
    assert [registration.club_id for registration in league.registrations] == [club.id]
    if is_private:
        assert league.password_hash != payload["password"]
        assert verify_password(payload["password"], league.password_hash)
    else:
        assert league.password_hash is None
    db.commit.assert_called_once()

    # Emulate generated database values before reading the lobby.
    league.id = 42
    league.status = "open"
    registration = league.registrations[0]
    registration.id = 1
    registration.league_id = league.id
    registration.joined_at = datetime.now(timezone.utc)
    monkeypatch.setattr(league_repository, "get_league_by_id", lambda db, league_id: league)
    monkeypatch.setattr(league_repository, "get_clubs_by_ids", lambda db, club_ids: [club])

    lobby = client.get("/leagues/42/lobby")
    assert lobby.status_code == 200
    body = lobby.json()
    assert body["isPrivate"] is is_private
    assert body["creatorClub"] == {"id": club.id, "name": club.name}
    assert body["registeredTeams"] == 1
    assert body["remainingSlots"] == 7
    assert body["isRegistered"] is True
    assert "password_hash" not in body


@pytest.mark.parametrize("visibility", ["public", "private"])
def test_creation_accepts_camel_case_fields_and_normalizes_naive_date(league_client, visibility):
    client, db, _ = league_client
    response = client.post(f"/leagues/{visibility}", json={
        "name": "Liga compatible",
        "minTeams": 3,
        "maxTeams": 8,
        "startDateTime": (datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None).isoformat(),
        "roundInterval": "WEEKLY",
        "password": "clave",
    })
    assert response.status_code == 201
    assert db.add.call_args.args[0].start_datetime.tzinfo == timezone.utc


@pytest.mark.parametrize("updates", [
    {"min_teams": 2},
    {"max_teams": 2},
    {"min_teams": 9, "max_teams": 8},
    {"round_interval": "INVALID"},
    {"name": "   "},
    {"start_date": "2000-01-01T00:00:00Z"},
])
@pytest.mark.parametrize("visibility", ["public", "private"])
def test_creation_rejects_invalid_configuration(league_client, updates, visibility):
    client, db, _ = league_client
    payload = {**league_payload(), "password": "clave", **updates}
    response = client.post(f"/leagues/{visibility}", json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_private_creation_requires_password(league_client):
    client, db, _ = league_client
    response = client.post("/leagues/private", json={**league_payload(), "password": "   "})
    assert response.status_code == 400
    db.add.assert_not_called()


def test_duplicate_league_rolls_back(league_client):
    client, db, _ = league_client
    original_error = Exception("duplicate league")
    original_error.diag = SimpleNamespace(constraint_name="leagues_name_key")
    db.flush.side_effect = IntegrityError("INSERT", {}, original_error)
    response = client.post("/leagues/public", json=league_payload())
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "LEAGUE_DUPLICATE"
    db.rollback.assert_called_once()
    db.commit.assert_not_called()
