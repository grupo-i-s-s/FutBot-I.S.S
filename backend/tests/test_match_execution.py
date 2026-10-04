from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.dependencies import get_current_club
from app.errors import AppError
from app.main import app
from app.models.auth_model import Club, User
from app.models.behaviour_model import Behavior
from app.models.matches_model import Matches
from app.models.player_model import Player
from app.repository import matches_repository
from app.services import match_execution_service as execution
from app.services.match_snapshot_service import read_snapshot
from app.controller import match_stream_controller as streams
from app.config import settings
from app.services.match_stream_services import StreamAccess
from primitives import match_simulation
from primitives.behaviours import DEFAULT_CODES


@pytest.fixture
def database(monkeypatch):
    # Persistencia real con sesiones independientes, sin requerir Docker.
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    tables = [User.__table__, Club.__table__, Behavior.__table__, Player.__table__, Matches.__table__]
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine) as db:
        for club_id in (1, 2):
            db.add(User(id=club_id, email=f"club{club_id}@test.com", password_hash="unused"))
            db.add(Club(id=club_id, user_id=club_id, name=f"Club {club_id}", avatar="avatar"))
            db.add(Behavior(id=club_id, club_id=club_id, name="Equilibrado", description="test", code=DEFAULT_CODES["Equilibrado"]))
            for index in range(3):
                db.add(Player(id=club_id * 10 + index, club_id=club_id, behavior_id=club_id,
                              name=f"Jugador {club_id}-{index}", power=60, agility=60,
                              control=60, speed=60, strength=60))
        db.add(Matches(match_id=42, creator_id=1, visitor_id=2,
                       init_date=datetime.now(timezone.utc) + timedelta(hours=1), duration_ms=200))
        db.commit()

    @contextmanager
    def execution_session(match_id):
        with Session(engine, expire_on_commit=False) as db:
            yield db

    monkeypatch.setattr(matches_repository, "execution_session", execution_session)
    monkeypatch.setattr(execution, "sleep", lambda _: None)
    yield engine
    engine.dispose()


def test_executor_persists_result_and_second_call_does_not_play_again(database, monkeypatch):
    monkeypatch.setattr(match_simulation, "step", lambda *_: "RIGHT")
    final = execution.run_persisted_match(42)

    with Session(database) as db:
        row = db.get(Matches, 42)
        assert row.status == "FINISHED"
        assert row.clock_ms == row.duration_ms == 200
        assert row.local_score == 0 and row.visitor_score == 6
        assert row.started_at is not None and row.finished_at is not None
        assert row.snapshot == final
        assert read_snapshot(db, 42, 1) == final
        assert read_snapshot(db, 42, 2) == final
        sequence, finished_at = row.sequence, row.finished_at

    assert execution.run_persisted_match(42) == final
    with Session(database) as db:
        row = db.get(Matches, 42)
        assert row.sequence == sequence and row.finished_at == finished_at


def test_resume_keeps_committed_clock_goals_and_frozen_behaviours(database, monkeypatch):
    monkeypatch.setattr(match_simulation, "step", lambda *_: "LEFT")
    calls = 0

    def interrupt_after_first_batch(_):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("worker detenido")

    monkeypatch.setattr(execution, "sleep", interrupt_after_first_batch)
    with pytest.raises(RuntimeError, match="detenido"):
        execution.run_persisted_match(42)

    with Session(database) as db:
        row = db.get(Matches, 42)
        assert row.status == "RUNNING" and row.clock_ms == 100
        assert row.local_score == 3 and row.sequence == 2
        # Cambiar el club después de comenzar no reconstruye la alineación.
        db.get(Behavior, 1).code = "código incompatible nuevo"
        db.commit()

    monkeypatch.setattr(execution, "sleep", lambda _: None)
    with pytest.raises(AppError) as error:
        execution.run_persisted_match(42, duration_ms=100)
    assert error.value.code == "MATCH_INVALID_DURATION"
    final = execution.run_persisted_match(42)
    assert final["state"]["status"] == "FINISHED"
    assert final["state"]["teams"][0]["score"] == 6
    assert final["sequence"] == 3


