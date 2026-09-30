from sqlalchemy.orm import Session

from app.models.behaviour_model import Behavior
from app.repository import behaviour_repository


def list_behaviours(db: Session, club_id: int) -> list[Behavior]:
    return behaviour_repository.get_all_behaviours(db, club_id)