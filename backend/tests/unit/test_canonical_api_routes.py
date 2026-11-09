from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.controller import dt_controller, match_stream_controller, matches_controller, team_controller
from app.database import get_db
from app.dependencies import get_current_club, get_current_identity
from app.main import app
from primitives.behaviours import DEFAULT_CODES


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setitem(app.dependency_overrides, get_db, lambda: db)
    monkeypatch.setitem(app.dependency_overrides, get_current_club, lambda: SimpleNamespace(id=7))
    monkeypatch.setitem(app.dependency_overrides, get_current_identity, lambda: SimpleNamespace(user_id=11))
    client = TestClient(app, headers={
        "Origin": next(iter(settings.allowed_origins)),
        "X-FutBot-Request": "1",
    })
    yield client
    client.close()


def test_default_team_paths_share_payload_and_response(client, db, monkeypatch):
    lineup = {
        "formationId": 1,
        "starters": [{"playerId": player_id, "behaviourId": 1} for player_id in range(1, 4)],
        "substitutes": [{"playerId": player_id, "behaviourId": 1} for player_id in range(4, 7)],
    }
    team = {"club_id": 7, "line_up": lineup}
    get_team = Mock(return_value=team)
    update_team = Mock(return_value=team)
    monkeypatch.setattr(team_controller.team_service, "get_default_team", get_team)
    monkeypatch.setattr(team_controller.team_service, "update_default_team", update_team)

    for path in ("/clubs/me/default-team", "/team/default"):
        for response in (client.get(path), client.put(path, json=lineup)):
            assert response.status_code == 200
            assert response.json() == {"clubId": 7, "lineUp": lineup}

    assert get_team.call_count == update_team.call_count == 2
    get_team.assert_called_with(db, 7)
    assert update_team.call_args.args[:2] == (db, 7)
    assert update_team.call_args.args[2].model_dump(by_alias=True) == lineup


def test_club_dt_paths_share_catalogue_and_settings(client, db, monkeypatch):
    behaviour = {"id": 21, "name": "Ofensiva", "code": "pass"}
    dt = {"id": 1, "is_active": True, "behaviour_id": 21}
    list_behaviours = Mock(return_value=[behaviour])
    create_behaviour = Mock(return_value=behaviour)
    update_dt = Mock(return_value=dt)
    monkeypatch.setattr(dt_controller.dt_service, "list_dt_behaviours", list_behaviours)
    monkeypatch.setattr(dt_controller.dt_service, "create_dt_behaviour", create_behaviour)
    monkeypatch.setattr(dt_controller.dt_service, "update_dt_settings", update_dt)

    for path in ("/clubs/me/dt", "/dt"):
        catalogue = client.get(f"{path}/behaviours")
        assert catalogue.status_code == 200
        assert catalogue.json() == {"items": [behaviour]}

        created = client.post(f"{path}/behaviours", json={"name": "Ofensiva", "code": "pass"})
        assert created.status_code == 201
        assert created.json() == behaviour

        updated = client.patch(path, json={"isActive": True, "activeBehaviourId": 21})
        assert updated.status_code == 200
        assert updated.json() == {"id": 1, "isActive": True, "activeBehaviourId": 21}

    assert list_behaviours.call_count == create_behaviour.call_count == update_dt.call_count == 2
    list_behaviours.assert_called_with(db, 11)
    assert create_behaviour.call_args.args[:2] == (db, 11)
    assert update_dt.call_args.args[:3] == (db, 7, 11)


def test_friendly_join_id_can_come_from_path_or_legacy_body(client, db, monkeypatch):
    join = Mock(return_value={"message": "Te uniste al partido.", "match_id": 42})
    monkeypatch.setattr(matches_controller.matches_service, "join_match", join)

    for response in (
        client.post("/friendly-matches/42/join"),
        client.post("/friendly-matches/join", json={"idPartido": 42}),
    ):
        assert response.status_code == 200
        assert response.json() == {"message": "Te uniste al partido.", "matchId": 42}

    assert join.call_count == 2
    join.assert_called_with(db, 42, 7)


