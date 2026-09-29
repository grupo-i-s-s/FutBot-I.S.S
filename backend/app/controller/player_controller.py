from fastapi import APIRouter, status

from app.dependencies import CurrentClub, Database
from app.schemas.player import PlayerCreate, PlayerRead
from app.services import player_service

player_router = APIRouter(prefix="/players", tags=["players"])


@player_router.post("", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
def create_player(payload: PlayerCreate, club: CurrentClub, db: Database):
    return player_service.create_player(db=db, club_id=club.id, data=payload)
