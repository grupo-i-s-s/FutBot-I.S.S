from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import os
from threading import Barrier
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_league_start import database, league_data
from app.controller.league_controller import league_router
from app.database import get_db
from app.dependencies import get_current_club
from app.errors import AppError
from app.main import app_error_handler
from app.models.behaviour_model import Behavior
from app.models.league_model import League, LeagueRegistration
from app.models.team_model import DefaultTeam
from app.security import hash_password
from app.services import league_access_service, league_service


@pytest.fixture
def private_league(database, league_data):
    with Session(database) as db:
        league = db.get(League, league_data.id)
        league.is_private = True
        league.password_hash = hash_password("league-password")
        db.commit()
    return league_data


@pytest.fixture
def client(database, private_league):
    app = FastAPI()
    app.include_router(league_router)
    app.add_exception_handler(AppError, app_error_handler)

    def session():
        with Session(database) as db:
            yield db

    app.dependency_overrides[get_db] = session
    app.dependency_overrides[get_current_club] = lambda: SimpleNamespace(id=private_league.clubs[3])
    with TestClient(app) as client:
        yield client


def payload(data, password="league-password"):
    return {"clubId": data.clubs[3], "lineUp": data.lineups[3], "accessCode": password}


def test_wrong_and_missing_password_share_error_and_do_not_consume_slot(client, database, private_league):
    data = private_league
    url = f"/leagues/{data.id}/join"
    missing = client.post(url, json=payload(data, None))
    wrong = client.post(url, json=payload(data, "wrong-secret"))
    assert missing.status_code == wrong.status_code == 409
    assert missing.json() == wrong.json()
    assert wrong.json()["error"]["code"] == "LEAGUE_ACCESS_INVALID"
    assert "wrong-secret" not in wrong.text
    with Session(database) as db:
        assert len(db.get(League, data.id).registrations) == 3
    assert client.post(url, json=payload(data)).status_code == 201
    with Session(database) as db:
        assert len(db.get(League, data.id).registrations) == 4


def test_sixth_attempt_is_limited_even_with_correct_password_then_expires(
        client, database, private_league, monkeypatch):
    data = private_league
    clock = [100.0]
    monkeypatch.setattr(league_access_service, "monotonic", lambda: clock[0])
    url = f"/leagues/{data.id}/join"
    for _ in range(5):
        assert client.post(url, json=payload(data, "wrong")).status_code == 409
    response = client.post(url, json=payload(data))
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    assert response.json()["error"]["fields"]["retryAfter"] == "60"
    with Session(database) as db:
        assert len(db.get(League, data.id).registrations) == 3
    clock[0] += 60
    assert client.post(url, json=payload(data)).status_code == 201


@pytest.mark.parametrize("invalid", ["closed", "full", "registered", "foreign_player"])
def test_correct_password_still_checks_league_and_player_ownership(
        client, database, private_league, invalid):
    data = private_league
    body = payload(data)
    codes = {"closed": "LEAGUE_CLOSED", "full": "LEAGUE_FULL", "registered": "ALREADY_REGISTERED"}
    if invalid in codes:
        with Session(database) as db:
            league = db.get(League, data.id)
            if invalid == "closed":
                league.status = "running"
            elif invalid == "full":
                league.max_teams = 3
            else:
                league.max_teams = 5
                db.add(LeagueRegistration(league_id=data.id, club_id=data.clubs[3], line_up=data.lineups[3]))
            db.commit()
    else:
        body["lineUp"] = data.lineups[0]
    response = client.post(f"/leagues/{data.id}/join", json=body)
    assert response.status_code == (409 if invalid in codes else 400)
    if invalid in codes:
        assert response.json()["error"]["code"] == codes[invalid]
    with Session(database) as db:
        assert len(db.get(League, data.id).registrations) == (4 if invalid == "registered" else 3)


def test_public_league_does_not_apply_password_attempt_limit(client, database, private_league):
    data = private_league
    with Session(database) as db:
        league = db.get(League, data.id)
        league.is_private, league.password_hash = False, None
        db.commit()
    body = payload(data)
    body["lineUp"] = []
    for _ in range(6):
        assert client.post(f"/leagues/{data.id}/join", json=body).status_code == 400
    assert client.post(f"/leagues/{data.id}/join", json=payload(data)).status_code == 201


@pytest.mark.parametrize("case, expected", [
    ("valid", None),
    ("stale", "LEAGUE_LINEUP_CHANGED"),
    ("formation", "LEAGUE_LINEUP_INVALID"),
    ("foreign_behaviour", "LEAGUE_LINEUP_INVALID"),
    ("deleted_behaviour", "LEAGUE_LINEUP_INVALID"),
    ("invalid_behaviour", "LEAGUE_LINEUP_INVALID"),
])
def test_join_validates_and_persists_complete_default_team(client, database, private_league, case, expected):
    data = private_league
    club_id = data.clubs[3]
    with Session(database) as db:
        lineup = deepcopy(db.get(DefaultTeam, club_id).line_up)
        if case == "formation":
            lineup["formationId"] = 9999
        elif case == "stale":
            lineup["starters"].reverse()
        elif case == "foreign_behaviour":
            lineup["starters"][0]["behaviourId"] = db.get(DefaultTeam, data.clubs[0]).line_up["starters"][0]["behaviourId"]
        elif case == "deleted_behaviour":
            db.get(Behavior, lineup["starters"][0]["behaviourId"]).is_deleted = True
        elif case == "invalid_behaviour":
            db.get(Behavior, lineup["starters"][0]["behaviourId"]).code = "import os"
        db.commit()

    response = client.post(f"/leagues/{data.id}/join", json={**payload(data), "lineUp": lineup})
    if expected:
        assert response.status_code == 409
        assert response.json()["error"]["code"] == expected
    else:
        assert response.status_code == 201, response.text

    with Session(database) as db:
        registration = db.scalar(select(LeagueRegistration).where(
            LeagueRegistration.league_id == data.id,
            LeagueRegistration.club_id == club_id,
        ))
        if expected:
            assert registration is None
        else:
            assert registration.line_up == lineup
            default_team = db.get(DefaultTeam, club_id)
            default_team.line_up = {**default_team.line_up, "formationId": 2}
            db.commit()
            assert registration.line_up == lineup


@pytest.mark.skipif(not os.getenv("LEAGUE_TEST_DATABASE_URL"), reason="Requiere PostgreSQL")
def test_two_valid_passwords_compete_for_last_slot(database, private_league):
    data = private_league
    with Session(database) as db:
        db.delete(db.scalar(select(LeagueRegistration).where(
            LeagueRegistration.league_id == data.id,
            LeagueRegistration.club_id == data.clubs[2],
        )))
        db.get(League, data.id).max_teams = 3
        db.commit()

    barrier = Barrier(2, timeout=10)

    def join(index):
        with Session(database) as db:
            barrier.wait()
            try:
                league_service.join_league(
                    db, data.id, data.clubs[index], data.lineups[index], "league-password",
                )
                return 201
            except AppError as error:
                assert error.code == "LEAGUE_FULL"
                db.rollback()
                return 409

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(join, [2, 3])) == [201, 409]
    with Session(database) as db:
        registrations = db.get(League, data.id).registrations
        assert len(registrations) == 3
        assert sum(row.club_id in data.clubs[2:] for row in registrations) == 1
