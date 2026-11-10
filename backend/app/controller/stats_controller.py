from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import CurrentIdentity, Database
from app.repository import stats_repository
from app.schemas.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, validate_page_offset
from app.schemas.stats_schemas import GlobalRankingResponse

stats_router = APIRouter(tags=["stats"])


@stats_router.get("/ranking-global", response_model=GlobalRankingResponse)
def get_global_ranking(
    identity: CurrentIdentity,
    db: Database,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
):
    validate_page_offset(page, page_size)
    items, total = stats_repository.get_rankings(db, page=page, page_size=page_size)
    return GlobalRankingResponse(items=items, page=page, page_size=page_size, total=total)
