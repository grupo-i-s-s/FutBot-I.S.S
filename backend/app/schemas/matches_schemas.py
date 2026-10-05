from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JoinMatchRequest(InputSchema):
    match_id: int = Field(alias="idPartido", gt=0)


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


class JoinMatchResponse(BaseModel):
    message: str
    match_id: int = Field(serialization_alias="matchId")


class MatchStateResponse(BaseModel):
    status: str = Field(serialization_alias="status")
    local_score: int = Field(serialization_alias="localScore")
    visitor_score: int = Field(serialization_alias="visitorScore")
    duration_ms: int = Field(serialization_alias="durationMs")
    model_config = ConfigDict(populate_by_name=True)
