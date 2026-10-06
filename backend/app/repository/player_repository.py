from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import List

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


def get_player_by_id(db: Session, club_id: int, player_id: int) -> Player | None:
    return db.scalar(
        select(Player).where(
            Player.id == player_id,
            Player.club_id == club_id,
            Player.is_deleted.is_(False),
        )
    )


def set_player_behaviour(db: Session, player: Player, behaviour_id: int) -> None:
    player.behavior_id = behaviour_id
    db.flush()


def get_players_by_club(db: Session, club_id: int) -> List[Player]:
    return list(
        db.scalars(
            select(Player).where(
                Player.club_id == club_id,
                Player.is_deleted.is_(False),
            )
        ).all()
    )


def get_by_id(db: Session, id: int) -> Player:
    player = db.get(Player, id)

    return player
