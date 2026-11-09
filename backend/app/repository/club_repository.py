from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.auth_model import Club
from app.models.league_model import League, LeagueRegistration
from app.models.matches_model import TEST_OPPONENT_CLUB_ID
from app.repository.stats_repository import get_club_profile_stats

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

def get_clubs( db: Session, *, exclude_user_id: int, name: str | None, page: int, page_size: int) -> tuple[list[Club], int]:
    query = select(Club).where(Club.user_id != exclude_user_id, Club.id != TEST_OPPONENT_CLUB_ID)

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

def get_club_profile_data(db: Session, club_id: int) -> dict | None:
    return get_club_profile_stats(db, club_id)


def get_by_name(
    db: Session, name: str, *, exclude_club_id: int | None = None, lock: bool = False,
) -> Club | None:
    normalized_name = func.lower(name.strip())
    if lock and db.get_bind().dialect.name == "postgresql":
        # Serializa las altas y los cambios que compiten por el mismo nombre.
        # No exige renombrar los clubes históricos que ya tienen colisiones.
        db.execute(select(func.pg_advisory_xact_lock(46002, func.hashtext(normalized_name))))

    query = select(Club).where(func.lower(Club.name) == normalized_name)
    if exclude_club_id is not None:
        query = query.where(Club.id != exclude_club_id)
    return db.scalar(query.limit(1))
