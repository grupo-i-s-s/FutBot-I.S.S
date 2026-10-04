from fastapi import APIRouter, status

from app.dependencies import CurrentClub, Database
from app.schemas.player import (
    PlayerBehaviourUpdate,
    PlayerCreate,
    PlayerListResponse,
    PlayerRead,
)
from app.services import player_service

player_router = APIRouter(prefix="/players", tags=["players"])


@player_router.get("", response_model=PlayerListResponse, status_code=status.HTTP_200_OK)
def list_players(club: CurrentClub, db: Database):
    players = player_service.get_players(db=db, club_id=club.id)
    return {"items": players}


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