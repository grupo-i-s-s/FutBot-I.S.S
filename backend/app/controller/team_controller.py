from fastapi import APIRouter

from app.dependencies import CurrentClub, Database
from app.schemas.team_schemas import (
    DefaultTeamRead,
    FormationListResponse,
    Lineup,
)
from app.services import team_service


team_router = APIRouter(prefix="/team", tags=["team"])
catalogs_router = APIRouter(prefix="/catalogs", tags=["catalogs"])


@team_router.get("/default", response_model=DefaultTeamRead)
def get_default_team(club: CurrentClub, db: Database):
    return team_service.get_default_team(db, club.id)


@team_router.put("/default", response_model=DefaultTeamRead)
def update_default_team(
    data: Lineup,
    club: CurrentClub,
    db: Database,
):
    return team_service.update_default_team(db, club.id, data)


@catalogs_router.get("/formations", response_model=FormationListResponse)
def get_formations(club: CurrentClub):
    return team_service.get_formations()