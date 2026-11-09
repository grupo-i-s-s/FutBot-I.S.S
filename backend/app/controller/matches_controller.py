from typing import Annotated

from fastapi import APIRouter, Body, Path, Query, status
from pydantic import StrictBool

from app.dependencies import CurrentClub, Database
from app.schemas.matches_schemas import (
    ClubFriendlyMatchResponse,
    CreateFriendlyMatchRequest,
    CreateFriendlyMatchResponse,
    FriendlyMatchResponse,
    JoinMatchRequest,
    JoinMatchResponse,
    MatchStateResponse,
)
from app.schemas.pagination import Page
from app.services import matches_service

matches_router = APIRouter(prefix="/friendly-matches", tags=["friendly-matches"])


@matches_router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=CreateFriendlyMatchResponse
)
def create_friendly_match(
        data: CreateFriendlyMatchRequest, db: Database, club: CurrentClub
):
    return matches_service.create_friendly_match(db=db, club_id=club.id, data=data)


@matches_router.get("", response_model=Page[FriendlyMatchResponse])
def list_friendly_matches(
    db: Database, club: CurrentClub, creator_name: str | None = Query(default=None, alias="creatorName"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
):
    return Page[FriendlyMatchResponse](
        **matches_service.list_available(db, club.id, creator_name=creator_name, page=page, page_size=page_size)
    )


@matches_router.get("/me", response_model=list[ClubFriendlyMatchResponse])
def list_my_friendly_matches(db: Database, club: CurrentClub):
    return matches_service.list_for_club(db, club.id)


@matches_router.post("/{match_id}/join", response_model=JoinMatchResponse)
def join_friendly_match(match_id: Annotated[int, Path(gt=0)], db: Database, club: CurrentClub):
    return matches_service.join_match(db, match_id, club.id)


@matches_router.post("/join", response_model=JoinMatchResponse, include_in_schema=False)
def join_match(data: JoinMatchRequest, db: Database, club: CurrentClub):
    return matches_service.join_match(db, data.match_id, club.id)


@matches_router.get("/{match_id}", response_model=MatchStateResponse, include_in_schema=False)
def get_match_state(match_id: int, db: Database, club: CurrentClub):
    return matches_service.get_match_state(db=db, match_id=match_id, club_id=club.id)

@matches_router.post( "/behaviour-test",status_code=status.HTTP_201_CREATED,response_model=CreateFriendlyMatchResponse)
def create_behaviour_test_match(db: Database, club: CurrentClub):
    return matches_service.create_behaviour_test_match(db, club.id)


@matches_router.post("/{match_id}/dt", include_in_schema=False)
def update_match_dt(
    match_id: int,
    db: Database,
    club: CurrentClub,
    dt_active: Annotated[StrictBool, Body(embed=True)],
):
    matches_service.reject_match_dt_change(db, match_id, club.id)
