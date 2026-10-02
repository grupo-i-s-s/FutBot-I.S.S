from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import CurrentClub, Database
from app.schemas.league_schemas import (LeagueLobbyRead, CreateLeagueRequest, CreateLeagueResponse,
                                        LeaveLeagueResponse, LeagueJoinRequest)
from app.services import league_service

league_router = APIRouter(prefix="/leagues", tags=["leagues"])


@league_router.get(
    "/{id}/lobby", response_model=LeagueLobbyRead, status_code=status.HTTP_200_OK
)
def get_league_lobby(id: int, club: CurrentClub, db: Database):
    return league_service.get_league_lobby(db=db, league_id=id)


@league_router.post(
    "/{id}/join",
    status_code=status.HTTP_201_CREATED,
)
def join_league(
    id: int,
    body: LeagueJoinRequest,
    club: CurrentClub,
    db: Database,
):
    if body.club_id != club.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El club indicado no corresponde al club autenticado.",
        )

    return league_service.join_league(
        db=db,
        league_id=id,
        club_id=club.id,
        line_up=body.line_up,
        access_code=body.access_code,
    )
def leave_league(id: int, club: CurrentClub, db: Database):
    return league_service.leave_league(db=db, league_id=id, club_id=club.id)

@league_router.post(
    "/public", response_model=CreateLeagueResponse, status_code=status.HTTP_201_CREATED

)
def create_league(db: Database, data:CreateLeagueRequest):
    return league_service.create_league(db=db, data=data)

@league_router.post(
    "/{id}/join",
    status_code=status.HTTP_201_CREATED,
)
def join_league(id: int, body: LeagueJoinRequest, club: CurrentClub, db: Database):
    return league_service.join_league(
        db=db, league_id=id, club_id=body.club_id, line_up=body.line_up
    )
