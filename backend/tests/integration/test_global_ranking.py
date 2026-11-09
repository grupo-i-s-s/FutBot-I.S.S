from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.controller.club_controller import club_router
from app.controller.stats_controller import stats_router
from app.database import get_db
from app.errors import AppError
from app.main import app_error_handler, validation_error_handler
from app.models.auth_model import AuthSession, Club, User
from app.models.league_model import League, LeagueRound
from app.models.matches_model import Matches, TEST_OPPONENT_CLUB_ID
from app.models.stats_model import Stats
from app.security import hash_session_token, new_session_token
from test_league_start import database, league_data


def make_client(database):
    app = FastAPI()
    app.include_router(stats_router)
    app.include_router(club_router)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    def database_session():
        with Session(database) as db:
            yield db

    app.dependency_overrides[get_db] = database_session
    return TestClient(app)


def create_session(db, club_id):
    token = new_session_token()
    now = datetime.now(timezone.utc)
    db.add(AuthSession(
        token_hash=hash_session_token(token),
        user_id=db.get(Club, club_id).user_id,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    ))
    return token


def test_ranking_and_profile_share_public_results_and_require_session(database, league_data):
    local_id, rival_id, *_ = league_data.clubs
    past = datetime.now(timezone.utc) - timedelta(days=3)
    with Session(database) as db:
        token = create_session(db, local_id)
        if db.get(Club, TEST_OPPONENT_CLUB_ID) is None:
            user = User(email="bot-ranking@example.com", password_hash="unused")
            db.add(user)
            db.flush()
            db.add(Club(id=TEST_OPPONENT_CLUB_ID, user_id=user.id, name="Bot", avatar="avatar-01.png"))

        private_league = League(
            name="Liga privada", start_datetime=past, min_teams=3, max_teams=3,
            round_interval="DAILY", status="finished", is_private=True,
        )
        round_ = LeagueRound(league_id=league_data.id, number=1, scheduled_at=past)
        db.add_all([private_league, round_])
        db.flush()

        def finished_match(goals_for, goals_against, *, visitor=rival_id, **league_link):
            return Matches(
                creator_id=local_id, visitor_id=visitor, init_date=past, finished_at=past,
                status="FINISHED", duration_ms=300_000, clock_ms=300_000,
                local_score=goals_for, visitor_score=goals_against, snapshot={}, **league_link,
            )

        db.add_all([
            # Un partido anterior al ranking y otro relacionado por ronda.
            finished_match(2, 0, league_id=league_data.id),
            finished_match(1, 1, league_round_id=round_.id),
            finished_match(9, 0),
            finished_match(8, 0, league_id=private_league.id),
            finished_match(7, 0, visitor=TEST_OPPONENT_CLUB_ID, league_id=league_data.id),
            Matches(
                creator_id=local_id, visitor_id=rival_id, init_date=past, finished_at=past,
                status="CANCELLED", cancellation_reason="CHECKPOINT_UNRECOVERABLE",
                local_score=6, visitor_score=0, league_round_id=round_.id,
            ),
            # El acumulado incorrecto anterior queda fuera de la fuente de verdad.
            Stats(club_id=local_id, points=99, played=99),
        ])
        db.commit()

    with make_client(database) as client:
        assert client.get("/ranking-global").status_code == 401
        client.cookies.set(settings.cookie_name, token)
        response = client.get("/ranking-global")
        assert response.status_code == 200, response.text
        assert [club["id"] for club in response.json()["items"]] == league_data.clubs
        leader = response.json()["items"][0]
        assert leader == {
            "id": local_id, "name": "Club 0", "avatar": "avatar-1", "position": 1,
            "points": 4, "played": 2, "wins": 1, "draws": 1, "losses": 0,
            "goalsFor": 3, "goalsAgainst": 1, "dg": 2,
        }
        profile = client.get(f"/clubs/{local_id}").json()
        assert profile["ranking"]["points"] == leader["points"]
        assert profile["ranking"]["position"] == leader["position"]
        assert profile["stats"]["played"] == 4
        assert client.get("/clubs", params={"name": "bot"}).json()["items"] == []


def test_ranking_reaches_position_101_and_validates_page_bounds(database, league_data):
    with Session(database) as db:
        token = create_session(db, league_data.clubs[0])
        users = [User(email=f"ranking-{index}@example.com", password_hash="unused") for index in range(97)]
        db.add_all(users)
        db.flush()
        db.add_all([
            Club(user_id=user.id, name=f"Ranking {index}", avatar="avatar-01.png")
            for index, user in enumerate(users)
        ])
        db.commit()

    with make_client(database) as client:
        client.cookies.set(settings.cookie_name, token)
        first = client.get("/ranking-global", params={"pageSize": 100}).json()
        second = client.get("/ranking-global", params={"pageSize": 100, "page": 2}).json()
        assert first["total"] == second["total"] == 101
        assert first["hasNext"] and not second["hasNext"]
        assert [club["position"] for club in first["items"]] == list(range(1, 101))
        assert [club["position"] for club in second["items"]] == [101]
        assert client.get("/ranking-global", params={"pageSize": 101}).status_code == 400
        assert client.get("/ranking-global", params={"pageSize": 100, "page": 2**63}).status_code == 400
