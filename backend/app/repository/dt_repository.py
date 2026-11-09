from sqlalchemy.orm import Session
from app.models.dt_model import Dt

def get_dt_by_club_id(db: Session, club_id: int) -> Dt | None:
    return db.query(Dt).filter(Dt.club_id == club_id).first()