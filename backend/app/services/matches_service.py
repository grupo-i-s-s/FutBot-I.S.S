from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.matches_model import Matches
from app.repository import matches_repository
from app.schemas.matches_schemas import CreateFriendlyMatchRequest


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


def join_match(db: Session, match_id: int, club_id: int) -> dict:
    match = matches_repository.get_by_id_for_update(db, match_id)
    if match is None:
        raise AppError("MATCH_NOT_FOUND", "El partido no existe.")
    if match.creator_id == club_id:
        raise AppError("MATCH_SELF_JOIN", "No podés unirte a tu propio partido.")
    if match.visitor_id is not None:
        raise AppError("MATCH_FULL", "El partido ya tiene visitante.")
    if match.status not in ("WAITING", "WAITING_OPPONENT") or match.init_date <= datetime.now(timezone.utc):
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

    match = Matches(creator_id=club_id, init_date=start_dt, status="WAITING_OPPONENT")
    db.add(match)
    db.commit()
    db.refresh(match)
    return {"message": "Amistoso creado exitosamente", "match_id": match.match_id}
