from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.controller import api_router
from app.database import Base, get_db
from app.errors import AppError
from app.main import app_error_handler, validation_error_handler
from app.models.auth_model import AuthSession, Club, User
from app.security import hash_session_token


URL = "/clubs"
VALID_TOKEN = "v" * 43
EXPIRED_TOKEN = "e" * 43


@pytest.fixture
def client():
    # Una base nueva para cada test.
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Club.__table__,
            AuthSession.__table__,
        ],
    )

    # Insertamos los clubes desordenados para comprobar el orden de salida.
    names = [
        "Zulu",
        "River Sur",
        "100X FC",
        "ClubXA",
        "River Plate",
        "100% FC",
        "Club_A",
    ]

    now = datetime.now(timezone.utc)

    with Session(engine) as db:
        user_ids = []

        for index, name in enumerate(names):
            user = User(
                email=f"test{index}@example.com",
                password_hash="hash-de-prueba",
            )
            db.add(user)
            db.flush()
            user_ids.append(user.id)

            db.add(
                Club(
                    user_id=user.id,
                    name=name,
                    avatar="avatar-1",
                )
            )

        # Una sesión válida y otra vencida.
        for token, expiration in [
            (VALID_TOKEN, now + timedelta(hours=1)),
            (EXPIRED_TOKEN, now - timedelta(hours=1)),
        ]:
            db.add(
                AuthSession(
                    token_hash=hash_session_token(token),
                    user_id=user_ids[0],
                    created_at=now - timedelta(hours=2),
                    expires_at=expiration,
                )
            )

        db.commit()

    # Reutilizamos las rutas y los manejadores reales,
    # sin iniciar el scheduler de partidos.
    application = FastAPI()
    application.include_router(api_router)
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(
        RequestValidationError,
        validation_error_handler,
    )

    def test_database():
        with Session(engine) as db:
            yield db

    # Las peticiones usarán SQLite en lugar de PostgreSQL.
    application.dependency_overrides[get_db] = test_database

    try:
        with TestClient(
            application,
            base_url="https://testserver",
        ) as test_client:
            test_client.cookies.set(
                settings.cookie_name,
                VALID_TOKEN,
            )
            yield test_client
    finally:
        engine.dispose()

def test_lists_clubs_in_order_with_only_public_fields(client):
    response = client.get(URL)

    assert response.status_code == 200, response.text

    body = response.json()

    assert [item["name"] for item in body["items"]] == [
        "100% FC",
        "100X FC",
        "ClubXA",
        "Club_A",
        "River Plate",
        "River Sur",
        "Zulu",
    ]

    assert body["page"] == 1
    assert body["pageSize"] == 20
    assert body["total"] == 7
    assert body["hasNext"] is False

    for item in body["items"]:
        assert set(item) == {"id", "name", "avatar"}
        assert isinstance(item["id"], int)
        assert item["avatar"] == "avatar-1"
        