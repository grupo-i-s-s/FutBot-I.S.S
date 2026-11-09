from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import partial
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.controller import api_router
from app.database import get_db
from app.dependencies import require_browser_write
from app.errors import AppError
from app.main import app_error_handler
from app.models.auth_model import AuthSession, Club
from app.models.behaviour_model import Behavior
from app.models.matches_model import Matches
from app.repository import dt_repository, matches_repository
from app.security import hash_session_token
from app.services import match_builder_service, match_execution_service as execution
from primitives.behaviours import DEFAULT_CODES
from primitives.match_simulation import Match
from test_league_start import database, league_data


STRATEGY = """from primitives.dt_behaviour import DtAction
from primitives.behaviours import BehaviourMode

def decide(observation):
    changes = [cambiar_comportamiento(jugador, BehaviourMode.OFFENSIVE) for jugador in observation.players_id]
    if observation.can_substitute and observation.pause_index == 1:
        return DtAction(changes, [sustituir(observation.players_id[0], observation.substitutes_id[0])])
    return DtAction(changes)
"""


@pytest.fixture
def dt_game(database, league_data, monkeypatch, sqlite_match_dates):
    now = datetime.now(timezone.utc)
    local_id, visitor_id = league_data.clubs[:2]
    token = "t" * 43
    with Session(database) as db:
        local = db.get(Club, local_id)
        default, *_ = dt_repository.create_default_dt_behaviours(db, local.user_id)
        dt_repository.create_dt(db, local_id, default.id)
        foreign = dt_repository.create_default_dt_behaviours(db, db.get(Club, visitor_id).user_id)[0]
        offensive = Behavior(
            club_id=local_id, name="Ofensivo", description="Prueba",
            code=DEFAULT_CODES["Ofensivo"], kind="PLAYER", validation_status="VALID",
        )
        match = Matches(
            creator_id=local_id, visitor_id=visitor_id,
            init_date=now - timedelta(seconds=1), status="SCHEDULED", duration_ms=1_000,
        )
        db.add_all([offensive, match, AuthSession(
            token_hash=hash_session_token(token), user_id=local.user_id,
            created_at=now, expires_at=now + timedelta(hours=1),
        )])
        db.flush()
        match_id, offensive_id, foreign_id = match.match_id, offensive.id, foreign.id
        db.commit()

    monkeypatch.setattr(execution, "sleep", lambda _: None)
    monkeypatch.setattr(match_builder_service, "Match", partial(Match, hydration_break_ms=100, half_break_ms=100))
    if database.dialect.name == "postgresql":
        monkeypatch.setattr(matches_repository, "engine", database)
    else:
        @contextmanager
        def execution_session(match_id):
            with Session(database, expire_on_commit=False) as db:
                yield db

        monkeypatch.setattr(matches_repository, "execution_session", execution_session)

    def session():
        with Session(database, expire_on_commit=False) as db:
            yield db

    app = FastAPI(dependencies=[Depends(require_browser_write)])
    app.include_router(api_router)
    app.add_exception_handler(AppError, app_error_handler)
    app.dependency_overrides[get_db] = session
    with TestClient(app) as client:
        client.cookies.set(settings.cookie_name, token)
        client.headers.update({"Origin": next(iter(settings.allowed_origins)), "X-FutBot-Request": "1"})
        yield SimpleNamespace(client=client, match_id=match_id, local_id=local_id,
                              offensive_id=offensive_id, foreign_id=foreign_id)


def assign_strategy(client, *, active):
    validated = client.post("/behaviours/validate", json={"kind": "COACH", "code": STRATEGY})
    assert validated.status_code == 200, validated.text
    assert validated.json() == {"valid": True, "diagnostics": []}
    created = client.post("/dt/behaviours", json={"name": "Cambiar en la pausa", "code": STRATEGY})
    assert created.status_code == 201, created.text
    strategy_id = created.json()["id"]
    saved = client.patch("/dt", json={"isActive": active, "activeBehaviourId": strategy_id})
    assert saved.status_code == 200, saved.text
    assert saved.json()["activeBehaviourId"] == strategy_id
    assert client.get("/club/me").json()["dt"] == saved.json()
    return strategy_id


