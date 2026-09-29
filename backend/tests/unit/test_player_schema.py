import pytest
from pydantic import ValidationError

from app.schemas.player import PlayerCreate


def test_player_attributes_must_be_at_least_20():
    with pytest.raises(ValidationError):
        PlayerCreate(
            name="Jugador",
            power=19,
            agility=70,
            control=70,
            speed=70,
            strength=70,
        )


def test_player_attributes_must_be_at_most_100():
    with pytest.raises(ValidationError):
        PlayerCreate(
            name="Jugador",
            power=101,
            agility=50,
            control=50,
            speed=50,
            strength=50,
        )


def test_player_attributes_must_be_integers():
    with pytest.raises(ValidationError):
        PlayerCreate(
            name="Jugador",
            power=60.5,
            agility=60,
            control=60,
            speed=60,
            strength=60,
        )


def test_player_boolean_is_not_accepted_as_integer():
    with pytest.raises(ValidationError):
        PlayerCreate(
            name="Jugador",
            power=True,
            agility=60,
            control=60,
            speed=60,
            strength=60,
        )
