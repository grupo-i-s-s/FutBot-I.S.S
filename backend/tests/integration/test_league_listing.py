"""Verifica creación, listado y lobby en PostgreSQL sin dejar datos de prueba."""
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import uuid4

from app.config import settings
from app.database import engine, get_db
from app.main import app
from app.models.auth_model import Club, User
from app.models.league_model import League, LeagueRegistration
from app.migrate_league_passwords import migrate_league_passwords
from app.services import email_service, league_access_service


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


@pytest.fixture
def register_and_login(league_database_client, monkeypatch):
    client, _ = league_database_client
    codes = {}
    monkeypatch.setattr(email_service, "send_verification_code", codes.__setitem__)

    def register(email, club_name):
        credentials = {"email": email, "password": "password-segura"}
        response = client.post("/auth/register", json={
            **credentials, "passwordConfirmation": credentials["password"], "clubName": club_name,
        })
        assert response.status_code == 202, response.text
        response = client.post("/auth/verify-email", json={"email": email, "code": codes[email]})
        assert response.status_code == 200, response.text
        assert client.post("/auth/login", json=credentials).status_code == 200
        return response.json()["clubId"]

    return register


def test_create_list_filter_and_read_lobby_with_authenticated_club(league_database_client, register_and_login):
    client, db = league_database_client
    prefix = f"Merge {uuid4().hex[:10]}"
    email = f"{uuid4().hex}@example.com"
    club = db.get(Club, register_and_login(email, f"Club {prefix}"))
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

    # El listado general excluye estados no abiertos y ligas sin cupo, incluso
    # para sus miembros. La búsqueda interpreta % y _ como caracteres literales.
    extra_leagues = {}
    for label, state, count in (
        ("closed", "closed", 1), ("running", "running", 1), ("finished", "finished", 1),
        ("cancelled", "cancelled", 1), ("full", "open", 3),
    ):
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
        extra_leagues[label] = league
    db.commit()

    response = client.get("/leagues", params={"name": f"  {prefix.lower()}  "})
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    expected_ids = sorted((league.id for league in leagues.values()), reverse=True)
    assert [item["id"] for item in items] == expected_ids
    items_by_id = {item["id"]: item for item in items}
    for league in leagues.values():
        item = items_by_id[league.id]
        assert item["status"] == "open"
        assert item["registeredCount"] == 1
        assert item["availableSlots"] == 2
    assert all(item["isMember"] is True for item in items)
    assert all("password_hash" not in item and "password" not in item for item in items)

    memberships = client.get("/club/me/leagues")
    assert memberships.status_code == 200, memberships.text
    memberships_by_id = {item["id"]: item["status"] for item in memberships.json()["items"]}
    for league in (*leagues.values(), *extra_leagues.values()):
        assert memberships_by_id[league.id] == league.status

    for page in (1, 2, 3):
        response = client.get("/leagues", params={"name": prefix, "page": page, "limit": 1})
        assert response.status_code == 200, response.text
        assert response.json() == {
            "items": items[page - 1:page], "total": 2, "page": page, "limit": 1, "totalPages": 2,
        }
        canonical = client.get("/leagues", params={"name": prefix, "page": page, "pageSize": 1})
        assert canonical.status_code == 200, canonical.text
        assert canonical.json() == {
            "items": items[page - 1:page], "total": 2, "page": page, "pageSize": 1,
            "totalPages": 2, "hasNext": page == 1,
        }

    filtered = client.get("/leagues", params={"name": f"{prefix} private 100%_"})
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()["items"]] == [leagues["private"].id]
    assert client.get("/leagues", params={"name": f"{prefix} missing"}).json() == {"items": []}
    empty_page = client.get("/leagues", params={"name": f"{prefix} missing", "page": 1})
    assert empty_page.json() == {"items": [], "total": 0, "page": 1, "limit": 20, "totalPages": 1}

    for kind, league in leagues.items():
        response = client.get(f"/leagues/{league.id}/lobby")
        assert response.status_code == 200, response.text
        lobby = response.json()
        assert lobby["isPrivate"] is (kind == "private")
        assert lobby["creatorClub"]["id"] == club.id
        assert lobby["registeredTeams"] == 1
        assert lobby["remainingSlots"] == 2
        assert lobby["isRegistered"] is True

    for state in ("running", "finished"):
        league_id = extra_leagues[state].id
        response = client.post(f"/leagues/{league_id}/leave")
        assert response.status_code == 409, response.text
        assert db.get(League, league_id).status == state

    public_id = leagues["public"].id
    response = client.post(f"/leagues/{public_id}/leave")
    assert response.status_code == 200, response.text
    assert response.json()["leagueId"] == public_id
    response = client.get("/leagues", params={"name": f"{prefix} public"})
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert client.get(f"/leagues/{public_id}/lobby").status_code == 404


