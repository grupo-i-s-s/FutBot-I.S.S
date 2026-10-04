from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timezone
from app.models.league_model import League
from app.repository import league_repository
from app.schemas.league_schemas import CreateLeagueRequest, LeagueRead


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


def list_leagues(db: Session, club_id: int, name: str | None = None) -> list[LeagueRead]:
    normalized_name = name.strip() if name is not None else None
    leagues = league_repository.get_all_available_leagues(db, name=normalized_name)

    items = []
    for league in leagues:
        registered_count = len(league.registrations)
        is_member = any(
            registration.club_id == club_id
            for registration in league.registrations
        )
        items.append(
            LeagueRead(
                id=league.id,
                name=league.name,
                start_datetime=league.start_datetime,
                round_interval=league.round_interval,
                status=league.status,
                min_teams=league.min_teams,
                max_teams=league.max_teams,
                registered_count=registered_count,
                available_slots=league.max_teams - registered_count,
                is_member=is_member,
            )
        )

    return items
