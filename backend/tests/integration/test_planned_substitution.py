from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import os
from threading import Barrier
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_league_start import database, league_data
from app.controller.planned_substitution_controller import planned_substitution_router
from app.database import get_db
from app.dependencies import get_current_club
from app.errors import AppError
from app.main import app_error_handler
from app.models.matches_model import Matches
from app.models.planned_substitution_model import PlannedSubstitution
from app.models.team_model import DefaultTeam
from app.repository import matches_repository
from app.schemas.matches_schemas import PlannedSubstitutionRequest
from app.services.match_builder_service import build_match
from app.services.planned_substitution_service import plan_substitution
from primitives.match_simulation import Match


@pytest.fixture
def running_match(database, league_data):
    now = datetime.now(timezone.utc)
    with Session(database) as db:
        row = Matches(creator_id=league_data.clubs[0], visitor_id=league_data.clubs[1], init_date=now)
        db.add(row)
        db.flush()
        simulation = build_match(db, row.match_id)
        matches_repository.save_progress(db, row, simulation, simulation.snapshot(1, now.isoformat()), now)
        db.commit()
        return row.match_id


@pytest.fixture
def api(database, league_data, running_match):
    app = FastAPI()
    app.include_router(planned_substitution_router)
    app.add_exception_handler(AppError, app_error_handler)
    club = [league_data.clubs[0]]

    def session():
        with Session(database) as db:
            yield db

    app.dependency_overrides[get_db] = session
    app.dependency_overrides[get_current_club] = lambda: SimpleNamespace(id=club[0])
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, club=club, url=f"/matches/{running_match}/planned-substitution")


def body(data, command="change-1", club=0):
    return {"outPlayerId": data.lineups[club][0], "inPlayerId": data.lineups[club][3], "commandId": command}


def plans(db):
    return db.scalars(select(PlannedSubstitution).order_by(PlannedSubstitution.id)).all()


def test_plan_is_persisted_without_changing_match(api, database, league_data, running_match):
    with Session(database) as db:
        row = db.get(Matches, running_match)
        before = deepcopy((row.runtime_state, row.snapshot, row.sequence))
    response = api.client.put(api.url, json=body(league_data))
    assert response.status_code == 200, response.text
    assert response.json() == {**body(league_data), "pauseId": f"{running_match}:1", "status": "PENDING"}
    with Session(database) as db:
        row = db.get(Matches, running_match)
        assert (row.runtime_state, row.snapshot, row.sequence) == before
        assert len(plans(db)) == 1
        assert plans(db)[0].club_id == league_data.clubs[0]


def test_replacement_and_retries_never_restore_an_old_plan(api, database, league_data):
    first = body(league_data)
    second = {**body(league_data, "change-2"), "inPlayerId": league_data.lineups[0][4]}
    assert api.client.put(api.url, json=first).status_code == 200
    confirmed = api.client.put(api.url, json=second).json()
    assert api.client.put(api.url, json=second).json() == confirmed
    assert api.client.put(api.url, json=first).json()["status"] == "REPLACED"
    conflict = api.client.put(api.url, json={**second, "inPlayerId": league_data.lineups[0][5]})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "SUBSTITUTION_COMMAND_CONFLICT"
    with Session(database) as db:
        saved = plans(db)
        assert [row.status for row in saved] == ["REPLACED", "PENDING"]
        assert saved[1].in_player_id == second["inPlayerId"]