def test_assigns_owned_strategy_and_persists_automatic_actions_across_resume(dt_game, league_data, database):
    client = dt_game.client
    match_id = dt_game.match_id
    assert dt_game.foreign_id not in {item["id"] for item in client.get("/dt/behaviours").json()["items"]}
    assert client.patch("/dt", json={"isActive": True, "activeBehaviourId": dt_game.foreign_id}).status_code == 404
    assert client.patch("/dt", json={"isActive": True, "activeBehaviourId": None}).status_code == 409
    assign_strategy(client, active=True)

    stop = Mock(spec=Event)
    stop.is_set.return_value = False
    stop.wait.side_effect = [False, False, False, True]
    paused = execution.run_persisted_match(match_id, stop_event=stop)
    assert paused["state"]["phase"] == "HYDRATION_BREAK"
    assert paused["state"]["teams"][0]["dtActive"] is True
    event, = paused["state"]["events"]
    assert event["source"] == "DT"
    assert (event["outPlayerId"], event["inPlayerId"]) == (league_data.lineups[0][0], league_data.lineups[0][3])
    assert client.patch("/clubs/me/dt", json={"isActive": False}).status_code == 200

    # Los checkpoints de la rama anterior guardaban la estrategia sin su catálogo.
    with Session(database) as db:
        row = db.get(Matches, match_id)
        state = row.runtime_state.copy()
        team = state["local_team"].copy()
        del team["dt_default_behaviours"]
        row.runtime_state = {**state, "local_team": team}
        db.commit()

    final = execution.run_persisted_match(match_id)
    assert final["state"]["events"] == [event]
    assert final["state"]["teams"][0]["dtActive"] is True
    assert final["state"]["teams"][0]["dtError"] is None
    assert {player["behaviourId"] for player in final["state"]["players"]
            if player["teamId"] == dt_game.local_id} == {dt_game.offensive_id}
    assert {player["behaviourMode"] for player in final["state"]["players"]
            if player["teamId"] != dt_game.local_id} == {"BALANCED"}
    assert client.get(f"/matches/{match_id}").json() == final


@pytest.mark.parametrize("active", [False, True])
def test_running_mode_rejects_toggles_and_controls_manual_actions(dt_game, league_data, monkeypatch, active):
    client, match_id = dt_game.client, dt_game.match_id
    path = f"/matches/{match_id}"
    assign_strategy(client, active=active)
    starting_actions = False
    pause_action = False

    def assert_manual_result(response, success_status):
        assert response.status_code == (409 if active else success_status), response.text
        if active:
            assert response.json()["error"]["code"] == "MATCH_DT_MANUAL_ACTION_FORBIDDEN"

    def during_wait(_):
        nonlocal starting_actions, pause_action
        if pause_action:
            return
        before = client.get(path).json()
        if not starting_actions:
            starting_actions = True
            for route, field in ((f"{path}/dt", "dtActive"), (f"/friendly-matches/{match_id}/dt", "dt_active")):
                for value in (active, not active):
                    response = client.post(route, json={field: value})
                    assert response.status_code == 409, response.text
                    assert response.json()["error"]["code"] == "MATCH_DT_MODE_FIXED"
            assert client.get(path).json() == before

            player_id = league_data.lineups[0][1]
            assert_manual_result(client.post(f"{path}/live-requests", json={
                "playerId": player_id, "behaviourId": dt_game.offensive_id,
            }), 200)
            assert_manual_result(client.post(f"{path}/live_request", json={
                "player_id": player_id, "behaviour_id": dt_game.offensive_id,
            }), 200)
            assert_manual_result(client.put(f"{path}/planned-substitution", json={
                "outPlayerId": league_data.lineups[0][2], "inPlayerId": league_data.lineups[0][5],
                "commandId": "planned-manual", "pauseId": before["state"]["nextPause"]["pauseId"],
            }), 200)
            assert client.patch("/clubs/me/dt", json={"isActive": not active}).status_code == 200

        state = before["state"]
        if state["phase"] == "HALF_BREAK":
            pause_action = True
            lineup = state["lineups"][0]
            assert_manual_result(client.post(f"{path}/substitutions", json={
                "outPlayerId": lineup["starters"][0]["playerId"],
                "inPlayerId": lineup["substitutes"][0]["playerId"],
                "commandId": "immediate-manual", "pauseId": f"{match_id}:{state['breakIndex']}",
            }), 202)

    monkeypatch.setattr(execution, "sleep", during_wait)
    final = execution.run_persisted_match(match_id)
    assert starting_actions and pause_action
    events = final["state"]["events"]
    if active:
        event, = events
        assert event["source"] == "DT"
        assert event["inPlayerId"] == league_data.lineups[0][3]
    else:
        assert [event["inPlayerId"] for event in events] == [league_data.lineups[0][5], league_data.lineups[0][3]]
        assert all(event["type"] == "SUBSTITUTION_APPLIED" for event in events)
        player = next(player for player in final["state"]["players"] if player["id"] == league_data.lineups[0][1])
        assert player["behaviourId"] == dt_game.offensive_id
    assert final["state"]["teams"][0]["dtActive"] is active
    assert client.get("/club/me").json()["dt"]["isActive"] is (not active)
