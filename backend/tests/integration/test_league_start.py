"""Inicio real y rollback; la concurrencia requiere LEAGUE_TEST_DATABASE_URL (PostgreSQL)."""
import os
import subprocess
import sys
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
from app.errors import AppError
from app.database import Base, get_db
from app.dependencies import get_current_club
from app.models.auth_model import Club, User
from app.models.behaviour_model import Behavior
from app.models.league_model import League, LeagueRegistration, LeagueRound, LeagueStanding
from app.models.matches_model import Matches
from app.models.player_model import Player
from app.models.team_model import DefaultTeam
from primitives.behaviours import DEFAULT_CODES
from app import migrate_league_passwords as password_migration
from app.repository import league_repository, matches_repository
from app.security import hash_password, verify_password
from app.services import league_fixture_service, league_service, match_execution_service


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
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT", no_parameters=True) as connection:
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
                club_id=club.id, name="Equilibrado", description="Prueba",
                code=DEFAULT_CODES["Equilibrado"], kind="PLAYER", validation_status="VALID",
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


@pytest.mark.parametrize("bad_field", ["formationId", "behaviourId", "legacy_players"])
def test_invalid_lineup_keeps_league_open(database, league_data, bad_field):
    with Session(database) as db:
        league = db.get(League, league_data.id)
        club_id = league_data.clubs[1]
        registration = league_repository.get_registration(db, league.id, club_id)
        lineup = db.get(DefaultTeam, club_id).line_up.copy()
        if bad_field == "legacy_players":
            registration.line_up = [999]
        else:
            if bad_field == "formationId":
                lineup["formationId"] = 999
            else:
                lineup["substitutes"][0]["behaviourId"] = 999
            registration.line_up = lineup
        db.commit()
        with pytest.raises(HTTPException) as error:
            league_service.start_league(db, league.id, league.creator_club_id)
        assert error.value.status_code == 409
        assert league.status == "open"
        assert db.scalar(select(LeagueRound)) is None


def test_password_migration_preserves_hashes_and_is_repeatable(database, league_data):
    existing_hash = hash_password("current-password")
    with Session(database) as db:
        legacy = db.get(League, league_data.id)
        legacy.access_code = "old-password"
        existing = League(
            name="Con hash y código antiguo", is_private=True,
            password_hash=existing_hash, access_code="obsolete-password",
            min_teams=3, max_teams=4, start_datetime=legacy.start_datetime,
            round_interval="DAILY",
        )
        public = League(
            name="Pública", min_teams=3, max_teams=4,
            start_datetime=legacy.start_datetime, round_interval="DAILY",
        )
        db.add_all([existing, public])
        db.commit()
        existing_id, public_id = existing.id, public.id
        assert password_migration.migrate_league_passwords(db) == 2
        migrated_hash = legacy.password_hash
        assert verify_password("old-password", migrated_hash)
        assert password_migration.migrate_league_passwords(db) == 0

    with Session(database) as db:
        legacy = db.get(League, league_data.id)
        existing = db.get(League, existing_id)
        public = db.get(League, public_id)
        assert legacy.password_hash == migrated_hash
        assert existing.password_hash == existing_hash
        assert legacy.access_code is existing.access_code is None
        assert legacy.is_private and existing.is_private
        assert not public.is_private
        assert public.password_hash is public.access_code is None
        for wrong_password in [None, "wrong-password"]:
            with pytest.raises(AppError) as error:
                league_service.join_league(
                    db, legacy.id, league_data.clubs[3], league_data.lineups[3], wrong_password,
                )
            assert error.value.code == "LEAGUE_ACCESS_INVALID"
        league_service.join_league(
            db, legacy.id, league_data.clubs[3], league_data.lineups[3], "old-password",
        )
        assert len(legacy.registrations) == 4


