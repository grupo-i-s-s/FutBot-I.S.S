from fastapi import APIRouter, Query

from app.dependencies import CurrentClub, Database, CurrentIdentity
from app.schemas.club_schemas import (
    ClubLeagueListResponse,
    ClubListResponse,
    ClubProfileRead,
    ClubPublicRead,
    ClubRead,
    ClubUpdate,
)
from app.schemas.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Page, validate_page_offset
from app.services import club_services as club_service
from typing import Annotated


club_router = APIRouter(tags=["clubs"])


@club_router.get("/clubs", response_model=Page[ClubPublicRead])
def get_clubs(
    identity: CurrentIdentity,
    db: Database,
    name: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
):
    validate_page_offset(page, page_size)
    result = club_service.list_clubs(db, name=name, user_id=identity.user_id, page=page, page_size=page_size)
    return Page[ClubPublicRead](items=result.items, page=page, page_size=page_size, total=result.total)


@club_router.get("/club", response_model=ClubListResponse, include_in_schema=False)
def get_legacy_clubs(
    identity: CurrentIdentity,
    db: Database,
    name: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[
        int,
        Query(alias="pageSize", ge=1, le=MAX_PAGE_SIZE),
    ] = DEFAULT_PAGE_SIZE,
):
    validate_page_offset(page, page_size)
    return club_service.list_clubs(
        db,
        name=name,
        user_id=identity.user_id,
        page=page,
        page_size=page_size,
    )

@club_router.get("/club/me", response_model=ClubRead, include_in_schema=False)
@club_router.get("/clubs/me", response_model=ClubRead)
def get_my_club(club: CurrentClub):
    return club


@club_router.patch("/club/me", response_model=ClubRead, include_in_schema=False)
@club_router.patch("/clubs/me", response_model=ClubRead)
def update_my_club(
        data: ClubUpdate,
        club: CurrentClub,
        db: Database,
):
    return club_service.update_club(db, club, data)


@club_router.get("/club/me/leagues", response_model=ClubLeagueListResponse, include_in_schema=False)
@club_router.get("/clubs/me/leagues", response_model=ClubLeagueListResponse)
def get_my_leagues(club: CurrentClub, db: Database):
    return club_service.list_joined_leagues(db, club.id)

@club_router.get("/club/{club_id}", response_model=ClubProfileRead, include_in_schema=False)
@club_router.get("/clubs/{club_id}", response_model=ClubProfileRead)
def get_club_profile( club_id: int, identity: CurrentIdentity, db: Database):
    return club_service.get_club_profile(db, club_id)
