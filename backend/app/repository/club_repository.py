from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.auth_model import Club
from app.models.league_model import League, LeagueRegistration


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
