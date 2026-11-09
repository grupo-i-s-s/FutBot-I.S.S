from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from app.schemas.avatar_schemas import AvatarFilename
from app.schemas.Dt_schemas import DtRead


class ClubRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatar: str
    friendly_available: bool = Field(
        serialization_alias="friendlyAvailable"
    )

    dt: DtRead | None = None


class ClubUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(min_length=1, max_length=50)
    avatar: AvatarFilename
    friendly_available: StrictBool = Field(alias="friendlyAvailable")

class ClubLeagueRead(BaseModel):
    id: int
    name: str
    type: str
    status: str
    teams: int
    max_teams: int = Field(serialization_alias="maxTeams")


class ClubLeagueListResponse(BaseModel):
    items: list[ClubLeagueRead]

class ClubPublicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatar: str

class ClubStatsRead(BaseModel):
    played: int = Field(ge=0)
    wins: int = Field(ge=0)
    draws: int = Field(ge=0)
    losses: int = Field(ge=0)


class ClubRankingRead(BaseModel):
    position: int = Field(ge=1)
    points: int = Field(ge=0)
    source: Literal["PUBLIC_LEAGUES"] = "PUBLIC_LEAGUES"


class ClubPlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class ClubProfileRead(ClubPublicRead):
    stats: ClubStatsRead
    ranking: ClubRankingRead
    players: list[ClubPlayerRead]

class ClubListResponse(BaseModel):
    items: list[ClubPublicRead]
    page: int
    page_size: int = Field(serialization_alias="pageSize")
    total: int
    has_next: bool = Field(serialization_alias="hasNext")
