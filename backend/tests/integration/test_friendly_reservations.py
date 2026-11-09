import os
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from queue import Queue
from time import monotonic, sleep
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.controller.matches_controller import matches_router
from app.database import get_db
from app.dependencies import get_current_club
from app.errors import AppError
from app.main import app_error_handler
from app.models.auth_model import Club
from app.models.matches_model import Matches
from app.services import matches_service
from test_league_start import database, league_data


@pytest.fixture
def available_clubs(database, league_data):
    with Session(database) as db:
        for club_id in league_data.clubs:
            db.get(Club, club_id).friendly_available = True
        db.commit()
    return league_data.clubs


@pytest.fixture
def friendly_client(database, sqlite_match_dates):
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

        yield as_club


def seed_match(
    database: Engine, start: datetime, creator: int, visitor: int | None = None, **fields,
) -> int:
    with Session(database) as db:
        match = Matches(creator_id=creator, visitor_id=visitor, init_date=start, **fields)
        db.add(match)
        db.flush()
        match_id = match.match_id
        db.commit()
    return match_id


@pytest.mark.parametrize("blocking_role, status, offset_seconds", [
    ("host", "SCHEDULED", 0),
    ("visitor", "SCHEDULED", -330),
    ("visitor", "RUNNING", 150),
    ("host", "WAITING", 0),
])
def test_accepting_overlapping_friendly_returns_the_blocking_reservation(
    database, available_clubs, friendly_client, blocking_role, status, offset_seconds,
):
    host, visitor, opponent, _ = available_clubs
    busy_club = host if blocking_role == "host" else visitor
    now = datetime.now(timezone.utc)
    blocking_start = now - timedelta(minutes=1) if status == "RUNNING" else now + timedelta(hours=1)
    seed_match(
        database, blocking_start, opponent, busy_club, status=status, duration_ms=120_000,
        started_at=blocking_start if status == "RUNNING" else None,
    )
    proposed_start = blocking_start + timedelta(seconds=offset_seconds)
    created = friendly_client(host).post(
        "/friendly-matches", json={"startDateTime": proposed_start.isoformat()},
    )
    assert created.status_code == 201, created.text
    invitation = created.json()["matchId"]

    response = friendly_client(visitor).post(f"/friendly-matches/{invitation}/join")

    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "FRIENDLY_SCHEDULE_CONFLICT"
    assert error["message"].startswith("El club rival" if blocking_role == "host" else "Tu club")
    fields = error["fields"]
    assert set(fields) == {"conflictStart", "conflictEnd"}
    assert datetime.fromisoformat(fields["conflictStart"]) == blocking_start
    assert datetime.fromisoformat(fields["conflictEnd"]) == blocking_start + timedelta(minutes=3)
    with Session(database) as db:
        match = db.get(Matches, invitation)
        assert (match.visitor_id, match.status, match.sequence) == (None, "WAITING_OPPONENT", 0)


@pytest.mark.parametrize("offset_seconds", [-360, 180])
def test_accepts_adjacent_friendly_and_ignores_pending_or_terminal_matches(
    database, available_clubs, friendly_client, offset_seconds,
):
    host, visitor, opponent, _ = available_clubs
    blocking_start = datetime.now(timezone.utc) + timedelta(hours=1)
    proposed_start = blocking_start + timedelta(seconds=offset_seconds)
    seed_match(database, blocking_start, host, opponent, status="SCHEDULED", duration_ms=120_000)
    seed_match(database, proposed_start, visitor, status="WAITING")
    seed_match(database, proposed_start, host, status="WAITING_OPPONENT")
    seed_match(
        database, proposed_start, visitor, opponent, status="CANCELLED",
        cancellation_reason="CLUB_BUSY",
    )
    seed_match(
        database, proposed_start, host, opponent, status="FINISHED", duration_ms=120_000,
        clock_ms=120_000, finished_at=proposed_start + timedelta(minutes=3), snapshot={},
    )
    invitation = seed_match(database, proposed_start, host, status="WAITING_OPPONENT")

    response = friendly_client(visitor).post(f"/friendly-matches/{invitation}/join")

    assert response.status_code == 200, response.text
    with Session(database) as db:
        match = db.get(Matches, invitation)
        assert (match.visitor_id, match.status, match.sequence) == (visitor, "SCHEDULED", 1)


def wait_until_blocked(
    database: Engine, waiting_pid: int, blocking_pid: int, request: Future[AppError],
) -> None:
    deadline = monotonic() + 5
    with database.connect() as observer:
        while monotonic() < deadline:
            if observer.scalar(
                text("SELECT :blocking_pid = ANY(pg_blocking_pids(:waiting_pid))"),
                {"blocking_pid": blocking_pid, "waiting_pid": waiting_pid},
            ):
                return
            if request.done():
                request.result()
                pytest.fail("La segunda aceptación terminó sin esperar el bloqueo de la primera.")
            sleep(0.01)
    pytest.fail("PostgreSQL no registró la espera entre las dos aceptaciones.")


@pytest.mark.skipif(
    not os.getenv("LEAGUE_TEST_DATABASE_URL"), reason="Requiere PostgreSQL para probar bloqueos",
)
@pytest.mark.parametrize("shared_role", ["visitor", "host"])
def test_concurrent_acceptances_commit_only_one_reservation_for_shared_club(
    database, available_clubs, monkeypatch, shared_role,
):
    first_host, shared_club, other, _ = available_clubs
    second_host, second_visitor = (
        (other, shared_club) if shared_role == "visitor" else (shared_club, other)
    )
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    first = seed_match(database, start, first_host, status="WAITING_OPPONENT")
    second = seed_match(database, start, second_host, status="WAITING_OPPONENT")
    waiting_pids = Queue()

    def accept_second():
        with Session(database) as db:
            db.execute(text("SET LOCAL lock_timeout = '10s'"))
            waiting_pids.put(db.scalar(text("SELECT pg_backend_pid()")))
            with pytest.raises(AppError) as conflict:
                matches_service.join_match(db, second, second_visitor)
            return conflict.value

    with Session(database) as db:
        blocking_pid = db.scalar(text("SELECT pg_backend_pid()"))
        commit = db.commit
        # Escribir la primera reserva y conservar sus bloqueos hasta observar la segunda.
        monkeypatch.setattr(db, "commit", db.flush)
        assert matches_service.join_match(db, first, shared_club)["match_id"] == first
        with ThreadPoolExecutor(max_workers=1) as pool:
            second_result = pool.submit(accept_second)
            try:
                waiting_pid = waiting_pids.get(timeout=5)
                wait_until_blocked(database, waiting_pid, blocking_pid, second_result)
            finally:
                commit()
            conflict = second_result.result(timeout=10)

    assert conflict.code == "FRIENDLY_SCHEDULE_CONFLICT"
    assert datetime.fromisoformat(conflict.fields["conflictStart"]) == start
    with Session(database) as db:
        rows = db.scalars(
            select(Matches).where(Matches.match_id.in_((first, second))).order_by(Matches.match_id),
        )
        assert [(row.visitor_id, row.status, row.sequence) for row in rows] == [
            (shared_club, "SCHEDULED", 1),
            (None, "WAITING_OPPONENT", 0),
        ]
