from typing import List

from sqlalchemy.orm import Session

from app.models.behaviour_model import Behavior
from app.models.player_model import Player

DEFAULT_PLAYERS = (
    {"name": "M. Marchisone", "power": 60, "agility": 60, "control": 60, "speed": 60, "strength": 60},
    {"name": "C. Gavilán", "power": 60, "agility": 60, "control": 60, "speed": 60, "strength": 60},
    {"name": "L. Heredia", "power": 60, "agility": 60, "control": 60, "speed": 60, "strength": 60},
    {"name": "V. Issidoro", "power": 60, "agility": 60, "control": 60, "speed": 60, "strength": 60},
    {"name": "S. Medina", "power": 60, "agility": 60, "control": 60, "speed": 60, "strength": 60},
    {"name": "G. Cisterna", "power": 60, "agility": 60, "control": 60, "speed": 60, "strength": 60},
)
def create_default_players(db: Session, club_id: int, behaviors: List[Behavior]) -> List[Player]:
    if len(behaviors) * 2 != len(DEFAULT_PLAYERS):
        raise ValueError("Debe haber un comportamiento por cada dos jugadores iniciales.")

    players = [
        Player(club_id=club_id, behavior_id=behaviors[index // 2].id, **player_data)
        for index, player_data in enumerate(DEFAULT_PLAYERS)
    ]
    db.add_all(players)
    db.flush()

    return players


def create_player(db: Session, player: Player) -> Player:
    db.add(player)
    db.flush()

    return player
