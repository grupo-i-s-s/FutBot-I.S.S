from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class LeagueCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str = Field(min_length=3, max_length=50)
    min_teams: int = Field(alias="minTeams", ge=3)
    max_teams: int = Field(alias="maxTeams", ge=3)
    start_datetime: datetime = Field(alias="startDatetime")


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


class LeagueType(str, Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class RoundInterval(str, Enum):
    CONTINUOUS = "CONTINUOUS"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"


class CreateLeagueRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    type: LeagueType
    min_teams: int = Field(..., alias="minTeams", ge=3)
    max_teams: int = Field(..., alias="maxTeams", ge=3)
    start_datetime: datetime = Field(..., alias="startDateTime")
    round_interval: RoundInterval = Field(..., alias="roundInterval")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def validate_league_config(self):
        if self.min_teams > self.max_teams:
            raise ValueError("minTeams no puede ser mayor que maxTeams.")
        return self


class CreateLeagueResponse(BaseModel):
    message: str
