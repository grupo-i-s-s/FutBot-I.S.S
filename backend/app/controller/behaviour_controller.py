from fastapi import APIRouter, status
from typing import Literal

from app.dependencies import CurrentClub, Database
from app.schemas.behaviour_schemas import BehaviourListResponse, BehaviourReadDetail
from app.services import behaviour_service
from app.schemas.behaviour_schemas import BehaviourCreate, BehaviourRead

behaviour_router = APIRouter(prefix="/behaviours", tags=["behaviours"])


# Obtengo la lista de comportamientos y un comportamiento en especifico

@behaviour_router.get("", response_model=BehaviourListResponse)
def get_behaviours(club: CurrentClub, db: Database, kind: Literal["PLAYER"]|None=None):
    behaviours = behaviour_service.list_behaviours(db, club.id, kind=kind)
    return {"items": behaviours}


@behaviour_router.get("/{behaviour_id}", response_model=BehaviourReadDetail)
def get_behaviour(club: CurrentClub, db: Database, behaviour_id: int):
    return behaviour_service.behaviour_id(db, club.id, behaviour_id)

@behaviour_router.post("",response_model=BehaviourRead,status_code=status.HTTP_201_CREATED)
def create_behaviour(payload: BehaviourCreate, club: CurrentClub, db: Database):
    return behaviour_service.create_behaviour(db=db, club_id=club.id, data=payload)

@behaviour_router.delete("/{behaviour_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_behaviour(behaviour_id: int, club: CurrentClub, db:Database) -> None:
    behaviour_service.delete_behaviour(db=db, club_id=club.id, behaviour_id=behaviour_id)

    