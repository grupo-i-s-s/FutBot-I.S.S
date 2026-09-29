from typing import Self

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from app.schemas.auth_schemas import Name


class ClubResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    # Conserva el campo actual de auth hasta acordar el catálogo de avatares.
    avatar: str
    friendly_available: bool = Field(serialization_alias="friendlyAvailable")


class ClubUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    friendly_available: StrictBool | None = Field(default=None, alias="friendlyAvailable")

    @field_validator("name", "friendly_available", mode="before")
    @classmethod
    def reject_explicit_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("El campo no puede ser null.")
        return value

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Enviá name o friendlyAvailable para modificar el club.")
        return self
