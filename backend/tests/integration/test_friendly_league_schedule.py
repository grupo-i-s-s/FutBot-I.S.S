from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.controller.matches_controller import matches_router
from app.database import get_db
from app.dependencies import get_current_club
from app.errors import AppError
from app.main import app_error_handler
from app.models.auth_model import Club
from app.models.league_model import League
from app.models.matches_model import Matches
from app.repository import league_repository, matches_repository
from app.services import league_fixture_service, league_service, match_start_service, matches_service
from app.services.league_round_service import generate_league_rounds
from test_league_start import database, league_data


@pytest.fixture
def agenda(database, league_data, monkeypatch, sqlite_match_dates):
    data = league_data
    start = datetime(2030, 1, 2, 20, tzinfo=timezone.utc)
    with Session(database) as db:
        league = db.get(League, data.id)
        league.start_datetime = start
        league.round_interval = "CONTINUOUS"
        league.draw_seed = 23
        rounds = generate_league_rounds(db, league)
        for club_id in data.clubs:
            db.get(Club, club_id).friendly_available = True
        db.commit()

    class Clock:
        @staticmethod
        def now(tz=None):
            return start - timedelta(hours=1)

    monkeypatch.setattr(league_service, "datetime", Clock)
    monkeypatch.setattr(matches_service, "datetime", Clock)
    app = FastAPI()
    app.include_router(matches_router)
    app.add_exception_handler(AppError, app_error_handler)

    def session():
        with Session(database) as db:
            yield db

    app.dependency_overrides[get_db] = session

    with TestClient(app) as client:
        def as_club(club_id):
            app.dependency_overrides[get_current_club] = lambda: SimpleNamespace(id=club_id)
            return client

        yield SimpleNamespace(start=start, data=data, rounds=rounds, as_club=as_club)


def create(client, start):
    return client.post("/friendly-matches", json={"startDateTime": start.isoformat()})


def start_league(database, agenda):
    with Session(database) as db:
        league_service.start_league(db, agenda.data.id, agenda.data.clubs[0])


def assert_conflict(response, start):
    assert response.status_code == 409, response.text
    assert response.json()["error"] == {
        "code": "LEAGUE_SCHEDULE_CONFLICT",
        "message": "El horario se superpone con un partido de liga confirmado.",
        "fields": {
            "conflictStart": start.isoformat(),
            "conflictEnd": (start + timedelta(minutes=6)).isoformat(),
        },
    }


def test_confirmed_league_reserves_game_and_breaks_but_not_adjacent_slots(database, agenda):
    start_league(database, agenda)
    club_id = agenda.rounds[0].pairings[0][0]
    client = agenda.as_club(club_id)

    assert_conflict(create(client, agenda.start - timedelta(minutes=5, seconds=30)), agenda.start)
    assert_conflict(create(client, agenda.start + timedelta(minutes=5, seconds=30)), agenda.start)
    assert create(client, agenda.start - timedelta(minutes=6)).status_code == 201
    assert create(client, agenda.start + timedelta(minutes=6)).status_code == 201
    bye_client = agenda.as_club(agenda.rounds[0].bye_club_id)
    assert create(bye_client, agenda.start).status_code == 201
    provisional_client = agenda.as_club(agenda.rounds[1].pairings[0][0])
    assert create(provisional_client, agenda.start + timedelta(minutes=6)).status_code == 201


@pytest.mark.parametrize("conflicting_role", ["host", "visitor"])
def test_join_rechecks_both_clubs_after_the_league_is_confirmed(database, agenda, conflicting_role):
    participant = agenda.rounds[0].pairings[0][1]
    outsider = agenda.data.clubs[3]
    host, visitor = (participant, outsider) if conflicting_role == "host" else (outsider, participant)
    match_id = create(agenda.as_club(host), agenda.start).json()["matchId"]
    start_league(database, agenda)

    response = agenda.as_club(visitor).post("/friendly-matches/join", json={"idPartido": match_id})
    assert_conflict(response, agenda.start)
    with Session(database) as db:
        match = db.get(Matches, match_id)
        assert (match.visitor_id, match.status, match.sequence) == (None, "WAITING_OPPONENT", 0)


@pytest.mark.parametrize("confirmation", ["first_round", "later_round"])
def test_friendly_reserved_before_confirmation_is_cancelled_only_at_start(database, agenda, confirmation):
    if confirmation == "first_round":
        host = agenda.rounds[0].pairings[0][0]
        friendly_at = agenda.start
    else:
        start_league(database, agenda)
        host = agenda.rounds[1].pairings[0][0]
        friendly_at = agenda.start + timedelta(minutes=12)

    match_id = create(agenda.as_club(host), friendly_at).json()["matchId"]
    response = agenda.as_club(agenda.data.clubs[3]).post("/friendly-matches/join", json={"idPartido": match_id})
    assert response.status_code == 200, response.text

    if confirmation == "first_round":
        start_league(database, agenda)
    else:
        with Session(database) as db:
            first, second, *_ = league_repository.get_fixture_rounds(db, agenda.data.id)
            assert second.schedule_confirmed is False
            for match in league_repository.get_round_matches_for_update(db, first.id):
                match.status = "FINISHED"
                match.clock_ms = match.duration_ms
                match.finished_at = agenda.start + timedelta(minutes=6)
                match.snapshot = {"state": {"status": "FINISHED"}}
            league_fixture_service.update_fixture_schedule(db, first.id)
            db.commit()
            assert second.schedule_confirmed is True

    with Session(database) as db:
        friendly = matches_repository.get_by_id_for_update(db, match_id)
        assert friendly.status == "SCHEDULED"
        assert match_start_service.prepare_match_start(db, friendly, friendly_at) is None
        db.commit()
        assert friendly.cancellation_reason == "LEAGUE_SCHEDULE_CONFLICT"
        assert friendly.snapshot["state"]["cancellationReason"] == "LEAGUE_SCHEDULE_CONFLICT"
