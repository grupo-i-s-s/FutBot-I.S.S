from fastapi import APIRouter, status
from app.dependencies import Database, CurrentClub, CurrentIdentity
from app.schemas.Dt_schemas import DtBehaviourCreate, DtBehaviourList, DtBehaviourRead, DtUpdate, DtRead
from app.services import dt_service

dt_router = APIRouter(tags=["clubs"])


@dt_router.get("/clubs/me/dt/behaviours", response_model=DtBehaviourList)
@dt_router.get("/dt/behaviours", response_model=DtBehaviourList, include_in_schema=False)
def get_dt_behaviours(db: Database, identity: CurrentIdentity):
    return {"items": dt_service.list_dt_behaviours(db, identity.user_id)}


@dt_router.post(
    "/clubs/me/dt/behaviours", response_model=DtBehaviourRead, status_code=status.HTTP_201_CREATED
)
@dt_router.post(
    "/dt/behaviours", response_model=DtBehaviourRead,
    status_code=status.HTTP_201_CREATED, include_in_schema=False,
)
def create_dt_behaviour(
    payload: DtBehaviourCreate, db: Database, identity: CurrentIdentity
):
    return dt_service.create_dt_behaviour(db, identity.user_id, payload)


@dt_router.patch("/clubs/me/dt", response_model=DtRead)
@dt_router.patch("/dt", response_model=DtRead, include_in_schema=False)
def update_dt(
    payload: DtUpdate, db: Database, club: CurrentClub, identity: CurrentIdentity
):
    return dt_service.update_dt_settings(db, club.id, identity.user_id, payload)
