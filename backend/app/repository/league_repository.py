from typing import Optional
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from app.models.league_model import League, LeagueRegistration


def get_league_by_id(db: Session, league_id: int) -> Optional[League]:
    return (
        db.query(League)
        .options(joinedload(League.registrations))
        .filter(League.id == league_id)
        .first()
    )

def create_league(db: Session, name: str, min_teams: int, max_teams:int, start_date:datetime, round_interval:str)->League:
    league = League(name=name, min_teams=min_teams, max_teams=max_teams, start_datetime=start_date, round_interval=round_interval)
    db.add(league)
    db.flush()
    return league