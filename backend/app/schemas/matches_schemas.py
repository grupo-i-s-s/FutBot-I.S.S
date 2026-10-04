from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


class InputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JoinMatchRequest(InputSchema):
    match_id: int = Field(alias="idPartido")
    club_id: int = Field(alias="idEquipo")


class CreateFriendlyMatchRequest(InputSchema):
    start_datetime: datetime = Field(..., alias="startDateTime")
    model_config = ConfigDict(populate_by_name=True)


class CreateFriendlyMatchResponse(BaseModel):
    message: str
