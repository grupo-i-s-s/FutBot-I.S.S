from fastapi import APIRouter

from app.dependencies import CurrentClub, Database
from app.schemas.behaviour import BehaviourListResponse, BehaviourReadDetail
from app.services import behaviour_service

behaviour_router = APIRouter(prefix="/behaviours", tags=["behaviours"])

# Obtengo la lista de comportamientos y un comportamiento en especifico

@behaviour_router.get("", response_model=BehaviourListResponse)
def get_behaviours(club: CurrentClub, db: Database):
    behaviours = behaviour_service.list_behaviours(db, club.id)
    return {"items": behaviours}


@behaviour_router.get("/{behaviour_id}", response_model=BehaviourReadDetail)
def get_behaviour(club: CurrentClub, db: Database, behaviour_id: int):
    return behaviour_service.behaviour_id(db, club.id, behaviour_id)