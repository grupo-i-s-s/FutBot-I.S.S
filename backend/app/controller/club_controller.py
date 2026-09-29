from fastapi import APIRouter

from app.dependencies import CurrentIdentity, Database
from app.schemas.club_schemas import ClubAvailabilityUpdate, ClubResponse
from app.services import club_service


club_router = APIRouter(prefix="/club", tags=["club"])


@club_router.get("/me", response_model=ClubResponse)
def get_my_club(db: Database, identity: CurrentIdentity) -> ClubResponse:
    return club_service.get_my_club(db, identity.user_id)


@club_router.patch("/me", response_model=ClubResponse)
def update_my_availability(
    data: ClubAvailabilityUpdate, db: Database, identity: CurrentIdentity,
) -> ClubResponse:
    return club_service.update_availability(db, identity.user_id, data)
