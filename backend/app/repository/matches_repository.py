from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth_model import Club
from app.models.matches_model import Matches

def get_by_id(db: Session, match_id: int) -> Matches | None:
    return db.get(Matches, match_id)


def get_by_id_for_update(db: Session, match_id: int) -> Matches | None:
    return db.scalar(select(Matches).where(Matches.match_id == match_id).with_for_update())


def list_available(db: Session, club_id: int, now: datetime):
    return db.execute(
        select(Matches, Club.name)
        .join(Club, Club.id == Matches.creator_id)
        .where(
            Matches.visitor_id.is_(None),
            Matches.creator_id != club_id,
            Matches.init_date > now,
        )
        .order_by(Matches.init_date, Matches.match_id)
    ).all()
