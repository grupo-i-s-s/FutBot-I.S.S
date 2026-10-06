from fastapi import Depends, Request
from sqlalchemy.orm import Session
from starlette.requests import HTTPConnection
from typing import Annotated

from app.config import settings
from app.database import get_db
from app.errors import AppError
from app.models.auth_model import Club
from app.repository import user_repository
from app.services.auth_service import (
    Identity,
    authenticate
)

Database = Annotated[Session, Depends(get_db)]


def require_browser_write(connection: HTTPConnection) -> None:
    if connection.scope["type"] == "websocket":
        return

    if connection.scope["method"] in {"GET", "HEAD", "OPTIONS"}:
        return

    origin = connection.headers.get("origin")
    marker = connection.headers.get("x-futbot-request")

    if origin not in settings.allowed_origins or marker != "1":
        raise AppError(
            "CSRF_INVALID",
            "No se pudo validar el origen de la solicitud.")


def get_current_identity(request: Request, db: Database) -> Identity:
    token = request.cookies.get(settings.cookie_name)

    return authenticate(db, token)


CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]


def get_current_club(identity: CurrentIdentity, db: Database) -> Club:
    club = user_repository.get_club(db, identity.user_id)

    if club is None:
        raise AppError(
            "ACCOUNT_INCOMPLETE",
            "La cuenta no tiene un club asociado.")

    return club


CurrentClub = Annotated[Club, Depends(get_current_club)]
