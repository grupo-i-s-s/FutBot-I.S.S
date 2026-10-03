from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class LeagueRegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    league_id: int = Field(serialization_alias="leagueId")
    club_id: int = Field(serialization_alias="clubId")
    joined_at: datetime = Field(serialization_alias="joinedAt")


class LeagueLobbyClubRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class LeagueLobbyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_private: bool = Field(serialization_alias="isPrivate")
    creator_club_id: Optional[int] = Field(None, serialization_alias="creatorClubId")
    min_teams: int = Field(serialization_alias="minTeams")
    max_teams: int = Field(serialization_alias="maxTeams")
    start_datetime: datetime = Field(serialization_alias="startDatetime")
    round_interval: str = Field(serialization_alias="roundInterval")
    end_datetime: Optional[datetime] = Field(None, serialization_alias="endDatetime")
    status: str
    registrations: list[LeagueRegistrationRead] = Field(default_factory=list)
    creator_club: Optional[LeagueLobbyClubRead] = Field(
        None, serialization_alias="creatorClub"
    )
    clubs: list[LeagueLobbyClubRead] = Field(default_factory=list)
    registered_teams: int = Field(serialization_alias="registeredTeams")
    remaining_slots: int = Field(serialization_alias="remainingSlots")
    is_registered: bool = Field(serialization_alias="isRegistered")


class LeaveLeagueResponse(BaseModel):
    model_config = ConfigDict()

    message: str
    league_id: int = Field(serialization_alias="leagueId")


class CreateLeagueResponse(BaseModel):
    message: str


class CreateLeagueRequest(BaseModel):
    name: str
    min_teams: int
    max_teams: int
    start_date: datetime
    round_interval: str


class CreatePrivateLeagueRequest(CreateLeagueRequest):
    password: str
