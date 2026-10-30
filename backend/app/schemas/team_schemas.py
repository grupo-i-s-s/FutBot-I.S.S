from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    model_validator,
)


class LineupPlayer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: StrictInt = Field(alias="playerId", gt=0)
    behaviour_id: StrictInt = Field(alias="behaviourId", gt=0)


class Lineup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formation_id: StrictInt = Field(alias="formationId", gt=0)
    starters: list[LineupPlayer] = Field(min_length=3, max_length=3)
    substitutes: list[LineupPlayer] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_unique_players(self) -> "Lineup":
        players = self.starters + self.substitutes
        player_ids = [player.player_id for player in players]

        if len(set(player_ids)) != len(player_ids):
            raise ValueError(
                "Los titulares y suplentes deben ser seis jugadores distintos."
            )

        return self


class DefaultTeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club_id: int = Field(serialization_alias="clubId")
    line_up: Lineup = Field(serialization_alias="lineUp")


class FormationRead(BaseModel):
    id: int
    name: str


class FormationListResponse(BaseModel):
    items: list[FormationRead]
