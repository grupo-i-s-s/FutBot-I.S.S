"""Disponibilidad de amistosos con HTTP real y bases aisladas de los datos de trabajo."""
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.controller.auth_controller import auth_router
from app.controller.club_controller import club_router
from app.controller.matches_controller import matches_router
from app.database import Base, engine as database_engine, get_db
from app.dependencies import require_browser_write
from app.errors import AppError
from app.main import app_error_handler, validation_error_handler
from app.models.auth_model import AuthSession, Club, User
from app.models.behaviour_model import Behavior
from app.models.dt_model import Dt, DtBehaviour
from app.models.league_model import League, LeagueRound
from app.models.matches_model import Matches
from app.models.player_model import Player
from app.models.team_model import DefaultTeam
from app.repository import user_repository
from app.schemas.avatar_schemas import DEFAULT_AVATAR
from app.schemas.matches_schemas import CreateFriendlyMatchRequest
from app.security import hash_password
from app.services import matches_service


def set_availability(client, available):
    response = client.get("/club/me")
    assert response.status_code == 200, response.text
    club = response.json()
    response = client.patch("/club/me", json={
        "name": club["name"], "avatar": club["avatar"], "friendlyAvailable": available,
    })
    assert response.status_code == 200, response.text
    assert response.json()["friendlyAvailable"] is available


@pytest.fixture
def context(sqlite_match_dates):
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine, tables=[
        model.__table__
        for model in (User, Club, AuthSession, Behavior, Player, DefaultTeam, League, LeagueRound, Matches, DtBehaviour, Dt)
    ])
    application = FastAPI(dependencies=[Depends(require_browser_write)])
    for router in (auth_router, club_router, matches_router):
        application.include_router(router)
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)

    def database():
        with Session(engine, expire_on_commit=False) as db:
            yield db

    application.dependency_overrides[get_db] = database
    try:
        # La aplicación aislada no inicia el scheduler de la API de trabajo.
        with ExitStack() as clients:
            def account(label, available=False):
                client = clients.enter_context(TestClient(application, base_url="https://testserver"))
                client.headers.update({
                    "Origin": next(iter(settings.allowed_origins)), "X-FutBot-Request": "1",
                })
                credentials = {"email": f"availability_{label}@example.com", "password": "availability-password"}
                with Session(engine, expire_on_commit=False) as db:
                    user = user_repository.create_user(
                        db, email=credentials["email"], password_hash=hash_password(credentials["password"]),
                    )
                    club = user_repository.create_club(
                        db, user_id=user.id, name=f"Availability {label}", avatar=DEFAULT_AVATAR,
                    )
                    db.commit()
                response = client.post("/auth/login", json=credentials)
                assert response.status_code == 200, response.text
                if available:
                    set_availability(client, True)
                return SimpleNamespace(client=client, id=club.id)

            yield SimpleNamespace(engine=engine, account=account)
    finally:
        engine.dispose()


def create_match(client):
    response = client.post("/friendly-matches", json={
        "startDateTime": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    })
    assert response.status_code == 201, response.text
    return response.json()["matchId"]


def assert_waiting_match(engine, match_id):
    with Session(engine) as db:
        match = db.get(Matches, match_id)
        assert (match.visitor_id, match.status, match.sequence) == (None, "WAITING_OPPONENT", 0)


def test_unavailable_club_cannot_create_until_it_opts_in(context):
    owner = context.account("owner")
    response = owner.client.post("/friendly-matches", json={
        "startDateTime": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    })

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "CLUB_NOT_AVAILABLE"
    with Session(context.engine) as db:
        assert db.scalar(select(func.count()).select_from(Matches)) == 0
    set_availability(owner.client, True)
    assert_waiting_match(context.engine, create_match(owner.client))


def test_listing_filters_unavailable_creators_and_retains_existing_match_filters(context):
    viewer = context.account("viewer")
    available = context.account("available", available=True)
    unavailable = context.account("unavailable")
    now = datetime.now(timezone.utc)
    with Session(context.engine) as db:
        early = Matches(creator_id=available.id, init_date=now + timedelta(hours=1), status="WAITING")
        later = Matches(creator_id=available.id, init_date=now + timedelta(hours=2), status="WAITING_OPPONENT")
        db.add_all([
            early, later,
            Matches(creator_id=unavailable.id, init_date=now + timedelta(hours=1), status="WAITING_OPPONENT"),
            Matches(creator_id=viewer.id, init_date=now + timedelta(hours=1), status="WAITING_OPPONENT"),
            Matches(creator_id=available.id, visitor_id=viewer.id, init_date=now + timedelta(hours=1), status="SCHEDULED"),
            Matches(creator_id=available.id, init_date=now - timedelta(hours=1), status="WAITING"),
            Matches(creator_id=available.id, init_date=now + timedelta(hours=1), status="RUNNING"),
        ])
        db.commit()
        expected = [early.match_id, later.match_id]

    response = viewer.client.get("/friendly-matches")

    assert response.status_code == 200, response.text
    assert [item["matchId"] for item in response.json()["items"]] == expected


