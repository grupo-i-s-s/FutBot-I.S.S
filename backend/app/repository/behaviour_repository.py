from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.behaviour_model import Behavior


DEFAULT_BEHAVIOR_CODE = '''print("hola futbot!")'''

DEFAULT_BEHAVIOURS = (
    ("Equilibrado", "Comportamiento inicial equilibrado."),
    ("Ofensivo", "Comportamiento inicial ofensivo."),
    ("Defensivo", "Comportamiento inicial defensivo."),
)

def create_default_behaviours(db: Session, club_id: int) -> list[Behavior]:
    behaviors = [
        Behavior(
            club_id=club_id,
            name=name,
            description=description,
            code=DEFAULT_BEHAVIOR_CODE,
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
