from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.main import app
from app.models.matches_model import Matches


@pytest.fixture
def match_accounts():
    # Los commits de la API liberan savepoints; el rollback final conserva la BD.
    # No iniciamos el lifespan: este flujo HTTP no necesita ejecutar el scheduler.
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            app.dependency_overrides[get_db] = lambda: db
            clients = []
            try:
                accounts = []
                prefix = uuid4().hex[:10]
                for label in ("creator", "visitor", "outsider"):
                    client = TestClient(app)
                    clients.append(client)
                    client.headers.update({
                        "Origin": next(iter(settings.allowed_origins)),
                        "X-FutBot-Request": "1",
                    })
                    credentials = {
                        "email": f"{prefix}_{label}@example.com",
                        "password": "friendly-match-password",
                    }
                    response = client.post("/auth/register", json={
                        **credentials,
                        "passwordConfirmation": credentials["password"],
                        "clubName": f"{prefix} {label}",
                        "avatar": "avatar-1",
                    })
                    assert response.status_code == 201, response.text
                    assert client.post("/auth/login", json=credentials).status_code == 200
                    accounts.append((client, response.json()["clubId"]))
                yield db, accounts
            finally:
                for client in clients:
                    client.close()
                app.dependency_overrides.clear()
        transaction.rollback()


def test_creator_can_recover_match_but_cannot_join_it(match_accounts):
    db, accounts = match_accounts
    (creator, creator_id), (visitor, _), (outsider, _) = accounts
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    response = creator.post("/friendly-matches", json={"startDateTime": start.isoformat()})
    assert response.status_code == 201
    match_id = response.json()["matchId"]

    own = creator.get("/friendly-matches/me").json()
    assert len(own) == 1
    assert own[0]["matchId"] == match_id
    assert own[0]["isCreator"] is True
    assert own[0]["visitorClubName"] is None
    assert own[0]["status"] == "WAITING_OPPONENT"
    assert creator.get(f"/matches/{match_id}").status_code == 200
    assert creator.get("/friendly-matches").json() == []

    rejected = creator.post("/friendly-matches/join", json={"idPartido": match_id})
    assert rejected.status_code == 409
    assert rejected.json() == {
        "error": {
            "code": "MATCH_SELF_JOIN",
            "message": "No podés unirte a tu propio partido.",
            "fields": {},
        }
    }
    db.expire_all()
    match = db.get(Matches, match_id)
    assert match.creator_id == creator_id
    assert match.visitor_id is None
    assert match.status == "WAITING_OPPONENT"
    assert match.sequence == 0

    assert visitor.get("/friendly-matches/me").json() == []
    assert visitor.get("/friendly-matches").json()[0]["matchId"] == match_id
    assert visitor.post("/friendly-matches/join", json={"idPartido": match_id}).status_code == 200
    for client, is_creator in ((creator, True), (visitor, False)):
        own = client.get("/friendly-matches/me").json()
        assert own[0]["matchId"] == match_id
        assert own[0]["isCreator"] is is_creator
        assert own[0]["visitorClubName"] is not None
        assert own[0]["status"] == "SCHEDULED"
        assert client.get(f"/matches/{match_id}").status_code == 200
    assert outsider.get("/friendly-matches/me").json() == []
    assert outsider.get(f"/matches/{match_id}").status_code == 403


def test_my_matches_keeps_all_states_and_excludes_other_clubs(match_accounts):
    db, accounts = match_accounts
    (creator, creator_id), (_, visitor_id), (outsider, _) = accounts
    now = datetime.now(timezone.utc)
    states = ("WAITING", "WAITING_OPPONENT", "SCHEDULED", "RUNNING", "FINISHED", "CANCELLED")
    for index, state in enumerate(states):
        db.add(Matches(
            creator_id=creator_id,
            visitor_id=visitor_id if state not in ("WAITING", "WAITING_OPPONENT") else None,
            init_date=now - timedelta(days=index),
            status=state,
            duration_ms=100,
            clock_ms=100 if state == "FINISHED" else 0,
            finished_at=now if state == "FINISHED" else None,
            snapshot={} if state == "FINISHED" else None,
            cancellation_reason="NO_OPPONENT" if state == "CANCELLED" else None,
        ))
    db.commit()

    response = creator.get("/friendly-matches/me")
    assert response.status_code == 200
    assert [item["status"] for item in response.json()] == list(states)
    assert outsider.get("/friendly-matches/me").json() == []
    creator.cookies.clear()
    assert creator.get("/friendly-matches/me").status_code == 401
