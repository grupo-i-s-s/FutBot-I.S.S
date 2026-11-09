from sqlalchemy.orm import Session
from app.models.dt_model import Dt, DtBehaviour

def get_dt_by_club_id(db: Session, club_id: int) -> Dt | None:
    return db.query(Dt).filter(Dt.club_id == club_id).first()


def get_all_dt_behaviours(db: Session, user_id: int) -> list[DtBehaviour]:
    return db.query(DtBehaviour).filter(DtBehaviour.user_id == user_id).all()