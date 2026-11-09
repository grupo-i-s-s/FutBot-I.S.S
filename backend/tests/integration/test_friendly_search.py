from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from test_league_start import database
from app.controller.matches_controller import matches_router
from app.database import get_db
from app.dependencies import get_current_club
from app.main import validation_error_handler
from app.models.auth_model import Club, User
from app.models.matches_model import Matches


@pytest.fixture
def search_context(database):
    now = datetime.now(timezone.utc)
    with Session(database) as db:
        clubs = []
        for index, name in enumerate(("Mi River", "River Norte", "RIVER Sur", "River inactivo", "Boca")):
            user = User(email=f"search-{index}@example.com", password_hash="unused")
            db.add(user)
            db.flush()
            club = Club(user_id=user.id, name=name, avatar="avatar-1", friendly_available=index != 3)
            db.add(club)
            db.flush()
            clubs.append(club.id)

        late = Matches(creator_id=clubs[1], init_date=now + timedelta(hours=2), status="WAITING")
        early = Matches(creator_id=clubs[1], init_date=now + timedelta(hours=1), status="WAITING_OPPONENT")
        tied = Matches(creator_id=clubs[2], init_date=early.init_date, status="WAITING")
        other = Matches(creator_id=clubs[4], init_date=now + timedelta(minutes=30), status="WAITING")
        db.add_all([late, early, tied, other])
        db.flush()
        ordered = [other.match_id, early.match_id, tied.match_id, late.match_id]
        northern = [early.match_id, late.match_id]
        southern = [tied.match_id]
        db.add_all([
            Matches(creator_id=clubs[0], init_date=early.init_date, status="WAITING"),
            Matches(creator_id=clubs[3], init_date=early.init_date, status="WAITING"),
            Matches(creator_id=clubs[1], visitor_id=clubs[0], init_date=early.init_date, status="WAITING"),
            Matches(creator_id=clubs[1], init_date=now - timedelta(hours=1), status="WAITING"),
            Matches(creator_id=clubs[1], init_date=early.init_date, status="SCHEDULED"),
            Matches(creator_id=clubs[1], init_date=early.init_date, status="RUNNING"),
            Matches(creator_id=clubs[1], init_date=early.init_date, status="FINISHED", duration_ms=1000,
                    clock_ms=1000, finished_at=now, snapshot={}),
            Matches(creator_id=clubs[1], init_date=early.init_date, status="CANCELLED", cancellation_reason="NO_OPPONENT"),
        ])
        db.commit()

    app = FastAPI()
    app.include_router(matches_router)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    def session():
        with Session(database) as db:
            yield db

    app.dependency_overrides[get_db] = session
    app.dependency_overrides[get_current_club] = lambda: SimpleNamespace(id=clubs[0])
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, clubs=clubs, ordered=ordered, northern=northern, southern=southern)


@pytest.mark.parametrize("name", [None, ""])
def test_empty_filter_preserves_available_matches_and_stable_order(search_context, name):
    response = search_context.client.get("/friendly-matches", params={} if name is None else {"creatorName": name})
    assert response.status_code == 200, response.text
    result = response.json()
    assert [item["matchId"] for item in result["items"]] == search_context.ordered
    assert (result["total"], result["page"], result["pageSize"]) == (4, 1, 20)
    assert all(set(item) == {"matchId", "creatorClubName", "startDateTime"} for item in result["items"])


@pytest.mark.parametrize("name,expected", [
    ("rIvEr", "both"), ("VER NOR", "northern"), ("sur", "southern"), ("no existe", "none"),
])
def test_partial_case_insensitive_search_keeps_availability_restrictions(search_context, name, expected):
    response = search_context.client.get("/friendly-matches", params={"creatorName": name})
    assert response.status_code == 200, response.text
    ids = {"both": search_context.ordered[1:], "northern": search_context.northern,
           "southern": search_context.southern, "none": []}
    assert [item["matchId"] for item in response.json()["items"]] == ids[expected]
    assert response.json()["total"] == len(ids[expected])


@pytest.mark.parametrize("name", ["%", "_", "%_", "/"])
def test_wildcards_and_escape_character_are_searched_literally(database, search_context, name):
    with Session(database) as db:
        db.get(Club, search_context.clubs[1]).name = "Club 100%_ /Norte"
        db.get(Club, search_context.clubs[2]).name = "Club 100XX ZNorte"
        db.commit()
    response = search_context.client.get("/friendly-matches", params={"creatorName": name})
    assert response.status_code == 200, response.text
    assert [item["matchId"] for item in response.json()["items"]] == search_context.northern
    assert response.json()["total"] == 2


@pytest.mark.parametrize("name,total", [("river", 3), ("", 4)])
def test_pagination_filters_before_counting_and_keeps_stable_order(search_context, name, total):
    collected = []
    for page in range(1, total + 1):
        response = search_context.client.get("/friendly-matches", params={
            "creatorName": name, "page": page, "pageSize": 1,
        })
        assert response.status_code == 200, response.text
        result = response.json()
        assert (result["total"], result["page"], result["pageSize"]) == (total, page, 1)
        assert len(result["items"]) == 1
        collected.append(result["items"][0]["matchId"])
    assert collected == (search_context.ordered[1:] if name else search_context.ordered)


@pytest.mark.parametrize("name,page,total", [("river", 4, 3), ("no existe", 1, 0)])
def test_empty_pages_keep_the_filtered_total(search_context, name, page, total):
    response = search_context.client.get("/friendly-matches", params={
        "creatorName": name, "page": page, "pageSize": 1,
    })
    assert response.status_code == 200, response.text
    assert response.json() == {"items": [], "total": total, "page": page, "pageSize": 1}


@pytest.mark.parametrize("field,value", [
    ("page", "0"), ("page", "-1"), ("page", "abc"), ("page", "1.5"),
    ("pageSize", "0"), ("pageSize", "-1"), ("pageSize", "101"), ("pageSize", "abc"),
])
def test_invalid_pagination_is_rejected(search_context, field, value):
    response = search_context.client.get("/friendly-matches", params={field: value})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert field in response.json()["error"]["fields"]
