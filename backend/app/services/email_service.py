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

def send_verification_code(recipient: str, code: str) -> None:
    subject = "Verificá tu correo en FutBot"
    body = f"""Hola,

Gracias por crear una cuenta en FutBot.

Tu código de verificación es: {code}

Ingresalo en la página de verificación dentro de los próximos 10 minutos.
Si no solicitaste crear una cuenta, podés ignorar este mensaje.

¡Te damos la bienvenida a FutBot!
"""
    send_email(recipient, subject, body)