from pydantic import BaseModel, Field

from app.schemas.pagination import Page


class GlobalRankingItem(BaseModel):
    id: int
    name: str
    avatar: str
    position: int
    points: int
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int = Field(serialization_alias="goalsFor")
    goals_against: int = Field(serialization_alias="goalsAgainst")
    dg: int


class GlobalRankingResponse(Page[GlobalRankingItem]):
    pass
