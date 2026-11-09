from fastapi import APIRouter, status
from app.dependencies import Database, CurrentClub, CurrentIdentity
from app.schemas.Dt_schemas import DtBehaviourCreate, DtBehaviourList, DtBehaviourRead, DtUpdate, DtRead
from app.services import dt_service

dt_router = APIRouter(prefix="/dt", tags=["dt"])


@dt_router.get("/behaviours", response_model=DtBehaviourList)
def get_dt_behaviours(db: Database, identity: CurrentIdentity):
    return {"items": dt_service.list_dt_behaviours(db, identity.user_id)}


@dt_router.post(
    "/behaviours", response_model=DtBehaviourRead, status_code=status.HTTP_201_CREATED
)
def create_dt_behaviour(
    payload: DtBehaviourCreate, db: Database, identity: CurrentIdentity
):
    return dt_service.create_dt_behaviour(db, identity.user_id, payload)


@dt_router.patch("", response_model=DtRead)
def update_dt(
    payload: DtUpdate, db: Database, club: CurrentClub, identity: CurrentIdentity
):
    return dt_service.update_dt_settings(db, club.id, identity.user_id, payload)
