from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import smtplib

from app.errors import AppError
from app.services import email_service
from app import security


@pytest.fixture
def smtp_settings(monkeypatch):
    settings = SimpleNamespace(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_username="futbot@example.com",
        smtp_password="test-app-password",
        smtp_from="futbot@example.com",
        smtp_starttls=True,
        smtp_timeout=10,
    )
    monkeypatch.setattr(email_service, "settings", settings)
    return settings


def test_send_email_uses_smtp_and_sends_message(monkeypatch, smtp_settings):
    server = Mock()
    server.__enter__ = Mock(return_value=server)
    server.__exit__ = Mock(return_value=False)
    smtp_factory = Mock(return_value=server)
    monkeypatch.setattr(email_service.smtplib, "SMTP", smtp_factory)

    email_service.send_email("user@example.com", "Código", "Tu código es 123456")

    smtp_factory.assert_called_once_with("smtp.gmail.com", 587, timeout=10)
    server.starttls.assert_called_once()
    server.login.assert_called_once_with("futbot@example.com", "test-app-password")

    message = server.send_message.call_args.args[0]
    assert message["From"] == "futbot@example.com"
    assert message["To"] == "user@example.com"
    assert message["Subject"] == "Código"
    assert message.get_content().strip() == "Tu código es 123456"


def test_send_email_converts_timeout_to_app_error(monkeypatch, smtp_settings):
    def timeout(*args, **kwargs):
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(email_service.smtplib, "SMTP", timeout)

    with pytest.raises(AppError) as error:
        email_service.send_email("user@example.com", "Código", "Texto")

    assert error.value.code == "EMAIL_DELIVERY_FAILED"
    assert "test-app-password" not in str(error.value)


def test_send_email_converts_provider_error_to_app_error(monkeypatch, smtp_settings):
    server = Mock()
    server.__enter__ = Mock(return_value=server)
    server.__exit__ = Mock(return_value=False)
    server.login.side_effect = smtplib.SMTPAuthenticationError(
        535, b"Authentication failed",
    )
    monkeypatch.setattr(
        email_service.smtplib, "SMTP", Mock(return_value=server),
    )

    with pytest.raises(AppError) as error:
        email_service.send_email("user@example.com", "Código", "Texto")

    assert error.value.code == "EMAIL_DELIVERY_FAILED"
    assert "test-app-password" not in str(error.value)

def test_new_email_verification_code_has_six_digits(monkeypatch):
    monkeypatch.setattr(security.secrets, "randbelow", lambda _: 67)

    assert security.new_email_verification_code() == "000067"


def test_send_verification_code_email(monkeypatch):
    send = Mock()
    monkeypatch.setattr(email_service, "send_email", send)

    email_service.send_verification_code("user@example.com", "123456")

    send.assert_called_once()
    recipient, subject, body = send.call_args.args
    assert recipient == "user@example.com"
    assert subject == "Verificá tu correo en FutBot"
    assert "123456" in body
    assert "10 minutos" in body