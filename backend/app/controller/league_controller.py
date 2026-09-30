from fastapi import APIRouter, status

from app.dependencies import CurrentClub, Database
from app.schemas.league import (LeagueLobbyRead, CreateLeagueRequest, CreateLeagueResponse,)
from app.services import league_service

league_router = APIRouter(prefix="/leagues", tags=["leagues"])


@league_router.get(
    "/{id}/lobby", response_model=LeagueLobbyRead, status_code=status.HTTP_200_OK
)
def get_league_lobby(id: int, club: CurrentClub, db: Database):
    return league_service.get_league_lobby(db=db, league_id=id)

@league_router.post(
    "/public", response_model=CreateLeagueResponse, status_code=status.HTTP_201_CREATED

)
def create_league(db: Database, data:CreateLeagueRequest):
    return league_service.create_league(db=db, data=data)