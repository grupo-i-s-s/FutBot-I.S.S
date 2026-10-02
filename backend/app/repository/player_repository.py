from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.player_model import Player

DEFAULT_PLAYERS = (
    {"name": "M. Marchisone", "power": 60, "agility": 60, "control": 60, "speed": 60, "strength": 60},
    {"name": "C. Gavilán", "power": 60, "agility": 60, "control": 60, "speed": 60, "strength": 60},
    {"name": "L. Heredia", "power": 60, "agility": 60, "control": 60, "speed": 60, "strength": 60},
    {"name": "V. Issidoro", "power": 60, "agility": 60, "control": 60, "speed": 60, "strength": 60},
    {"name": "S. Medina", "power": 60, "agility": 60, "control": 60, "speed": 60, "strength": 60},
    {"name": "G. Cisterna", "power": 60, "agility": 60, "control": 60, "speed": 60, "strength": 60},
)
def create_default_players(db: Session, club_id: int, behaviour_id) -> List[Player]:
    players = [
        Player(club_id=club_id, behavior_id=behaviour_id, **player_data)
        for player_data in DEFAULT_PLAYERS
    ]
    db.add_all(players)
    db.flush()

    return players


def create_player(db: Session, player: Player) -> Player:
    db.add(player)
    db.flush()

    return player



def get_by_id(db: Session, id: int) -> Player:
    player = db.get(Player, id)

    return player

