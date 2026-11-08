import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Setting:
    cookie_name: str
    cookie_secure: bool
    session_hours: int
    allowed_origins: frozenset[str]
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from: str
    smtp_starttls: bool
    smtp_timeout: int


settings = Setting(cookie_name="FutBotSession",
                   cookie_secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
                   session_hours=int(os.getenv("AUTH_SESSION_HOURS", "8")),
                   allowed_origins=frozenset(origin.strip().rstrip("/")
                                             for origin in
                                             os.getenv("AUTH_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
                                             if origin.strip()),
                   smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
                   smtp_port=int(os.getenv("SMTP_PORT", "587")),
                   smtp_username=os.getenv("SMTP_USERNAME", ""),
                   smtp_password=os.getenv("SMTP_PASSWORD", ""),
                   smtp_from=os.getenv("SMTP_FROM", ""),
                   smtp_starttls=os.getenv("SMTP_STARTTLS", "true").lower() == "true",
                   smtp_timeout=int(os.getenv("SMTP_TIMEOUT", "10")),)

if settings.session_hours <= 0:
    raise ValueError("AUTH_SESSION_HOURS debe ser positivo")

if not settings.allowed_origins or "*" in settings.allowed_origins:
    raise ValueError(
        "AUTH_ALLOWED_ORIGINS debe contener orígenes explícitos"
    )