@pytest.mark.parametrize("out_club,out_index,in_club,in_index", [
    (1, 0, 0, 3), (0, 0, 1, 3), (0, 3, 0, 4), (0, 0, 0, 1),
])
def test_rejects_foreign_players_and_wrong_roles(api, database, league_data, out_club, out_index, in_club, in_index):
    payload = {**body(league_data), "outPlayerId": league_data.lineups[out_club][out_index],
               "inPlayerId": league_data.lineups[in_club][in_index]}
    response = api.client.put(api.url, json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SUBSTITUTION_INVALID_PLAYERS"
    with Session(database) as db:
        assert plans(db) == []


def test_each_participant_can_plan_independently_but_outsider_cannot(api, database, league_data):
    assert api.client.put(api.url, json=body(league_data)).status_code == 200
    api.club[0] = league_data.clubs[1]
    assert api.client.put(api.url, json=body(league_data, club=1)).status_code == 200
    with Session(database) as db:
        assert {plan.club_id for plan in plans(db)} == set(league_data.clubs[:2])
    api.club[0] = league_data.clubs[2]
    assert api.client.put(api.url, json=body(league_data, club=2)).status_code == 403
    assert api.client.put("/matches/999999/planned-substitution", json=body(league_data)).status_code == 404


def test_invalid_replacement_preserves_confirmed_plan(api, database, league_data):
    assert api.client.put(api.url, json=body(league_data)).status_code == 200
    payload = {**body(league_data, "invalid-change"), "inPlayerId": league_data.lineups[1][3]}
    assert api.client.put(api.url, json=payload).status_code == 409
    with Session(database) as db:
        saved = plans(db)
        assert len(saved) == 1
        assert saved[0].status == "PENDING"
        assert saved[0].command_id == "change-1"


@pytest.mark.parametrize("status", ["WAITING", "SCHEDULED", "FINISHED", "CANCELLED"])
def test_rejects_matches_outside_running_state(api, database, league_data, running_match, status):
    with Session(database) as db:
        row = db.get(Matches, running_match)
        row.status = status
        if status == "FINISHED":
            row.clock_ms = row.duration_ms
            row.finished_at = datetime.now(timezone.utc)
        if status == "CANCELLED":
            row.cancellation_reason = "NO_OPPONENT"
        db.commit()
    response = api.client.put(api.url, json=body(league_data))
    assert response.status_code == 409
    with Session(database) as db:
        assert plans(db) == []


@pytest.mark.parametrize("next_index,remaining,hydration,half,expected", [
    (0, 0, 15000, 30000, 1), (1, 0, 15000, 30000, 2), (2, 0, 15000, 30000, 3),
    (0, 0, 0, 30000, 2), (3, 0, 15000, 30000, "NO_UPCOMING_PAUSE"),
    (0, 0, 0, 0, "NO_UPCOMING_PAUSE"), (1, 1, 15000, 30000, "MATCH_STATE_INVALID"),
])
def test_target_pause_comes_from_server_state(api, database, league_data, running_match,
                                           next_index, remaining, hydration, half, expected):
    with Session(database) as db:
        row = db.get(Matches, running_match)
        state = deepcopy(row.runtime_state)
        state["breaks"] = {"next_index": next_index, "remaining_seconds": remaining,
                           "hydration_ms": hydration, "half_ms": half}
        row.runtime_state = state
        db.commit()
    response = api.client.put(api.url, json=body(league_data))
    if isinstance(expected, int):
        assert response.status_code == 200
        assert response.json()["pauseId"] == f"{running_match}:{expected}"
    else:
        assert response.status_code == 409
        assert response.json()["error"]["code"] == expected


def test_bank_is_frozen_and_survives_checkpoint_recovery(api, database, league_data, running_match):
    with Session(database) as db:
        row = db.get(Matches, running_match)
        restored = Match.from_checkpoint(row.runtime_state)
        assert [p.id for p in restored.local_team.substitutes] == league_data.lineups[0][3:]
        assert len(restored.world.players) == 6
        team = db.get(DefaultTeam, league_data.clubs[0])
        lineup = deepcopy(team.line_up)
        lineup["starters"], lineup["substitutes"] = lineup["substitutes"], lineup["starters"]
        team.line_up = lineup
        db.commit()
    assert api.client.put(api.url, json=body(league_data)).status_code == 200


def test_old_checkpoint_without_bank_does_not_guess_substitutes(api, database, league_data, running_match):
    with Session(database) as db:
        row = db.get(Matches, running_match)
        state = deepcopy(row.runtime_state)
        state["version"] = 4
        del state["local_team"]["substitutes"]
        del state["visitor_team"]["substitutes"]
        assert Match.from_checkpoint(state).local_team.substitutes == ()
        row.runtime_state = state
        db.commit()
    response = api.client.put(api.url, json=body(league_data))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "MATCH_STATE_INVALID"


@pytest.mark.skipif(not os.getenv("LEAGUE_TEST_DATABASE_URL"), reason="Requiere PostgreSQL")
@pytest.mark.parametrize("same_command", [True, False])
def test_concurrent_commands_keep_one_pending_plan(database, league_data, running_match, same_command):
    barrier = Barrier(2)

    def submit(index):
        command = "shared" if same_command else f"change-{index}"
        with Session(database) as db:
            barrier.wait(timeout=10)
            return plan_substitution(db, running_match, league_data.clubs[0],
                                     PlannedSubstitutionRequest.model_validate(body(league_data, command)))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, range(2)))
    with Session(database) as db:
        saved = plans(db)
        assert len(saved) == (1 if same_command else 2)
        assert sum(row.status == "PENDING" for row in saved) == 1
    if same_command:
        assert results[0] == results[1]
