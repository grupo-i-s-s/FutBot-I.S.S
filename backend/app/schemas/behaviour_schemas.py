from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator
)

from typing import Literal

# Esta implementado la iss-72 y 74 donde se pide la lista de comportamientos y el detalle de un comportamiento

class BehaviourRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    kind: str
    version: int
    validation_status: str = Field( serialization_alias="validationStatus")


class BehaviourListResponse(BaseModel):
    items: list[BehaviourRead]


class BehaviourReadDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    kind: str
    version: int
    validation_status: str = Field( serialization_alias="validationStatus")


class BehaviourCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=50)
    code: str
    kind: Literal["PLAYER"]

    @field_validator("name")
    @classmethod 
    def validate_name(cls, value:str) -> str:
        clean = value.strip()
        if not clean: raise ValueError("El nombre no puede estar vacio")
        return clean

    @field_validator("code")
    @classmethod
    def validate_code_size(cls, value: str)->str:
        if len(value.encode("utf-8")) > 65_536: raise ValueError("El codigo no puede superar los 64KiB")
        return value
