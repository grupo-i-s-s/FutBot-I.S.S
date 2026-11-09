from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.services.league_access_service import check_access_limit
from app.repository import league_repository, player_repository
from app.schemas.league_schemas import (
    CreateLeagueRequest,
    CreatePrivateLeagueRequest,
    LeagueRead,
)
from app.security import hash_password, verify_password
from app.services.league_lineup_service import prepare_registration_lineup
from app.services.league_round_service import generate_league_rounds
from app.services.league_fixture_service import ROUND_INTERVALS


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
        "standings": league_repository.get_standings(db, league_id)
        if league.status in {"running", "finished"} else [],
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

    start_dt = data.start_date
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)

    if start_dt <= datetime.now(timezone.utc):
        raise AppError("VALIDATION_ERROR", "La fecha de inicio debe ser futura.")

    try:
        league = league_repository.create_league(
            db=db,
            name=name,
            min_teams=data.min_teams,
            max_teams=data.max_teams,
            start_date=start_dt,
            round_interval=data.round_interval.value,
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
    return {"message": "Liga creada exitosamente.", "league_id": league.id, }


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


def start_league(db: Session, league_id: int, club_id: int) -> dict:
    try:
        # Join y leave toman el mismo bloqueo hasta confirmar su transacción.
        league = league_repository.get_league_by_id(db, league_id)
        if league is None:
            raise HTTPException(404, "La liga no existe.")
        if league.creator_club_id != club_id:
            raise HTTPException(403, "Sólo el creador puede iniciar la liga.")

        result = {"league_id": league.id, "status": "running"}
        if league.status == "running":
            db.commit()
            return result
        if league.status != "open":
            raise HTTPException(409, "La liga no está abierta.")
        if len(league.registrations) < league.min_teams:
            raise HTTPException(409, "No hay suficientes clubes para iniciar la liga.")

        for registration in league.registrations:
            prepare_registration_lineup(db, registration, league.creator_club_id)
        rounds = generate_league_rounds(db, league)
        start = league.start_datetime
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        first_start = max(start, datetime.now(timezone.utc))
        interval = ROUND_INTERVALS[league.round_interval]

        for draw in rounds:
            round_ = league_repository.create_round(
                db, league.id, draw.number,
                first_start + (draw.number - 1) * interval, draw.bye_club_id,
                schedule_confirmed=draw.number == 1,
            )
            league_repository.create_round_matches(db, round_, draw.pairings)

        league_repository.create_standings(
            db, league.id, [row.club_id for row in league.registrations],
        )
        league.status = "running"
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def leave_league(db: Session, league_id: int, club_id: int) -> dict:
    league = league_repository.get_league_by_id(db, league_id)
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La liga no existe.",
        )

    if league.creator_club_id == club_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No es posible que un jugador creador abandone su propia liga",
        )

    if league.status != "open":
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
        "league_id": league_id,
    }


def join_league(
        db: Session,
        league_id: int,
        club_id: int,
        line_up: list[int],
        access_code: str | None = None,
) -> dict:
    league = league_repository.get_league_for_join(db, league_id)

    if league is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La liga no existe.",
        )

    if league.is_private or league.password_hash is not None or league.access_code is not None:
        check_access_limit(club_id, league_id)
        if not (
            access_code and league.password_hash
            and verify_password(access_code, league.password_hash)
        ):
            raise AppError(
                "LEAGUE_ACCESS_INVALID",
                "La contraseña de la liga es incorrecta.",
            )

    if league.status != "open":
        raise AppError(
            "LEAGUE_CLOSED",
            "No es posible unirse a una liga que ya ha comenzado o no está abierta.",
        )

    registration_count = league_repository.count_registrations(db, league_id)

    if registration_count >= league.max_teams:
        raise AppError(
            "LEAGUE_FULL",
            "La liga ha alcanzado el límite máximo de equipos.",
        )

    existing_registration = league_repository.get_registration(db, league_id, club_id)

    if existing_registration:
        raise AppError(
            "ALREADY_REGISTERED",
            "El club ya se encuentra inscripto en esta liga.",
        )

    if (
            not isinstance(line_up, list)
            or len(line_up) != 6
            or any(
        type(player_id) is not int or player_id <= 0
        for player_id in line_up
    )
            or len(set(line_up)) != 6
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Elegí 6 jugadores diferentes y válidos.",
        )

    active_ids = {
        player.id
        for player in player_repository.get_players_by_club(db, club_id)
    }

    if not set(line_up).issubset(active_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Los jugadores deben pertenecer a tu club y estar activos.",
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


def list_leagues(
        db: Session, club_id: int, name: str | None = None
) -> list[LeagueRead]:
    normalized_name = name.strip() if name is not None else None
    leagues = league_repository.get_all_available_leagues(db, name=normalized_name)

    items = []
    for league in leagues:
        registered_count = len(league.registrations)
        is_member = any(
            registration.club_id == club_id for registration in league.registrations
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
                available_slots=max(0, league.max_teams - registered_count),
                is_member=is_member,
                is_private=league.is_private,
            )
        )

    return items


def league_rank(league_id: int, db:Session):
    league = league_repository.get_league_by_id(db, league_id)
    if league is None:
        raise HTTPException(404, "La liga no existe.")

    clubs_id = {registration.club_id for registration in league.registrations}

    clubs = league_repository.get_clubs_by_ids(db,list(clubs_id))

    ranking = {}

    for club in clubs:
        ranking[club.id] = {
            "id": club.id,
            "nombre": club.name,
            "puntos": 0,
            "pj": 0,
            "pg":0,
            "pe":0,
            "pp":0,
            "gf":0,
            "gc":0,
            "dg":0
        }

    partidos = league_repository.get_completed_matches(league_id, db)

    for partido in partidos:
        local_id = partido.creator_id
        visitante_id = partido.visitor_id
        goles_local = partido.local_score
        goles_visitante = partido.visitor_score

        ranking[local_id]["pj"] += 1
        ranking[visitante_id]["pj"] += 1

        ranking[local_id]["gf"] += goles_local
        ranking[local_id]["gc"] += goles_visitante

        ranking[visitante_id]["gf"] += goles_visitante
        ranking[visitante_id]["gc"] += goles_local

        if goles_local > goles_visitante:
            ranking[local_id]["pg"] += 1
            ranking[local_id]["puntos"] += 3
            ranking[visitante_id]["pp"] += 1

        elif goles_local < goles_visitante:
            ranking[visitante_id]["pg"] += 1
            ranking[visitante_id]["puntos"] += 3

            ranking[local_id]["pp"] += 1

        else:
            ranking[local_id]["pe"] += 1
            ranking[local_id]["puntos"] += 1
            ranking[visitante_id]["pe"] += 1
            ranking[visitante_id]["puntos"] += 1

    rank = []
    for stats in ranking.values():
        stats["dg"] = stats["gf"] - stats["gc"]
        rank.append(stats)

    rank.sort(key=lambda x : (x["puntos"], x["dg"]), reverse=True)
    return rank
