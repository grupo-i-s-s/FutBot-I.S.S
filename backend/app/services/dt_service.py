from sqlalchemy.orm import Session
from app.repository.dt_repository import get_all_dt_behaviours, get_dt_by_club_id
from app.models.dt_model import DtBehaviour, Dt
from app.schemas.Dt_schemas import DtBehaviourCreate, DtUpdate
from primitives.behaviour_api.validation import validate_program
from app.errors import AppError


def list_dt_behaviours(db: Session, user_id: int):
    return db.query(DtBehaviour).filter(DtBehaviour.user_id == user_id).all()


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
    dt = get_dt_by_club_id(db, club_id)
    if not dt:
        raise AppError("ACCOUNT_INCOMPLETE", "El club no tiene un DT configurado.")

    dt.is_active = data.is_active

    if data.active_behaviour_id is not None:
        behaviour = (
            db.query(DtBehaviour)
            .filter(
                DtBehaviour.id == data.active_behaviour_id,
                DtBehaviour.user_id == user_id,
            )
            .first()
        )

        if not behaviour:
            raise AppError(
                "BEHAVIOUR_NOT_FOUND",
                "El comportamiento de DT no existe o no te pertenece.",
            )

        dt.behaviour_id = behaviour.id

    db.commit()
    db.refresh(dt)
    return dt
