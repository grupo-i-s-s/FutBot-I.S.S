from sqlalchemy.orm import Session
from app.models.matches_model import Matches 

def get_by_id(db:Session, match_id:int) -> Matches|None:
    return db.get(Matches, match_id)

