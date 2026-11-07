from sqlalchemy import select, func
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

def get_clubs(
    db: Session,
    *,
    name: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Club], int]:
    query = select(Club)

    if name:
        query = query.where(
            Club.name.icontains(name, autoescape=True)
        )

    total = db.scalar(
        select(func.count()).select_from(query.subquery())
    )

    clubs = db.scalars(
        query
        .order_by(Club.name, Club.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return list(clubs), total