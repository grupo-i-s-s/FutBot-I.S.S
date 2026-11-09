from pydantic import BaseModel, Field

class GlobalRankingItem(BaseModel):
    id: int
    name: str
    avatar: str
    points: int
    played: int
    wins: int
    draws: int
    losses: int
    dg: int


class GlobalRankingResponse(BaseModel):
    items: list[GlobalRankingItem]
