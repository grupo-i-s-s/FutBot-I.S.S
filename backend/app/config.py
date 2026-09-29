import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Setting:
    cookie_name: str
    cookie_secure: bool
    session_hours: int
    allowed_origins: frozenset[str]


settings = Setting(cookie_name="FutBotSession",
                   cookie_secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
                   session_hours=int(os.getenv("AUTH_SESSION_HOURS", "8")),
                   allowed_origins=frozenset(origin.strip().rstrip("/")
                                             for origin in os.getenv("AUTH_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
                                             if origin.strip()))

if settings.session_hours <= 0:
    raise ValueError("AUTH_SESSION_HOURS debe ser positivo")

if not settings.allowed_origins or "*" in settings.allowed_origins:
    raise ValueError(
        "AUTH_ALLOWED_ORIGINS debe contener orígenes explícitos"
    )
