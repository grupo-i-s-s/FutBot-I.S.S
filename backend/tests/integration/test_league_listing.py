"""Verifica creación, listado y lobby en PostgreSQL sin dejar datos de prueba."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.main import app
from app.models.auth_model import Club, User
from app.models.league_model import League, LeagueRegistration


@pytest.fixture
def league_database_client():
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            app.dependency_overrides[get_db] = lambda: db
            try:
                with TestClient(app) as client:
                    client.headers.update({
                        "Origin": next(iter(settings.allowed_origins)),
                        "X-FutBot-Request": "1",
                    })
                    yield client, db
            finally:
                app.dependency_overrides.clear()
        transaction.rollback()


def test_create_list_filter_and_read_lobby_with_authenticated_club(league_database_client):
    client, db = league_database_client
    prefix = f"Merge {uuid4().hex[:10]}"
    email = f"{uuid4().hex}@example.com"
    credentials = {"email": email, "password": "password-segura"}
    response = client.post("/auth/register", json={
        **credentials,
        "passwordConfirmation": credentials["password"],
        "clubName": f"Club {prefix}",
        "avatar": "avatar-1",
    })
    assert response.status_code == 201, response.text
    assert client.post("/auth/login", json=credentials).status_code == 200
    club = db.scalar(select(Club).join(User).where(User.email == email))
    payload = {
        "minTeams": 3,
        "maxTeams": 3,
        "startDatetime": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "roundInterval": "DAILY",
    }
    leagues = {}
    for kind in ("public", "private"):
        name = f"{prefix} {kind} 100%_"
        response = client.post(f"/leagues/{kind}", json={
            **payload, "name": name, "password": "clave-de-liga",
        })
        assert response.status_code == 201, response.text
        leagues[kind] = db.scalar(select(League).where(League.name == name))

    # Excluir las ligas cerradas y llenas; buscar % y _ como caracteres literales.
    for label, state, count in (("closed", "closed", 1), ("full", "open", 3)):
        league = League(
            name=f"{prefix} {label}", min_teams=3, max_teams=3,
            start_datetime=datetime.now(timezone.utc) + timedelta(days=1),
            round_interval="DAILY", status=state, creator_club_id=club.id,
        )
        league.registrations.append(LeagueRegistration(club_id=club.id))
        for index in range(count - 1):
            user = User(email=f"{uuid4().hex}@example.com", password_hash="unused")
            db.add(user)
            db.flush()
            other_club = Club(user_id=user.id, name=f"{prefix} {label} {index}", avatar="avatar-1")
            db.add(other_club)
            db.flush()
            league.registrations.append(LeagueRegistration(club_id=other_club.id))
        db.add(league)
    db.commit()

    response = client.get("/leagues", params={"name": f"  {prefix.lower()}  "})
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert {item["id"] for item in items} == {league.id for league in leagues.values()}
    assert all(item["registeredCount"] == 1 for item in items)
    assert all(item["availableSlots"] == 2 for item in items)
    assert all(item["isMember"] is True for item in items)
    assert all("password_hash" not in item and "password" not in item for item in items)

    filtered = client.get("/leagues", params={"name": f"{prefix} private 100%_"})
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()["items"]] == [leagues["private"].id]
    assert client.get("/leagues", params={"name": f"{prefix} missing"}).json() == {"items": []}

    for kind, league in leagues.items():
        response = client.get(f"/leagues/{league.id}/lobby")
        assert response.status_code == 200, response.text
        lobby = response.json()
        assert lobby["isPrivate"] is (kind == "private")
        assert lobby["creatorClub"]["id"] == club.id
        assert lobby["registeredTeams"] == 1
        assert lobby["remainingSlots"] == 2
        assert lobby["isRegistered"] is True

    public_id = leagues["public"].id
    response = client.post(f"/leagues/{public_id}/leave")
    assert response.status_code == 200, response.text
    assert response.json()["leagueId"] == public_id
    response = client.get("/leagues", params={"name": f"{prefix} public"})
    assert response.status_code == 200
    assert response.json()["items"][0]["registeredCount"] == 0
    assert response.json()["items"][0]["availableSlots"] == 3
    assert response.json()["items"][0]["isMember"] is False
    assert client.get(f"/leagues/{public_id}/lobby").json()["isRegistered"] is False


def test_listing_requires_session(league_database_client):
    client, _ = league_database_client
    response = client.get("/leagues")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_INVALID"
