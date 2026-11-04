from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.player_model import Player
from app.repository import behaviour_repository, player_repository
from app.schemas.player import PlayerCreate

#Para evitar la carrera entre asignar y eliminar, las asignaciones deben tomar el mismo bloqueo antes de consultar el comportamiento.

def create_player(db: Session, club_id: int, data: PlayerCreate) -> Player:
    try:
        behaviour_repository.lock_club(db, club_id)

        behaviour = behaviour_repository.get_default_behaviour(db, club_id)
        if behaviour is None:
            raise AppError(
                "ACCOUNT_INCOMPLETE",
                "El club no tiene un comportamiento para asignar al jugador.",
            )

        player = Player(
            club_id=club_id,
            behavior_id=behaviour.id,
            **data.model_dump(),
        )

        created = player_repository.create_player(db, player)
        db.commit()
        return created
    
    except Exception:
        db.rollback()
        raise


def assign_behaviour(db: Session, club_id: int, player_id: int, behaviour_id: int,) -> Player:
    try:
        behaviour_repository.lock_club(db, club_id)

        player = player_repository.get_player_by_id(db, club_id, player_id)
        if player is None:
            raise AppError(
                "PLAYER_NOT_FOUND",
                "El jugador no existe en tu club.",
            )

        behaviour = behaviour_repository.get_behaviour_by_id(
            db, club_id, behaviour_id
        )
        if behaviour is None:
            raise AppError(
                "BEHAVIOUR_NOT_FOUND",
                "El comportamiento no existe en tu club.",
            )

        if behaviour.kind != "PLAYER":
            raise AppError(
                "BEHAVIOUR_INVALID",
                "El comportamiento debe ser de tipo PLAYER.",
            )

        if behaviour.validation_status != "VALID":
            raise AppError(
                "BEHAVIOUR_INVALID",
                "El comportamiento aún no está validado.",
            )

        player_repository.set_player_behaviour(db, player, behaviour.id)
        db.commit()
        db.refresh(player)
        return player

    except Exception:
        db.rollback()
        raise

def get_players(
    db: Session,
    club_id: int,
    page: int,
    limit: int,
    search: str | None = None,
) -> tuple[list[Player], int]:
    query = db.query(Player).filter(
        Player.club_id == club_id,
        Player.is_deleted.is_(False),
    )

    if search and search.strip():
        query = query.filter(
            Player.name.ilike(f"%{search.strip()}%")
        )

    total_count = query.count()
    players = (
        query.order_by(Player.id)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return players, total_count


def get_players_by_ids(
    db: Session,
    club_id: int,
    player_ids: list[int],
) -> list[Player]:
    return (
        db.query(Player)
        .filter(
            Player.club_id == club_id,
            Player.is_deleted.is_(False),
            Player.id.in_(player_ids),
        )
        .order_by(Player.id)
        .all()
    )