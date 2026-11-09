"""Cambios en vivo: autorización, programa congelado y confirmación de la cola."""
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.controller import match_stream_controller as controller
from app.errors import AppError
from app.schemas.matches_schemas import LiveRequests
from app.services.match_request_handler import (
    acknowledge_requests,
    clear_requests,
    enqueue_request,
    pending_requests,
)
from primitives.behaviour_api.registry import API_VERSION
from primitives.behaviours import BehaviourMode, DEFAULT_CODES


CUSTOM_SOURCE = "def decide(observation):\n    return ir_a_pelota()"


@pytest.fixture
def queue_match_id():
    match_id = uuid4().int
    try:
        yield match_id
    finally:
        clear_requests(match_id)


@pytest.fixture
def live_change(db, monkeypatch, queue_match_id):
    match = SimpleNamespace(
        match_id=queue_match_id,
        creator_id=7,
        visitor_id=8,
        status="RUNNING",
        runtime_state={
            "local_team": {"club_id": 7, "players": [{"id": 71}]},
            "visitor_team": {"club_id": 8, "players": [{"id": 81}]},
        },
    )
    behaviour = SimpleNamespace(
        id=101,
        club_id=7,
        name="Custom",
        code=CUSTOM_SOURCE,
        kind="PLAYER",
        validation_status="VALID",
        version=3,
    )
    match_lookup = Mock(return_value=match)
    behaviour_lookup = Mock(return_value=behaviour)
    monkeypatch.setattr(controller.matches_repository, "get_by_id", match_lookup)
    monkeypatch.setattr(controller.behaviour_service, "behaviour_id", behaviour_lookup)
    return SimpleNamespace(
        db=db,
        match_id=queue_match_id,
        match=match,
        club=SimpleNamespace(id=7),
        payload=LiveRequests(player_id=71, behaviour_id=101),
        behaviour=behaviour,
        match_lookup=match_lookup,
        behaviour_lookup=behaviour_lookup,
    )


def reject_change(change, expected_code):
    enqueue_request(change.match_id, {"action": "EXISTING"})
    before = pending_requests(change.match_id)
    with pytest.raises(AppError) as error:
        controller.update_behaviour(
            change.match_id, change.payload, change.db, change.club
        )
    assert error.value.code == expected_code
    assert pending_requests(change.match_id) == before


@pytest.mark.parametrize("club_id, player_id", [(7, 71), (8, 81)])
def test_live_change_freezes_custom_program_and_request_identifiers(
    live_change, club_id, player_id
):
    change = live_change
    change.club.id = club_id
    change.payload.player_id = player_id
    change.behaviour.club_id = club_id

    result = controller.update_behaviour(
        change.match_id, change.payload, change.db, change.club
    )

    change.behaviour.code = "def decide(observation):\n    return cubrir_arco()"
    change.behaviour.version = 4
    change.payload.player_id = 999
    change.payload.behaviour_id = 202
    change.club.id = 99
    assert result["queued"] is True
    assert type(result["requestId"]) is str and result["requestId"]
    assert pending_requests(change.match_id) == [{
        "request_id": result["requestId"],
        "action": "CHANGE_BEHAVIOUR",
        "player_id": player_id,
        "club_id": club_id,
        "behaviour_id": 101,
        "program": {
            "behaviour_mode": BehaviourMode.BALANCED,
            "behaviour_code": CUSTOM_SOURCE,
            "behaviour_version": 3,
            "behaviour_api_version": API_VERSION,
        },
    }]
    change.match_lookup.assert_called_once_with(change.db, change.match_id)
    change.behaviour_lookup.assert_called_once_with(change.db, club_id, 101)
    change.db.commit.assert_not_called()


