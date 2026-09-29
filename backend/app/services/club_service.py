from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.auth_model import Club
from app.repository import club_repository
from app.schemas.club_schemas import ClubResponse, ClubUpdate


def require_club(db: Session, user_id: int) -> Club:
    club = club_repository.get_by_user_id(db, user_id)
    if club is None:
        raise AppError("ACCOUNT_INCOMPLETE", "La cuenta no tiene un club asociado.")
    return club


def get_my_club(db: Session, user_id: int) -> ClubResponse:
    return ClubResponse.model_validate(require_club(db, user_id))


def update_club(
    db: Session, user_id: int, data: ClubUpdate,
) -> ClubResponse:
    try:
        club = require_club(db, user_id)
        if data.name is not None:
            club_repository.set_name(club, data.name)
        if data.friendly_available is not None:
            club_repository.set_availability(club, data.friendly_available)
        result = ClubResponse.model_validate(club)
        # La autenticación ya consultó con esta sesión: confirmar la transacción
        # existente, sin abrir un db.begin() anidado.
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
