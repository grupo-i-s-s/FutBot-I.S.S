import pytest
from fastapi.testclient import TestClient
from types import SimpleNamespace
from unittest.mock import Mock

from app.config import settings
from app.database import get_db
from app.main import app
from app.security import hash_password
from app.services import auth_service


@pytest.mark.parametrize("user_exists", [False, True])
def test_login_with_invalid_credentials_returns_401(monkeypatch, user_exists):
    db = Mock()
    user = SimpleNamespace(password_hash=hash_password("correct-password")) if user_exists else None
    monkeypatch.setattr(
        auth_service.user_repository,
        "get_by_email",
        lambda session, email, *, lock=False: user,
    )
    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "wrong-password"},
                headers={
                    "Origin": next(iter(settings.allowed_origins)),
                    "X-Futbot-Request": "1",
                },
            )

        assert response.status_code == 401
        assert response.json() == {
            "error": {
                "code": "INVALID_CREDENTIALS",
                "message": "Email o contraseña incorrectos.",
                "fields": {},
            }
        }
        assert "set-cookie" not in response.headers
        db.rollback.assert_called_once_with()
        db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_login_with_malformed_email_returns_validation_error():
    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"email": "not-an-email", "password": "wrong-password"},
            headers={
                "Origin": next(iter(settings.allowed_origins)),
                "X-Futbot-Request": "1",
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "email" in response.json()["error"]["fields"]


def test_login_without_browser_write_headers_returns_403():
    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "wrong-password"},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_INVALID"
