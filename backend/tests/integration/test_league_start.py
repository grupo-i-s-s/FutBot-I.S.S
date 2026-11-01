"""Inicio real y rollback; la concurrencia requiere LEAGUE_TEST_DATABASE_URL (PostgreSQL)."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

for name, value in {
    "POSTGRES_USER": "test", "POSTGRES_PASSWORD": "test",
    "POSTGRES_DB": "test", "POSTGRES_HOST": "unused.invalid",
}.items():
    os.environ.setdefault(name, value)

from app.controller.league_controller import league_router
from app.database import Base, get_db
from app.dependencies import get_current_club
from app.models.auth_model import Club, User
from app.models.behaviour_model import Behavior
from app.models.league_model import League, LeagueRegistration, LeagueRound, LeagueStanding
from app.models.matches_model import Matches
from app.models.player_model import Player
from app.models.team_model import DefaultTeam
from app.repository import league_repository, matches_repository
from app.services import league_service


@pytest.fixture
def database():
    url = os.getenv("LEAGUE_TEST_DATABASE_URL")
    if url:
        # Cada prueba usa sólo su esquema, incluso al aplicar las migraciones.
        schema = "test_league_" + uuid4().hex
        admin = create_engine(url)
        with admin.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
        try:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                for migration in sorted((Path(__file__).parents[2] / "migrations").glob("*.sql")):
                    connection.exec_driver_sql(migration.read_text(encoding="utf-8"))
            yield engine
        finally:
            engine.dispose()
            with admin.begin() as connection:
                connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
            admin.dispose()
    else:
        engine = create_engine(
            "sqlite://", poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(engine)
        try:
            yield engine
        finally:
            engine.dispose()


@pytest.fixture
def league_data(database):
    with Session(database) as db:
        clubs = []
        lineups = []
        for index in range(4):
            user = User(email=f"club{index}@example.com", password_hash="unused")
            db.add(user)
            db.flush()
            club = Club(user_id=user.id, name=f"Club {index}", avatar="avatar-1")
            db.add(club)
            db.flush()
            behaviour = Behavior(
                club_id=club.id, name="Equilibrado", description="Prueba", code="unused",
            )
            db.add(behaviour)
            db.flush()
            players = [Player(
                club_id=club.id, behavior_id=behaviour.id, name=f"Jugador {i}",
                power=60, agility=60, control=60, speed=60, strength=60,
            ) for i in range(6)]
            db.add_all(players)
            db.flush()
            ids = [player.id for player in players]
            db.add(DefaultTeam(club_id=club.id, line_up={
                "formationId": 1,
                "starters": [{"playerId": id_, "behaviourId": behaviour.id} for id_ in ids[:3]],
                "substitutes": [{"playerId": id_, "behaviourId": behaviour.id} for id_ in ids[3:]],
            }))
            clubs.append(club.id)
            lineups.append(ids)

        league = League(
            name="Liga de prueba", creator_club_id=clubs[0], min_teams=3, max_teams=4,
            start_datetime=datetime.now(timezone.utc) - timedelta(days=1),
            round_interval="DAILY",
            registrations=[LeagueRegistration(
                club_id=clubs[i], line_up=lineups[i] if i else [],
            ) for i in range(3)],
        )
        db.add(league)
        db.commit()
        return SimpleNamespace(id=league.id, clubs=clubs, lineups=lineups)


def test_http_start_persists_seed_fixture_and_zero_standings(database, league_data):
    data = league_data
    app = FastAPI()
    app.include_router(league_router)
    with Session(database, expire_on_commit=False) as db:
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_club] = lambda: SimpleNamespace(id=data.clubs[0])
        with TestClient(app) as client:
            response = client.post(f"/leagues/{data.id}/start")
            assert response.status_code == 200, response.text
            assert response.json() == {"leagueId": data.id, "status": "running"}
            assert client.post(f"/leagues/{data.id}/start").json() == response.json()

    with Session(database) as db:
        league = db.get(League, data.id)
        assert league.status == "running"
        assert isinstance(league.draw_seed, int)
        rounds = db.scalars(select(LeagueRound).order_by(LeagueRound.number)).all()
        assert [round_.number for round_ in rounds] == [1, 2, 3]
        assert {round_.bye_club_id for round_ in rounds} == set(data.clubs[:3])
        matches = db.scalars(select(Matches)).all()
        assert len(matches) == 3
        assert all(match.status == "SCHEDULED" for match in matches)
        assert {tuple(sorted((m.creator_id, m.visitor_id))) for m in matches} == {
            tuple(sorted(pair)) for pair in [
                (data.clubs[0], data.clubs[1]), (data.clubs[0], data.clubs[2]),
                (data.clubs[1], data.clubs[2]),
            ]
        }
        standings = db.scalars(select(LeagueStanding)).all()
        assert {row.club_id for row in standings} == set(data.clubs[:3])
        for row in standings:
            assert (row.played, row.wins, row.draws, row.losses,
                    row.goals_for, row.goals_against, row.points) == (0,) * 7
        creator = db.scalar(select(LeagueRegistration).where(
            LeagueRegistration.club_id == data.clubs[0],
        ))
        assert creator.line_up == data.lineups[0]


def test_failure_rolls_back_seed_lineups_rounds_matches_and_standings(database, league_data, monkeypatch):
    create_standings = league_repository.create_standings

    def fail_after_writing(*args):
        create_standings(*args)
        raise RuntimeError("Error después de guardar la tabla")

    monkeypatch.setattr(league_repository, "create_standings", fail_after_writing)
    with Session(database) as db:
        with pytest.raises(RuntimeError):
            league_service.start_league(db, league_data.id, league_data.clubs[0])

    with Session(database) as db:
        league = db.get(League, league_data.id)
        assert (league.status, league.draw_seed) == ("open", None)
        assert next(row for row in league.registrations if row.club_id == league.creator_club_id).line_up == []
        for model in [LeagueRound, Matches, LeagueStanding]:
            assert db.scalars(select(model)).all() == []


def test_running_league_rejects_join_and_leave(database, league_data):
    data = league_data
    with Session(database) as db:
        league_service.start_league(db, data.id, data.clubs[0])
        with pytest.raises(HTTPException) as error:
            league_service.join_league(db, data.id, data.clubs[3], data.lineups[3])
        assert error.value.status_code == 409
        db.rollback()
        with pytest.raises(HTTPException) as error:
            league_service.leave_league(db, data.id, data.clubs[1])
        assert error.value.status_code == 409


def test_friendly_scheduler_does_not_execute_league_fixture(database, league_data):
    with Session(database) as db:
        league_service.start_league(db, league_data.id, league_data.clubs[0])
        friendly = Matches(
            creator_id=league_data.clubs[0], visitor_id=league_data.clubs[3],
            init_date=datetime.now(timezone.utc) - timedelta(days=1), status="SCHEDULED",
        )
        db.add(friendly)
        db.commit()
        due_ids = matches_repository.get_due_match_ids(db, datetime.now(timezone.utc))
        assert due_ids == [friendly.match_id]


@pytest.mark.skipif(not os.getenv("LEAGUE_TEST_DATABASE_URL"), reason="Requiere PostgreSQL para probar bloqueos")
@pytest.mark.parametrize("operation", ["start", "join", "leave", "cancel"])
def test_concurrent_operations_keep_participants_consistent(database, league_data, operation):
    data = league_data
    barrier = Barrier(2, timeout=10)

    def run(action):
        with Session(database) as db:
            barrier.wait()
            try:
                if action == "start":
                    league_service.start_league(db, data.id, data.clubs[0])
                elif action == "join":
                    league_service.join_league(db, data.id, data.clubs[3], data.lineups[3])
                elif action == "leave":
                    league_service.leave_league(db, data.id, data.clubs[2])
                else:
                    # Cancel aún no tiene endpoint; comprobar el mismo bloqueo compartido.
                    league = league_repository.get_league_by_id(db, data.id)
                    if league.status != "open":
                        raise HTTPException(409, "La liga ya inició")
                    league.status = "cancelled"
                    db.commit()
                return 200
            except HTTPException as exc:
                db.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(run, "start")
        second = executor.submit(run, operation)
        results = [first.result(timeout=15), second.result(timeout=15)]
    assert all(result in {200, 409} for result in results)
    if operation == "start":
        assert results == [200, 200]

    with Session(database) as db:
        league = db.get(League, data.id)
        club_ids = {row.club_id for row in league.registrations}
        standings = db.scalars(select(LeagueStanding)).all()
        matches = db.scalars(select(Matches)).all()
        if league.status == "running":
            assert {row.club_id for row in standings} == club_ids
            assert len(matches) == len(club_ids) * (len(club_ids) - 1) // 2
            assert {id_ for match in matches for id_ in [match.creator_id, match.visitor_id]} == club_ids
        else:
            assert standings == []
            assert matches == []
            assert league.draw_seed is None
