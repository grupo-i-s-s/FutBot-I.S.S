from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime

from app.models.league_model import League
from app.repository import league_repository
from app.schemas.league import CreateLeagueRequest


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