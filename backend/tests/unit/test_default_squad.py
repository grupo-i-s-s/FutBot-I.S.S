"""Datos y construcción de nuestro plantel inicial; sesión simulada, sin SQL."""
from unittest.mock import Mock

import pytest

from app.models.behaviour_model import Behavior
from app.models.player_model import Player
from app.repository import behaviour_repository, player_repository

PACSS = ("power", "agility", "control", "speed", "strength")


def test_there_are_exactly_six_default_players_with_unique_names():
    names = [player["name"] for player in player_repository.DEFAULT_PLAYERS]

    assert len(names) == 6
    assert len(set(names)) == 6
    assert all(0 < len(name) <= 50 for name in names)


@pytest.mark.parametrize(
    "player",
    player_repository.DEFAULT_PLAYERS,
    ids=lambda player: player["name"],
)
def test_default_player_has_valid_pacss(player):
    # Nuestro plantel inicial respeta el presupuesto PACSS, sin consultar tablas.
    assert set(PACSS) <= player.keys()
    assert all(20 <= player[attr] <= 100 for attr in PACSS)
    assert sum(player[attr] for attr in PACSS) == 300


def test_create_default_behaviours_belong_to_club_and_are_flushed():
    db = Mock()

    behaviors = behaviour_repository.create_default_behaviours(db, club_id=7)

    assert len(behaviors) == 3
    assert all(isinstance(behavior, Behavior) for behavior in behaviors)
    assert all(behavior.club_id == 7 for behavior in behaviors)
    assert len({behavior.name for behavior in behaviors}) == 3
    assert all(behavior.description and behavior.code for behavior in behaviors)
    db.add_all.assert_called_once_with(behaviors)
    db.flush.assert_called_once_with()


def test_create_default_players_assigns_club_and_behaviour():
    db = Mock()
    behaviors = [Behavior(id=i, club_id=7, name=str(i), description="d", code="c") for i in (3, 4, 5)]

    players = player_repository.create_default_players(db, club_id=7, behaviors=behaviors)

    assert len(players) == len(player_repository.DEFAULT_PLAYERS)
    assert all(isinstance(player, Player) for player in players)
    assert all(player.club_id == 7 for player in players)
    assert [player.behavior_id for player in players] == [3, 3, 4, 4, 5, 5]
    assert [p.name for p in players] == [p["name"] for p in player_repository.DEFAULT_PLAYERS]
    db.add_all.assert_called_once_with(players)
    db.flush.assert_called_once_with()