def test_persistence_failure_never_publishes_uncommitted_final_state(database, monkeypatch):
    with Session(database, expire_on_commit=False) as db:
        commit = db.commit
        calls = 0

        def fail_second_commit():
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("falló persistencia")
            commit()

        monkeypatch.setattr(db, "commit", fail_second_commit)
        with pytest.raises(RuntimeError, match="persistencia"):
            execution._execute(db, 42, None)

    with Session(database) as db:
        snapshot = read_snapshot(db, 42, 1)
        assert snapshot["sequence"] == 1
        assert snapshot["state"]["status"] == "RUNNING"
        assert snapshot["state"]["clockMs"] == 0


def test_waiting_read_and_access_checks_do_not_start_match(database):
    with Session(database) as db:
        snapshot = read_snapshot(db, 42, 1)
        assert snapshot["state"]["status"] == "WAITING"
        assert snapshot["state"]["players"] == [] and snapshot["state"]["ball"] is None
        assert db.get(Matches, 42).runtime_state is None
        with pytest.raises(AppError) as error:
            read_snapshot(db, 42, 99)
        assert error.value.code == "MATCH_FORBIDDEN"
        with pytest.raises(AppError) as error:
            read_snapshot(db, 404, 1)
        assert error.value.code == "MATCH_NOT_FOUND"


@pytest.mark.parametrize("duration", [0, -1, True])
def test_executor_rejects_invalid_duration_before_starting(database, duration):
    with pytest.raises(AppError) as error:
        execution.run_persisted_match(42, duration_ms=duration)
    assert error.value.code == "MATCH_INVALID_DURATION"
    with Session(database) as db:
        assert db.get(Matches, 42).status == "WAITING"
        assert db.get(Matches, 42).snapshot is None


def test_get_and_websocket_return_same_persisted_final_snapshot(database, monkeypatch):
    final = execution.run_persisted_match(42)
    with Session(database) as db:
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_club] = lambda: SimpleNamespace(id=1)
        monkeypatch.setattr(streams, "authorize_with_db", lambda *_: StreamAccess("session", 1))
        monkeypatch.setattr(streams, "snapshot_with_db", lambda *_: final)
        try:
            with TestClient(app) as client:
                assert client.get("/matches/42").json() == final
                with client.websocket_connect("/matches/42/stream", headers={"Origin": next(iter(settings.allowed_origins))}) as socket:
                    assert socket.receive_json() == final
                    assert socket.receive() == {"type": "websocket.close", "code": 1000, "reason": "Partido finalizado"}
        finally:
            app.dependency_overrides.clear()


def test_stream_omits_repeated_sequence_and_sends_new_final_state(monkeypatch):
    snapshots = iter([
        {"sequence": 1, "state": {"status": "RUNNING"}},
        {"sequence": 1, "state": {"status": "RUNNING"}},
        {"sequence": 2, "state": {"status": "FINISHED"}},
    ])
    monkeypatch.setattr(streams, "authorize_with_db", lambda *_: StreamAccess("session", 1))
    monkeypatch.setattr(streams, "snapshot_with_db", lambda *_: next(snapshots))
    with TestClient(app) as client:
        with client.websocket_connect("/matches/42/stream", headers={"Origin": next(iter(settings.allowed_origins))}) as socket:
            assert socket.receive_json()["sequence"] == 1
            assert socket.receive_json()["sequence"] == 2
            assert socket.receive()["code"] == 1000


def test_stream_rechecks_session_while_sending_snapshots(monkeypatch):
    monkeypatch.setattr(streams, "authorize_with_db", lambda *_: StreamAccess("session", 1))
    monkeypatch.setattr(streams, "SESSION_CHECK_SECONDS", 0)
    monkeypatch.setattr(streams, "session_active_with_db", lambda *_: False)
    with TestClient(app) as client:
        with client.websocket_connect("/matches/42/stream", headers={"Origin": next(iter(settings.allowed_origins))}) as socket:
            assert socket.receive()["code"] == 1008


@pytest.mark.parametrize("acquired", [True, False])
def test_execution_lock_is_released_on_error_and_rejects_second_writer(monkeypatch, acquired):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.scalar.return_value = acquired
    monkeypatch.setattr(matches_repository, "engine", SimpleNamespace(connect=lambda: connection))
    with pytest.raises(RuntimeError if acquired else AppError) as error:
        with matches_repository.execution_session(42):
            raise RuntimeError("test error")
    if acquired:
        assert "pg_advisory_unlock" in str(connection.execute.call_args.args[0])
        connection.rollback.assert_called_once()
    else:
        assert error.value.code == "MATCH_ALREADY_RUNNING"
        connection.execute.assert_not_called()
