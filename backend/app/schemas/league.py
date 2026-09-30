from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LeagueRegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    league_id: int = Field(serialization_alias="leagueId")
    club_id: int = Field(serialization_alias="clubId")
    joined_at: datetime = Field(serialization_alias="joinedAt")


class LeagueLobbyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    min_teams: int = Field(serialization_alias="minTeams")
    max_teams: int = Field(serialization_alias="maxTeams")
    start_datetime: datetime = Field(serialization_alias="startDatetime")
    end_datetime: Optional[datetime] = Field(None, serialization_alias="endDatetime")
    status: str
    registrations: list[LeagueRegistrationRead] = Field(default_factory=list)


class LeaveLeagueResponse(BaseModel):
    model_config = ConfigDict()

    message: str
    league_id: int = Field(serialization_alias="leagueId")
