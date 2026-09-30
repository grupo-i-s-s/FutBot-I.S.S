from fastapi import APIRouter, status

from app.dependencies import CurrentClub, Database
from app.schemas.league import LeagueLobbyRead
from app.schemas.league import LeaveLeagueResponse
from app.services import league_service

league_router = APIRouter(prefix="/leagues", tags=["leagues"])


@league_router.get(
    "/{id}/lobby", response_model=LeagueLobbyRead, status_code=status.HTTP_200_OK
)
def get_league_lobby(id: int, club: CurrentClub, db: Database):
    return league_service.get_league_lobby(db=db, league_id=id)


@league_router.post(
    "/{id}/leave",
    response_model=LeaveLeagueResponse,
    status_code=status.HTTP_200_OK,
)
def leave_league(id: int, club: CurrentClub, db: Database):
    return league_service.leave_league(db=db, league_id=id, club_id=club.id)
