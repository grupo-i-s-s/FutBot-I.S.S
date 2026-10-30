"""Pruebas del plantel inicial (comportamientos y jugadores default) creado al registrarse.

- Las pruebas unitarias están en tests/unit/test_default_squad.py y test_auth_service.py.
- Las de integración usan la base configurada, pero trabajan dentro de una
  transacción que se revierte al final: no dejan datos. Requieren que las
  migraciones 001 y 002 estén aplicadas.
"""
import pytest
from collections.abc import Iterator
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