def test_password_migration_rolls_back_all_rows_on_failure(database, league_data, monkeypatch):
    with Session(database) as db:
        legacy = db.get(League, league_data.id)
        legacy.access_code = "first-password"
        db.add(League(
            name="Segunda liga antigua", access_code="second-password",
            min_teams=3, max_teams=4, start_datetime=legacy.start_datetime,
            round_interval="DAILY",
        ))
        db.commit()

        def fail_on_second_password(password):
            if password == "second-password":
                raise RuntimeError("Error simulado")
            return hash_password(password)

        monkeypatch.setattr(password_migration, "hash_password", fail_on_second_password)
        with pytest.raises(RuntimeError, match="Error simulado"):
            password_migration.migrate_league_passwords(db)

    with Session(database) as db:
        leagues = db.scalars(select(League).order_by(League.id)).all()
        assert [league.access_code for league in leagues] == ["first-password", "second-password"]
        assert all(league.password_hash is None for league in leagues)


@pytest.mark.skipif(not os.getenv("LEAGUE_TEST_DATABASE_URL"), reason="Requiere PostgreSQL")
def test_password_migration_command_runs_without_exposing_secrets(database, league_data):
    with Session(database) as db:
        league = db.get(League, league_data.id)
        league.access_code = "cli-private-password"
        db.commit()
        schema = db.connection().exec_driver_sql("SELECT current_schema()").scalar_one()
    url = database.url
    env = {
        **os.environ, "POSTGRES_USER": url.username, "POSTGRES_PASSWORD": url.password,
        "POSTGRES_DB": url.database, "POSTGRES_HOST": url.host,
        "POSTGRES_PORT": str(url.port), "PGOPTIONS": f"-csearch_path={schema}",
    }
    for count in [1, 0]:
        result = subprocess.run(
            [sys.executable, "-m", "app.migrate_league_passwords"],
            cwd=Path(__file__).parents[2], env=env, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == f"Ligas migradas: {count}"
        assert result.stderr == ""
    with Session(database) as db:
        league = db.get(League, league_data.id)
        assert league.access_code is None
        assert verify_password("cli-private-password", league.password_hash)


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
            lobby = client.get(f"/leagues/{data.id}/lobby")
            assert lobby.status_code == 200, lobby.text
            assert {row["clubId"] for row in lobby.json()["standings"]} == set(data.clubs[:3])
            assert all(row["points"] == 0 for row in lobby.json()["standings"])

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
        assert creator.line_up == db.get(DefaultTeam, data.clubs[0]).line_up


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
        with pytest.raises(AppError) as error:
            league_service.join_league(db, data.id, data.clubs[3], data.lineups[3])
        assert error.value.code == "LEAGUE_CLOSED"
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


def test_fixture_http_returns_persisted_draw_rest_and_next_match(database, league_data):
    data = league_data
    app = FastAPI()
    app.include_router(league_router)
    club = SimpleNamespace(id=data.clubs[0])
    app.dependency_overrides[get_current_club] = lambda: club
    with Session(database, expire_on_commit=False) as db:
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app) as client:
            empty = client.get(f"/leagues/{data.id}/fixture")
            assert empty.json() == {"leagueId": data.id, "rounds": [], "nextMatch": None}
            assert client.get("/leagues/999999/fixture").status_code == 404
            assert client.post(f"/leagues/{data.id}/start").status_code == 200
            response = client.get(f"/leagues/{data.id}/fixture")
            assert response.status_code == 200, response.text
            fixture = response.json()
            assert len(fixture["rounds"]) == 3
            assert [round_["scheduleConfirmed"] for round_ in fixture["rounds"]] == [True, False, False]
            assert all(round_["scheduledAt"].endswith("Z") for round_ in fixture["rounds"])
            assert all(len(round_["matches"]) == 1 for round_ in fixture["rounds"])
            seed = db.get(League, data.id).draw_seed
            assert client.get(f"/leagues/{data.id}/fixture").json() == fixture
            assert db.get(League, data.id).draw_seed == seed

            club.id = fixture["rounds"][0]["byeClubId"]
            resting_club = client.get(f"/leagues/{data.id}/fixture", params={"clubId": data.clubs[3]}).json()
            next_match = resting_club["nextMatch"]
            assert next_match["roundNumber"] > 1
            assert club.id in (next_match["creatorClubId"], next_match["visitorClubId"])
            club.id = data.clubs[3]
            assert client.get(f"/leagues/{data.id}/fixture").json()["nextMatch"] is None

    # Una sesión nueva representa volver a cargar el backend sin datos en memoria.
    with Session(database) as db:
        stored = league_fixture_service.get_league_fixture(db, data.id, data.clubs[0])
        assert [round_["matches"][0]["match_id"] for round_ in stored["rounds"]] == [
            round_["matches"][0]["matchId"] for round_ in fixture["rounds"]
        ]
        assert db.get(League, data.id).draw_seed == seed


