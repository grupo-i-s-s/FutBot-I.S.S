import pytest
from pydantic import ValidationError

from app.schemas.auth_schemas import LoginRequest, RegisterRequest
from app.schemas.league_schemas import CreateLeagueRequest


@pytest.fixture
def registration():
    return {
        "email": "USER@EXAMPLE.COM", "password": "safe-password",
        "passwordConfirmation": "safe-password", "clubName": "  MY CLUB  ", "avatar": "avatar-1",
    }


def test_register_and_login_use_same_email_normalization(registration):
    registered = RegisterRequest.model_validate(registration)
    login = LoginRequest(email=registration["email"], password=registration["password"])
    assert registered.email == login.email == "user@example.com"
    assert registered.club_name == "my club"


def test_registration_requires_matching_password_confirmation(registration):
    registration["passwordConfirmation"] = "another-password"
    with pytest.raises(ValidationError, match="no coinciden"):
        RegisterRequest.model_validate(registration)


def test_league_configuration_rejects_minimum_greater_than_maximum():
    with pytest.raises(ValidationError, match="minTeams"):
        CreateLeagueRequest.model_validate({
            "name": "League", "minTeams": 8, "maxTeams": 3,
            "startDatetime": "2030-01-02T00:00:00Z", "roundInterval": "DAILY",
        })
