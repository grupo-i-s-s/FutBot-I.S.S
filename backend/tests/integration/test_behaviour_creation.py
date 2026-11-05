from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.dependencies import get_current_club
from app.main import app
from app.models.auth_model import Club, User
from app.models.behaviour_model import Behavior
from app.models.player_model import Player


CODE = (
    "from primitives.behaviours import Action\n"
    "def decide(observation):\n"
    "    return Action(observation.ball_position)"
)


def payload(**changes):
    return {
        "name": "Nuevo",
        "code": CODE,
        "kind": "PLAYER",
        **changes,
    }


def count_behaviours(db):
    return db.scalar(select(func.count()).select_from(Behavior))


@pytest.fixture
def api():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Club.__table__,
            Behavior.__table__,
            Player.__table__,
        ],
    )
    previous_overrides = app.dependency_overrides.copy()

    with Session(engine) as db:
        db.connection().exec_driver_sql("PRAGMA foreign_keys=ON")

        for club_id in (1, 2):
            db.add(User(
                id=club_id,
                email=f"club{club_id}@example.com",
                password_hash="unused",
            ))
        db.flush()

        for club_id in (1, 2):
            db.add(Club(
                id=club_id,
                user_id=club_id,
                name=f"Club {club_id}",
                avatar="avatar-1",
            ))
        db.flush()

        for club_id in (1, 2):
            db.add(Behavior(
                id=club_id,
                club_id=club_id,
                name=f"Inicial {club_id}",
                description="",
                code=CODE,
                kind="PLAYER",
                version=1,
                validation_status="VALID",
                is_deleted=False,
            ))
        db.flush()

        db.add(Player(
            id=22,
            club_id=2,
            behavior_id=2,
            name="Jugador rival",
            power=60,
            agility=60,
            control=60,
            speed=60,
            strength=60,
            is_deleted=False,
        ))
        db.commit()

        club = SimpleNamespace(id=1)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_club] = lambda: club

        # Sin contexto de lifespan: no inicia el scheduler.
        client = TestClient(app)
        client.headers.update({
            "Origin": next(iter(settings.allowed_origins)),
            "X-Futbot-Request": "1",
        })

        try:
            yield SimpleNamespace(client=client, db=db, club=club)
        finally:
            client.close()
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous_overrides)

    engine.dispose()


def test_creation_persists_and_appears_in_catalog(api):
    response = api.client.post("/behaviours", json=payload())

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Nuevo"
    assert body["kind"] == "PLAYER"
    assert body["version"] == 1
    assert body["validationStatus"] == "VALID"

    saved = api.db.get(Behavior, body["id"])
    assert saved.club_id == 1
    assert saved.code == CODE
    assert count_behaviours(api.db) == 3

    listing = api.client.get("/behaviours?kind=PLAYER")
    assert listing.status_code == 200
    assert body["id"] in {
        item["id"] for item in listing.json()["items"]
    }

    detail = api.client.get(f"/behaviours/{body['id']}")
    assert detail.status_code == 200
    for field in ("id", "name", "kind", "version", "validationStatus"):
        assert detail.json()[field] == body[field]
    assert detail.json()["code"] == CODE


@pytest.mark.parametrize("code, diagnostic", [
    (
        "def decide(observation)\n    return None",
        "SYNTAX_ERROR",
    ),
    (
        "def decide(observation):\n    return None",
        "INVALID_ACTION",
    ),
    (
        "import os\ndef decide(observation):\n    return None",
        "IMPORT_NOT_ALLOWED",
    ),
])
def test_invalid_code_is_not_saved(api, code, diagnostic):
    response = api.client.post(
        "/behaviours",
        json=payload(code=code),
    )

    assert response.status_code == 400, response.text
    error = response.json()["error"]
    assert error["code"] == "BEHAVIOUR_INVALID"
    assert error["diagnostics"][0]["code"] == diagnostic
    assert count_behaviours(api.db) == 2


