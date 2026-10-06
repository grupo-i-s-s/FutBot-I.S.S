from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.behaviour_model import Behavior
from app.repository import behaviour_repository


def list_behaviours(db: Session, club_id: int) -> list[Behavior]:
    return behaviour_repository.get_all_behaviours(db, club_id)


def behaviour_id(db: Session, club_id: int, behaviour_id: int) -> Behavior:
    behaviour = behaviour_repository.get_behaviour_by_id(db, club_id, behaviour_id)

    if behaviour is None:
        raise AppError(
            "BEHAVIOUR_NOT_FOUND",
            "No se encontro el comportamiento.")
    return behaviour
