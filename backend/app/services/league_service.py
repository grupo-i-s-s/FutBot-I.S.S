from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime

from datetime import datetime, timezone
from app.models.league_model import League
from app.repository import league_repository
from app.schemas.league_schemas import CreateLeagueRequest


def get_league_lobby(db: Session, league_id: int) -> League:
    league = league_repository.get_league_by_id(db, league_id)
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La liga no existe."
        )
    return league

def create_league(db: Session, data:CreateLeagueRequest) -> dict[str, str]:
    league = league_repository.create_league(
        db,
        name = data.name,
        min_teams = data.min_teams,
        max_teams = data.max_teams,
        start_date = data.start_date,
        round_interval = data.round_interval
    )
    db.commit()
    return {"message": "Liga creada correctamente."}

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


def join_league(
    db: Session,
    league_id: int,
    club_id: int,
    line_up: list | dict,
    access_code: str | None = None,
) -> dict:
    league = league_repository.get_league_for_join(db, league_id)

    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La liga no existe.",
        )

    if league.access_code is not None:
        if access_code != league.access_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El código de acceso es incorrecto.",
            )

    now_utc = datetime.now(timezone.utc)

    if league.status != "open" or (
        league.start_datetime and league.start_datetime <= now_utc
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No es posible unirse a una liga que ya ha comenzado o no está abierta.",
        )

    registration_count = league_repository.count_registrations(
        db, league_id
    )

    if registration_count >= league.max_teams:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La liga ha alcanzado el límite máximo de equipos.",
        )

    existing_registration = league_repository.get_registration(
        db, league_id, club_id
    )

    if existing_registration:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El club ya se encuentra inscripto en esta liga.",
        )

    league_repository.create_registration(
        db,
        league_id,
        club_id,
        line_up,
    )

    db.commit()

    return {
        "message": "Te has unido a la liga exitosamente.",
        "leagueId": league_id,
        "clubId": club_id,
    }
