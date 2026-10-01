from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)

PACSS_TOTAL = 300


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

    @model_validator(mode="after")
    def validate_pacss_total(self) -> "PlayerCreate":
        total = self.power + self.agility + self.control + self.speed + self.strength
        if total != PACSS_TOTAL:
            raise ValueError(
                f"La suma de los atributos PACSS debe ser exactamente {PACSS_TOTAL} (actual: {total})."
            )
        return self


class PlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    club_id: int = Field(serialization_alias="clubId")
    behavior_id: int = Field(serialization_alias="behaviorId")
    name: str
    power: int
    agility: int
    control: int
    speed: int
    strength: int


class PlayerBehaviourUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    behaviour_id: StrictInt = Field(alias="behaviourId", gt=0)
