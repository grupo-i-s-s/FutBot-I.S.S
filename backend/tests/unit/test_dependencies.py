from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app import dependencies as dependencies
from app.errors import AppError


@pytest.fixture
def browser(monkeypatch):
    monkeypatch.setattr(dependencies, "settings", SimpleNamespace(
        allowed_origins={"https://futbot.example"}, cookie_name="futbot_session"))


def connection(method, headers=None):
    return SimpleNamespace(scope={"type": "http", "method": method}, headers=headers or {})


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
def test_read_only_requests_do_not_require_write_marker(browser, method):
    dependencies.require_browser_write(connection(method))


def test_websocket_origin_is_handled_by_its_controller(browser):
    dependencies.require_browser_write(SimpleNamespace(scope={"type": "websocket"}))


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize("headers", [
    {}, {"origin": "https://evil.example", "x-futbot-request": "1"},
    {"origin": "https://futbot.example"},
    {"origin": "https://futbot.example", "x-futbot-request": "0"},
])
def test_write_requires_allowed_origin_and_marker(browser, method, headers):
    with pytest.raises(AppError) as error:
        dependencies.require_browser_write(connection(method, headers))
    assert error.value.code == "CSRF_INVALID"


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_browser_write_accepts_valid_origin_and_marker(browser, method):
    dependencies.require_browser_write(connection(method, {
        "origin": "https://futbot.example", "x-futbot-request": "1"}))


@pytest.mark.parametrize("token", [None, "browser-token"])
def test_identity_uses_configured_session_cookie(db, browser, monkeypatch, token):
    authenticate = Mock(return_value=object())
    monkeypatch.setattr(dependencies, "authenticate", authenticate)
    request = SimpleNamespace(cookies={"futbot_session": token, "other": "ignored"})
    assert dependencies.get_current_identity(request, db) is authenticate.return_value
    authenticate.assert_called_once_with(db, token)


@pytest.mark.parametrize("has_club", [True, False])
def test_current_club_comes_from_authenticated_user(db, monkeypatch, has_club):
    club = SimpleNamespace(id=7) if has_club else None
    repository = Mock()
    repository.get_club.return_value = club
    monkeypatch.setattr(dependencies, "user_repository", repository)
    identity = SimpleNamespace(user_id=3)
    if has_club:
        assert dependencies.get_current_club(identity, db) is club
    else:
        with pytest.raises(AppError) as error:
            dependencies.get_current_club(identity, db)
        assert error.value.code == "ACCOUNT_INCOMPLETE"
    repository.get_club.assert_called_once_with(db, 3)
