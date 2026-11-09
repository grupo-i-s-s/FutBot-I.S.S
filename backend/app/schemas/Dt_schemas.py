from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, StrictBool, StringConstraints

class DtBehaviourRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str


class DtBehaviourList(BaseModel):
    items: list[DtBehaviourRead]


class DtBehaviourCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
    code: str = Field(min_length=1)


class DtRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool = Field(serialization_alias="isActive")
    behaviour_id: int | None = Field(serialization_alias="activeBehaviourId")


class DtUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    is_active: StrictBool = Field(alias="isActive")
    active_behaviour_id: PositiveInt | None = Field(alias="activeBehaviourId", default=None)
