from sqlalchemy.orm import Session
from app.models.behaviour import Behaviour


def get_by_id(db: Session, behaviour_id: int) -> Behaviour | None:
    return db.query(Behaviour).filter(Behaviour.id == behaviour_id).first()
