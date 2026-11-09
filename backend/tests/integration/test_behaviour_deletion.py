import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from queue import Queue
from time import monotonic, sleep
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.config import settings
from app.database import Base, get_db
from app.dependencies import get_current_club
from app.errors import AppError
from app.main import app
from app.models.auth_model import Club, User
from app.models.behaviour_model import Behavior
from app.models.league_model import League, LeagueRegistration, LeagueRound
from app.models.matches_model import Matches
from app.models.player_model import Player
from app.models.team_model import DefaultTeam
from app.services import behaviour_service, player_service
from primitives.behaviours import DEFAULT_CODES


@pytest.fixture
def database():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Definí TEST_DATABASE_URL para ejecutar estas pruebas.")

    raw_engine = create_engine(url, isolation_level="READ COMMITTED")
    if raw_engine.dialect.name != "postgresql":
        raw_engine.dispose()
        pytest.fail("Estas pruebas requieren PostgreSQL real.")

    schema = f"iss205_{uuid4().hex}"

    with raw_engine.begin() as connection:
        connection.execute(CreateSchema(schema))

    engine = raw_engine.execution_options(
        schema_translate_map={None: schema}
    )

    try:
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            db.add_all([
                User(
                    id=i,
                    email=f"club{i}@example.com",
                    password_hash="unused",
                )
                for i in (1, 2)
            ])
            db.flush()

            db.add_all([
                Club(
                    id=i,
                    user_id=i,
                    name=f"Club {i}",
                    avatar="avatar-1",
                )
                for i in (1, 2)
            ])
            db.flush()

            db.add_all([
                Behavior(
                    id=behaviour_id,
                    club_id=club_id,
                    name=f"Comportamiento {behaviour_id}",
                    description="Prueba ISS-205",
                    code=DEFAULT_CODES["Equilibrado"],
                    kind="PLAYER",
                    version=3,
                    validation_status="VALID",
                    is_deleted=False,
                )
                for behaviour_id, club_id in (
                    (10, 1), (20, 1), (30, 2)
                )
            ])
            db.flush()

            db.add_all([
                Player(
                    id=i,
                    club_id=1,
                    behavior_id=10,
                    name=f"Jugador {i}",
                    power=60,
                    agility=60,
                    control=60,
                    speed=60,
                    strength=60,
                    is_deleted=False,
                )
                for i in range(101, 107)
            ])
            db.flush()

            db.add(DefaultTeam(
                club_id=1,
                line_up={
                    "formationId": 1,
                    "starters": [
                        {"playerId": i, "behaviourId": 10}
                        for i in (101, 102, 103)
                    ],
                    "substitutes": [
                        {"playerId": i, "behaviourId": 10}
                        for i in (104, 105, 106)
                    ],
                },
            ))
            db.commit()

        yield engine

    finally:
        with raw_engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        raw_engine.dispose()


@pytest.fixture
def api(database):
    with Session(database) as db:
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_club] = (
            lambda: SimpleNamespace(id=1)
        )

        # Sin entrar al lifespan: no inicia el scheduler.
        client = TestClient(app)
        client.headers.update({
            "Origin": next(iter(settings.allowed_origins)),
            "X-Futbot-Request": "1",
        })

        try:
            yield client, db
        finally:
            client.close()
            app.dependency_overrides.clear()


def add_league(db, lineup, club_id=1, *, league_id=7, status="open"):
    db.add(League(
        id=league_id,
        name=f"Liga de prueba {league_id}",
        min_teams=3,
        max_teams=8,
        start_datetime=datetime.now(timezone.utc) + timedelta(days=1),
        round_interval="DAILY",
        status=status,
    ))
    db.flush()
    registration = LeagueRegistration(
        league_id=league_id,
        club_id=club_id,
        line_up=lineup,
    )
    db.add(registration)
    return registration


def match_row(status="RUNNING", reference_club=1):
    now = datetime.now(timezone.utc)
    team_key = "local_team" if reference_club == 1 else "visitor_team"

    return Matches(
        match_id=42,
        creator_id=1,
        visitor_id=2,
        init_date=now,
        status=status,
        duration_ms=1000,
        clock_ms=1000 if status == "FINISHED" else 0,
        local_score=2,
        visitor_score=1,
        sequence=5,
        finished_at=now if status == "FINISHED" else None,
        cancellation_reason=(
            "TEST_CANCELLED" if status == "CANCELLED" else None
        ),
        snapshot={
            "state": {
                "players": [{
                    "id": 101,
                    "teamId": reference_club,
                    "behaviourId": 20,
                }],
            },
        },
        runtime_state={
            team_key: {
                "club_id": reference_club,
                "players": [{"id": 101, "behaviour_id": 20}],
            },
        },
    )


def assert_conflict(response, reference):
    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "BEHAVIOUR_IN_USE"
    assert reference in error["fields"]


