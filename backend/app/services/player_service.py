from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.player import Player
from app.repositories import player_repository
from app.schemas.player import PlayerCreate


def create_player(db: Session, club_id: int, data: PlayerCreate) -> Player:
    total = data.power + data.agility + data.control + data.speed + data.strength
    if total != 300:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La suma de los atributos PACSS debe ser exactamente 300 (actual: {total}).",
        )

    player = Player(
        club_id=club_id,
        name=data.name,
        power=data.power,
        agility=data.agility,
        control=data.control,
        speed=data.speed,
        strength=data.strength,
    )

    try:
        created = player_repository.create(db, player)
        db.commit()
        db.refresh(created)
        return created
    except Exception:
        db.rollback()
        raise
