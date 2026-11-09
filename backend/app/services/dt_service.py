from app.repository.dt_repository import get_all_dt_behaviours
from sqlalchemy.orm import Session

def list_dt_behaviours(db:Session):
    return get_all_dt_behaviours(db)