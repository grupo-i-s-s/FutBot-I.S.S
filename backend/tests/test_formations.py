"""Guardado HTTP y uso en partidos con repositorios reales y SQLite aislado."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.controller.team_controller import catalogs_router, team_router
from app.database import Base, get_db
from app.dependencies import get_current_club, require_browser_write
from app.errors import AppError
from app.main import app_error_handler, validation_error_handler
from app.models.auth_model import Club, User
from app.models.behaviour_model import Behavior
from app.models.matches_model import Matches
from app.models.player_model import Player
from app.models.team_model import DefaultTeam
from app.repository import matches_repository
from app.services import match_execution_service
from app.services.match_builder_service import build_match
from primitives import match_simulation
from primitives.behaviours import DEFAULT_CODES


def lineup(club_id, formation_id=1):
    return {
        "formationId": formation_id,
        "starters": [
            {"playerId": club_id * 10 + index, "behaviourId": club_id}
            for index in (4, 0, 2)
        ],
        "substitutes": [
            {"playerId": club_id * 10 + index, "behaviourId": club_id}
            for index in (1, 3, 5)
        ],
    }


@pytest.fixture
def context():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    tables = [model.__table__ for model in (User, Club, Behavior, Player, DefaultTeam, Matches)]
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine) as db:
        for club_id in (1, 2):
            db.add(User(id=club_id, email=f"club{club_id}@test.com", password_hash="unused"))
            db.add(Club(id=club_id, user_id=club_id, name=f"Club {club_id}", avatar="shield"))
            db.add(Behavior(id=club_id, club_id=club_id, name="Equilibrado", description="test",
                            code=DEFAULT_CODES["Equilibrado"]))
            for index in range(6):
                db.add(Player(id=club_id * 10 + index, club_id=club_id, behavior_id=club_id,
                              name=f"Jugador {club_id}-{index}", power=60, agility=60,
                              control=60, speed=60, strength=60))
            db.add(DefaultTeam(club_id=club_id, line_up=lineup(club_id, 1 if club_id == 1 else 3)))
        for match_id in (42, 43):
            db.add(Matches(match_id=match_id, creator_id=1, visitor_id=2,
                           init_date=datetime.now(timezone.utc) - timedelta(minutes=1), duration_ms=200))
        db.commit()

    # Exercise the production routers and handlers without a background scheduler.
    application = FastAPI(dependencies=[Depends(require_browser_write)])
    application.include_router(team_router)
    application.include_router(catalogs_router)
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)

    def database():
        with Session(engine) as db:
            yield db

    application.dependency_overrides[get_db] = database
    application.dependency_overrides[get_current_club] = lambda: SimpleNamespace(id=1)
    try:
        with TestClient(application) as client:
            client.headers.update({"Origin": next(iter(settings.allowed_origins)), "X-FutBot-Request": "1"})
            yield SimpleNamespace(engine=engine, client=client)
    finally:
        engine.dispose()


@pytest.mark.parametrize("formation_id", [1, 2, 3])
def test_saved_formation_is_returned_and_used_with_selected_starter_order(context, formation_id):
    response = context.client.get("/catalogs/formations")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 3
    data = lineup(1, formation_id)
    assert context.client.put("/team/default", json=data).status_code == 200
    assert context.client.get("/team/default").json() == {"clubId": 1, "lineUp": data}

    with Session(context.engine) as db:
        simulation = build_match(db, 42)
        assert simulation.local_team.formation_id == formation_id
        assert simulation.visitor_team.formation_id == 3
        assert [player.id for player in simulation.local_team.players] == [14, 10, 12]
        assert db.get(DefaultTeam, 2).line_up == lineup(2, 3)


@pytest.mark.parametrize("invalid", ["formation", "foreign_player", "foreign_behaviour"])
def test_invalid_save_does_not_replace_the_persisted_team(context, invalid):
    data = lineup(1)
    if invalid == "formation":
        data["formationId"] = 999
    elif invalid == "foreign_player":
        data["starters"][0]["playerId"] = 24
    else:
        data["starters"][0]["behaviourId"] = 2
    assert context.client.put("/team/default", json=data).status_code == 400
    assert context.client.get("/team/default").json()["lineUp"] == lineup(1)


def test_configuration_changes_apply_to_future_matches_and_not_resumed_matches(context, monkeypatch):
    assert context.client.put("/team/default", json=lineup(1, 2)).status_code == 200
    now = datetime.now(timezone.utc)
    with Session(context.engine) as db:
        simulation = build_match(db, 42)
        simulation.run_match(0.1)
        row = db.get(Matches, 42)
        matches_repository.save_progress(db, row, simulation, simulation.snapshot(1, now.isoformat()), now)
        db.commit()

    assert context.client.put("/team/default", json=lineup(1, 1)).status_code == 200

    @contextmanager
    def execution_session(match_id):
        with Session(context.engine, expire_on_commit=False) as db:
            yield db

    monkeypatch.setattr(matches_repository, "execution_session", execution_session)
    monkeypatch.setattr(match_execution_service, "sleep", lambda _: None)
    monkeypatch.setattr(match_simulation, "step", lambda *_: "LEFT")
    final = match_execution_service.run_persisted_match(42)

    with Session(context.engine) as db:
        row = db.get(Matches, 42)
        assert final["state"]["status"] == "FINISHED"
        assert row.runtime_state["local_team"]["formation_id"] == 2
        restored = match_simulation.Match.from_checkpoint(row.runtime_state)
        assert restored.init_players_pos == simulation.init_players_pos
        assert build_match(db, 43).local_team.formation_id == 1
