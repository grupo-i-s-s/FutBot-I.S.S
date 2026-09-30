from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.league_model import League
from app.repository import league_repository


def get_league_lobby(db: Session, league_id: int) -> League:
    league = league_repository.get_league_by_id(db, league_id)
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La liga no existe."
        )
    return league
