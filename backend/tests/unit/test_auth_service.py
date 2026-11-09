import pytest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from app.errors import AppError
from app.schemas.auth_schemas import ChangePasswordRequest, LoginRequest, RegisterRequest, VerifyEmailRequest, ResendVerificationRequest
from app.services import auth_service as service


@pytest.fixture
def auth(monkeypatch, now):
    mocks = SimpleNamespace(
        users=Mock(), sessions=Mock(), behaviours=Mock(), players=Mock(), teams=Mock(), dt=Mock(),
        hash_password=Mock(return_value="encoded-password"),
        verify=Mock(return_value=True), hash_token=Mock(return_value="hashed-token"), pending=Mock(), email=Mock())
    for name, value in {
        "user_repository": mocks.users, "session_repository": mocks.sessions,
        "behaviour_repository": mocks.behaviours, "player_repository": mocks.players,
        "dt_repository": mocks.dt,
        "team_repository": mocks.teams, "hash_password": mocks.hash_password,
        "verify_password": mocks.verify, "hash_session_token": mocks.hash_token,
        "new_session_token": Mock(return_value="t" * 43), "utc_now": Mock(return_value=now),
        "pending_email_verification_repository": mocks.pending, "email_service": mocks.email, "new_email_verification_code": Mock(return_value="004281"),
    }.items():
        monkeypatch.setattr(service, name, value)
    mocks.users.get_by_email.return_value = SimpleNamespace(
        id=1, email="user@example.com", password_hash="old-hash",
    )
    mocks.users.get_by_id.return_value = mocks.users.get_by_email.return_value
    mocks.users.get_club.return_value = SimpleNamespace(id=7)
    mocks.sessions.get_active.return_value = SimpleNamespace(user_id=1)
    return mocks


