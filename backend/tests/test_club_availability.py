from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.auth_model import AuthSession, Club, User
from app.schemas.club_schemas import ClubAvailabilityUpdate
from app.security import hash_session_token
from app.services import club_service


HEADERS = {"Origin": next(iter(settings.allowed_origins)), "X-Futbot-Request": "1"}
TOKENS = {1: "a" * 43, 2: "b" * 43, 3: "c" * 43, 4: "d" * 43}


@pytest.fixture
def client():
    """Base aislada y una sesión nueva por petición; autenticación real por cookie."""
    test_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def enforce_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(test_engine)
    now = datetime.now(timezone.utc)
    with Session(test_engine) as db:
        for user_id, token in TOKENS.items():
            db.add(User(
                id=user_id, name=f"User {user_id}", username=f"user{user_id}",
                email=f"user{user_id}@example.com", password_hash="unused-in-this-test",
            ))
            db.flush()
            if user_id != 3:
                db.add(Club(
                    id=user_id, user_id=user_id, name=f"Club {user_id}",
                    avatar="existing-avatar", friendly_available=False,
                ))
            db.add(AuthSession(
                token_hash=hash_session_token(token), user_id=user_id,
                created_at=now - timedelta(hours=2),
                expires_at=now + timedelta(hours=-1 if user_id == 4 else 1),
            ))
        db.commit()

    def override_db():
        with Session(test_engine, expire_on_commit=False) as db:
            yield db

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as http:
            http.cookies.set(settings.cookie_name, TOKENS[1])
            yield http
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        test_engine.dispose()


def test_get_returns_only_own_public_club_fields(client):
    response = client.get("/club/me")
    assert response.status_code == 200
    assert response.json() == {
        "id": 1, "name": "Club 1", "avatar": "existing-avatar",
        "friendlyAvailable": False,
    }


def test_update_persists_both_values_without_changing_profile_or_other_club(client):
    for available in (True, False):
        response = client.patch(
            "/club/me", json={"friendlyAvailable": available}, headers=HEADERS,
        )
        assert response.status_code == 200
        expected = {
            "id": 1, "name": "Club 1", "avatar": "existing-avatar",
            "friendlyAvailable": available,
        }
        assert response.json() == expected
        # GET usa otra sesión: comprueba commit, no solo el objeto en memoria.
        assert client.get("/club/me").json() == expected
        client.cookies.set(settings.cookie_name, TOKENS[2])
        rival = client.get("/club/me").json()
        assert rival["id"] == 2
        assert rival["friendlyAvailable"] is False
        client.cookies.set(settings.cookie_name, TOKENS[1])


@pytest.mark.parametrize("payload", [
    {}, {"friendlyAvailable": None}, {"friendlyAvailable": "true"},
    {"friendlyAvailable": 1}, {"friendlyAvailable": 0},
    {"friendlyAvailable": []}, {"friendly_available": True},
    {"friendlyAvailable": True, "clubId": 2},
    {"friendlyAvailable": True, "userId": 2},
    {"friendlyAvailable": True, "name": "Changed"},
    {"friendlyAvailable": True, "avatarId": "new"},
    {"friendlyAvailable": True, "avatar": "new"},
])
def test_invalid_payload_returns_400_without_partial_changes(client, payload):
    before = client.get("/club/me").json()
    response = client.patch("/club/me", json=payload, headers=HEADERS)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(response.json()["error"]["fields"], dict)
    assert client.get("/club/me").json() == before


@pytest.mark.parametrize("method", ["GET", "PATCH"])
@pytest.mark.parametrize("token", [None, "invalid", "z" * 43, TOKENS[4]])
def test_missing_invalid_and_expired_sessions_return_401(client, method, token):
    client.cookies.clear()
    if token:
        client.cookies.set(settings.cookie_name, token)
    options = {"json": {"friendlyAvailable": True}} if method == "PATCH" else {}
    response = client.request(method, "/club/me", headers=HEADERS, **options)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_INVALID"


@pytest.mark.parametrize("headers", [
    {}, {"Origin": HEADERS["Origin"]},
    {"Origin": "https://untrusted.example", "X-Futbot-Request": "1"},
])
def test_write_requires_existing_csrf_protection(client, headers):
    response = client.patch("/club/me", json={"friendlyAvailable": True}, headers=headers)
    assert response.status_code == 403
    assert client.get("/club/me").json()["friendlyAvailable"] is False


@pytest.mark.parametrize("method", ["GET", "PATCH"])
def test_authenticated_account_without_club_returns_409(client, method):
    client.cookies.set(settings.cookie_name, TOKENS[3])
    options = {"json": {"friendlyAvailable": True}} if method == "PATCH" else {}
    response = client.request(method, "/club/me", headers=HEADERS, **options)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACCOUNT_INCOMPLETE"


def test_failed_commit_rolls_back_and_does_not_return_success(monkeypatch):
    db = Mock()
    db.commit.side_effect = RuntimeError("test commit failure")
    club = Club(id=1, user_id=1, name="Club", avatar="existing", friendly_available=False)
    monkeypatch.setattr(club_service.club_repository, "get_by_user_id", lambda *_: club)
    with pytest.raises(RuntimeError, match="test commit failure"):
        club_service.update_availability(
            db, 1, ClubAvailabilityUpdate(friendlyAvailable=True),
        )
    db.rollback.assert_called_once_with()
