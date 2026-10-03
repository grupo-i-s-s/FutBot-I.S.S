from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime

from datetime import datetime, timezone
from app.models.league_model import League
from app.repository import league_repository
from app.schemas.league_schemas import CreateLeagueRequest, CreatePrivateLeagueRequest
from app.errors import AppError
from app.security import hash_password
from sqlalchemy.exc import IntegrityError


def get_league_lobby(
    db: Session,
    league_id: int,
    club_id: int,
) -> dict[str, object]:
    league = league_repository.get_league_by_id(db, league_id)

    if league is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La liga no existe.",
        )

    club_ids = {registration.club_id for registration in league.registrations}

    if league.creator_club_id is not None:
        club_ids.add(league.creator_club_id)

    clubs = league_repository.get_clubs_by_ids(db, list(club_ids))
    clubs_by_id = {club.id: club for club in clubs}

    registered_teams = len(league.registrations)

    return {
        "id": league.id,
        "name": league.name,
        "is_private": league.is_private,
        "creator_club_id": league.creator_club_id,
        "min_teams": league.min_teams,
        "max_teams": league.max_teams,
        "start_datetime": league.start_datetime,
        "round_interval": league.round_interval,
        "status": league.status,
        "registrations": league.registrations,
        "creator_club": clubs_by_id.get(league.creator_club_id),
        "clubs": [
            clubs_by_id[registration.club_id]
            for registration in league.registrations
            if registration.club_id in clubs_by_id
        ],
        "registered_teams": registered_teams,
        "remaining_slots": max(0, league.max_teams - registered_teams),
        "is_registered": any(
            registration.club_id == club_id for registration in league.registrations
        ),
    }


def _create_league(
    db: Session,
    data: CreateLeagueRequest,
    *,
    is_private: bool,
    password_hash: str | None,
    creator_club_id: int,
) -> dict[str, str]:
    name = data.name.strip()

    if not name or len(name) > 50:
        raise AppError(
            "VALIDATION_ERROR", "El nombre debe tener entre 1 y 50 caracteres."
        )

    if data.min_teams < 3:
        raise AppError("VALIDATION_ERROR", "El mínimo de clubes debe ser al menos 3.")

    if data.max_teams < data.min_teams:
        raise AppError(
            "VALIDATION_ERROR",
            f"El máximo de clubes debe ser al menos {data.min_teams}.",
        )

    if data.round_interval not in {"CONTINUOUS", "DAILY", "WEEKLY"}:
        raise AppError("VALIDATION_ERROR", "La frecuencia de rondas no es válida.")

    try:
        league_repository.create_league(
            db=db,
            name=name,
            min_teams=data.min_teams,
            max_teams=data.max_teams,
            start_date=data.start_date,
            round_interval=data.round_interval,
            is_private=is_private,
            password_hash=password_hash,
            creator_club_id=creator_club_id,
        )
        db.commit()

    except IntegrityError as exc:
        db.rollback()

        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)

        if constraint == "leagues_name_key":
            raise AppError(
                "LEAGUE_DUPLICATE", "Ya existe una liga con ese nombre."
            ) from exc
        raise
    return {"message": "Liga creada exitosasmente."}


def create_league(
    db: Session, data: CreateLeagueRequest, creator_club_id: int
) -> dict[str, str]:
    return _create_league(
        db=db,
        data=data,
        is_private=False,
        password_hash=None,
        creator_club_id=creator_club_id,
    )


def create_private_league(
    db: Session, data: CreatePrivateLeagueRequest, creator_club_id: int
) -> dict[str, str]:
    if not data.password.strip():
        raise AppError("VALIDATION_ERROR", "La liga privada necesita contraseña.")
    return _create_league(
        db=db,
        data=data,
        is_private=True,
        password_hash=hash_password(data.password),
        creator_club_id=creator_club_id,
    )

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