def test_creator_opting_out_after_listing_cannot_be_joined_via_direct_request(context):
    owner = context.account("owner", available=True)
    visitor = context.account("visitor", available=True)
    match_id = create_match(owner.client)
    assert [item["matchId"] for item in visitor.client.get("/friendly-matches").json()["items"]] == [match_id]

    set_availability(owner.client, False)
    assert visitor.client.get("/friendly-matches").json()["items"] == []
    response = visitor.client.post("/friendly-matches/join", json={"idPartido": match_id})

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "CLUB_NOT_AVAILABLE"
    assert_waiting_match(context.engine, match_id)


def test_visitor_opting_out_after_listing_cannot_join(context):
    owner = context.account("owner", available=True)
    visitor = context.account("visitor", available=True)
    match_id = create_match(owner.client)
    assert [item["matchId"] for item in visitor.client.get("/friendly-matches").json()["items"]] == [match_id]

    set_availability(visitor.client, False)
    response = visitor.client.post("/friendly-matches/join", json={"idPartido": match_id})

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "CLUB_NOT_AVAILABLE"
    assert_waiting_match(context.engine, match_id)


def test_available_clubs_can_join_and_keep_their_matches_after_opting_out(context):
    owner = context.account("owner", available=True)
    visitor = context.account("visitor", available=True)
    match_id = create_match(owner.client)

    response = visitor.client.post("/friendly-matches/join", json={"idPartido": match_id})

    assert response.status_code == 200, response.text
    with Session(context.engine) as db:
        match = db.get(Matches, match_id)
        assert (match.visitor_id, match.status, match.sequence) == (visitor.id, "SCHEDULED", 1)
    for account in (owner, visitor):
        set_availability(account.client, False)
        response = account.client.get("/friendly-matches/me")
        assert response.status_code == 200, response.text
        assert [(item["matchId"], item["status"]) for item in response.json()] == [(match_id, "SCHEDULED")]


@pytest.fixture
def postgres_context():
    """Cada conexión usa un esquema UUID; nunca se escriben las tablas públicas."""
    schema = "friendly_availability_" + uuid4().hex
    with database_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        database_engine.url,
        connect_args={"options": f"-csearch_path={schema}", "connect_timeout": 3},
    )
    try:
        Base.metadata.create_all(engine, tables=[model.__table__ for model in (User, Club, League, LeagueRound, Matches)])
        with Session(engine) as db:
            for club_id in (1, 2):
                db.add(User(id=club_id, email=f"availability-{club_id}@example.com", password_hash="unused"))
            db.flush()
            for club_id in (1, 2):
                db.add(Club(id=club_id, user_id=club_id, name=f"Availability {club_id}",
                            avatar="avatar-01.png", friendly_available=True))
            db.flush()
            db.add(Matches(match_id=42, creator_id=1, init_date=datetime.now(timezone.utc) + timedelta(hours=1),
                           status="WAITING_OPPONENT"))
            db.commit()
        yield engine
    finally:
        engine.dispose()
        with database_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


@pytest.mark.parametrize("operation, changed_club", [("create", 1), ("join", 1), ("join", 2)])
def test_committed_opt_out_is_rechecked_even_with_cached_available_clubs(postgres_context, operation, changed_club):
    with Session(postgres_context) as stale_request:
        cached = {club.id: club for club in stale_request.scalars(select(Club))}
        assert all(club.friendly_available for club in cached.values())
        with Session(postgres_context) as other_request:
            other_request.get(Club, changed_club).friendly_available = False
            other_request.commit()
        assert cached[changed_club].friendly_available is True

        with pytest.raises(AppError) as error:
            if operation == "create":
                matches_service.create_friendly_match(
                    stale_request, 1,
                    CreateFriendlyMatchRequest(startDateTime=datetime.now(timezone.utc) + timedelta(hours=1)),
                )
            else:
                matches_service.join_match(stale_request, 42, 2)

        assert error.value.code == "CLUB_NOT_AVAILABLE"
        assert cached[changed_club].friendly_available is False
        stale_request.rollback()
    assert_waiting_match(postgres_context, 42)
    with Session(postgres_context) as db:
        assert db.scalar(select(func.count()).select_from(Matches)) == 1
