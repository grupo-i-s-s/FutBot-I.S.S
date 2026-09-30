from fastapi import APIRouter

from app.dependencies import CurrentClub, Database
from app.schemas.behaviour import BehaviourListResponse
from app.services import behaviour_service

behaviour_router = APIRouter(prefix="/behaviours", tags=["behaviours"])


@behaviour_router.get("", response_model=BehaviourListResponse)
def get_behaviours(club: CurrentClub, db: Database):
    behaviours = behaviour_service.list_behaviours(db, club.id)
    return {"items": behaviours}
