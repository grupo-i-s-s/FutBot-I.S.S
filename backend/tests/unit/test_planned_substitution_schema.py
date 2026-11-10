import pytest
from pydantic import ValidationError

from app.schemas.matches_schemas import PlannedSubstitutionRequest


VALID_REQUEST = {"outPlayerId": 10, "inPlayerId": 20, "commandId": "change-1", "pauseId": "42:1"}


def test_valid_request_preserves_player_ids_command_and_pause():
    request = PlannedSubstitutionRequest.model_validate(VALID_REQUEST)
    assert request.out_player_id == 10
    assert request.in_player_id == 20
    assert request.command_id == "change-1"
    assert request.pause_id == "42:1"
    assert request.model_dump(by_alias=True) == VALID_REQUEST


@pytest.mark.parametrize("field", list(VALID_REQUEST))
def test_all_fields_are_required(field):
    payload = {key: value for key, value in VALID_REQUEST.items() if key != field}
    with pytest.raises(ValidationError):
        PlannedSubstitutionRequest.model_validate(payload)


@pytest.mark.parametrize("field", ["outPlayerId", "inPlayerId"])
@pytest.mark.parametrize("value", [0, -1, True, 1.5, "10", None])
def test_player_ids_must_be_positive_integers(field, value):
    with pytest.raises(ValidationError):
        PlannedSubstitutionRequest.model_validate({**VALID_REQUEST, field: value})


def test_same_player_cannot_enter_and_leave():
    with pytest.raises(ValidationError, match="distinto del saliente"):
        PlannedSubstitutionRequest.model_validate({**VALID_REQUEST, "inPlayerId": 10})


@pytest.mark.parametrize("field", ["commandId", "pauseId"])
@pytest.mark.parametrize("value", ["", " \t\n", None, 123])
def test_command_and_pause_ids_must_be_nonblank_text(field, value):
    with pytest.raises(ValidationError):
        PlannedSubstitutionRequest.model_validate({**VALID_REQUEST, field: value})


def test_client_cannot_supply_club():
    with pytest.raises(ValidationError):
        PlannedSubstitutionRequest.model_validate({**VALID_REQUEST, "clubId": 1})
