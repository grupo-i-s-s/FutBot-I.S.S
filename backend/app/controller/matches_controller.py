from fastapi import APIRouter, status
from app.dependencies import CurrentIdentity, Database
from app.schemas.matches_schemas import (
    CreateFriendlyMatchRequest,
    CreateFriendlyMatchResponse,
    JoinMatchRequest,
)
from app.services import matches_service

matches_router = APIRouter(prefix="/friendly-matches", tags=["friendly-matches"])


@matches_router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=CreateFriendlyMatchResponse
)
def create_friendly_match(
    data: CreateFriendlyMatchRequest, db: Database, identity: CurrentIdentity
):
    return matches_service.create_friendly_match(db=db, club_id=identity.id, data=data)


@matches_router.post("/join", status_code=200)
def join_match(data: JoinMatchRequest, db: Database, identity: CurrentIdentity):
    return matches_service.join_match(db, data)
