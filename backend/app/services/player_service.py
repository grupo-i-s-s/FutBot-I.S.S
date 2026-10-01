from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.player_model import Player
from app.repository import behaviour_repository, player_repository
from app.schemas.player import PlayerCreate


def create_player(db: Session, club_id: int, data: PlayerCreate) -> Player:
    behaviour = behaviour_repository.get_default_behaviour(db, club_id)

    if behaviour is None:
        raise AppError(
            "ACCOUNT_INCOMPLETE",
            "El club no tiene un comportamiento para asignar al jugador.")

    player = Player(
        club_id=club_id,
        behavior_id=behaviour.id,
        **data.model_dump(),
    )

    try:
        created = player_repository.create_player(db, player)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return created


def assign_behaviour(
    db: Session, club_id: int, player_id: int, behaviour_id: int
) -> Player:
    player = player_repository.get_player_by_id(db, club_id, player_id)
    if player is None:
        raise AppError("PLAYER_NOT_FOUND", "El jugador no existe en tu club.")

    behaviour = behaviour_repository.get_behaviour_by_id(db, club_id, behaviour_id)
    if behaviour is None:
        raise AppError("BEHAVIOUR_NOT_FOUND", "El comportamiento no existe en tu club.")

    try:
        player_repository.set_player_behaviour(db, player, behaviour.id)
        db.commit()
        db.refresh(player)
    except Exception:
        db.rollback()
        raise

    return player
