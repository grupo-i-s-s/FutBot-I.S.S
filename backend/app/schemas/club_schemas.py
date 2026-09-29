from pydantic import BaseModel, ConfigDict, Field, StrictBool


class ClubResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    # Conserva el campo actual de auth hasta acordar el catálogo de avatares.
    avatar: str
    friendly_available: bool = Field(serialization_alias="friendlyAvailable")


class ClubAvailabilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    friendly_available: StrictBool = Field(alias="friendlyAvailable")
