from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator


class PlayerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(..., min_length=1, max_length=50)
    power: StrictInt = Field(..., ge=20, le=100)
    agility: StrictInt = Field(..., ge=20, le=100)
    control: StrictInt = Field(..., ge=20, le=100)
    speed: StrictInt = Field(..., ge=20, le=100)
    strength: StrictInt = Field(..., ge=20, le=100)

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("El nombre no puede estar vacío.")
        return clean


class PlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    club_id: int = Field(alias="clubId")
    name: str
    power: int
    agility: int
    control: int
    speed: int
    strength: int
