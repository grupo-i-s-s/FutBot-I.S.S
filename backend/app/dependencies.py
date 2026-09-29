from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.errors import AppError
from app.services.auth_service import (
    Identity,
    authenticate
)

Database = Annotated[Session, Depends(get_db)]


def require_browser_write(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return

    origin = request.headers.get("origin")
    marker = request.headers.get("x-futbot-request")

    if origin not in settings.allowed_origins or marker != "1":
        raise AppError(
            "CSRF_INVALID",
            "No se pudo validar el origen de la solicitud.")


def get_current_identity(request: Request, db: Database) -> Identity:
    token = request.cookies.get(settings.cookie_name)

    return authenticate(db, token)


CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
