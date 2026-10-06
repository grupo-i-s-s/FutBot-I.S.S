"""Contrato de errores y exclusión de datos sensibles, sin servidor HTTP."""
import asyncio
import json
import pytest
from unittest.mock import Mock

from app.errors import AppError
from app.main import app_error_handler, validation_error_handler


@pytest.mark.parametrize("code, status", [("INVALID_CREDENTIALS", 401), ("CSRF_INVALID", 403),
                                          ("MATCH_NOT_FOUND", 404), ("MATCH_SELF_JOIN", 409),
                                          ("MATCH_INVALID_DATE", 400), ("UNKNOWN", 400)])
def test_domain_error_keeps_public_code_message_and_field_errors(code, status):
    error = AppError(code, "Readable message", {"name": "Choose another name"})
    response = asyncio.run(app_error_handler(None, error))
    assert response.status_code == status
    assert json.loads(response.body) == {"error": {
        "code": code, "message": "Readable message", "fields": {"name": "Choose another name"}}}


def test_validation_errors_use_public_nested_paths_without_returning_inputs():
    error = Mock()
    error.errors.return_value = [
        {"loc": ("body", "password"), "msg": "Invalid password", "input": "private-password"},
        {"loc": ("body", "starters", 1, "playerId"), "msg": "Invalid player", "input": 999},
        {"loc": ("query", "name"), "msg": "Invalid name", "input": "private-name"},
        {"loc": ("path", "id"), "msg": "Invalid id", "input": -1},
        {"loc": ("body",), "msg": "Invalid form", "input": {"password": "private-password"}},
    ]
    response = asyncio.run(validation_error_handler(None, error))
    assert response.status_code == 400
    body = json.loads(response.body)
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["fields"] == {
        "password": "Invalid password", "starters.1.playerId": "Invalid player",
        "name": "Invalid name", "id": "Invalid id", "form": "Invalid form"}
    assert "private-password" not in response.body.decode()
    assert "private-name" not in response.body.decode()
    assert "input" not in response.body.decode()