def test_match_dt_preserves_legacy_response_and_uses_camel_case_in_canonical_route(client, db, monkeypatch):
    update_dt = Mock(return_value={"message": "Actualizado", "dt_active": True})
    monkeypatch.setattr(matches_controller.matches_service, "set_match_dt", update_dt)

    canonical = client.post("/matches/42/dt", json={"dtActive": True})
    legacy = client.post("/friendly-matches/42/dt", json={"dt_active": True})

    assert canonical.status_code == legacy.status_code == 200
    assert canonical.json() == {"message": "Actualizado", "dtActive": True}
    assert legacy.json() == {"message": "Actualizado", "dt_active": True}
    assert update_dt.call_count == 2
    update_dt.assert_called_with(db=db, match_id=42, club_id=7, dt_active=True)


def test_live_request_paths_enqueue_equivalent_commands(client, monkeypatch):
    match = SimpleNamespace(
        creator_id=7, visitor_id=8, status="RUNNING",
        runtime_state={"local_team": {"club_id": 7, "players": [{"id": 71}]}},
    )
    behaviour = SimpleNamespace(
        id=21, kind="PLAYER", validation_status="VALID", name="Ofensivo",
        code=DEFAULT_CODES["Ofensivo"], version=3,
    )
    enqueue = Mock(return_value="command-1")
    monkeypatch.setattr(match_stream_controller.matches_repository, "get_by_id", lambda db, match_id: match)
    monkeypatch.setattr(match_stream_controller.behaviour_service, "behaviour_id", lambda *args: behaviour)
    monkeypatch.setattr(match_stream_controller, "enqueue_request", enqueue)

    canonical = client.post("/matches/42/live-requests", json={"playerId": 71, "behaviourId": 21})
    legacy = client.post("/matches/42/live_request", json={"player_id": 71, "behaviour_id": 21})

    assert canonical.status_code == legacy.status_code == 200
    assert canonical.json() == legacy.json() == {"queued": True, "requestId": "command-1"}
    assert enqueue.call_count == 2
    assert enqueue.call_args_list[0] == enqueue.call_args_list[1]
    assert enqueue.call_args.args[1]["player_id"] == 71


@pytest.mark.parametrize("path", ["/matches/42/dt", "/friendly-matches/42/dt"])
def test_match_mutations_keep_origin_and_session_requirements(db, monkeypatch, path):
    monkeypatch.setitem(app.dependency_overrides, get_db, lambda: db)
    client = TestClient(app)

    missing_origin = client.post(path)
    assert missing_origin.status_code == 403
    assert missing_origin.json()["error"]["code"] == "CSRF_INVALID"

    missing_session = client.post(path, headers={
        "Origin": next(iter(settings.allowed_origins)),
        "X-FutBot-Request": "1",
    })
    assert missing_session.status_code == 401
    assert missing_session.json()["error"]["code"] == "SESSION_INVALID"
    client.close()


def test_openapi_contains_canonical_routes_and_omits_compatibility_aliases():
    paths = app.openapi()["paths"]
    assert {"get", "put"} == paths["/clubs/me/default-team"].keys()
    assert {"get", "post"} == paths["/clubs/me/dt/behaviours"].keys()
    assert "patch" in paths["/clubs/me/dt"]
    assert "post" in paths["/friendly-matches/{match_id}/join"]
    assert "get" in paths["/matches/{match_id}"]
    assert "post" in paths["/matches/{match_id}/dt"]
    assert "post" in paths["/matches/{match_id}/live-requests"]
    assert paths.keys().isdisjoint({
        "/team/default", "/dt", "/dt/behaviours", "/friendly-matches/join",
        "/friendly-matches/{match_id}", "/friendly-matches/{match_id}/dt",
        "/matches/{match_id}/live_request",
    })


def test_openapi_documents_the_runtime_validation_error(client):
    response = client.post("/matches/42/dt", json={"dtActive": "true"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "dtActive" in response.json()["error"]["fields"]

    responses = app.openapi()["paths"]["/matches/{match_id}/dt"]["post"]["responses"]
    assert "422" not in responses
    schema = responses["400"]["content"]["application/json"]["schema"]
    assert {variant["$ref"] for variant in schema["anyOf"]} == {
        "#/components/schemas/ApiErrorResponse", "#/components/schemas/HttpErrorResponse",
    }
