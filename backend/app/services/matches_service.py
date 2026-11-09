from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.errors import AppError
from app.models.matches_model import Matches
from app.repository import matches_repository
from app.schemas.matches_schemas import CreateFriendlyMatchRequest, MatchStateResponse
from app.models.auth_model import Club
from app.services.match_builder_service import build_match
from app.services.match_start_service import cancel_match

def _require_available_clubs(
        db: Session, club_ids: tuple[int, ...], current_club_id: int
) -> None:
    # Releer bajo bloqueo evita aceptar un rival con la disponibilidad que tenía
    # al cargar el listado o al autenticar la petición.
    clubs = {
        club.id: club
        for club in matches_repository.get_clubs_for_update(db, club_ids)
    }
    current = clubs.get(current_club_id)
    if current is None or not current.friendly_available:
        raise AppError(
            "CLUB_NOT_AVAILABLE",
            "Tu club no está disponible para amistosos. "
            "Activá la disponibilidad desde Mi club.",
        )
    if any(club_id not in clubs or not clubs[club_id].friendly_available for club_id in club_ids):
        raise AppError(
            "CLUB_NOT_AVAILABLE",
            "El club rival ya no está disponible para amistosos.",
        )


def list_available(db: Session, club_id: int) -> list[dict]:
    return [
        {
            "match_id": match.match_id,
            "creator_club_name": club_name,
            "start_datetime": match.init_date,
        }
        for match, club_name in matches_repository.list_available(
            db, club_id, datetime.now(timezone.utc)
        )
    ]


def list_for_club(db: Session, club_id: int) -> list[dict]:
    return [
        {
            "match_id": match.match_id,
            "creator_club_name": creator_name,
            "visitor_club_name": visitor_name,
            "start_datetime": match.init_date,
            "status": match.status,
            "is_creator": match.creator_id == club_id,
        }
        for match, creator_name, visitor_name in matches_repository.list_for_club(
            db, club_id
        )
    ]


def join_match(db: Session, match_id: int, club_id: int) -> dict:
    match = matches_repository.get_by_id_for_update(db, match_id)
    if match is None:
        raise AppError("MATCH_NOT_FOUND", "El partido no existe.")
    if match.creator_id == club_id:
        raise AppError("MATCH_SELF_JOIN", "No podés unirte a tu propio partido.")
    if match.visitor_id is not None:
        raise AppError("MATCH_FULL", "El partido ya tiene visitante.")
    if match.status not in (
            "WAITING",
            "WAITING_OPPONENT",
    ) or match.init_date <= datetime.now(timezone.utc):
        raise AppError("MATCH_STARTED", "Ya pasó la fecha de inicio del partido.")

    _require_available_clubs(db, (match.creator_id, club_id), club_id)
    if match.init_date <= datetime.now(timezone.utc):
        raise AppError("MATCH_STARTED", "Ya pasó la fecha de inicio del partido.")

    match.visitor_id = club_id
    match.status = "SCHEDULED"
    # El snapshot de espera cambia al incorporarse el rival. Los espectadores
    # descartan secuencias repetidas, por lo que esta transición también cuenta.
    match.sequence += 1
    db.commit()
    return {"message": "Te uniste al partido.", "match_id": match.match_id}


def create_friendly_match(
        db: Session, club_id: int, data: CreateFriendlyMatchRequest
) -> dict:
    now_utc = datetime.now(timezone.utc)
    start_dt = data.start_datetime

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)

    if start_dt <= now_utc:
        raise AppError("MATCH_INVALID_DATE", "La fecha de inicio debe ser futura.")

    _require_available_clubs(db, (club_id,), club_id)
    if start_dt <= datetime.now(timezone.utc):
        raise AppError("MATCH_INVALID_DATE", "La fecha de inicio debe ser futura.")

    match = Matches(creator_id=club_id, init_date=start_dt, status="WAITING_OPPONENT")
    db.add(match)
    db.commit()
    db.refresh(match)
    return {"message": "Amistoso creado exitosamente", "match_id": match.match_id}


def get_match_state(db, match_id: int, club_id: int) -> MatchStateResponse:
    match = matches_repository.get_by_id(db, match_id)

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="El partido no existe."
        )

    if match.creator_id != club_id and match.visitor_id != club_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permiso para consultar este partido.",
        )

    return MatchStateResponse(
        status=match.status,
        local_score=match.local_score,
        visitor_score=match.visitor_score,
        duration_ms=match.duration_ms,
    )

TEST_OPPONENT_CLUB_ID = 999 
def create_behaviour_test_match(db: Session, club_id: int) -> dict:
    if club_id == TEST_OPPONENT_CLUB_ID:
        raise AppError(
            "MATCH_SELF_JOIN",
            "El club rival de prueba no puede ser el club de tu sesión.",
        )

    if db.get(Club, TEST_OPPONENT_CLUB_ID) is None:
        raise AppError(
            "MATCH_NOT_FOUND",
            "No está configurado el club rival de prueba.",
        )
    
    now = datetime.now(timezone.utc)
    previous_match = matches_repository.get_active_test_match(db, club_id, TEST_OPPONENT_CLUB_ID)

    if previous_match is not None:
        cancel_match(db, previous_match, "REPLACED_BY_NEW_TEST_MATCH", now)

    match = Matches(
        creator_id= club_id,
        visitor_id= TEST_OPPONENT_CLUB_ID,
        init_date= now + timedelta(seconds=1),
        status = "SCHEDULED",
    )
    db.add(match)
    db.flush()

    build_match(db, match.match_id)

    db.commit()
    return {
        "message": "Partido de prueba creado.",
        "match_id": match.match_id,
    }

def set_match_dt(db: Session, match_id: int, club_id: int, dt_active: bool) -> dict:
    match = matches_repository.get_by_id_for_update(db, match_id)
    if match is None:
        raise AppError("MATCH_NOT_FOUND", "El partido no existe.")
    
    if club_id not in (match.creator_id, match.visitor_id):
        raise AppError("MATCH_FORBIDDEN", "El club no participa de este partido.")
    
    if match.runtime_state:
        is_local = (club_id == match.creator_id)
        team_key = "local_team" if is_local else "visitor_team"
        if team_key in match.runtime_state:
            match.runtime_state[team_key]["dt_active"] = dt_active
            flag_modified(match, "runtime_state")

    db.commit()
    return {"message": "Estado del DT actualizado con éxito", "dt_active": dt_active}
