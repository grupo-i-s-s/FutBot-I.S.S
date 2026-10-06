from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.behaviour_model import Behavior
from primitives.behaviours import DEFAULT_CODES

DEFAULT_BEHAVIOURS = (
    ("Equilibrado", "El más cercano busca la pelota; los demás acompañan manteniendo su línea."),
    ("Ofensivo", "Busca la pelota en toda la cancha y patea hacia el arco rival."),
    ("Defensivo", "Protege su posición y busca la pelota cuando está en su mitad de cancha."),
)


def create_default_behaviours(db: Session, club_id: int) -> list[Behavior]:
    behaviors = [
        Behavior(
            club_id=club_id,
            name=name,
            description=description,
            code=DEFAULT_CODES[name],
        )
        for name, description in DEFAULT_BEHAVIOURS
    ]
    db.add_all(behaviors)
    db.flush()  # Necesitamos los IDs para asignarlos a los jugadores.

    return behaviors


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


def get_behaviour_by_id(db: Session, club_id: int, behaviour_id: int) -> Behavior | None:
    return db.scalar(
        select(Behavior)
        .where(Behavior.club_id == club_id, Behavior.is_deleted.is_(False), Behavior.id == behaviour_id)
    )
