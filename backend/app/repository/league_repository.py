from typing import Optional
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from app.models.auth_model import Club

from app.models.league_model import League, LeagueRegistration


def get_league_by_id(db: Session, league_id: int) -> Optional[League]:
    return (
        db.query(League)
        .options(joinedload(League.registrations))
        .filter(League.id == league_id)
        .first()
    )


def create_league(
    db: Session,
    name: str,
    min_teams: int,
    max_teams: int,
    start_date: datetime,
    round_interval: str,
    *,
    creator_club_id: int,
    is_private: bool = False,
    password_hash: str | None = None
) -> League:
    league = League(
        name=name,
        min_teams=min_teams,
        max_teams=max_teams,
        start_datetime=start_date,
        round_interval=round_interval,
        creator_club_id=creator_club_id,
        is_private=is_private,
        password_hash=password_hash,
    )
    db.add(league)
    db.flush()
    return league


def get_clubs_by_ids(db: Session, club_ids: list[int]) -> list[Club]:
    if not club_ids:
        return []

    return db.query(Club).filter(Club.id.in_(club_ids)).all()
