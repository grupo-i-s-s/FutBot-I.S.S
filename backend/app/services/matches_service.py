from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.matches_model import Matches
from app.schemas.matches_schemas import CreateFriendlyMatchRequest, JoinMatchRequest


def join_match(db, data):

    partido = db.query(Matches).filter(Matches.match_id == data.match_id).first()

    partido.visitor_id = data.club_id
    db.commit()

    return {"mensaje": "¡Te uniste al partido con éxito!"}


def create_friendly_match(
    db: Session, club_id: int, data: CreateFriendlyMatchRequest
) -> dict:
    now_utc = datetime.now(timezone.utc)
    start_dt = data.start_datetime

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)

    if start_dt <= now_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de inicio debe ser futura.",
        )

    match = Matches(creator_id=club_id, init_date=start_dt)
    db.add(match)
    db.commit()
    db.refresh(match)
    return {"message": "Amistoso creado exitosamente"}
