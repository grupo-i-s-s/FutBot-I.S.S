import math
from fastapi import APIRouter, status, Query

from app.dependencies import CurrentClub, Database
from app.schemas.player import (
    PlayerBehaviourUpdate,
    PlayerCreate,
    PlayerListResponse,
    PlayerRead,
)
from app.services import player_service

player_router = APIRouter(prefix="/players", tags=["players"])


@player_router.get(
    "", response_model=PlayerListResponse, status_code=status.HTTP_200_OK
)
def list_players(club: CurrentClub, db: Database):
    players = player_service.get_players(db=db, club_id=club.id)
    return {"items": players}


@player_router.get(
    "", response_model=PlayerListResponse, status_code=status.HTTP_200_OK
)
def list_players(
    club: CurrentClub,
    db: Database,
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(9, ge=1, le=9, description="Cantidad de elementos por página"),
):
    
    players, total_count = player_service.get_players(db=db, club_id=club.id, page=page, limit=limit)
    total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

    return {
        "items": players,
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


@player_router.post("", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
def create_player(payload: PlayerCreate, club: CurrentClub, db: Database):
    return player_service.create_player(db=db, club_id=club.id, data=payload)


@player_router.patch("/{player_id}/behaviour", response_model=PlayerRead)
def assign_player_behaviour(
    player_id: int, payload: PlayerBehaviourUpdate, club: CurrentClub, db: Database
):
    return player_service.assign_behaviour(
        db=db, club_id=club.id, player_id=player_id, behaviour_id=payload.behaviour_id
    )
