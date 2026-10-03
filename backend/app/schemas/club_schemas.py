from pydantic import BaseModel, ConfigDict, Field, StrictBool


class ClubRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatar: str
    friendly_available: bool = Field(
        serialization_alias="friendlyAvailable"
    )


class ClubUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(min_length=1, max_length=50)
    avatar: str = Field(min_length=1, max_length=80)
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
    