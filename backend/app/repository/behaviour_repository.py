from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.behaviour_model import Behavior


DEFAULT_BEHAVIOR_CODE = '''print("hola futbot!")'''


def create_default_behaviour(db: Session, club_id: int) -> Behavior:
    behavior = Behavior(
        club_id=club_id,
        name="Equilibrado",
        description="Patea cuando tiene la pelota; si no, corre.",
        code=DEFAULT_BEHAVIOR_CODE
    )
    db.add(behavior)
    db.flush()  # Necesitamos behavior.id para asignarlo a los jugadores.

    return behavior


def get_default_behaviour(db: Session, club_id: int) -> Behavior | None:
    return db.scalar(
        select(Behavior)
        .where(Behavior.club_id == club_id, Behavior.is_deleted.is_(False))
        .order_by(Behavior.id)
        .limit(1)
    )


def get_all_behaviours(db: Session, club_id: int) -> list[Behavior]:
    query = (
        select(Behavior)
        .where(Behavior.club_id == club_id, Behavior.is_deleted.is_(False))
        .order_by(Behavior.id)
    )
    return list(db.scalars(query).all())


def get_behaviour_by_id(db:Session, club_id: int, behaviour_id: int) -> Behavior | None:
        return db.scalar(
        select(Behavior)
        .where(Behavior.club_id == club_id, Behavior.is_deleted.is_(False), Behavior.id == behaviour_id)
    )