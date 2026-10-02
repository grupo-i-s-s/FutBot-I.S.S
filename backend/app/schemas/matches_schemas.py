from typing import Annotated

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
