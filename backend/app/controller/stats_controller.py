from fastapi import APIRouter
from app.dependencies import Database
from app.repository import stats_repository
from app.schemas.stats_schemas import GlobalRankingResponse

stats_router = APIRouter(tags=["stats"])


@stats_router.get("/ranking-global", response_model=GlobalRankingResponse)
def get_global_ranking(db: Database):
    rankings = stats_repository.get_rankings(db, limit=100)
    return {"items": [dict(row) for row in rankings]}
