from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import WebSocketDenialResponse

from app.config import settings
from app.controller import match_stream_controller
from app.database import get_db
from app.main import app
from app.models.auth_model import AuthSession, Club
from app.models.matches_model import Matches
from app.models.planned_substitution_model import PlannedSubstitution
from app.repository import matches_repository
from app.security import hash_session_token, new_session_token
from app.services.match_start_service import cancel_match
from test_league_start import database, league_data
from test_planned_substitution import body, running_match
from test_substitution_execution import game, run_until_pause


@pytest.fixture
def browsers(database, league_data, monkeypatch):
    sessions = sessionmaker(database)
    tokens = {}
    now = datetime.now(timezone.utc)
    with sessions() as db:
        for club_id in league_data.clubs[:3]:
            token = new_session_token()
            tokens[club_id] = token
            db.add(AuthSession(
                token_hash=hash_session_token(token), user_id=db.get(Club, club_id).user_id,
                created_at=now, expires_at=now + timedelta(hours=1),
            ))
        db.commit()

    def get_test_db():
        with sessions() as db:
            yield db

    monkeypatch.setitem(app.dependency_overrides, get_db, get_test_db)
    monkeypatch.setattr(match_stream_controller, "SessionLocal", sessions)
    clients = {
        club_id: TestClient(app, headers={
            "Origin": next(iter(settings.allowed_origins)), "X-Futbot-Request": "1",
        }) for club_id in tokens
    }
    for club_id, client in clients.items():
        client.cookies.set(settings.cookie_name, tokens[club_id])
    try:
        yield clients
    finally:
        for client in clients.values():
            client.close()


def test_http_and_websocket_keep_substitution_details_private_to_the_owner(
    browsers, database, league_data, game,
):
    local_id, visitor_id, outsider_id = league_data.clubs[:3]
    path = f"/matches/{game}"
    commands = {
        local_id: body(league_data, game, "local-private-plan"),
        visitor_id: body(league_data, game, "visitor-private-plan", club=1),
    }
    for club_id, command in commands.items():
        response = browsers[club_id].put(f"{path}/planned-substitution", json=command)
        assert response.status_code == 200, response.text

    def stored_match():
        with Session(database) as db:
            row = db.get(Matches, game)
            return deepcopy((row.snapshot, row.runtime_state, row.sequence))

    def assert_viewer_snapshots(raw):
        for viewer, rival in ((local_id, visitor_id), (visitor_id, local_id)):
            # Un identificador enviado por el cliente no reemplaza al club autenticado.
            spoofed_query = f"?clubId={rival}&club_id={rival}"
            client = browsers[viewer]
            response = client.get(f"{path}{spoofed_query}")
            assert response.status_code == 200, response.text
            assert {item.strip() for item in response.headers["cache-control"].split(",")} == {"private", "no-store"}
            with client.websocket_connect(f"{path}/stream{spoofed_query}") as stream:
                streamed = stream.receive_json()

            expected = deepcopy(raw)
            for lineup in expected["state"]["lineups"]:
                if lineup["clubId"] == rival:
                    lineup["pendingSubstitution"] = None
            expected["state"]["events"] = [
                event for event in raw["state"]["events"]
                if event["type"] != "SUBSTITUTION_REJECTED" or event["clubId"] == viewer
            ]
            assert response.json() == streamed == expected

    stored = stored_match()
    raw = stored[0]
    assert raw["sequence"] == stored[2]
    assert {lineup["clubId"]: lineup["pendingSubstitution"] for lineup in raw["state"]["lineups"]} == {
        club_id: {**command, "status": "PENDING"} for club_id, command in commands.items()
    }
    assert_viewer_snapshots(raw)

    outsider = browsers[outsider_id]
    response = outsider.get(f"{path}?clubId={local_id}")
    assert response.status_code == 403 and response.json()["error"]["code"] == "MATCH_FORBIDDEN"
    with pytest.raises(WebSocketDenialResponse) as denied:
        with outsider.websocket_connect(f"{path}/stream?clubId={local_id}"):
            pytest.fail("El club ajeno al partido pudo conectarse al stream.")
    assert denied.value.status_code == 403
    assert stored_match() == stored

    # Simular un plan viejo que ya no pasa la validación del plantel en la pausa.
    with Session(database) as db:
        visitor_plan = db.scalar(select(PlannedSubstitution).where(
            PlannedSubstitution.match_id == game, PlannedSubstitution.club_id == visitor_id,
        ))
        visitor_plan.in_player_id = league_data.lineups[0][4]
        db.commit()

    paused = run_until_pause(game)
    applied, rejected = paused["state"]["events"]
    assert (applied["type"], applied["clubId"], applied["inPlayerId"]) == (
        "SUBSTITUTION_APPLIED", local_id, commands[local_id]["inPlayerId"],
    )
    assert (rejected["type"], rejected["clubId"], rejected["inPlayerId"]) == (
        "SUBSTITUTION_REJECTED", visitor_id, league_data.lineups[0][4],
    )
    stored = stored_match()
    assert stored[0] == paused and stored[2] > raw["sequence"]
    assert_viewer_snapshots(paused)
    assert stored_match() == stored

    with Session(database) as db:
        row = matches_repository.get_by_id_for_update(db, game)
        cancel_match(db, row, "REPLACED_BY_NEW_TEST_MATCH", datetime.now(timezone.utc))
        db.commit()
    stored = stored_match()
    cancelled = stored[0]
    assert cancelled["state"]["status"] == "CANCELLED"
    assert cancelled["state"]["events"] == [applied, rejected]
    assert_viewer_snapshots(cancelled)
    assert stored_match() == stored
