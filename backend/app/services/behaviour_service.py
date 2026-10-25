from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.behaviour_model import Behavior
from app.repository import behaviour_repository
from app.schemas.behaviour_schemas import BehaviourCreate
from app.services.behaviour_validation_service import validate_program

def list_behaviours(db: Session, club_id: int, kind: str|None=None) -> list[Behavior]:
    return behaviour_repository.get_all_behaviours(db, club_id, kind=kind)


def behaviour_id(db: Session, club_id: int, behaviour_id: int) -> Behavior:
    behaviour = behaviour_repository.get_behaviour_by_id(db, club_id, behaviour_id)

    if behaviour is None:
        raise AppError(
            "BEHAVIOUR_NOT_FOUND",
            "No se encontro el comportamiento.")
    return behaviour

def create_behaviour(db: Session, club_id: int, data: BehaviourCreate)-> Behavior:
    diagnostics = validate_program(data.code)

    if diagnostics:
        raise AppError("BEHAVIOUR_INVALID", "El programa del comportamiento es inválido.", diagnostics=diagnostics)
        
    behavior = Behavior(
        club_id=club_id,
        name=data.name,
        description="",
        code=data.code,
        kind=data.kind,
        version=1,
        validation_status="VALID",
        is_deleted=False,
    )
    try:
        created = behaviour_repository.create_behaviour(db, behavior)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return created