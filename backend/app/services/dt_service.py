from sqlalchemy.orm import Session
from app.repository.dt_repository import get_all_dt_behaviours, get_dt_behaviour, get_dt_by_club_id
from app.models.dt_model import DtBehaviour, Dt
from app.schemas.Dt_schemas import DtBehaviourCreate, DtUpdate
from primitives.behaviour_api.validation import validate_program
from app.errors import AppError


def list_dt_behaviours(db: Session, user_id: int) -> list[DtBehaviour]:
    return get_all_dt_behaviours(db, user_id)


def create_dt_behaviour(
    db: Session, user_id: int, data: DtBehaviourCreate
) -> DtBehaviour:
    diagnostics = validate_program(data.code, kind="DT")
    if diagnostics:
        raise AppError(
            "BEHAVIOUR_INVALID",
            "El programa del DT es inválido.",
            diagnostics=diagnostics,
        )
    new_behaviour = DtBehaviour(user_id=user_id, name=data.name, code=data.code)
    db.add(new_behaviour)
    db.commit()
    db.refresh(new_behaviour)
    return new_behaviour


def update_dt_settings(db: Session, club_id: int, user_id: int, data: DtUpdate) -> Dt:
    try:
        dt = get_dt_by_club_id(db, club_id, lock=True)
        if dt is None:
            raise AppError("ACCOUNT_INCOMPLETE", "El club no tiene un DT configurado.")

        behaviour_id = (
            data.active_behaviour_id
            if "active_behaviour_id" in data.model_fields_set
            else dt.behaviour_id
        )
        if behaviour_id is not None and get_dt_behaviour(db, user_id, behaviour_id) is None:
            raise AppError(
                "BEHAVIOUR_NOT_FOUND",
                "El comportamiento de DT no existe o no te pertenece.",
            )
        if data.is_active and behaviour_id is None:
            raise AppError("DT_BEHAVIOUR_REQUIRED", "Elegí un comportamiento para activar el DT.")

        dt.is_active = data.is_active
        dt.behaviour_id = behaviour_id
        db.commit()
        return dt
    except Exception:
        db.rollback()
        raise
