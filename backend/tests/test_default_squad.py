"""Pruebas del plantel inicial (comportamientos y jugadores default) creado al registrarse.

- Las pruebas unitarias usan sesiones simuladas y no necesitan base de datos.
- Las de integración usan la base configurada, pero trabajan dentro de una
  transacción que se revierte al final: no dejan datos. Requieren que las
  migraciones 001 y 002 estén aplicadas.
"""
from collections.abc import Iterator
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.main import app
from app.models.auth_model import Club, User
from app.models.behaviour_model import Behavior
from app.models.player_model import Player
from app.repository import behaviour_repository, player_repository
from app.schemas.auth_schemas import RegisterRequest
from app.services import auth_service

PACSS = ("power", "agility", "control", "speed", "strength")
BROWSER_HEADERS = {
    "Origin": next(iter(settings.allowed_origins)),
    "X-Futbot-Request": "1",
}


def register_payload(suffix: str = "a") -> dict:
    return {
        "email": f"test_squad_{suffix}@example.com",
        "password": "password-segura",
        "passwordConfirmation": "password-segura",
        "clubName": f"Club {suffix}",
        "avatar": "avatar-1",
    }


# --- Datos default -----------------------------------------------------------

def test_there_are_exactly_six_default_players_with_unique_names():
    names = [player["name"] for player in player_repository.DEFAULT_PLAYERS]

    assert len(names) == 6
    assert len(set(names)) == 6
    assert all(0 < len(name) <= 50 for name in names)


@pytest.mark.parametrize(
    "player",
    player_repository.DEFAULT_PLAYERS,
    ids=lambda player: player["name"],
)
def test_default_player_has_valid_pacss(player):
    # Mismas reglas que los CHECK de la tabla players.
    assert set(PACSS) <= player.keys()
    assert all(20 <= player[attr] <= 100 for attr in PACSS)
    assert sum(player[attr] for attr in PACSS) == 300


# --- Repositorios -----------------------------------------------------------

def test_create_default_behaviours_belong_to_club_and_are_flushed():
    db = Mock()

    behaviors = behaviour_repository.create_default_behaviours(db, club_id=7)

    assert len(behaviors) == 3
    assert all(isinstance(behavior, Behavior) for behavior in behaviors)
    assert all(behavior.club_id == 7 for behavior in behaviors)
    assert len({behavior.name for behavior in behaviors}) == 3
    assert all(behavior.description and behavior.code for behavior in behaviors)
    db.add_all.assert_called_once_with(behaviors)
    db.flush.assert_called_once_with()


def test_create_default_players_assigns_club_and_behaviour():
    db = Mock()
    behaviors = [Behavior(id=i, club_id=7, name=str(i), description="d", code="c") for i in (3, 4, 5)]

    players = player_repository.create_default_players(db, club_id=7, behaviors=behaviors)

    assert len(players) == len(player_repository.DEFAULT_PLAYERS)
    assert all(isinstance(player, Player) for player in players)
    assert all(player.club_id == 7 for player in players)
    assert [player.behavior_id for player in players] == [3, 3, 4, 4, 5, 5]
    assert [p.name for p in players] == [p["name"] for p in player_repository.DEFAULT_PLAYERS]
    db.add_all.assert_called_once_with(players)
    db.flush.assert_called_once_with()


# --- Servicio de registro (sin base) ---------------------------------------

@pytest.fixture
def fake_registration(monkeypatch):
    """Simula los repositorios y registra el orden de las llamadas."""
    calls = []
    db = Mock()
    db.commit.side_effect = lambda: calls.append("commit")

    repo = auth_service.user_repository
    monkeypatch.setattr(repo, "get_by_email", lambda *a, **k: None)
    monkeypatch.setattr(
        repo, "create_user",
        lambda *a, **k: User(id=1, email=k["email"], password_hash="x"),
    )
    monkeypatch.setattr(
        repo, "create_club",
        lambda *a, **k: Club(id=10, user_id=k["user_id"], name=k["name"], avatar=k["avatar"]),
    )

    def fake_behaviours(session, club_id):
        calls.append(("behaviours", club_id))
        return [
            Behavior(id=i, club_id=club_id, name=str(i), description="d", code="c")
            for i in (97, 98, 99)
        ]

    def fake_players(session, club_id, behaviors):
        calls.append(("players", club_id, tuple(behavior.id for behavior in behaviors)))
        return []

    monkeypatch.setattr(auth_service.behaviour_repository, "create_default_behaviours", fake_behaviours)
    monkeypatch.setattr(auth_service.player_repository, "create_default_players", fake_players)
    return db, calls


