from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentClub, Database
from app.schemas.league_schemas import (
    CreateLeagueRequest,
    CreateLeagueResponse,
    CreatePrivateLeagueRequest,
    LeagueListResponse,
    LeagueLobbyRead,
    LeaveLeagueResponse,
    LeagueJoinRequest,
    StartLeagueResponse,
    LeagueFixtureRead,
    LeagueLineupRead,
    LeagueLineupUpdate,
)
from app.services import league_fixture_service, league_service, league_lineup_service

league_router = APIRouter(prefix="/leagues", tags=["leagues"])

@league_router.get("/{id}/lineup", response_model=LeagueLineupRead)
def get_league_lineup(id: int, club: CurrentClub, db: Database):
    return league_lineup_service.get_lineup(db, id, club.id)


@league_router.put("/{id}/lineup", response_model=LeagueLineupRead)
def update_league_lineup( id: int, data: LeagueLineupUpdate, club: CurrentClub, db: Database):
    return league_lineup_service.update_lineup(db, id, club.id, data)

@league_router.get("/{id}/fixture", response_model=LeagueFixtureRead)
def get_league_fixture(id: int, club: CurrentClub, db: Database):
    return league_fixture_service.get_league_fixture(db, id, club.id)


@league_router.post("/{id}/start", response_model=StartLeagueResponse)
def start_league(id: int, club: CurrentClub, db: Database):
    return league_service.start_league(db=db, league_id=id, club_id=club.id)


@league_router.get(
    "/{id}/lobby", response_model=LeagueLobbyRead, status_code=status.HTTP_200_OK
)
def get_league_lobby(id: int, club: CurrentClub, db: Database):
    return league_service.get_league_lobby(
        db=db,
        league_id=id,
        club_id=club.id,
    )


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


@league_router.post(
    "/{id}/leave",
    response_model=LeaveLeagueResponse,
    status_code=status.HTTP_200_OK,
)
def leave_league(id: int, club: CurrentClub, db: Database):
    return league_service.leave_league(
        db=db,
        league_id=id,
        club_id=club.id,
    )


@league_router.post(
    "/public",
    response_model=CreateLeagueResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_league(db: Database, data: CreateLeagueRequest, club: CurrentClub):
    return league_service.create_league(
        db=db,
        data=data,
        creator_club_id=club.id,
    )


@league_router.post(
    "/private",
    response_model=CreateLeagueResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_private_league(
        db: Database, data: CreatePrivateLeagueRequest, club: CurrentClub
):
    return league_service.create_private_league(
        db=db, data=data, creator_club_id=club.id
    )


@league_router.get("", response_model=LeagueListResponse)
def get_leagues(club: CurrentClub, db: Database, name: str | None = None):
    leagues = league_service.list_leagues(db=db, club_id=club.id, name=name)
    return {"items": leagues}

@league_router.get("/{id}/ranking", status_code = status.HTTP_200_OK)
def get_league_ranking(id:int, club: CurrentClub, db:Database):
    return league_service.league_rank(id, db)