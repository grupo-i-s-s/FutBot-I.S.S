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


URL = "/club"
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

@pytest.mark.parametrize(
    "search, expected_names",
    [
        ("  rIvEr  ", ["River Plate", "River Sur"]),
        ("Plate", ["River Plate"]),
        ("%", ["100% FC"]),
        ("_", ["Club_A"]),
    ],
)
def test_filters_by_partial_name_and_literal_characters(
    client,
    search,
    expected_names,
):
    response = client.get(URL, params={"name": search})

    assert response.status_code == 200, response.text

    body = response.json()

    assert [item["name"] for item in body["items"]] == expected_names
    assert body["total"] == len(expected_names)


@pytest.mark.parametrize("search", ["", "   "])
def test_empty_filter_lists_all_clubs(client, search):
    response = client.get(URL, params={"name": search})

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 7
    assert len(response.json()["items"]) == 7


def test_paginates_filtered_results_and_preserves_total(client):
    collected_ids = []

    for page, expected_name, has_next in [
        (1, "River Plate", True),
        (2, "River Sur", False),
    ]:
        response = client.get(
            URL,
            params={
                "name": "river",
                "page": page,
                "pageSize": 1,
            },
        )

        assert response.status_code == 200, response.text

        body = response.json()

        assert [item["name"] for item in body["items"]] == [
            expected_name
        ]
        assert body["page"] == page
        assert body["pageSize"] == 1
        assert body["total"] == 2
        assert body["hasNext"] is has_next

        collected_ids.append(body["items"][0]["id"])

    assert len(set(collected_ids)) == 2


@pytest.mark.parametrize(
    "search, page, expected_total",
    [
        ("inexistente", 1, 0),
        ("river", 3, 2),
    ],
)
def test_returns_empty_items_when_no_results_on_page(
    client,
    search,
    page,
    expected_total,
):
    response = client.get(
        URL,
        params={
            "name": search,
            "page": page,
            "pageSize": 1,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "items": [],
        "page": page,
        "pageSize": 1,
        "total": expected_total,
        "hasNext": False,
    }


@pytest.mark.parametrize(
    "field, value",
    [
        ("page", "0"),
        ("page", "-1"),
        ("page", "abc"),
        ("page", "1.5"),
        ("pageSize", "0"),
        ("pageSize", "-1"),
        ("pageSize", "101"),
        ("pageSize", "abc"),
        ("pageSize", "1.5"),
    ],
)
def test_rejects_invalid_pagination(client, field, value):
    response = client.get(URL, params={field: value})

    assert response.status_code == 400, response.text

    error = response.json()["error"]

    assert error["code"] == "VALIDATION_ERROR"
    assert field in error["fields"]


def test_accepts_maximum_page_size(client):
    response = client.get(URL, params={"pageSize": 100})

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["pageSize"] == 100
    assert body["total"] == 7
    assert len(body["items"]) == 7
    assert body["hasNext"] is False


@pytest.mark.parametrize(
    "token",
    [None, "incorrecto", "x" * 43, EXPIRED_TOKEN],
)
def test_listing_requires_valid_session(client, token):
    client.cookies.clear()

    if token is not None:
        client.cookies.set(settings.cookie_name, token)

    response = client.get(URL)

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "SESSION_INVALID"


def test_my_club_route_is_not_captured_as_profile_id(client):
    response = client.get("/club/me")

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Zulu"
    