def test_free_behaviour_is_hidden_and_cannot_be_assigned(api):
    client, db = api

    response = client.delete("/behaviours/20")
    assert response.status_code == 204
    assert response.content == b""

    assert client.get("/behaviours/20").status_code == 404
    assert client.delete("/behaviours/20").status_code == 404

    items = client.get("/behaviours").json()["items"]
    assert 20 not in {item["id"] for item in items}

    response = client.patch(
        "/players/101/behaviour",
        json={"behaviourId": 20},
    )
    assert response.status_code == 404

    lineup = deepcopy(db.get(DefaultTeam, 1).line_up)
    lineup["starters"][0]["behaviourId"] = 20
    response = client.put("/team/default", json=lineup)
    assert response.status_code == 400

    db.expire_all()
    behaviour = db.get(Behavior, 20)
    assert behaviour.is_deleted is True
    assert behaviour.code == DEFAULT_CODES["Equilibrado"]
    assert behaviour.version == 3
    assert db.get(Player, 101).behavior_id == 10


@pytest.mark.parametrize("behaviour_id", [30, 999])
def test_foreign_and_missing_behaviours_return_same_404(api, behaviour_id):
    client, _ = api
    response = client.delete(f"/behaviours/{behaviour_id}")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "BEHAVIOUR_NOT_FOUND",
            "message": "No se encontró el comportamiento.",
            "fields": {},
        },
    }


def test_direct_player_assignment_blocks_deletion(api):
    client, db = api
    db.get(Player, 101).behavior_id = 20
    db.commit()

    assert_conflict(
        client.delete("/behaviours/20"),
        "players.101",
    )

    db.expire_all()
    assert db.get(Behavior, 20).is_deleted is False


@pytest.mark.parametrize("context", ["default", "league"])
@pytest.mark.parametrize(
    "field",
    ["starters", "substitutes", "coach", "penalties"],
)
def test_stored_lineup_references_block_deletion(api, context, field):
    client, db = api
    selection = {"playerId": 101, "behaviourId": 20}
    payload = {
        field: selection if field == "coach" else [selection]
    }

    if context == "default":
        db.get(DefaultTeam, 1).line_up = payload
        reference = "defaultTeam"
    else:
        add_league(db, payload)
        reference = "leagues.7"

    db.commit()

    assert_conflict(client.delete("/behaviours/20"), reference)


def test_legacy_league_lineup_keeps_indirect_reference(api):
    client, db = api
    player = db.get(Player, 101)
    player.behavior_id = 20
    player.is_deleted = True

    add_league(db, [101, 102, 103, 104, 105, 106])
    db.commit()

    assert_conflict(client.delete("/behaviours/20"), "leagues.7")


@pytest.mark.parametrize("status", ["finished", "cancelled", "canceled"])
def test_historical_league_allows_deletion_without_changing_its_history(api, status):
    client, db = api
    lineup = deepcopy(db.get(DefaultTeam, 1).line_up)
    lineup["starters"][0]["behaviourId"] = 20
    registration = add_league(db, lineup, status=status)
    registration.lineup_version = 4
    db.add(LeagueRegistration(league_id=7, club_id=2, line_up=[]))
    league_round = LeagueRound(
        league_id=7, number=1, scheduled_at=datetime.now(timezone.utc), schedule_confirmed=True,
    )
    db.add(league_round)
    db.flush()
    registration_id = registration.id

    match = match_row("FINISHED")
    match.league_round_id = league_round.id
    match.lineup_snapshot = {"leagueId": 7, "teams": {"1": {"lineUp": lineup, "lineupVersion": 4}}}
    db.add(match)
    db.commit()

    def public_history():
        fixture = client.get("/leagues/7/fixture")
        ranking = client.get("/leagues/7/ranking")
        saved_lineup = client.get("/leagues/7/lineup")
        assert fixture.status_code == ranking.status_code == saved_lineup.status_code == 200
        return fixture.json(), ranking.json(), saved_lineup.json()

    match_query = select(Matches.__table__).where(Matches.match_id == 42)
    saved_match = db.execute(match_query).mappings().one()
    history = public_history()
    fixture, ranking, saved_lineup = history
    published_match, = fixture["rounds"][0]["matches"]
    assert (published_match["status"], published_match["localScore"], published_match["visitorScore"]) == (
        "FINISHED", 2, 1,
    )
    assert [(club["id"], club["puntos"]) for club in ranking] == [(1, 3), (2, 0)]
    assert saved_lineup["editable"] is False and saved_lineup["lineUp"] == lineup

    response = client.delete("/behaviours/20")
    assert response.status_code == 204, response.text
    assert client.get("/behaviours/20").status_code == 404

    db.expire_all()
    assert db.get(Behavior, 20).is_deleted is True
    assert db.get(League, 7).status == status
    registration = db.get(LeagueRegistration, registration_id)
    assert registration.line_up == lineup and registration.lineup_version == 4
    assert db.execute(match_query).mappings().one() == saved_match
    assert public_history() == history


