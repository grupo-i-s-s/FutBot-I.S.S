from fastapi import APIRouter

from app.dependencies import CurrentClub, Database
from app.schemas.club_schemas import (
    ClubLeagueListResponse,
    ClubRead,
    ClubUpdate,
)
from app.services import club_services as club_service

club_router = APIRouter(prefix="/club", tags=["club"])


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
