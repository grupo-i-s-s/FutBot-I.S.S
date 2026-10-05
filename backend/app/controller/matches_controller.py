from fastapi import APIRouter, status
from app.dependencies import CurrentClub, Database
from app.schemas.matches_schemas import (
    CreateFriendlyMatchRequest,
    CreateFriendlyMatchResponse,
    FriendlyMatchResponse,
    JoinMatchRequest,
    JoinMatchResponse,
    MatchStateResponse,
)
from app.services import matches_service

matches_router = APIRouter(prefix="/friendly-matches", tags=["friendly-matches"])


@matches_router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=CreateFriendlyMatchResponse
)
def create_friendly_match(
    data: CreateFriendlyMatchRequest, db: Database, club: CurrentClub
):
    return matches_service.create_friendly_match(db=db, club_id=club.id, data=data)


@matches_router.get("", response_model=list[FriendlyMatchResponse])
def list_friendly_matches(db: Database, club: CurrentClub):
    return matches_service.list_available(db, club.id)


@matches_router.post("/join", response_model=JoinMatchResponse)
def join_match(data: JoinMatchRequest, db: Database, club: CurrentClub):
    return matches_service.join_match(db, data.match_id, club.id)


@matches_router.get("/{match_id}", response_model=MatchStateResponse)
def get_match_state(match_id: int, db: Database, club: CurrentClub):
    return matches_service.get_match_state(db=db, match_id=match_id, club_id=club.id)