def test_register_creates_default_squad_before_commit(fake_registration):
    db, calls = fake_registration

    auth_service.register(db, RegisterRequest.model_validate(register_payload()))

    assert calls == [("behaviours", 10), ("players", 10, (97, 98, 99)), "commit"]
    db.rollback.assert_not_called()


def test_register_rolls_back_everything_if_default_squad_fails(fake_registration, monkeypatch):
    db, calls = fake_registration

    def failing_players(*args, **kwargs):
        raise RuntimeError("falló la creación de jugadores")

    monkeypatch.setattr(auth_service.player_repository, "create_default_players", failing_players)

    with pytest.raises(RuntimeError):
        auth_service.register(db, RegisterRequest.model_validate(register_payload()))

    db.commit.assert_not_called()
    db.rollback.assert_called_once_with()


# --- Integración con PostgreSQL (con rollback) ------------------------------

@pytest.fixture
def db_session() -> Iterator[Session]:
    """Sesión sobre una transacción externa que se revierte al terminar.

    Los commit del servicio sólo liberan savepoints, así que nada queda guardado.
    """
    missing = {"users", "clubs", "behaviors", "players"} - set(inspect(engine).get_table_names())
    if missing:
        pytest.fail(f"Faltan tablas {sorted(missing)}: aplicá las migraciones antes de correr los tests.")

    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    app.dependency_overrides[get_db] = lambda: session
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()
        transaction.rollback()
        connection.close()


def register_and_get_club(client: TestClient, session: Session, suffix: str) -> Club:
    payload = register_payload(suffix)
    response = client.post("/auth/register", json=payload, headers=BROWSER_HEADERS)
    assert response.status_code == 201, response.text

    return session.scalar(
        select(Club).join(User, User.id == Club.user_id).where(User.email == payload["email"])
    )


def test_register_endpoint_persists_default_behaviours_and_players(db_session):
    with TestClient(app) as client:
        club = register_and_get_club(client, db_session, "a")

    behaviors = db_session.scalars(select(Behavior).where(Behavior.club_id == club.id)).all()
    players = db_session.scalars(select(Player).where(Player.club_id == club.id)).all()

    assert len(behaviors) == 3
    assert len(players) == 6
    assert {p.name for p in players} == {p["name"] for p in player_repository.DEFAULT_PLAYERS}
    assert {behavior.name for behavior in behaviors} == {name for name, _ in behaviour_repository.DEFAULT_BEHAVIOURS}
    assert {p.behavior_id for p in players} == {behavior.id for behavior in behaviors}
    assert all(sum(p.behavior_id == behavior.id for p in players) == 2 for behavior in behaviors)
    assert all(not p.is_deleted for p in players)
    assert all(not behavior.is_deleted for behavior in behaviors)


def test_each_club_gets_its_own_default_squad(db_session):
    with TestClient(app) as client:
        club_a = register_and_get_club(client, db_session, "a")
        club_b = register_and_get_club(client, db_session, "b")

    def squad(club):
        players = db_session.scalars(select(Player).where(Player.club_id == club.id)).all()
        behavior_ids = set(db_session.scalars(select(Behavior.id).where(Behavior.club_id == club.id)))
        return players, behavior_ids

    players_a, behaviors_a = squad(club_a)
    players_b, behaviors_b = squad(club_b)

    assert len(players_a) == len(players_b) == 6
    assert len(behaviors_a) == len(behaviors_b) == 3
    assert {p.id for p in players_a}.isdisjoint({p.id for p in players_b})
    assert behaviors_a.isdisjoint(behaviors_b)
    # Cada jugador usa un comportamiento de su propio club.
    assert all(p.behavior_id in behaviors_a for p in players_a)
    assert all(p.behavior_id in behaviors_b for p in players_b)


def test_failed_registration_does_not_leave_players(db_session):
    with TestClient(app) as client:
        register_and_get_club(client, db_session, "a")
        players_before = db_session.scalar(select(func.count()).select_from(Player))

        # Mismo email: el registro se rechaza y no debe crear otro plantel.
        duplicate = register_payload("b") | {"email": register_payload("a")["email"]}
        response = client.post("/auth/register", json=duplicate, headers=BROWSER_HEADERS)

    assert response.status_code == 400
    assert db_session.scalar(select(func.count()).select_from(Player)) == players_before
