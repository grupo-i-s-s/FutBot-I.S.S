from fastapi import APIRouter, Query

from app.dependencies import CurrentClub, Database, CurrentIdentity
from app.schemas.club_schemas import (
    ClubLeagueListResponse,
    ClubRead,
    ClubUpdate,
    ClubListResponse
)
from app.services import club_services as club_service
from typing import Annotated


club_router = APIRouter(prefix="/club", tags=["club"])

@club_router.get("", response_model=ClubListResponse)
def get_clubs(
    identity: CurrentIdentity,
    db: Database,
    name: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[
        int,
        Query(alias="pageSize", ge=1, le=100),
    ] = 20,
):
    return club_service.list_clubs(
        db,
        name=name,
        page=page,
        page_size=page_size,
    )

@club_router.get("/me", response_model=ClubRead)
def get_my_club(club: CurrentClub):
    return club


@club_router.patch("/me", response_model=ClubRead)
def update_my_club(
        data: ClubUpdate,
        club: CurrentClub,
        db: Database,
):
    return club_service.update_club(db, club, data)


@club_router.get("/me/leagues", response_model=ClubLeagueListResponse)
def get_my_leagues(club: CurrentClub, db: Database):
    return club_service.list_joined_leagues(db, club.id)
