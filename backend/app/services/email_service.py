import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings
from app.errors import AppError


def send_email(recipient: str, subject: str, body: str) -> None:
    if not settings.smtp_username or not settings.smtp_password or not settings.smtp_from:
        raise AppError(
            "EMAIL_NOT_CONFIGURED",
            "El servicio de correo no está configurado correctamente.",
        )

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout,
        ) as server:
            if settings.smtp_starttls:
                server.starttls(context=ssl.create_default_context())

            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise AppError(
            "EMAIL_DELIVERY_FAILED",
            "No se pudo enviar el correo. Intentá nuevamente más tarde.",
        ) from exc