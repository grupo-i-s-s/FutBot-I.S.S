from fastapi import APIRouter
from app.dependencies import CurrentIdentity, Database
from app.schemas.matches_schemas import JoinMatchRequest
from app.services import matches_service

matches_router = APIRouter(prefix="/partidos", tags=["partidos"])


@matches_router.post("/unirse", status_code=200)
def join_match(data: JoinMatchRequest, db: Database, identity: CurrentIdentity):
    return matches_service.join_match(db, data)
