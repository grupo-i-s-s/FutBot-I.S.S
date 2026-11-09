from fastapi import APIRouter, status
from typing import Literal

from app.dependencies import CurrentClub, Database
from app.schemas.behaviour_schemas import BehaviourListResponse, BehaviourReadDetail, BehaviourUpdate
from app.services import behaviour_service
from app.schemas.behaviour_schemas import BehaviourCreate, BehaviourRead
from app.schemas.behaviour_schemas import ( BehaviourValidateRequest, BehaviourValidateResponse)
from primitives.behaviour_api.validation import validate_program

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

@behaviour_router.post("/validate", response_model=BehaviourValidateResponse)
def validate_behaviour( payload: BehaviourValidateRequest, club: CurrentClub) -> BehaviourValidateResponse:
    diagnostics = validate_program(payload.code, kind=payload.kind)

    return BehaviourValidateResponse(
        valid=not diagnostics,
        diagnostics=diagnostics,
    )

@behaviour_router.put(
    "/{behaviour_id}",
    response_model=BehaviourReadDetail,
    status_code=status.HTTP_200_OK,
)
def update_behaviour(
    behaviour_id: int,
    payload: BehaviourUpdate,
    club: CurrentClub,
    db: Database,
):
    return behaviour_service.update_behaviour(
        db=db,
        club_id=club.id,
        behaviour_id=behaviour_id,
        data=payload,
    )

@behaviour_router.get("/{behaviour_id}/usage")
def get_behaviour_usage( behaviour_id: int, club: CurrentClub, db: Database):
    return behaviour_service.get_behaviour_usage(
        db=db,
        club_id=club.id,
        behaviour_id=behaviour_id)