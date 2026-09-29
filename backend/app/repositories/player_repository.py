from sqlalchemy.orm import Session
from app.models.player import Player


def create(db: Session, player: Player) -> Player:
    db.add(player)
    db.flush()
    return player
