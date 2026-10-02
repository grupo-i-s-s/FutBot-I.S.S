from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.league_model import League, LeagueRegistration

from tests.test_default_squad import (
    BROWSER_HEADERS,
    db_session,
    register_and_get_club,
)


def test_join_league_creates_registration(db_session):
    with TestClient(app) as client:
        club = register_and_get_club(
            client,
            db_session,
            "league_join",
        )

        login_response = client.post(
            "/auth/login",
            json={
                "email": "test_squad_league_join@example.com",
                "password": "password-segura",
            },
            headers=BROWSER_HEADERS,
        )

        assert login_response.status_code == 200

        league = League(
            name="Liga Test Join",
            min_teams=2,
            max_teams=4,
            start_datetime=datetime.now(timezone.utc) + timedelta(days=1),
            round_interval="daily",
            status="open",
        )

        db_session.add(league)
        db_session.flush()

        line_up = [1, 2, 3, 4, 5, 6]

        response = client.post(
            f"/leagues/{league.id}/join",
            json={
                "clubId": club.id,
                "lineUp": line_up,
            },
            headers=BROWSER_HEADERS,
        )

    assert response.status_code == 201

    registration = db_session.scalar(
        select(LeagueRegistration).where(
            LeagueRegistration.league_id == league.id,
            LeagueRegistration.club_id == club.id,
        )
    )

    assert registration is not None
    assert registration.line_up == line_up


def test_join_league_uses_one_available_slot(db_session):
    with TestClient(app) as client:
        club = register_and_get_club(
            client,
            db_session,
            "league_slot",
        )

        login_response = client.post(
            "/auth/login",
            json={
                "email": "test_squad_league_slot@example.com",
                "password": "password-segura",
            },
            headers=BROWSER_HEADERS,
        )

        assert login_response.status_code == 200

        league = League(
            name="Liga Test Slot",
            min_teams=2,
            max_teams=2,
            start_datetime=datetime.now(timezone.utc) + timedelta(days=1),
            round_interval="daily",
            status="open",
        )

        db_session.add(league)
        db_session.flush()

        response = client.post(
            f"/leagues/{league.id}/join",
            json={
                "clubId": club.id,
                "lineUp": [1, 2, 3, 4, 5, 6],
            },
            headers=BROWSER_HEADERS,
        )

        assert response.status_code == 201

        registration_count = db_session.query(
            LeagueRegistration
        ).filter(
            LeagueRegistration.league_id == league.id
        ).count()

        assert registration_count == 1
        assert league.max_teams - registration_count == 1


def test_join_league_rejects_when_full(db_session):
    with TestClient(app) as client:
        club_a = register_and_get_club(
            client,
            db_session,
            "league_full_a",
        )

        login_response = client.post(
            "/auth/login",
            json={
                "email": "test_squad_league_full_a@example.com",
                "password": "password-segura",
            },
            headers=BROWSER_HEADERS,
        )

        assert login_response.status_code == 200

        league = League(
            name="Liga Test Full",
            min_teams=2,
            max_teams=2,
            start_datetime=datetime.now(timezone.utc) + timedelta(days=1),
            round_interval="daily",
            status="open",
        )

        db_session.add(league)
        db_session.flush()

        response_a = client.post(
            f"/leagues/{league.id}/join",
            json={
                "clubId": club_a.id,
                "lineUp": [1, 2, 3, 4, 5, 6],
            },
            headers=BROWSER_HEADERS,
        )

        assert response_a.status_code == 201

        club_b = register_and_get_club(
            client,
            db_session,
            "league_full_b",
        )

        login_response = client.post(
            "/auth/login",
            json={
                "email": "test_squad_league_full_b@example.com",
                "password": "password-segura",
            },
            headers=BROWSER_HEADERS,
        )

        assert login_response.status_code == 200

        response_b = client.post(
            f"/leagues/{league.id}/join",
            json={
                "clubId": club_b.id,
                "lineUp": [1, 2, 3, 4, 5, 6],
            },
            headers=BROWSER_HEADERS,
        )

        assert response_b.status_code == 201

        club_c = register_and_get_club(
            client,
            db_session,
            "league_full_c",
        )

        login_response = client.post(
            "/auth/login",
            json={
                "email": "test_squad_league_full_c@example.com",
                "password": "password-segura",
            },
            headers=BROWSER_HEADERS,
        )

        assert login_response.status_code == 200

        response_c = client.post(
            f"/leagues/{league.id}/join",
            json={
                "clubId": club_c.id,
                "lineUp": [1, 2, 3, 4, 5, 6],
            },
            headers=BROWSER_HEADERS,
        )

        assert response_c.status_code == 409

        registration_count = db_session.query(
            LeagueRegistration
        ).filter(
            LeagueRegistration.league_id == league.id
        ).count()

        assert registration_count == 2