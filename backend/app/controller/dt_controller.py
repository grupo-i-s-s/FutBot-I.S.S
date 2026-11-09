from fastapi import APIRouter
from sqlalchemy.orm import Session
from app.repository.dt_repository import get_all_dt_behaviours

dt_router = APIRouter()

@dt_router.get("/dt-behaviours")
def get_dt_behaviours(db:Session):
    behaviours = get_all_dt_behaviours(db)
    return {"items": behaviours}

