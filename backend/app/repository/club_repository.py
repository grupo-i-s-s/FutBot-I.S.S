from sqlalchemy import select, desc
from sqlalchemy.orm import Session, selectinload

from app.models.auth_model import Club
from app.models.league_model import League, LeagueRegistration
from app.models.stats_model import Stats

def update_club(
        db: Session,
        club: Club,
        *,
        name: str,
        avatar: str,
        friendly_available: bool,
) -> Club:
    club.name = name
    club.avatar = avatar
    club.friendly_available = friendly_available
    db.flush()
    return club


def get_joined_leagues(db: Session, club_id: int) -> list[League]:
    query = (
        select(League)
        .where(
            League.registrations.any(
                LeagueRegistration.club_id == club_id
            )
        )
        .options(selectinload(League.registrations))
        .order_by(League.id)
    )

    return list(db.scalars(query).all())

def get_club_stats(db: Session, club_id: int) -> dict:
    query = ( select (Stats.points, Stats.played, Stats.wins, Stats.losses, Stats.draws, Stats.gF,Stats.gA)
             .where(Stats.club_id == club_id))
    return(db.execute(query).mappings().first()) 

def get_rankings(db: Session):
    query = (select( Club.name, Stats.points,
                    Stats.played, Stats.wins,
                    Stats.draws, Stats.losses,
                    Stats.gF,Stats.gA)

        .join(Club.stats)
        .order_by(Stats.points.desc(), Stats.gF.desc(), Stats.gA.desc())
        .limit(50))

    return (db.execute(query).mappings().all())
