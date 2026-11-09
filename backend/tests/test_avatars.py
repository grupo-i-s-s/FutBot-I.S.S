"""Registro y edición de avatares con HTTP real y SQLite en memoria."""
from datetime import timezone
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.controller.auth_controller import auth_router
from app.controller.club_controller import club_router
from app.database import Base, get_db
from app.dependencies import require_browser_write
from app.errors import AppError
from app.main import app_error_handler, validation_error_handler
from app.models.auth_model import AuthSession, Club, PendingEmailVerification, User
from app.models.behaviour_model import Behavior
from app.models.dt_model import Dt, DtBehaviour
from app.models.player_model import Player
from app.models.team_model import DefaultTeam
from app.services import email_service


@pytest.fixture
def context(monkeypatch):
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False},
    )
    verification_codes = {}

    def capture_verification_code(email, code):
        verification_codes[email] = code

    monkeypatch.setattr(email_service, "send_verification_code", capture_verification_code)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine, tables=[
        model.__table__ for model in (
            User, Club, AuthSession, Behavior, Player, DefaultTeam,
            PendingEmailVerification, DtBehaviour, Dt,
        )
    ])

    def restore_expiration_timezone(pending, context):
        if context.session.get_bind() is engine and pending.expires_at.tzinfo is None:
            pending.expires_at = pending.expires_at.replace(tzinfo=timezone.utc)

    # SQLite no conserva la zona horaria de la expiración, PostgreSQL sí.
    event.listen(PendingEmailVerification, "load", restore_expiration_timezone)
    # Se ejercitan los routers reales sin iniciar el scheduler ni consultar PostgreSQL.
    application = FastAPI(dependencies=[Depends(require_browser_write)])
    application.include_router(auth_router)
    application.include_router(club_router)
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)

    def database():
        with Session(engine, expire_on_commit=False) as db:
            yield db

    application.dependency_overrides[get_db] = database
    try:
        with TestClient(application, base_url="https://testserver") as client:
            client.headers.update({
                "Origin": next(iter(settings.allowed_origins)),
                "X-FutBot-Request": "1",
            })
            yield SimpleNamespace(engine=engine, client=client, verification_codes=verification_codes)
    finally:
        event.remove(PendingEmailVerification, "load", restore_expiration_timezone)
        engine.dispose()


def registration(label="owner"):
    return {
        "email": f"avatar_{label}@example.com",
        "password": "avatar-test-password",
        "passwordConfirmation": "avatar-test-password",
        "clubName": f"Avatar {label}",
    }


def register_and_login(context, label="owner"):
    client = context.client
    payload = registration(label)
    email = payload["email"]
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 202, response.text
    response = client.post("/auth/verify-email", json={
        "email": email, "code": context.verification_codes[email],
    })
    assert response.status_code == 200, response.text
    club_id = response.json()["clubId"]
    response = client.post("/auth/login", json={
        "email": email, "password": payload["password"],
    })
    assert response.status_code == 200, response.text
    return club_id


def update_payload(avatar):
    return {"name": "Avatar owner", "avatar": avatar, "friendlyAvailable": True}


def test_registration_persists_default_avatar_without_client_selection(context):
    club_id = register_and_login(context)

    # Una sesión nueva verifica lo persistido, no el estado de la petición de registro.
    with Session(context.engine) as db:
        assert db.get(Club, club_id).avatar == "avatar-01.png"
    response = context.client.get("/club/me")
    assert response.status_code == 200, response.text
    assert response.json()["avatar"] == "avatar-01.png"


@pytest.mark.parametrize("avatar", ["avatar-01.png", "avatar-20.png"])
def test_registration_rejects_supplied_avatar_without_creating_account(context, avatar):
    response = context.client.post("/auth/register", json={**registration(), "avatar": avatar})

    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "avatar" in response.json()["error"]["fields"]
    with Session(context.engine) as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
        assert db.scalar(select(func.count()).select_from(Club)) == 0
        assert db.get(PendingEmailVerification, registration()["email"]) is None


def test_all_catalog_avatars_can_be_saved_and_read_back(context):
    club_id = register_and_login(context)

    for number in range(1, 21):
        filename = f"avatar-{number:02d}.png"
        response = context.client.patch("/club/me", json=update_payload(filename))
        assert response.status_code == 200, response.text
        assert response.json()["avatar"] == filename
        response = context.client.get("/club/me")
        assert response.status_code == 200, response.text
        assert response.json()["avatar"] == filename
        with Session(context.engine) as db:
            assert db.get(Club, club_id).avatar == filename


@pytest.mark.parametrize("avatar", [
    "avatar-00.png",
    "avatar-21.png",
    "avatar-1",
    "shield",
    "../avatar-01.png",
    "/avatars/avatar-01.png",
    "https://example.com/avatar-01.png",
    "avatar-01.png.exe",
    "",
    None,
])
def test_invalid_avatar_does_not_replace_saved_avatar(context, avatar):
    club_id = register_and_login(context)
    response = context.client.patch("/club/me", json=update_payload("avatar-15.png"))
    assert response.status_code == 200, response.text

    response = context.client.patch("/club/me", json=update_payload(avatar))
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "avatar" in response.json()["error"]["fields"]
    assert context.client.get("/club/me").json()["avatar"] == "avatar-15.png"
    with Session(context.engine) as db:
        assert db.get(Club, club_id).avatar == "avatar-15.png"


def test_changing_avatar_only_updates_authenticated_club(context):
    first_id = register_and_login(context, "first")
    second_id = register_and_login(context, "second")

    response = context.client.patch("/club/me", json={
        **update_payload("avatar-20.png"), "name": "Avatar second",
    })
    assert response.status_code == 200, response.text
    assert response.json()["id"] == second_id
    with Session(context.engine) as db:
        assert db.get(Club, first_id).avatar == "avatar-01.png"
        assert db.get(Club, second_id).avatar == "avatar-20.png"