@pytest.mark.parametrize("name", ["", "   ", "x" * 51])
def test_invalid_name_is_not_saved(api, name):
    response = api.client.post(
        "/behaviours",
        json=payload(name=name),
    )

    assert response.status_code == 400
    assert "name" in response.json()["error"]["fields"]
    assert count_behaviours(api.db) == 2


@pytest.mark.parametrize(
    "field",
    ["clubId", "club_id", "userId", "ownerId"],
)
def test_client_cannot_choose_owner(api, field):
    response = api.client.post(
        "/behaviours",
        json=payload(**{field: 2}),
    )

    assert response.status_code == 400
    assert field in response.json()["error"]["fields"]
    assert count_behaviours(api.db) == 2


def test_code_size_is_measured_in_utf8_bytes(api):
    exact = CODE + "\n#"
    exact += "x" * (65_536 - len(exact.encode("utf-8")))

    response = api.client.post(
        "/behaviours",
        json=payload(code=exact),
    )
    assert response.status_code == 201, response.text

    for name, code in (
        ("Exceso ASCII", exact + "x"),
        ("Exceso UTF8", CODE + "\n#" + "é" * 32_768),
    ):
        response = api.client.post(
            "/behaviours",
            json=payload(name=name, code=code),
        )

        assert response.status_code == 400
        assert "code" in response.json()["error"]["fields"]

    assert count_behaviours(api.db) == 3


def test_other_club_cannot_list_read_or_assign_created_behaviour(api):
    created = api.client.post("/behaviours", json=payload())
    assert created.status_code == 201
    behaviour_id = created.json()["id"]

    api.club.id = 2

    listing = api.client.get("/behaviours?kind=PLAYER")
    assert listing.status_code == 200
    assert behaviour_id not in {
        item["id"] for item in listing.json()["items"]
    }

    detail = api.client.get(f"/behaviours/{behaviour_id}")
    assert detail.status_code == 404

    assigned = api.client.patch(
        "/players/22/behaviour",
        json={"behaviourId": behaviour_id},
    )
    assert assigned.status_code == 404
    assert assigned.json()["error"]["code"] == "BEHAVIOUR_NOT_FOUND"
    assert api.db.get(Player, 22).behavior_id == 2

    # La unicidad del nombre es por club.
    same_name = api.client.post("/behaviours", json=payload())
    assert same_name.status_code == 201
    assert api.db.get(Behavior, same_name.json()["id"]).club_id == 2


@pytest.mark.parametrize("failure_at", ["flush", "commit"])
def test_duplicate_name_returns_409_and_rolls_back(
    api,
    monkeypatch,
    failure_at,
):
    # Simula el diagnóstico de la restricción de PostgreSQL.
    original = Exception("duplicate")
    original.diag = SimpleNamespace(
        constraint_name="uq_behaviors_club_name",
    )
    failure = IntegrityError("unused", {}, original)

    rollback = Mock(wraps=api.db.rollback)
    monkeypatch.setattr(api.db, "rollback", rollback)
    monkeypatch.setattr(
        api.db,
        failure_at,
        Mock(side_effect=failure),
    )

    response = api.client.post("/behaviours", json=payload())

    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "BEHAVIOUR_NAME_DUPLICATE"
    assert "name" in error["fields"]
    rollback.assert_called_once()

    monkeypatch.undo()
    assert count_behaviours(api.db) == 2


def test_unrelated_integrity_error_is_not_reported_as_duplicate(
    api,
    monkeypatch,
):
    original = Exception("other constraint")
    original.diag = SimpleNamespace(
        constraint_name="another_constraint",
    )
    failure = IntegrityError("unused", {}, original)

    rollback = Mock(wraps=api.db.rollback)
    monkeypatch.setattr(api.db, "rollback", rollback)
    monkeypatch.setattr(
        api.db,
        "flush",
        Mock(side_effect=failure),
    )

    with pytest.raises(IntegrityError) as captured:
        api.client.post("/behaviours", json=payload())

    assert captured.value is failure
    rollback.assert_called_once()