def test_listing_requires_session(league_database_client):
    client, _ = league_database_client
    response = client.get("/leagues")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_INVALID"


@pytest.mark.parametrize("kind", ["public", "private", "legacy"])
def test_join_updates_listing_and_lobby_for_newly_created_league(league_database_client, register_and_login, kind, monkeypatch):
    client, db = league_database_client
    clock = [100.0]
    monkeypatch.setattr(league_access_service, "monotonic", lambda: clock[0])
    prefix = uuid4().hex[:10]

    creator_id = register_and_login(f"{prefix}_creator@example.com", f"{prefix} creator")
    creator_line_up = client.get("/team/default").json()["lineUp"]
    name = f"Merge Join {prefix}"
    response = client.post(f"/leagues/{'private' if kind == 'private' else 'public'}", json={
        "name": name, "minTeams": 3, "maxTeams": 3,
        "startDatetime": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "roundInterval": "DAILY", "password": "clave-de-liga",
    })
    assert response.status_code == 201, response.text
    league = db.scalar(select(League).where(League.name == name))
    assert league.registrations[0].line_up == creator_line_up
    if kind == "legacy":
        league.access_code = "clave-de-liga"
        db.commit()
        migrate_league_passwords(db)
        assert league.access_code is None

    club_id = register_and_login(f"{prefix}_member@example.com", f"{prefix} member")
    line_up = client.get("/team/default").json()["lineUp"]
    payload = {"clubId": club_id, "lineUp": line_up}
    listed = client.get("/leagues", params={"name": name}).json()["items"][0]
    assert listed["isMember"] is False
    assert listed["registeredCount"] == 1

    wrong_club = client.post(f"/leagues/{league.id}/join", json={**payload, "clubId": creator_id})
    assert wrong_club.status_code == 403
    if kind in {"private", "legacy"}:
        for access in ({}, {"accessCode": "incorrecto"}):
            response = client.post(f"/leagues/{league.id}/join", json={**payload, **access})
            assert response.status_code == 409
        payload["accessCode"] = "clave-de-liga"

    response = client.post(f"/leagues/{league.id}/join", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["clubId"] == club_id
    registration = db.scalar(select(LeagueRegistration).where(
        LeagueRegistration.league_id == league.id, LeagueRegistration.club_id == club_id,
    ))
    assert registration.line_up == line_up
    assert registration.joined_at.tzinfo is not None
    assert client.post(f"/leagues/{league.id}/join", json=payload).status_code == 409
    listed = client.get("/leagues", params={"name": name}).json()["items"][0]
    assert listed["isMember"] is True
    assert listed["registeredCount"] == 2
    assert listed["availableSlots"] == 1
    lobby = client.get(f"/leagues/{league.id}/lobby").json()
    assert lobby["registeredTeams"] == 2
    assert lobby["isRegistered"] is True
    assert {club["id"] for club in lobby["clubs"]} == {creator_id, club_id}
    assert client.post(f"/leagues/{league.id}/leave").status_code == 200
    assert client.get("/leagues", params={"name": name}).json()["items"][0]["isMember"] is False
    league.status = "closed"
    db.commit()
    assert client.get("/leagues", params={"name": name}).json() == {"items": []}
    assert client.post(f"/leagues/{league.id}/join", json=payload).status_code == 409
    league.status = "open"
    league.start_datetime = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()
    assert client.get("/leagues", params={"name": name}).json()["items"][0]["id"] == league.id
    # Este flujo ya hizo cinco intentos; la nueva inscripción ocurre un minuto después.
    clock[0] += 60
    assert client.post(f"/leagues/{league.id}/join", json=payload).status_code == 201
    assert client.post(f"/leagues/{league.id}/leave").status_code == 200
    assert client.post("/auth/logout").status_code == 204
    assert client.post(f"/leagues/{league.id}/join", json=payload).status_code == 401
