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


class CreateLeagueResponse(BaseModel):
    message: str 
    
class CreateLeagueRequest(BaseModel):
    name: str
    min_teams:int 
    max_teams:int
    start_date: datetime 
    round_interval: str


class LeagueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    start_datetime: datetime = Field(serialization_alias="startDatetime")
    round_interval: str = Field(serialization_alias="roundInterval")
    status: str
    min_teams: int = Field(serialization_alias="minTeams")
    max_teams: int = Field(serialization_alias="maxTeams")
    registered_count: int = Field(serialization_alias="registeredCount")
    available_slots: int = Field(serialization_alias="availableSlots")
    is_member: bool = Field(serialization_alias="isMember")


class LeagueListResponse(BaseModel):
    items: list[LeagueRead]
