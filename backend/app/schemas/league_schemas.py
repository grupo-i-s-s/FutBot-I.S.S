from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


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


class RoundInterval(str, Enum):
    CONTINUOUS = "CONTINUOUS"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"


class CreateLeagueRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=50)
    min_teams: int = Field(alias="minTeams", ge=3)
    max_teams: int = Field(alias="maxTeams", ge=3)
    start_date: datetime = Field(
        validation_alias=AliasChoices(
            "start_date", "start_datetime", "startDateTime", "startDatetime"
        )
    )
    round_interval: RoundInterval = Field(alias="roundInterval")

    @model_validator(mode="after")
    def validate_league_config(self):
        if self.min_teams > self.max_teams:
            raise ValueError("minTeams no puede ser mayor que maxTeams.")
        return self


class CreatePrivateLeagueRequest(CreateLeagueRequest):
    password: str


class LeagueJoinRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    club_id: int = Field(
        validation_alias="clubId",
        serialization_alias="clubId",
    )
    line_up: list = Field(
        validation_alias="lineUp",
        serialization_alias="lineUp",
    )
    access_code: str | None = Field(
        default=None,
        validation_alias="accessCode",
        serialization_alias="accessCode",
    )