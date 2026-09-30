from typing import Optional
from sqlalchemy.orm import Session, joinedload

from app.models.league_model import League, LeagueRegistration


def get_league_by_id(db: Session, league_id: int) -> Optional[League]:
    return (
        db.query(League)
        .options(joinedload(League.registrations))
        .filter(League.id == league_id)
        .with_for_update()
        .first()
    )


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