def finish_fixture_match(db, match, finished_at, monkeypatch):
    monkeypatch.setattr(match_execution_service, "datetime", SimpleNamespace(now=lambda _: finished_at))
    simulation = SimpleNamespace(
        finished=True, status="FINISHED", duration_ms=match.duration_ms,
        scorer={"LOCAL": 1, "VISITANTE": 0},
        checkpoint=lambda: {"finished": True},
        snapshot=lambda sequence, sent_at: {
            "sequence": sequence, "sentAt": sent_at,
            "state": {"clockMs": match.duration_ms, "status": "FINISHED"},
        },
    )
    return match_execution_service._persist(db, match, simulation)


@pytest.mark.parametrize("frequency, interval", [
    ("CONTINUOUS", timedelta(seconds=360)),
    ("DAILY", timedelta(days=1)),
    ("WEEKLY", timedelta(days=7)),
])
def test_finished_round_persists_confirmed_schedule_and_forecasts(database, league_data, monkeypatch, frequency, interval):
    data = league_data
    with Session(database) as db:
        db.get(League, data.id).round_interval = frequency
        db.commit()
        league_service.start_league(db, data.id, data.clubs[0])
        before = league_fixture_service.get_league_fixture(db, data.id, data.clubs[0])
        first_match = db.get(Matches, before["rounds"][0]["matches"][0]["match_id"])
        finished_at = before["rounds"][0]["scheduled_at"] + timedelta(hours=2)
        finish_fixture_match(db, first_match, finished_at, monkeypatch)

    with Session(database) as db:
        after = league_fixture_service.get_league_fixture(db, data.id, data.clubs[0])
        assert after["rounds"][0]["matches"][0]["status"] == "FINISHED"
        assert after["rounds"][0]["matches"][0]["local_score"] == 1
        assert after["rounds"][1]["scheduled_at"] == finished_at + interval
        assert after["rounds"][1]["schedule_confirmed"] is True
        assert after["rounds"][2]["scheduled_at"] == finished_at + interval * 2
        assert after["rounds"][2]["schedule_confirmed"] is False
        assert [round_["matches"][0]["match_id"] for round_ in after["rounds"]] == [
            round_["matches"][0]["match_id"] for round_ in before["rounds"]
        ]
        for round_ in after["rounds"][1:]:
            match = db.get(Matches, round_["matches"][0]["match_id"])
            actual = match.init_date
            if actual.tzinfo is None:
                actual = actual.replace(tzinfo=timezone.utc)
            assert actual == round_["scheduled_at"]


def test_fixture_update_and_final_result_roll_back_together(database, league_data, monkeypatch):
    data = league_data
    update_schedule = match_execution_service.update_fixture_schedule

    def fail_after_schedule_update(*args):
        update_schedule(*args)
        raise RuntimeError("Fallo después de actualizar horarios")

    with Session(database) as db:
        league_service.start_league(db, data.id, data.clubs[0])
        before = league_fixture_service.get_league_fixture(db, data.id, data.clubs[0])
    monkeypatch.setattr(match_execution_service, "update_fixture_schedule", fail_after_schedule_update)
    with pytest.raises(RuntimeError):
        with Session(database) as db:
            match = db.get(Matches, before["rounds"][0]["matches"][0]["match_id"])
            finish_fixture_match(db, match, datetime.now(timezone.utc), monkeypatch)

    with Session(database) as db:
        assert league_fixture_service.get_league_fixture(db, data.id, data.clubs[0]) == before


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
            except AppError as exc:
                assert exc.code == "LEAGUE_CLOSED"
                db.rollback()
                return 409
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
