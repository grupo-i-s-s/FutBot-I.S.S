from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.errors import AppError
from app.repository import matches_repository, session_repository, user_repository
from app.services.auth_service import authenticate, utc_now


@dataclass(frozen=True)
class StreamAccess:
    session_hash: str
    club_id: int


def authorize(db: Session, token: str | None, match_id: int) -> StreamAccess:
    identity = authenticate(db, token)
    club = user_repository.get_club(db, identity.user_id)
    if club is None:
        raise AppError("ACCOUNT_INCOMPLETE", "Usuario incompleto.")
    match = matches_repository.get_by_id(db, match_id)
    if match is None:
        raise AppError("MATCH_NOT_FOUND", "El partido no existe.")
    if club.id not in (match.creator_id, match.visitor_id):
        raise AppError("MATCH_FORBIDDEN", "El club no participa de este partido.")
    return StreamAccess(session_hash=identity.session_hash, club_id=club.id)


def session_is_active(db: Session, session_hash: str) -> bool:
    session = session_repository.get_active(db, session_hash, utc_now())
    return session is not None
