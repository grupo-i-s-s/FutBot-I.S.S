from fastapi import APIRouter

from app.dependencies import CurrentClub, Database
from app.schemas.matches_schemas import PlannedSubstitutionRequest, SubstitutionRequest
from app.services.planned_substitution_service import plan_substitution, request_substitution


planned_substitution_router = APIRouter(prefix="/matches", tags=["matches"])


@planned_substitution_router.put("/{match_id}/planned-substitution")
def plan_match_substitution(match_id: int, data: PlannedSubstitutionRequest, db: Database, club: CurrentClub):
    return plan_substitution(db, match_id, club.id, data)


@planned_substitution_router.post("/{match_id}/substitutions", status_code=202)
def request_match_substitution(match_id: int, data: SubstitutionRequest, db: Database, club: CurrentClub):
    return request_substitution(db, match_id, club.id, data)