@pytest.mark.parametrize("name, mode", [
    ("Equilibrado", BehaviourMode.BALANCED),
    ("Ofensivo", BehaviourMode.OFFENSIVE),
    ("Defensivo", BehaviourMode.DEFENSIVE),
])
def test_live_change_queues_default_mode_without_custom_source(live_change, name, mode):
    change = live_change
    change.behaviour.name = name
    change.behaviour.code = DEFAULT_CODES[name]

    result = controller.update_behaviour(
        change.match_id, change.payload, change.db, change.club
    )

    queued, = pending_requests(change.match_id)
    assert queued["request_id"] == result["requestId"]
    assert queued["program"] == {
        "behaviour_mode": mode,
        "behaviour_code": None,
        "behaviour_version": 3,
        "behaviour_api_version": API_VERSION,
    }


def test_missing_match_rejects_live_change_before_behaviour_lookup(live_change):
    live_change.match_lookup.return_value = None
    reject_change(live_change, "MATCH_NOT_FOUND")
    live_change.behaviour_lookup.assert_not_called()


def test_foreign_club_cannot_enqueue_live_change(live_change):
    live_change.club.id = 99
    reject_change(live_change, "MATCH_FORBIDDEN")
    live_change.behaviour_lookup.assert_not_called()


@pytest.mark.parametrize("status", ["WAITING", "FINISHED", "CANCELLED"])
def test_match_must_be_running_to_accept_live_change(live_change, status):
    live_change.match.status = status
    reject_change(live_change, "MATCH_STATE_INVALID")
    live_change.behaviour_lookup.assert_not_called()


@pytest.mark.parametrize("runtime_state", [None, {}])
def test_running_match_requires_checkpoint_before_live_change(live_change, runtime_state):
    live_change.match.runtime_state = runtime_state
    reject_change(live_change, "MATCH_STATE_INVALID")
    live_change.behaviour_lookup.assert_not_called()


@pytest.mark.parametrize("player_id", [72, 81, 999])
def test_live_change_requires_an_active_player_of_own_team(live_change, player_id):
    live_change.payload.player_id = player_id
    reject_change(live_change, "MATCH_FORBIDDEN")
    live_change.behaviour_lookup.assert_not_called()


def test_participant_with_missing_own_team_checkpoint_cannot_enqueue(live_change):
    live_change.match.runtime_state.pop("local_team")
    reject_change(live_change, "MATCH_FORBIDDEN")
    live_change.behaviour_lookup.assert_not_called()


@pytest.mark.parametrize("kind, status", [("COACH", "VALID"), ("PLAYER", "PENDING")])
def test_live_change_rejects_disabled_or_wrong_kind_behaviour(live_change, kind, status):
    live_change.behaviour.kind = kind
    live_change.behaviour.validation_status = status
    reject_change(live_change, "BEHAVIOUR_INVALID")
    live_change.behaviour_lookup.assert_called_once_with(live_change.db, 7, 101)


def test_foreign_or_missing_behaviour_cannot_enqueue_live_change(live_change):
    live_change.behaviour_lookup.side_effect = AppError("BEHAVIOUR_NOT_FOUND", "missing")
    reject_change(live_change, "BEHAVIOUR_NOT_FOUND")
    live_change.behaviour_lookup.assert_called_once_with(live_change.db, 7, 101)


@pytest.mark.parametrize("field, value", [("code", "import os"), ("version", 0)])
def test_invalid_program_cannot_enqueue_even_if_marked_valid(live_change, field, value):
    setattr(live_change.behaviour, field, value)
    reject_change(live_change, "BEHAVIOUR_INVALID")


def test_acknowledgement_removes_only_the_processed_batch(queue_match_id):
    first = enqueue_request(queue_match_id, {"action": "FIRST"})
    second = enqueue_request(queue_match_id, {"action": "SECOND"})
    batch = pending_requests(queue_match_id)
    later = enqueue_request(queue_match_id, {"action": "LATER"})

    assert len({first, second, later}) == 3
    assert [request["request_id"] for request in batch] == [first, second]
    acknowledge_requests(queue_match_id, {request["request_id"] for request in batch})
    assert pending_requests(queue_match_id) == [{"action": "LATER", "request_id": later}]

    acknowledge_requests(queue_match_id, {later})
    assert pending_requests(queue_match_id) == []
