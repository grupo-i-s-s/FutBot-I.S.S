from sqlalchemy.orm import Session
from app.models.dt_model import Dt, DtBehaviour
from primitives.dt_behaviour import DEFAULT_DT_CODES

def get_dt_by_club_id(db: Session, club_id: int) -> Dt | None:
    return db.query(Dt).filter(Dt.club_id == club_id).first()


def get_all_dt_behaviours(db: Session, club_id: int) -> list[DtBehaviour]:
    return db.query(DtBehaviour).filter(DtBehaviour.user_id == club_id).all()


def create_default_dt_behaviours(db: Session, user_id: int) -> list[DtBehaviour]:
    behaviours = [
        DtBehaviour(user_id=user_id, name=name, code=code)
        for name, code in DEFAULT_DT_CODES.items()
    ]
    db.add_all(behaviours)
    db.flush() 
    return behaviours


def create_dt(db: Session, club_id: int, behaviour_id: int | None = None) -> Dt:
    dt = Dt(club_id=club_id, is_active=False, behaviour_id=behaviour_id)
    db.add(dt)
    db.flush()
    return dt
