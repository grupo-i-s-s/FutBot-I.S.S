from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


class InputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JoinMatchRequest(InputSchema):
    match_id: int = Field(alias="idPartido", gt=0)


class PlannedSubstitutionRequest(InputSchema):
    out_player_id: StrictInt = Field(alias="outPlayerId", gt=0)
    in_player_id: StrictInt = Field(alias="inPlayerId", gt=0)
    command_id: str = Field(alias="commandId", min_length=1, pattern=r"\S")

    @model_validator(mode="after")
    def validate_different_players(self) -> "PlannedSubstitutionRequest":
        if self.out_player_id == self.in_player_id:
            raise ValueError("El jugador entrante debe ser distinto del saliente.")
        return self


class SubstitutionRequest(PlannedSubstitutionRequest):
    pause_id: str = Field(alias="pauseId", min_length=1, pattern=r"\S")


class CreateFriendlyMatchRequest(InputSchema):
    start_datetime: datetime = Field(..., alias="startDateTime")
    model_config = ConfigDict(populate_by_name=True)


class CreateFriendlyMatchResponse(BaseModel):
    message: str
    match_id: int = Field(serialization_alias="matchId")


class FriendlyMatchResponse(BaseModel):
    match_id: int = Field(serialization_alias="matchId")
    creator_club_name: str = Field(serialization_alias="creatorClubName")
    start_datetime: datetime = Field(serialization_alias="startDateTime")


class FriendlyMatchListResponse(BaseModel):
    items: list[FriendlyMatchResponse]
    total: int
    page: int
    page_size: int = Field(serialization_alias="pageSize")


class ClubFriendlyMatchResponse(FriendlyMatchResponse):
    visitor_club_name: str | None = Field(serialization_alias="visitorClubName")
    status: str
    is_creator: bool = Field(serialization_alias="isCreator")


class JoinMatchResponse(BaseModel):
    message: str
    match_id: int = Field(serialization_alias="matchId")


class MatchStateResponse(BaseModel):
    status: str = Field(serialization_alias="status")
    local_score: int = Field(serialization_alias="localScore")
    visitor_score: int = Field(serialization_alias="visitorScore")
    duration_ms: int = Field(serialization_alias="durationMs")
    model_config = ConfigDict(populate_by_name=True)

class LiveRequests(BaseModel):
    player_id: int
    behaviour_id: int