@pytest.fixture
def registration(auth):
    auth.users.get_by_email.return_value = None
    auth.users.create_user.return_value = SimpleNamespace(id=1, email="user@example.com")
    auth.users.create_club.return_value = SimpleNamespace(id=7)
    auth.dt.create_default_dt_behaviours.return_value = [SimpleNamespace(id=9)]
    auth.behaviours.create_default_behaviours.return_value = [SimpleNamespace(id=i) for i in (10, 11, 12)]
    auth.players.create_default_players.return_value = [
        SimpleNamespace(id=i + 1, behavior_id=10 + i // 2) for i in range(6)
    ]
    return RegisterRequest.model_validate({
        "email": "user@example.com", "password": "safe-password",
        "passwordConfirmation": "safe-password", "clubName": "My club",
    })

def test_registration_creates_pending_request_and_sends_code(db, auth, registration, now):
    auth.pending.get_by_email.return_value = None

    result = service.register(db, registration)

    assert result == {
        "message": "Se envio código para verificar tu correo."
    }
    auth.pending.create.assert_called_once()
    values = auth.pending.create.call_args.kwargs
    assert values["email"] == "user@example.com"
    assert values["password_hash"] == "encoded-password"
    assert values["code_hash"] == "encoded-password"
    assert values["expires_at"] == now + timedelta(minutes=10)
    auth.email.send_verification_code.assert_called_once_with(
        "user@example.com", "004281"
    )
    auth.users.create_user.assert_not_called()
    auth.dt.create_dt.assert_not_called()
    db.commit.assert_called_once()


def test_registration_rejects_existing_account_without_sending_email(db, auth, registration):
    auth.users.get_by_email.return_value = SimpleNamespace(id=2)

    with pytest.raises(AppError) as error:
        service.register(db, registration)

    assert error.value.code == "ACCOUNT_DUPLICATE"
    auth.pending.create.assert_not_called()
    auth.email.send_verification_code.assert_not_called()
    db.rollback.assert_called_once()

def test_registration_rejects_existing_pending_verification(db, auth, registration, now):
    auth.pending.get_by_email.return_value = SimpleNamespace(expires_at=now + timedelta(minutes=5),)

    with pytest.raises(AppError) as error:
        service.register(db, registration)

    assert error.value.code == "EMAIL_VERIFICATION_PENDING"
    auth.pending.create.assert_not_called()
    auth.pending.delete_by_email.assert_not_called()
    auth.email.send_verification_code.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_called_once()

def test_registration_replaces_expired_pending_verification(db, auth, registration, now):
    auth.pending.get_by_email.return_value = SimpleNamespace(
        expires_at=now - timedelta(seconds=1),
    )

    service.register(db, registration)

    auth.pending.delete_by_email.assert_called_once_with(
        db, "user@example.com"
    )
    auth.pending.create.assert_called_once()
    values = auth.pending.create.call_args.kwargs
    assert values["email"] == "user@example.com"
    assert values["created_at"] == now
    assert values["expires_at"] == now + timedelta(minutes=10)
    assert values["last_sent_at"] == now
    assert values["resend_window_started_at"] == now

    auth.hash_password.assert_any_call("004281")
    auth.email.send_verification_code.assert_called_once_with("user@example.com", "004281")
    auth.users.create_user.assert_not_called()
    db.commit.assert_called_once()

def test_verify_email_creates_account_and_deletes_pending_request(db, auth, registration, now):
    pending = SimpleNamespace(
        expires_at=now + timedelta(minutes=10),
        code_hash="stored-code-hash",
        password_hash="stored-password-hash",
        club_name="my club",
    )
    auth.pending.get_by_email.return_value = pending

    result = service.verify_email(
        db,
        VerifyEmailRequest(email="user@example.com", code="004281"),
    )

    assert result.email == "user@example.com"
    auth.verify.assert_called_once_with("004281", "stored-code-hash")
    auth.users.create_user.assert_called_once_with(
        db,
        email="user@example.com",
        password_hash="stored-password-hash",
    )
    auth.dt.create_default_dt_behaviours.assert_called_once_with(db, 1)
    auth.dt.create_dt.assert_called_once_with(db, 7, 9)
    auth.pending.delete_by_email.assert_called_once_with(db, "user@example.com")
    db.commit.assert_called_once()


def test_verify_email_rejects_wrong_code_and_counts_attempt(db, auth, registration, now):
    pending = SimpleNamespace(
        expires_at=now + timedelta(minutes=10),
        code_hash="stored-code-hash",
        password_hash="stored-password-hash",
        club_name="my club",
    )
    auth.pending.get_by_email.return_value = pending
    auth.verify.return_value = False
    auth.pending.increment_attempts.return_value = 1

    with pytest.raises(AppError) as error:
        service.verify_email(
            db,
            VerifyEmailRequest(email="user@example.com", code="000000"),
        )

    assert error.value.code == "EMAIL_VERIFICATION_INVALID"
    auth.pending.increment_attempts.assert_called_once_with(db, pending)
    auth.users.create_user.assert_not_called()
    db.commit.assert_called_once()


@pytest.mark.parametrize("previous", [None, "previous-token"])
def test_login_rotates_browser_session_and_sets_expiration(db, auth, now, previous):
    data = LoginRequest(email="user@example.com", password="safe-password")
    user, token = service.login(db, data, previous)
    assert user.club_id == 7 and token == "t" * 43
    auth.users.get_by_email.assert_called_once_with(db, "user@example.com", lock=True)
    auth.sessions.create.assert_called_once_with(
        db, token_hash="hashed-token", user_id=1, created_at=now,
        expires_at=now + timedelta(hours=service.settings.session_hours),
    )
    if previous:
        auth.sessions.delete_by_token.assert_called_once_with(db, "hashed-token")
    else:
        auth.sessions.delete_by_token.assert_not_called()
    db.commit.assert_called_once()


@pytest.mark.parametrize("exists", [False, True])
def test_invalid_login_creates_no_session_and_uses_dummy_hash_for_unknown_email(db, auth, exists):
    if not exists:
        auth.users.get_by_email.return_value = None
    auth.verify.return_value = False
    with pytest.raises(AppError) as error:
        service.login(db, LoginRequest(email="user@example.com", password="wrong"), None)
    assert error.value.code == "INVALID_CREDENTIALS"
    auth.verify.assert_called_once_with("wrong", "old-hash" if exists else service.DUMMY_PASSWORD_HASH)
    auth.sessions.create.assert_not_called()
    db.rollback.assert_called_once()


def test_login_without_club_creates_no_session(db, auth):
    auth.users.get_club.return_value = None
    with pytest.raises(AppError) as error:
        service.login(db, LoginRequest(email="user@example.com", password="password"), None)
    assert error.value.code == "ACCOUNT_INCOMPLETE"
    auth.sessions.create.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("token", [None, "", "short", "t" * 44])
def test_authentication_rejects_malformed_tokens_without_querying(db, auth, token):
    with pytest.raises(AppError) as error:
        service.authenticate(db, token)
    assert error.value.code == "SESSION_INVALID"
    auth.sessions.get_active.assert_not_called()


def test_authentication_requires_active_session_and_returns_its_identity(db, auth, now):
    identity = service.authenticate(db, "t" * 43)
    assert identity == service.Identity(1, "hashed-token")
    auth.sessions.get_active.assert_called_once_with(db, "hashed-token", now)
    auth.sessions.get_active.return_value = None
    with pytest.raises(AppError) as error:
        service.authenticate(db, "t" * 43)
    assert error.value.code == "SESSION_INVALID"


@pytest.mark.parametrize("missing,code", [("user", "SESSION_INVALID"), ("club", "ACCOUNT_INCOMPLETE")])
def test_current_user_rejects_deleted_account_or_missing_club(db, auth, missing, code):
    if missing == "user":
        auth.users.get_by_id.return_value = None
    else:
        auth.users.get_club.return_value = None
    with pytest.raises(AppError) as error:
        service.get_current_user(db, service.Identity(1, "hash"))
    assert error.value.code == code


@pytest.mark.parametrize("token", [None, "old-token"])
def test_logout_removes_only_requested_session(db, auth, token):
    service.logout(db, token)
    if token:
        auth.sessions.delete_by_token.assert_called_once_with(db, "hashed-token")
    else:
        auth.sessions.delete_by_token.assert_not_called()
    auth.sessions.delete_for_user.assert_not_called()
    db.commit.assert_called_once()


def test_password_change_revalidates_session_and_revokes_all_sessions(db, auth):
    auth.verify.side_effect = [True, False]
    service.change_password(db, service.Identity(1, "current-session"), ChangePasswordRequest(
        oldPassword="old-password", newPassword="new-password",
    ))
    auth.users.get_by_id.assert_called_once_with(db, 1, lock=True)
    auth.sessions.get_active.assert_called_once()
    auth.users.set_password.assert_called_once_with(auth.users.get_by_id.return_value, "encoded-password")
    auth.sessions.delete_for_user.assert_called_once_with(db, 1)
    db.commit.assert_called_once()


@pytest.mark.parametrize("case,code,field", [
    ("revoked", "SESSION_INVALID", None),
    ("deleted", "SESSION_INVALID", None),
    ("wrong_old", "PASSWORD_INVALID", "oldPassword"),
    ("same_new", "PASSWORD_INVALID", "newPassword"),
])
def test_invalid_password_change_preserves_password_and_sessions(db, auth, case, code, field):
    if case == "revoked":
        auth.sessions.get_active.return_value = None
    elif case == "deleted":
        auth.users.get_by_id.return_value = None
    else:
        auth.verify.side_effect = [False] if case == "wrong_old" else [True, True]
    with pytest.raises(AppError) as error:
        service.change_password(db, service.Identity(1, "session"), ChangePasswordRequest(
            oldPassword="old-password", newPassword="new-password",
        ))
    assert error.value.code == code
    if field:
        assert field in error.value.fields
    auth.users.set_password.assert_not_called()
    auth.sessions.delete_for_user.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_called_once()


@pytest.mark.parametrize("operation", ["login", "logout", "change_password"])
def test_session_write_commit_failures_are_rolled_back(db, auth, operation):
    failure = RuntimeError("commit failed")
    db.commit.side_effect = failure
    auth.verify.side_effect = [True, False]
    with pytest.raises(RuntimeError) as error:
        if operation == "login":
            service.login(db, LoginRequest(email="user@example.com", password="password"), None)
        elif operation == "logout":
            service.logout(db, "raw-token")
        else:
            service.change_password(db, service.Identity(1, "session"), ChangePasswordRequest(
                oldPassword="old-password", newPassword="new-password"))
    assert error.value is failure
    db.rollback.assert_called_once()

def test_resend_verification_rejects_before_60_seconds(db, auth, now):
    pending = SimpleNamespace(
        expires_at=now + timedelta(minutes=10),
        last_sent_at=now - timedelta(seconds=59),
        resend_window_started_at=now - timedelta(minutes=10),
        resend_count=1,
    )
    auth.pending.get_by_email.return_value = pending

    with pytest.raises(AppError) as error:
        service.resend_verification(
            db, ResendVerificationRequest(email="user@example.com")
        )

    assert error.value.code == "EMAIL_VERIFICATION_RESEND_LIMIT"
    auth.pending.update_for_resend.assert_not_called()
    auth.email.send_verification_code.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_called_once()

def test_resend_verification_rejects_after_five_resends_within_hour(db, auth, now):
    pending = SimpleNamespace(
        expires_at=now + timedelta(minutes=10),
        last_sent_at=now - timedelta(seconds=61),
        resend_window_started_at=now - timedelta(minutes=30),
        resend_count=5,
    )
    auth.pending.get_by_email.return_value = pending

    with pytest.raises(AppError) as error:
        service.resend_verification(
            db, ResendVerificationRequest(email="user@example.com")
        )

    assert error.value.code == "EMAIL_VERIFICATION_RESEND_LIMIT"
    auth.pending.update_for_resend.assert_not_called()
    auth.email.send_verification_code.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_called_once()

def test_resend_verification_resets_expired_hourly_window(db, auth, now):
    pending = SimpleNamespace(
        expires_at=now + timedelta(minutes=10),
        last_sent_at=now - timedelta(seconds=61),
        resend_window_started_at=now - timedelta(hours=1, seconds=1),
        resend_count=5,
    )
    auth.pending.get_by_email.return_value = pending

    result = service.resend_verification(
        db, ResendVerificationRequest(email="user@example.com")
    )

    assert result == {
        "message": "Si existe una verificación pendiente, se envió un nuevo código."
    }
    values = auth.pending.update_for_resend.call_args.kwargs
    assert values["resend_window_started_at"] == now
    assert values["resend_count"] == 1
    auth.email.send_verification_code.assert_called_once_with(
        "user@example.com", "004281"
    )
    db.commit.assert_called_once()
    db.rollback.assert_not_called()
