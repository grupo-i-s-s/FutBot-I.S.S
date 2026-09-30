from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from datetime import datetime, timezone
from app.models.league_model import League
from app.repository import league_repository


def get_league_lobby(db: Session, league_id: int) -> League:
    league = league_repository.get_league_by_id(db, league_id)
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La liga no existe."
        )
    return league


def leave_league(db: Session, league_id: int, club_id: int) -> dict:
    league = league_repository.get_league_by_id(db, league_id)
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La liga no existe.",
        )

    # Preguntar dsp cual de los dos usar
    now_utc = datetime.now(timezone.utc)
    if league.status != "open" or (
        league.start_datetime and league.start_datetime <= now_utc
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No es posible abandonar una liga que ya ha iniciado.",
        )

    registration = league_repository.get_registration(db, league_id, club_id)
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El club no se encuentra inscripto en esta liga.",
        )

    league_repository.delete_registration(db, registration)
    db.commit()
    return {
        "message": "Has salido de la liga exitosamente.",
        "leagueId": league_id,
    }
