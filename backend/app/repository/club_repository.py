from sqlalchemy.orm import Session

from app.models.auth_model import Club
from app.repository.user_repository import get_club


def get_by_user_id(db: Session, user_id: int) -> Club | None:
    return get_club(db, user_id)


def set_availability(club: Club, available: bool) -> None:
    club.friendly_available = available
