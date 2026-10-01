from sqlalchemy.orm import Session
from app.models.player import Player


def create(db: Session, player: Player) -> Player:
    db.add(player)
    db.flush()
    return player

def get_by_id(db: Session, player_id: int) -> Player | None:
    return db.query(Player).filter(Player.id == player_id).first()
