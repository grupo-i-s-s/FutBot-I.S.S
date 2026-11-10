from concurrent.futures import ThreadPoolExecutor
from datetime import timezone
from threading import Barrier

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.controller.auth_controller import auth_router
from app.controller.club_controller import club_router
from app.database import get_db
from app.dependencies import require_browser_write
from app.errors import AppError
from app.main import app_error_handler
from app.models.auth_model import Club, PendingEmailVerification
from app.repository import club_repository
from app.services import email_service
from test_league_start import database


ORIGINAL_PASSWORD = "original-password"
NEW_PASSWORD = "replacement-password"
HEADERS = {
    "Origin": next(iter(settings.allowed_origins)),
    "X-Futbot-Request": "1",
}


@pytest.fixture
def registration_api(database, monkeypatch):
    app = FastAPI(dependencies=[Depends(require_browser_write)])
    app.include_router(auth_router)
    app.include_router(club_router)
    app.add_exception_handler(AppError, app_error_handler)
    codes = {}
    monkeypatch.setattr(email_service, "send_verification_code", codes.__setitem__)

    def get_session():
        with Session(database, expire_on_commit=False) as db:
            yield db

    def restore_sqlite_timezone(pending, context):
        if context.session.get_bind() is database and pending.expires_at.tzinfo is None:
            pending.expires_at = pending.expires_at.replace(tzinfo=timezone.utc)

    app.dependency_overrides[get_db] = get_session
    event.listen(PendingEmailVerification, "load", restore_sqlite_timezone)
    try:
        with TestClient(app, headers=HEADERS) as client:
            yield client, codes
    finally:
        event.remove(PendingEmailVerification, "load", restore_sqlite_timezone)


def register(client, email, club_name, password=ORIGINAL_PASSWORD):
    return client.post("/auth/register", json={
        "email": email, "clubName": club_name, "password": password, "passwordConfirmation": password,
    })


def verify(client, email, code, **changes):
    body = {"email": email, "code": code}
    if changes:
        body["registration"] = changes
    return client.post("/auth/verify-email", json=body)


def login(client, email, password=ORIGINAL_PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def rename(client, name):
    return client.patch("/clubs/me", json={"name": name, "avatar": "avatar-01.png", "friendlyAvailable": False})


def test_verified_code_can_correct_pending_data_after_another_club_takes_the_name(registration_api):
    client, codes = registration_api
    first, second = "first@example.com", "second@example.com"
    assert register(client, first, "Talas").status_code == 202
    assert register(client, second, "Talas").status_code == 202
    assert verify(client, first, codes[first]).status_code == 200

    conflict = verify(client, second, codes[second])
    assert conflict.status_code == 400
    assert "clubName" in conflict.json()["error"]["fields"]
    for name in ("Talas", "Sauces"):
        pending = register(client, second, name, NEW_PASSWORD)
        assert pending.status_code == 409
        assert pending.json()["error"]["code"] == "EMAIL_VERIFICATION_PENDING"

    changes = {"clubName": "Sauces", "password": NEW_PASSWORD, "passwordConfirmation": NEW_PASSWORD}
    wrong_code = "000000" if codes[second] != "000000" else "000001"
    assert verify(client, second, wrong_code, **changes).status_code == 400
    assert verify(client, second, codes[second]).status_code == 400
    assert verify(client, second, codes[second], **changes).status_code == 200

    assert login(client, second).status_code == 401
    assert login(client, second, NEW_PASSWORD).status_code == 200
    assert client.get("/clubs/me").json()["name"] == "sauces"


def test_verify_and_rename_serialize_case_insensitive_name_claims(database, registration_api, monkeypatch):
    if database.dialect.name != "postgresql":
        pytest.skip("Requiere PostgreSQL para probar el bloqueo de nombres.")

    client, codes = registration_api
    owner, pending = "owner@example.com", "pending@example.com"
    assert register(client, owner, "Inicial").status_code == 202
    assert verify(client, owner, codes[owner]).status_code == 200
    assert login(client, owner).status_code == 200
    assert register(client, pending, "Los Pinos").status_code == 202

    barrier = Barrier(2, timeout=10)
    get_by_name = club_repository.get_by_name

    def synchronized_lookup(db, name, **kwargs):
        if kwargs.get("lock") and name.lower() == "los pinos":
            barrier.wait()
        return get_by_name(db, name, **kwargs)

    monkeypatch.setattr(club_repository, "get_by_name", synchronized_lookup)

    with ThreadPoolExecutor(max_workers=2) as executor:
        verifying = executor.submit(verify, client, pending, codes[pending])
        renaming = executor.submit(rename, client, "Los Pinos")
        verified = verifying.result(timeout=15)
        renamed = renaming.result(timeout=15)

    assert sorted([verified.status_code, renamed.status_code]) == [200, 400]
    rejected = verified if verified.status_code == 400 else renamed
    assert rejected.json()["error"]["code"] in {"ACCOUNT_DUPLICATE", "CLUB_NAME_DUPLICATE"}
    with Session(database) as db:
        assert db.scalar(select(func.count()).select_from(Club).where(func.lower(Club.name) == "los pinos")) == 1


def test_existing_case_collisions_preserve_current_names_and_allow_other_club_updates(database, registration_api):
    client, codes = registration_api
    first, second = "legacy-first@example.com", "legacy-second@example.com"
    assert register(client, first, "Nombre histórico").status_code == 202
    assert verify(client, first, codes[first]).status_code == 200
    assert register(client, second, "Otro nombre").status_code == 202
    second_id = verify(client, second, codes[second]).json()["clubId"]
    with Session(database) as db:
        db.get(Club, second_id).name = "Nombre histórico"
        db.commit()

    assert login(client, first).status_code == 200
    response = client.patch("/clubs/me", json={
        "name": "nombre histórico", "avatar": "avatar-02.png", "friendlyAvailable": True,
    })
    assert response.status_code == 200
    assert response.json()["avatar"] == "avatar-02.png"
    assert rename(client, "NOMBRE histórico").json()["error"]["code"] == "CLUB_NAME_DUPLICATE"
    assert rename(client, "Club sin colisión").status_code == 200
