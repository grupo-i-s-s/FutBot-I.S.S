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

