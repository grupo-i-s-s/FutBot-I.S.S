from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.controller import api_router
from app.database import get_db
from app.dependencies import get_current_club, get_current_identity
from app.errors import AppError
from app.main import app_error_handler, validation_error_handler
from app.models.auth_model import Club
from app.models.matches_model import Matches
from test_league_start import database, league_data


BIGINT_MAX = 9_223_372_036_854_775_807


@pytest.fixture
def pagination_client(database, league_data):
    club_id, rival_id, *_ = league_data.clubs
    with Session(database) as db:
        user_id = db.get(Club, club_id).user_id
        db.get(Club, rival_id).friendly_available = True
        db.add(Matches(
            creator_id=rival_id,
            init_date=datetime.now(timezone.utc) + timedelta(hours=1),
            status="WAITING_OPPONENT",
        ))
        db.commit()

    api = FastAPI()
    api.include_router(api_router)
    api.add_exception_handler(AppError, app_error_handler)
    api.add_exception_handler(RequestValidationError, validation_error_handler)

    def database_session():
        with Session(database) as db:
            yield db

    api.dependency_overrides[get_db] = database_session
    api.dependency_overrides[get_current_club] = lambda: SimpleNamespace(id=club_id)
    api.dependency_overrides[get_current_identity] = lambda: SimpleNamespace(user_id=user_id)

    statements = []

    def capture_statement(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(database, "before_cursor_execute", capture_statement)
    try:
        with TestClient(api) as client:
            yield client, statements
    finally:
        event.remove(database, "before_cursor_execute", capture_statement)


@pytest.mark.parametrize(("path", "size_parameter"), [
    ("/players", "pageSize"),
    ("/players", "limit"),
    ("/clubs", "pageSize"),
    ("/club", "pageSize"),
    ("/friendly-matches", "pageSize"),
    ("/leagues", "pageSize"),
    ("/leagues", "limit"),
])
def test_accepts_empty_page_at_offset_limit_and_rejects_overflow(pagination_client, path, size_parameter):
    client, statements = pagination_client
    valid_page = BIGINT_MAX + 1
    response = client.get(path, params={"page": valid_page, size_parameter: 1})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["page"] == valid_page
    assert body[size_parameter] == 1
    assert body["items"] == []
    assert body["total"] > 0
    assert statements

    statements.clear()
    # La página cabe en bigint, pero su desplazamiento con tamaño 2 no.
    response = client.get(path, params={"page": BIGINT_MAX // 2 + 2, size_parameter: 2})
    assert_invalid_without_sql(response, "page", statements)


def test_offset_uses_default_size_when_only_page_is_sent_to_leagues(pagination_client):
    client, statements = pagination_client
    response = client.get("/leagues", params={"page": BIGINT_MAX // 20 + 2})
    assert_invalid_without_sql(response, "page", statements)


@pytest.mark.parametrize("size_parameter", ["pageSize", "limit"])
def test_players_accepts_hundred_items_per_page_and_rejects_larger_sizes(pagination_client, size_parameter):
    client, statements = pagination_client
    response = client.get("/players", params={size_parameter: 100})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body[size_parameter] == 100
    assert len(body["items"]) == body["total"] == 6

    statements.clear()
    for size in (101, BIGINT_MAX + 1):
        response = client.get("/players", params={size_parameter: size})
        assert_invalid_without_sql(response, size_parameter, statements)


def assert_invalid_without_sql(response, field, statements):
    assert response.status_code == 400, response.text
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert field in error["fields"]
    assert not statements