@pytest.mark.parametrize("active_status", ["open", "running"])
def test_active_references_still_block_when_a_finished_league_uses_the_same_behaviour(api, active_status):
    client, db = api
    lineup = {"starters": [{"playerId": 101, "behaviourId": 20}]}
    add_league(db, lineup, status="finished")
    add_league(db, lineup, league_id=8, status=active_status)
    db.get(Player, 101).behavior_id = 20
    db.get(DefaultTeam, 1).line_up = lineup
    db.commit()

    response = client.delete("/behaviours/20")
    assert_conflict(response, "leagues.8")
    assert set(response.json()["error"]["fields"]) == {"defaultTeam", "players.101", "leagues.8"}

    db.expire_all()
    assert db.get(Behavior, 20).is_deleted is False


def test_explicit_lineup_override_does_not_use_old_assignment(api):
    client, db = api
    player = db.get(Player, 101)
    player.behavior_id = 20
    player.is_deleted = True
    db.commit()

    # El equipo default sigue seleccionando explícitamente el 10.
    assert client.delete("/behaviours/20").status_code == 204


@pytest.mark.parametrize(
    "status",
    ["WAITING", "WAITING_OPPONENT", "SCHEDULED", "RUNNING"],
)
@pytest.mark.parametrize("source", ["snapshot", "runtime"])
def test_active_match_reference_blocks_deletion(api, status, source):
    client, db = api
    row = match_row(status)

    if source == "snapshot":
        row.runtime_state = None
    else:
        row.snapshot = None

    db.add(row)
    db.commit()

    assert_conflict(client.delete("/behaviours/20"), "matches.42")


@pytest.mark.parametrize("status", ["FINISHED", "CANCELLED"])
def test_historical_matches_are_preserved(api, status):
    client, db = api
    row = match_row(status)
    db.add(row)
    db.commit()

    before = (
        deepcopy(row.snapshot),
        deepcopy(row.runtime_state),
        row.local_score,
        row.visitor_score,
        row.sequence,
        row.finished_at,
        row.status,
    )

    assert client.delete("/behaviours/20").status_code == 204

    db.expire_all()
    row = db.get(Matches, 42)
    after = (
        row.snapshot,
        row.runtime_state,
        row.local_score,
        row.visitor_score,
        row.sequence,
        row.finished_at,
        row.status,
    )

    assert after == before


def test_foreign_club_references_do_not_block_or_leak(api):
    client, db = api
    payload = {"coach": {"behaviourId": 20}}

    db.add(DefaultTeam(club_id=2, line_up=payload))
    add_league(db, payload, club_id=2)

    # Partido compartido, pero la referencia está en los perfiles rivales.
    db.add(match_row(reference_club=2))
    db.commit()

    assert client.delete("/behaviours/20").status_code == 204


def test_commit_failure_rolls_back_soft_deletion(api, monkeypatch):
    client, db = api

    def fail_commit():
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(db, "commit", fail_commit)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        client.delete("/behaviours/20")

    db.expire_all()
    assert db.get(Behavior, 20).is_deleted is False


def wait_until_blocked(engine, pid, future):
    deadline = monotonic() + 5

    with engine.connect() as observer:
        while monotonic() < deadline:
            blocked = observer.scalar(
                text(
                    "SELECT cardinality(pg_blocking_pids(:pid)) > 0"
                ),
                {"pid": pid},
            )

            if blocked:
                return

            if future.done():
                future.result()
                pytest.fail(
                    "La segunda operación terminó sin esperar el bloqueo."
                )

            sleep(0.01)

    pytest.fail("PostgreSQL no registró la espera del bloqueo.")


@pytest.mark.parametrize("first_operation", ["assign", "delete"])
def test_assignment_and_deletion_are_serialized(
    database,
    monkeypatch,
    first_operation,
):
    pids = Queue()

    def second_operation():
        with Session(database) as db:
            db.execute(text("SET LOCAL lock_timeout = '10s'"))

            # Precargar verifica también que no se use un objeto ORM viejo.
            db.get(Behavior, 20)
            pids.put(db.scalar(text("SELECT pg_backend_pid()")))

            try:
                if first_operation == "assign":
                    behaviour_service.delete_behaviour(db, 1, 20)
                else:
                    player_service.assign_behaviour(db, 1, 101, 20)
            except AppError as error:
                return error.code

            return "OK"

    with Session(database, expire_on_commit=False) as first:
        real_commit = first.commit

        # Retener la primera transacción para observar la espera de la otra.
        monkeypatch.setattr(first, "commit", lambda: None)

        if first_operation == "assign":
            player_service.assign_behaviour(first, 1, 101, 20)
        else:
            behaviour_service.delete_behaviour(first, 1, 20)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(second_operation)

            try:
                pid = pids.get(timeout=5)
                wait_until_blocked(database, pid, future)
            finally:
                real_commit()

            expected = (
                "BEHAVIOUR_IN_USE"
                if first_operation == "assign"
                else "BEHAVIOUR_NOT_FOUND"
            )
            assert future.result(timeout=15) == expected

    with Session(database) as db:
        behaviour = db.get(Behavior, 20)
        player = db.get(Player, 101)

        assert behaviour.is_deleted == (first_operation == "delete")
        assert player.behavior_id == (
            20 if first_operation == "assign" else 10
        )
