from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.player import Player
from app.repositories import player_repository, behaviour_repository
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


def assign_behaviour(
    db: Session,
    player_id: int,
    behaviour_id: int,
    current_user_club_id: int,
) -> Player:
    """
    Asigna un comportamiento a un jugador, validando existencia,
    pertenencia al club del usuario, y asegurando atomicidad.
    """
    # 1. Buscar jugador y validar existencia (404)
    player = player_repository.get_by_id(db, player_id)
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jugador no encontrado.",
        )
    
    # 2. Validar pertenencia del jugador al club (403)
    if player.club_id != current_user_club_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permisos para modificar un jugador de otro club.",
        )
    
    # 3. Buscar comportamiento y validar existencia (404)
    behaviour = behaviour_repository.get_by_id(db, behaviour_id)
    if not behaviour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El comportamiento no existe.",
        )
    
    # 4. Validar pertenencia del comportamiento al mismo club (403)
    if behaviour.club_id != current_user_club_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El comportamiento no pertenece al club.",
        )

    # 5. Asignar y persistir de forma atómica
    try:
        player.behaviour_id = behaviour_id  # Asegúrate que coincida con el modelo (behaviour_id o behavior_id)
        db.commit()
        db.refresh(player)
    except Exception:
        db.rollback()
        raise

    return player