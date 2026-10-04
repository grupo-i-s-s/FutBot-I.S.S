from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload
from datetime import datetime

from app.models.league_model import League, LeagueRegistration


def get_league_by_id(db: Session, league_id: int) -> Optional[League]:
    return (
        db.query(League)
        .options(joinedload(League.registrations))
        .filter(League.id == league_id)
        .with_for_update()
        .first()
    )

def create_league(db: Session, name: str, min_teams: int, max_teams:int, start_date:datetime, round_interval:str)->League:
    league = League(name=name, min_teams=min_teams, max_teams=max_teams, start_datetime=start_date, round_interval=round_interval)
    db.add(league)
    db.flush()
    return league

def get_registration(
    db: Session, league_id: int, club_id: int
) -> Optional[LeagueRegistration]:
    return (
        db.query(LeagueRegistration)
        .filter(
            LeagueRegistration.league_id == league_id,
            LeagueRegistration.club_id == club_id,
        )
        .first()
    )


def delete_registration(db: Session, registration: LeagueRegistration) -> None:
    db.delete(registration)


def get_all_available_leagues(db: Session, name: str | None = None) -> list[League]:
    registered_count = (
        select(func.count(LeagueRegistration.id))
        .where(LeagueRegistration.league_id == League.id)
        .correlate(League)
        .scalar_subquery()
    )
    query = (
        select(League)
        .options(selectinload(League.registrations))
        .where(League.status == "open", registered_count < League.max_teams)
        .order_by(League.id)
    )
    if name:
        query = query.where(League.name.icontains(name, autoescape=True))

    return list(db.scalars(query).all())